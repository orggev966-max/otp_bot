# ================================
# FILE: main.py
# FastAPI backend with Twilio calls + AI TTS + keypad
# ================================

import os
import uuid
import logging
from typing import Optional
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
import requests

# ----------------
# CONFIG
# ----------------
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")
BASE_URL = os.getenv("BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VOICE_DIR = "./voices"
os.makedirs(VOICE_DIR, exist_ok=True)

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("call-system")

app = FastAPI()
app.mount("/voices", StaticFiles(directory=VOICE_DIR), name="voices")

# ----------------
# MODELS
# ----------------
class CallRequest(BaseModel):
    to_number: str
    company_name: str
    user_name: str
    message: str
    outro: Optional[str] = None

BANNED_WORDS = {"password", "otp", "pin", "card", "cvv"}

def contains_banned(text: str) -> bool:
    return any(w in text.lower() for w in BANNED_WORDS)

# ----------------
# START CALL
# ----------------
@app.post("/start-call")
def start_call(payload: CallRequest):
    try:
        if contains_banned(payload.message):
            return {"error": "Message contains restricted words."}

        call_id = str(uuid.uuid4())
        call = client.calls.create(
            to=payload.to_number,
            from_=TWILIO_FROM_NUMBER,
            url=f"{BASE_URL}/voice?cid={call_id}&c={payload.company_name}&u={payload.user_name}",
            status_callback=f"{BASE_URL}/status?cid={call_id}",
            status_callback_event=["completed", "failed"],
            status_callback_method="POST",
        )
        return {"status": "initiated", "sid": call.sid, "call_id": call_id}
    except Exception as e:
        logger.exception("Start call failed")
        return {"error": str(e)}

# ----------------
# VOICE WEBHOOK
# ----------------
@app.post("/voice", response_class=PlainTextResponse)
async def voice(request: Request):
    try:
        q = request.query_params
        company = q.get("c", "Our Company")
        user = q.get("u", "Customer")

        vr = VoiceResponse()
        vr.say(f"Hello {user}. This is an automated call from {company}.", voice="Polly.Joanna")

        gather = Gather(
            input="dtmf",
            timeout=20,
            num_digits=1,
            action="/gather",
            action_on_empty_result=True,
        )
        gather.say(
            "This message is regarding a system update. "
            "Press 1 to confirm receipt. "
            "Press 2 to leave a voice message.",
            voice="Polly.Joanna",
        )
        vr.append(gather)
        vr.say("We did not receive a response. Please stay on the line.", voice="Polly.Joanna")
        return str(vr)
    except Exception:
        logger.exception("Voice webhook error")
        vr = VoiceResponse()
        vr.say("We are experiencing technical difficulties. Goodbye.")
        return str(vr)

# ----------------
# GATHER KEYPAD
# ----------------
@app.post("/gather", response_class=PlainTextResponse)
async def gather_handler(Digits: Optional[str] = Form(default=None)):
    vr = VoiceResponse()
    try:
        if Digits == "1":
            vr.say("Thank you. Your confirmation has been recorded.", voice="Polly.Joanna")
        elif Digits == "2":
            vr.say("Please leave your message after the beep.", voice="Polly.Joanna")
            vr.record(timeout=5, max_length=60, play_beep=True)
        else:
            vr.say("Invalid input. No further action is required.", voice="Polly.Joanna")
    except Exception:
        logger.exception("Gather handler error")
        vr.say("An error occurred. Goodbye.")

    vr.say("Thank you for your time. Goodbye.", voice="Polly.Joanna")
    vr.hangup()
    return str(vr)

# ----------------
# STATUS CALLBACK
# ----------------
@app.post("/status")
async def status_callback(request: Request):
    try:
        data = await request.form()
        logger.info(f"Call status: {dict(data)}")
    except Exception:
        logger.exception("Status callback error")
    return {"ok": True}

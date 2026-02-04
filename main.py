from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import psycopg2
import os
import openai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def get_db():
    return psycopg2.connect(DATABASE_URL)

# ---------- ROOT ----------

@app.get("/")
def root():
    return {"status": "SmartSpeak AI running"}

# ---------- START CALL ----------

@app.post("/start-call")
def start_call(phone: str):
    call = twilio_client.calls.create(
        to=phone,
        from_=TWILIO_PHONE,
        url="https://smartspeak-backend-orit.onrender.com/voice"
    )
    return {"sid": call.sid}

# ---------- TWILIO ENTRY ----------

@app.post("/voice")
async def voice():
    vr = VoiceResponse()

    vr.say("Hello. I am your Smart Speak AI coach. Tell me about yourself.")

    gather = Gather(
        input="speech",
        action="/process",
        method="POST",
        speech_timeout="auto"
    )

    vr.append(gather)
    return str(vr)

# ---------- PROCESS SPEECH ----------

@app.post("/process")
async def process(request: Request):

    form = await request.form()
    user_text = form.get("SpeechResult")

    vr = VoiceResponse()

    if not user_text:
        vr.say("Sorry, I did not hear you.")
        vr.redirect("/voice")
        return str(vr)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a friendly English speaking coach. Ask questions, correct grammar softly, encourage fluency."
            },
            {"role": "user", "content": user_text}
        ]
    )

    reply = completion.choices[0].message.content

    vr.say(reply)

    gather = Gather(
        input="speech",
        action="/process",
        method="POST",
        speech_timeout="auto"
    )

    vr.append(gather)

    return str(vr)

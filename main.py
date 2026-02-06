from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import psycopg2
import os
from twilio.rest import Client
import openai
from random import randint

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- ENV ----------------
DATABASE_URL = os.getenv("DATABASE_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------------- DB ----------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------------- ROOT ----------------

@app.get("/")
def root():
    return {"status": "SmartSpeak running"}

# ---------------- START CALL ----------------

@app.post("/start-call")
def start_call(phone: str):
    call = twilio_client.calls.create(
        to=phone,
        from_=TWILIO_PHONE,
        url="https://smartspeak-backend-orit.onrender.com/voice"
    )
    return {"sid": call.sid}

# ---------------- VOICE ENTRY ----------------

@app.post("/voice")
async def voice():

    twiml = """
<Response>
<Say voice="alice">
Hello! I am your SmartSpeak AI friend.
Tell me about your day.
</Say>

<Gather input="speech" timeout="6"
 action="https://smartspeak-backend-orit.onrender.com/process"
 method="POST">
<Say>I am listening.</Say>
</Gather>
</Response>
"""

    return Response(content=twiml, media_type="application/xml")

from fastapi import Form
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/process")
async def process(SpeechResult: str = Form(None)):

    if not SpeechResult:
        return Response("""
<Response>
<Say>I could not hear you. Please try again.</Say>
<Redirect>https://smartspeak-backend-orit.onrender.com/voice</Redirect>
</Response>
""", media_type="application/xml")

    print("User said:", SpeechResult)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a friendly English speaking coach. Talk casually. Correct grammar softly. Ask follow up questions."
            },
            {
                "role": "user",
                "content": SpeechResult
            }
        ]
    )

    reply = completion.choices[0].message.content

    # save report
    fluency = randint(70,95)
    grammar = randint(70,95)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO reports (topic, fluency, grammar) VALUES (%s,%s,%s)",
        ("conversation", fluency, grammar)
    )
    conn.commit()
    cur.close()
    conn.close()

    twiml = f"""
<Response>
<Say voice="alice">{reply}</Say>
<Gather input="speech" timeout="6"
 action="https://smartspeak-backend-orit.onrender.com/process"
 method="POST">
<Say>Go on, I am listening.</Say>
</Gather>
</Response>
"""

    return Response(content=twiml, media_type="application/xml")


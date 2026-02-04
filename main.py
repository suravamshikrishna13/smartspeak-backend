from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import psycopg2
import os
from twilio.rest import Client
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

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------------- DB ----------------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------------- MODELS ----------------

class ScheduleRequest(BaseModel):
    name: str
    topic: str
    datetime: str

# ---------------- ROOT ----------------

@app.get("/")
def root():
    return {"status": "SmartSpeak running"}

# ---------------- DASHBOARD ----------------

@app.get("/dashboard")
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.datetime, s.topic, r.fluency, r.grammar
        FROM schedules s
        LEFT JOIN reports r ON TRUE
        ORDER BY s.datetime DESC, r.created_at DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return {
            "upcoming_call": str(row[0]),
            "topic": row[1],
            "fluency": row[2] or 0,
            "grammar": row[3] or 0
        }

    return {}

# ---------------- REPORTS ----------------

@app.get("/reports")
def reports():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT created_at, topic, fluency, grammar FROM reports ORDER BY created_at DESC")
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [{"date": str(r[0]), "topic": r[1], "fluency": r[2], "grammar": r[3]} for r in rows]

# ---------------- SCHEDULE ----------------

@app.post("/schedule")
def schedule(req: ScheduleRequest):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO schedules (name, topic, datetime) VALUES (%s,%s,%s)",
        (req.name, req.topic, req.datetime)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "scheduled"}

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
        Hello! Welcome to Smart Speak.
        Please tell me about your day.
    </Say>

    <Gather input="speech" timeout="6" action="/process" method="POST">
        <Say voice="alice">I am listening.</Say>
    </Gather>

    <Say voice="alice">Goodbye.</Say>
</Response>
"""

    return Response(content=twiml, media_type="application/xml")

import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.post("/voice")
async def voice():

    twiml = """
<Response>
    <Say voice="alice">
        Hello! Welcome to Smart Speak.
        Please tell me about your day.
    </Say>

    <Gather input="speech" timeout="6"
        action="https://smartspeak-backend-orit.onrender.com/process"
        method="POST">
        <Say voice="alice">I am listening.</Say>
    </Gather>

    <Say voice="alice">Goodbye.</Say>
</Response>
"""

    return Response(content=twiml, media_type="application/xml")

    # ---- GPT CALL ----
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "You are a friendly English speaking coach. Talk casually like a friend. Correct grammar softly. Ask follow-up questions."
            },
            {
                "role": "user",
                "content": speech
            }
        ]
    )

    reply = completion.choices[0].message.content

    # Save basic report
    fluency = randint(70, 95)
    grammar = randint(70, 95)

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO reports (topic, fluency, grammar) VALUES (%s,%s,%s)",
        ("conversation", fluency, grammar)
    )

    conn.commit()
    cur.close()
    conn.close()

    # ---- Twilio reply + LOOP ----
    twiml = f"""
<Response>
    <Say voice="alice">{reply}</Say>
    <Gather input="speech" timeout="6" action="/process" method="POST">
        <Say voice="alice">Go on, I am listening.</Say>
    </Gather>
</Response>
"""

    return Response(content=twiml, media_type="application/xml")

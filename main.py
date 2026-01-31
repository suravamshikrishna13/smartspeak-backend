from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import psycopg2
import os
from random import randint
from twilio.rest import Client

# ---------------- APP ----------------

app = FastAPI()

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

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")

if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE:
    raise Exception("Twilio environment variables not set")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------------- DB ----------------

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------------- MODELS ----------------

class ScheduleRequest(BaseModel):
    name: str
    topic: str
    datetime: str

class AICallRequest(BaseModel):
    name: str
    topic: str
    phone: str

# ---------------- ROUTES ----------------

@app.get("/")
def root():
    return {"status": "SmartSpeak backend running"}

# DASHBOARD
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
            "fluency_score": row[2] or 0,
            "grammar_score": row[3] or 0
        }

    return {
        "upcoming_call": None,
        "topic": None,
        "fluency_score": 0,
        "grammar_score": 0
    }

# REPORTS
@app.get("/reports")
def reports():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT created_at, topic, fluency, grammar
        FROM reports
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "date": str(r[0]),
            "topic": r[1],
            "fluency": r[2],
            "grammar": r[3]
        }
        for r in rows
    ]

# SCHEDULE
@app.post("/schedule")
def schedule_call(req: ScheduleRequest):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO schedules (name, topic, datetime)
        VALUES (%s,%s,%s)
    """, (req.name, req.topic, req.datetime))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "scheduled"}

# GET SCHEDULED
@app.get("/scheduled")
def get_scheduled():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name, topic, datetime
        FROM schedules
        ORDER BY datetime DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "name": r[0],
            "topic": r[1],
            "datetime": str(r[2])
        }
        for r in rows
    ]

# ---------------- AI CALL (OUTBOUND) ----------------

@app.post("/start-call")
def start_call(req: AICallRequest):

    call = twilio_client.calls.create(
        to=req.phone,
        from_=TWILIO_PHONE,
        url="https://smartspeak-backend-orit.onrender.com/ai-call"
    )

    return {"status": "calling", "sid": call.sid}

# ---------------- TWILIO VOICE FLOW ----------------

@app.post("/ai-call", response_class=PlainTextResponse)
async def ai_call(request: Request):

    twiml = """
<Response>
    <Say voice="alice">
        Hello. Welcome to SmartSpeak.
        Please speak for one minute.
    </Say>

    <Record
        timeout="5"
        maxLength="60"
        action="/save-recording"
        method="POST"
    />

    <Say voice="alice">
        Thank you. Your session is complete.
    </Say>
</Response>
"""

    return twiml

# ---------------- SAVE RECORDING ----------------

@app.post("/save-recording")
async def save_recording(request: Request):
    form = await request.form()

    recording_url = form.get("RecordingUrl")

    fluency = randint(70, 95)
    grammar = randint(70, 95)

    conn = get_db_connection()
    cur = conn.cursor()

    # save recording
    cur.execute("""
        INSERT INTO recordings (audio_url)
        VALUES (%s)
    """, (recording_url,))

    # save report
    cur.execute("""
        INSERT INTO reports (topic, fluency, grammar)
        VALUES (%s,%s,%s)
    """, ("AI Practice", fluency, grammar))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "saved"}

from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import psycopg2
import os
from twilio.rest import Client
from random import randint
import requests

app = FastAPI()

BASE_URL = "http://localhost:8000"  # change when using ngrok

# ---------- CORS ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- ENV ----------
DATABASE_URL = os.getenv("DATABASE_URL")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ---------- DB ----------
def get_db():
    return psycopg2.connect(DATABASE_URL)

# ---------- OLLAMA ----------
def ask_ai(text):
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": f"""
You are a friendly English speaking coach.
Talk casually like a friend.
Correct grammar softly.
Ask follow up questions.

User: {text}
AI:
""",
                "stream": False
            },
            timeout=60
        )

        return r.json().get("response", "Sorry, I had trouble thinking.")

    except Exception:
        return "Sorry, I had trouble thinking. Please continue."

# ---------- ROOT ----------
@app.get("/")
def root():
    return {"status": "SmartSpeak running"}

# ---------- REPORTS ----------
@app.get("/reports")
def get_reports():
    try:
        conn = get_db()
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
                "grammar": r[3],
            }
            for r in rows
        ]

    except Exception as e:
        return {"error": str(e)}

# ---------- START CALL ----------
@app.post("/start-call")
def start_call(phone: str):
    call = twilio_client.calls.create(
        to=phone,
        from_=TWILIO_PHONE,
        url=f"{BASE_URL}/voice"
    )
    return {"sid": call.sid}

# ---------- VOICE ----------
@app.post("/voice")
async def voice():
    twiml = f"""
<Response>
<Say voice="alice">
Hello! I am your SmartSpeak AI friend.
Tell me about your day.
</Say>

<Gather input="speech" timeout="6"
        action="{BASE_URL}/process"
        method="POST">
<Say voice="alice">I am listening.</Say>
</Gather>
</Response>
"""
    return Response(twiml, media_type="application/xml")

# ---------- PROCESS ----------
@app.post("/process")
async def process(SpeechResult: str = Form(None)):

    if not SpeechResult:
        return Response(f"""
<Response>
<Say>I did not hear you.</Say>
<Redirect>{BASE_URL}/voice</Redirect>
</Response>
""", media_type="application/xml")

    reply = ask_ai(SpeechResult)

    fluency = randint(70, 95)
    grammar = randint(70, 95)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO reports(topic, fluency, grammar) VALUES(%s,%s,%s)",
            ("conversation", fluency, grammar)
        )
        conn.commit()
        cur.close()
        conn.close()
    except:
        pass

    twiml = f"""
<Response>
<Say voice="alice">{reply}</Say>

<Gather input="speech" timeout="6"
        action="{BASE_URL}/process"
        method="POST">
<Say voice="alice">Go on, I am listening.</Say>
</Gather>
</Response>
"""
    return Response(twiml, media_type="application/xml")
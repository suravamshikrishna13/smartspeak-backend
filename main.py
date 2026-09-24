from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

import psycopg2
import os
from twilio.rest import Client
from random import randint
import requests


# =========================================================
# APP
# =========================================================

app = FastAPI()


# =========================================================
# CONFIGURATION
# =========================================================

BASE_URL = "http://localhost:8000"

DATABASE_URL = os.getenv("DATABASE_URL")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# TWILIO CLIENT
# =========================================================

twilio_client = Client(
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN
)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    return psycopg2.connect(DATABASE_URL)


# =========================================================
# CURRENT AI - TEMPORARY VERSION
# =========================================================

def ask_ai(text):

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",

            json={
                "model": "mistral",

                "prompt": f"""
You are a friendly English speaking coach.

Talk casually like a friend.

Correct grammar softly.

Ask follow-up questions.

User:
{text}

AI:
""",

                "stream": False
            },

            timeout=60
        )

        return response.json().get(
            "response",
            "Sorry, I had trouble thinking."
        )

    except Exception:

        return (
            "Sorry, I had trouble thinking. "
            "Please continue."
        )


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():

    return {
        "status": "SmartSpeak running"
    }


# =========================================================
# REPORTS
# =========================================================

@app.get("/reports")
def get_reports():

    try:

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                created_at,
                topic,
                fluency,
                grammar
            FROM reports
            ORDER BY created_at DESC
            """
        )

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [
            {
                "date": str(row[0]),
                "topic": row[1],
                "fluency": row[2],
                "grammar": row[3],
            }
            for row in rows
        ]

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/dashboard")
def get_dashboard(
    user_id: Optional[str] = None
):

    try:

        conn = get_db()
        cur = conn.cursor()

        # -------------------------------------------------
        # REPORT STATISTICS
        # -------------------------------------------------

        cur.execute(
            """
            SELECT
                COUNT(*) AS total_sessions,
                AVG(fluency) AS avg_fluency,
                AVG(grammar) AS avg_grammar
            FROM reports
            """
        )

        row = cur.fetchone()

        total_sessions = row[0] or 0

        avg_fluency = (
            round(float(row[1]), 1)
            if row[1] is not None
            else 0
        )

        avg_grammar = (
            round(float(row[2]), 1)
            if row[2] is not None
            else 0
        )

        # -------------------------------------------------
        # UPCOMING CALL
        # -------------------------------------------------

        if user_id:

            cur.execute(
                """
                SELECT
                    id,
                    name,
                    topic,
                    scheduled_time
                FROM scheduled_calls
                WHERE
                    user_id = %s
                    AND scheduled_time >= NOW()
                    AND status = 'scheduled'
                ORDER BY scheduled_time ASC
                LIMIT 1
                """,
                (user_id,)
            )

        else:

            cur.execute(
                """
                SELECT
                    id,
                    name,
                    topic,
                    scheduled_time
                FROM scheduled_calls
                WHERE
                    scheduled_time >= NOW()
                    AND status = 'scheduled'
                ORDER BY scheduled_time ASC
                LIMIT 1
                """
            )

        upcoming_row = cur.fetchone()

        upcoming_call = None

        if upcoming_row:

            upcoming_call = {
                "id": str(upcoming_row[0]),
                "name": upcoming_row[1],
                "topic": upcoming_row[2],
                "scheduled_time": str(upcoming_row[3])
            }

        cur.close()
        conn.close()

        return {
            "upcoming_call": upcoming_call,
            "total_sessions": total_sessions,
            "fluency_score": avg_fluency,
            "grammar_score": avg_grammar
        }

    except Exception as e:

        return {
            "upcoming_call": None,
            "total_sessions": 0,
            "fluency_score": 0,
            "grammar_score": 0,
            "error": str(e)
        }


# =========================================================
# SCHEDULE REQUEST MODEL
# =========================================================

class ScheduleRequest(BaseModel):

    user_id: Optional[str] = None

    name: str

    phone: str

    topic: str

    scheduled_time: str

    duration: int = 10

    status: str = "scheduled"


# =========================================================
# SCHEDULE CALL
# =========================================================

@app.post("/schedule")
def schedule_call(data: ScheduleRequest):

    try:

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO scheduled_calls
            (
                user_id,
                name,
                phone,
                topic,
                scheduled_time,
                duration,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                id,
                user_id,
                name,
                phone,
                topic,
                scheduled_time,
                duration,
                status,
                created_at
            """,

            (
                data.user_id,
                data.name,
                data.phone,
                data.topic,
                data.scheduled_time,
                data.duration,
                data.status
            )
        )

        row = cur.fetchone()

        conn.commit()

        cur.close()
        conn.close()

        return {
            "success": True,
            "id": str(row[0]),
            "user_id": str(row[1]) if row[1] else None,
            "name": row[2],
            "phone": row[3],
            "topic": row[4],
            "scheduled_time": str(row[5]),
            "duration": row[6],
            "status": row[7],
            "created_at": str(row[8])
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# GET SCHEDULED CALLS
# =========================================================

@app.get("/scheduled-calls")
def get_scheduled_calls(
    user_id: Optional[str] = None
):

    try:

        conn = get_db()
        cur = conn.cursor()

        if user_id:

            cur.execute(
                """
                SELECT
                    id,
                    user_id,
                    name,
                    phone,
                    topic,
                    scheduled_time,
                    duration,
                    status,
                    created_at
                FROM scheduled_calls
                WHERE user_id = %s
                ORDER BY scheduled_time ASC
                """,
                (user_id,)
            )

        else:

            cur.execute(
                """
                SELECT
                    id,
                    user_id,
                    name,
                    phone,
                    topic,
                    scheduled_time,
                    duration,
                    status,
                    created_at
                FROM scheduled_calls
                ORDER BY scheduled_time ASC
                """
            )

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [
            {
                "id": str(row[0]),
                "user_id": str(row[1]) if row[1] else None,
                "name": row[2],
                "phone": row[3],
                "topic": row[4],
                "scheduled_time": str(row[5]),
                "duration": row[6],
                "status": row[7],
                "created_at": str(row[8])
            }
            for row in rows
        ]

    except Exception as e:

        return {
            "error": str(e)
        }


# =========================================================
# START CALL
# =========================================================

@app.post("/start-call")
def start_call(phone: str):

    try:

        call = twilio_client.calls.create(
            to=phone,
            from_=TWILIO_PHONE,
            url=f"{BASE_URL}/voice"
        )

        return {
            "success": True,
            "sid": call.sid
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# TWILIO VOICE
# =========================================================

@app.post("/voice")
async def voice():

    twiml = f"""
<Response>

    <Say voice="alice">
        Hello! I am your SmartSpeak AI friend.
        Tell me about your day.
    </Say>

    <Gather
        input="speech"
        timeout="6"
        action="{BASE_URL}/process"
        method="POST">

        <Say voice="alice">
            I am listening.
        </Say>

    </Gather>

</Response>
"""

    return Response(
        twiml,
        media_type="application/xml"
    )


# =========================================================
# PROCESS USER SPEECH
# =========================================================

@app.post("/process")
async def process(
    SpeechResult: str = Form(None)
):

    if not SpeechResult:

        return Response(
            f"""
<Response>

    <Say>
        I did not hear you.
    </Say>

    <Redirect>
        {BASE_URL}/voice
    </Redirect>

</Response>
""",
            media_type="application/xml"
        )

    # -----------------------------------------------------
    # CURRENT AI RESPONSE
    # -----------------------------------------------------

    reply = ask_ai(SpeechResult)

    # -----------------------------------------------------
    # TEMPORARY SCORES
    # -----------------------------------------------------

    fluency = randint(70, 95)

    grammar = randint(70, 95)

    # -----------------------------------------------------
    # SAVE REPORT
    # -----------------------------------------------------

    try:

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO reports
            (
                topic,
                fluency,
                grammar
            )
            VALUES
            (
                %s,
                %s,
                %s
            )
            """,

            (
                "conversation",
                fluency,
                grammar
            )
        )

        conn.commit()

        cur.close()
        conn.close()

    except Exception:

        pass

    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    twiml = f"""
<Response>

    <Say voice="alice">
        {reply}
    </Say>

    <Gather
        input="speech"
        timeout="6"
        action="{BASE_URL}/process"
        method="POST">

        <Say voice="alice">
            Go on, I am listening.
        </Say>

    </Gather>

</Response>
"""

    return Response(
        twiml,
        media_type="application/xml"
    )
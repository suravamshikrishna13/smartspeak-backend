from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.get("/")
def root():
    return {"message": "SmartSpeak Backend Running"}

@app.get("/dashboard")
def dashboard():
    return {
        "upcoming_call": "Tomorrow 10 AM",
        "fluency_score": 3.3,
        "grammar_score": 2.1
    }

@app.get("/reports")
def reports():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT created_at, topic, fluency, grammar FROM reports ORDER BY created_at DESC")
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
@app.get("/dashboard")
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    # Latest scheduled call
    cur.execute("""
        SELECT scheduled_time
        FROM scheduled_calls
        ORDER BY scheduled_time DESC
        LIMIT 1
    """)
    call = cur.fetchone()

    # Latest report
    cur.execute("""
        SELECT fluency, grammar
        FROM reports
        ORDER BY created_at DESC
        LIMIT 1
    """)
    report = cur.fetchone()

    cur.close()
    conn.close()

    return {
        "upcoming_call": str(call[0]) if call else "No calls",
        "fluency_score": report[0] if report else 0,
        "grammar_score": report[1] if report else 0
    }

# ---------------- SCHEDULE CALL -----------------

@app.post("/schedule")
def schedule_call(payload: dict):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO scheduled_calls (name, topic, scheduled_time)
        VALUES (%s, %s, %s)
        """,
        (
            payload["name"],
            payload["topic"],
            payload["scheduled_time"]
        )
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "scheduled"}

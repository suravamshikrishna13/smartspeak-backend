from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.environ.get("DATABASE_URL")


# ---------- DB CONNECTION ----------
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


# ---------- ROOT ----------
@app.get("/")
def root():
    return {"message": "SmartSpeak Backend Running"}


# ---------- DASHBOARD ----------
@app.get("/dashboard")
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT scheduled_time
        FROM schedules
        ORDER BY scheduled_time DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    upcoming = row[0] if row else "No upcoming call"

    cur.close()
    conn.close()

    return {
        "upcoming_call": str(upcoming),
        "fluency_score": 3.3,
        "grammar_score": 2.1
    }


# ---------- REPORTS ----------
@app.get("/reports")
def get_reports():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT date, topic, fluency, grammar
        FROM reports
        ORDER BY date DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    reports = []

    for r in rows:
        reports.append({
            "date": str(r[0]),
            "topic": r[1],
            "fluency": r[2],
            "grammar": r[3]
        })

    return reports


# ---------- SCHEDULE ----------
@app.post("/schedule")
def schedule_call(data: dict):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO schedules (topic, scheduled_time)
        VALUES (%s, %s)
    """, (data["topic"], data["time"]))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "scheduled"}

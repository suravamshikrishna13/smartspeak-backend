from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScheduleCall(BaseModel):
    topic: str
    time: str

@app.get("/")
def root():
    return {"message": "SmartSpeak Backend Running"}

# ---------------- DASHBOARD ----------------

@app.get("/dashboard")
def get_dashboard():
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT topic, scheduled_time, fluency_score, grammar_score
            FROM calls
            ORDER BY created_at DESC
            LIMIT 1
        """)).fetchone()

    if not row:
        return {
            "upcoming_call": "No calls",
            "fluency_score": 0,
            "grammar_score": 0
        }

    return {
        "upcoming_call": str(row.scheduled_time),
        "fluency_score": row.fluency_score or 0,
        "grammar_score": row.grammar_score or 0
    }

# ---------------- REPORTS ----------------

@app.get("/reports")
def get_reports():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT topic, fluency, grammar, created_at
            FROM reports
            ORDER BY created_at DESC
        """)).fetchall()

    reports = []

    for r in rows:
        reports.append({
            "topic": r.topic,
            "fluency": r.fluency,
            "grammar": r.grammar,
            "date": str(r.created_at)
        })

    return reports

# ---------------- SCHEDULE CALL ----------------

@app.post("/schedule-call")
def schedule_call(data: ScheduleCall):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO calls (topic, scheduled_time, status)
            VALUES (:topic, :time, 'scheduled')
        """), {
            "topic": data.topic,
            "time": data.time
        })
        conn.commit()

    return {"message": "Call scheduled successfully"}

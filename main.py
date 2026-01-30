from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DB ----------------
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not set")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------------- ROUTES ----------------

@app.get("/")
def root():
    return {"status": "SmartSpeak backend running"}

@app.get("/dashboard")
def dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT created_at, fluency, grammar
        FROM reports
        ORDER BY created_at DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row:
        return {
            "upcoming_call": str(row[0]),
            "fluency_score": row[1],
            "grammar_score": row[2],
        }

    return {
        "upcoming_call": None,
        "fluency_score": 0,
        "grammar_score": 0,
    }


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
            "grammar": r[3],
        }
        for r in rows
    ]
from fastapi import Body

@app.post("/schedule")
def schedule_call(data: dict = Body(...)):
    conn = get_db_connection()
    cur = conn.cursor()

    name = data.get("name")
    topic = data.get("topic")
    datetime = data.get("datetime")

    cur.execute(
        """
        INSERT INTO schedules (name, topic, datetime)
        VALUES (%s, %s, %s)
        """,
        (name, topic, datetime)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "scheduled"}

from pydantic import BaseModel

class ScheduleRequest(BaseModel):
    name: str
    topic: str
    datetime: str


@app.post("/schedule")
def schedule_call(req: ScheduleRequest):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO schedules (name, topic, datetime)
        VALUES (%s, %s, %s)
    """, (req.name, req.topic, req.datetime))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "scheduled"}

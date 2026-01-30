from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os

app = FastAPI()

# ✅ CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise Exception("DATABASE_URL environment variable not set")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

@app.get("/")
def root():
    return {"message": "SmartSpeak Backend Running"}

@app.get("/dashboard")
def dashboard():
    return {
        "upcoming_call": "Tomorrow 10 AM",
        "fluency_score": 82,
        "grammar_score": 85
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
            "grammar": r[3]
        }
        for r in rows
    ]

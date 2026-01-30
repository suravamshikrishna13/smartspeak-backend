from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

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
        "fluency_score": 3.3,
        "grammar_score": 2.1
    }

@app.get("/reports")
def reports():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT created_at, fluency_score, grammar_score
        FROM reports
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return [
        {
            "date": str(r[0]),
            "fluency": r[1],
            "grammar": r[2]
        }
        for r in rows
    ]

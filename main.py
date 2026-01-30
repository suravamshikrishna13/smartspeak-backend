from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

# Get DATABASE_URL from Render Environment
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise Exception("DATABASE_URL environment variable not set")

# ---------------- DB CONNECTION ----------------

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ---------------- ROOT ----------------

@app.get("/")
def root():
    return {"message": "SmartSpeak Backend Running"}

# ---------------- DASHBOARD ----------------

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

    if row is None:
        return {
            "upcoming_call": "Not scheduled",
            "fluency_score": 0,
            "grammar_score": 0
        }

    return {
        "upcoming_call": str(row[0]),
        "fluency_score": row[1],
        "grammar_score": row[2]
    }

# ---------------- REPORTS ----------------

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

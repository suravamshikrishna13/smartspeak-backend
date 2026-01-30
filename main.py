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
    try:
        print("Connecting DB...")
        conn = get_db_connection()
        print("Connected.")

        cur = conn.cursor()

        print("Running query...")
        cur.execute("SELECT created_at, topic, fluency, grammar FROM reports")

        rows = cur.fetchall()
        print("Rows:", rows)

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

    except Exception as e:
        return {"error": str(e)}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# -----------------------------
# CORS (VERY IMPORTANT)
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later restrict
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Models
# -----------------------------
class ScheduleCall(BaseModel):
    topic: str
    time: str

# -----------------------------
# Root
# -----------------------------
@app.get("/")
def root():
    return {"message": "SmartSpeak Backend Running"}

# -----------------------------
# DASHBOARD (OBVIOUS TEST VALUES)
# -----------------------------
@app.get("/dashboard")
def get_dashboard():
    return {
        "upcoming_call": "Tomorrow 10 AM",
        "fluency_score": 3.3,
        "grammar_score": 2.1
    }

@app.get("/reports")
def get_reports():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT topic, fluency, grammar, created_at
        FROM reports
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    cur.close()
    conn.close()

    reports = []

    for r in rows:
        reports.append({
            "topic": r[0],
            "fluency": r[1],
            "grammar": r[2],
            "date": r[3].strftime("%Y-%m-%d")
        })

    return reports

# -----------------------------
# SCHEDULE CALL
# -----------------------------
@app.post("/schedule-call")
def schedule_call(data: ScheduleCall):
    return {
        "status": "success",
        "message": "Call scheduled successfully",
        "data": data
    }


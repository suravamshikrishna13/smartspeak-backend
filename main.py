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

# -----------------------------
# REPORTS
# -----------------------------
@app.get("/reports")
def get_reports():
    return {
        "reports": [
            {
                "date": "2026-01-18",
                "topic": "Business Meeting",
                "fluency": 85,
                "grammar": 88
            },
            {
                "date": "2026-01-16",
                "topic": "Interview Practice",
                "fluency": 78,
                "grammar": 82
            }
        ]
    }

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


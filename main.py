
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "SmartSpeak backend running"}
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScheduleCall(BaseModel):
    phone: str
    topic: str
    datetime: str

@app.get("/dashboard")
def get_dashboard():
    return {
        "upcoming_call": "Today, 6:00 PM",
        "fluency_score": 7.5,
        "grammar_score": 6.8
    }
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


@app.post("/schedule-call")
def schedule_call(data: ScheduleCall):
    return {
        "status": "success",
        "message": "AI call scheduled successfully"
    }

from fastapi import FastAPI
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

@app.post("/schedule-call")
def schedule_call(data: ScheduleCall):
    return {
        "status": "success",
        "message": "AI call scheduled successfully"
    }

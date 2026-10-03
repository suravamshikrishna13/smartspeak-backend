from fastapi import FastAPI, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from google import genai
from dotenv import load_dotenv

import psycopg2
import os
import json
import asyncio
import html

from twilio.rest import Client
from twilio.request_validator import RequestValidator


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

BASE_URL = "https://smartspeak-backend-orit.onrender.com"

GEMINI_MODEL = "gemini-3.8-flash"


# ============================================================
# GEMINI CLIENT
# ============================================================

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

gemini_client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# TWILIO CLIENT
# ============================================================

twilio_client = None

if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(
        TWILIO_ACCOUNT_SID,
        TWILIO_AUTH_TOKEN
    )


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="SmartSpeak Backend",
    version="2.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

def get_db_connection():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is missing")

    return psycopg2.connect(DATABASE_URL)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "status": "SmartSpeak running",
        "version": "2.0",
        "voice_agent": "enabled"
    }


# ============================================================
# REPORTS
# ============================================================

@app.get("/reports")
def get_reports():
    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                id,
                name,
                topic,
                scheduled_time,
                created_at,
                status
            FROM scheduled_calls
            ORDER BY created_at DESC
        """)

        rows = cur.fetchall()

        reports = []

        for row in rows:
            reports.append({
                "id": str(row[0]),
                "name": row[1],
                "topic": row[2],
                "scheduled_time": str(row[3]),
                "created_at": str(row[4]),
                "status": row[5]
            })

        return reports

    except Exception as e:
        return {
            "error": str(e)
        }

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/dashboard")
def dashboard(user_id: Optional[str] = None):

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if user_id:
            cur.execute("""
                SELECT
                    id,
                    name,
                    topic,
                    scheduled_time,
                    created_at,
                    status
                FROM scheduled_calls
                WHERE user_id = %s
                ORDER BY scheduled_time ASC
            """, (user_id,))
        else:
            cur.execute("""
                SELECT
                    id,
                    name,
                    topic,
                    scheduled_time,
                    created_at,
                    status
                FROM scheduled_calls
                ORDER BY scheduled_time ASC
            """)

        rows = cur.fetchall()

        upcoming_calls = []

        for row in rows:
            upcoming_calls.append({
                "id": str(row[0]),
                "name": row[1],
                "topic": row[2],
                "scheduled_time": str(row[3]),
                "created_at": str(row[4]),
                "status": row[5]
            })

        return {
            "upcoming_calls": upcoming_calls
        }

    except Exception as e:
        return {
            "error": str(e)
        }

    finally:
        if cur:
            cur.close()

        if conn:
            conn.close()


# ============================================================
# SCHEDULE REQUEST
# ============================================================

class ScheduleRequest(BaseModel):
    user_id: Optional[str] = None
    name: str
    phone: str
    topic: str
    scheduled_time: str
    duration: int = 10


# ============================================================
# SCHEDULE CALL
# ============================================================

@app.post("/schedule")
def schedule_call(request: ScheduleRequest):

    conn = None
    cur = None

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO scheduled_calls
            (
                user_id,
                name,
                phone,
                topic,
                scheduled_time,
                duration,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, name, phone, topic,
                      scheduled_time, duration, status, created_at
        """, (
            request.user_id,
            request.name,
            request.phone,
            request.topic,
            request.scheduled_time,
            request.duration,
            "scheduled"
        ))

        row = cur.fetchone()

        conn.commit()

        return {
            "success": True,
            "id": str(row[0]),
            "user_id": row[1],
            "name": row[2],
            "phone": row[3],
            "topic": row[4],
            "scheduled_time": str(row[5]),
            "duration": row[6],
            "status": row[7],
            "created_at": str(row[8])
        }

    except Exception as e:

        if conn:
            conn.rollback()

        return {
            "success": False,
            "error": str(e)
        }

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()


# ============================================================
# GET SCHEDULED CALLS
# ============================================================

@app.get("/scheduled-calls")
def get_scheduled_calls(user_id: Optional[str] = None):

    conn = None
    cur = None

    try:

        conn = get_db_connection()
        cur = conn.cursor()

        if user_id:

            cur.execute("""
                SELECT
                    id,
                    user_id,
                    name,
                    phone,
                    topic,
                    scheduled_time,
                    duration,
                    status,
                    created_at
                FROM scheduled_calls
                WHERE user_id = %s
                ORDER BY scheduled_time ASC
            """, (user_id,))

        else:

            cur.execute("""
                SELECT
                    id,
                    user_id,
                    name,
                    phone,
                    topic,
                    scheduled_time,
                    duration,
                    status,
                    created_at
                FROM scheduled_calls
                ORDER BY scheduled_time ASC
            """)

        rows = cur.fetchall()

        calls = []

        for row in rows:

            calls.append({
                "id": str(row[0]),
                "user_id": str(row[1]) if row[1] else None,
                "name": row[2],
                "phone": row[3],
                "topic": row[4],
                "scheduled_time": str(row[5]),
                "duration": row[6],
                "status": row[7],
                "created_at": str(row[8])
            })

        return calls

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()


# ============================================================
# START OUTBOUND CALL
# ============================================================

@app.post("/start-call")
def start_call(
    phone: str = Form(...),
    name: str = Form("Learner"),
    topic: str = Form("General Conversation"),
    duration: int = Form(10)
):

    if not twilio_client:
        return {
            "success": False,
            "error": "Twilio is not configured"
        }

    try:

        # Escape values before putting them into the URL
        from urllib.parse import urlencode

        params = urlencode({
            "name": name,
            "topic": topic,
            "duration": duration
        })

        voice_url = f"{BASE_URL}/voice?{params}"

        call = twilio_client.calls.create(
            to=phone,
            from_=TWILIO_PHONE,
            url=voice_url,
            method="POST"
        )

        return {
            "success": True,
            "call_sid": call.sid,
            "phone": phone,
            "name": name,
            "topic": topic,
            "duration": duration
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# TWILIO VOICE WEBHOOK
# ============================================================

@app.post("/voice")
async def voice(
    name: str = "Learner",
    topic: str = "General Conversation",
    duration: int = 10
):

    # Escape values so they are safe inside XML attributes
    safe_name = html.escape(str(name), quote=True)
    safe_topic = html.escape(str(topic), quote=True)
    safe_duration = html.escape(str(duration), quote=True)

    twiml = f"""
<Response>
    <Connect>
        <ConversationRelay
            url="wss://smartspeak-backend-orit.onrender.com/ws"
            welcomeGreeting="Hi {safe_name}! Welcome to SmartSpeak. Today we'll practice speaking about {safe_topic}. Let's have a natural conversation. To start, tell me a little about yourself."
            language="en-IN"
            ttsProvider="Google"
            transcriptionProvider="Google">

            <Parameter name="name" value="{safe_name}" />
            <Parameter name="topic" value="{safe_topic}" />
            <Parameter name="duration" value="{safe_duration}" />

        </ConversationRelay>
    </Connect>
</Response>
"""

    return Response(
        content=twiml,
        media_type="application/xml"
    )


# ============================================================
# SMARTSPEAK AI SYSTEM PROMPT
# ============================================================

SMARTSPEAK_SYSTEM_PROMPT = """
You are SmartSpeak, a friendly AI English speaking practice partner.

Your job is to help the learner improve spoken English through a natural
conversation.

IMPORTANT CONVERSATION RULES:

1. Talk like a friendly human, not like a robot.

2. Do not repeatedly say:
   - "I am listening."
   - "Please continue."
   - "How can I help you?"
   - "Could you say that again?"
   unless the learner actually could not be understood.

3. Remember what the learner said earlier in the conversation.

4. Ask relevant follow-up questions based on the learner's previous answer.

5. Do not ask unrelated questions.

6. Keep your responses concise because this is a spoken conversation.

7. Usually respond in 1-3 sentences.

8. If the learner makes grammar mistakes, do not interrupt constantly.
   Keep the conversation flowing naturally.

9. When appropriate, naturally introduce better vocabulary or grammar.

10. If the learner asks you a question, answer it naturally before continuing.

11. Never give a long lecture during the conversation.

12. If the learner says they need to leave, politely close the conversation.

13. If the conversation is ending, say goodbye naturally.

14. The learner's selected topic should guide the conversation.

15. The selected duration controls the session length.

16. Near the end of the session, naturally say something like:
    "We have about a minute left, so let's finish with one final question."

17. After the final question and answer, close politely.

The goal is a natural two-person conversation that helps the learner
practice spoken English.
"""


# ============================================================
# GEMINI CONVERSATION
# ============================================================

async def generate_gemini_response(
    user_text: str,
    previous_interaction_id: Optional[str],
    name: str,
    topic: str,
    duration: int
):

    context_prompt = f"""
Learner name: {name}
Practice topic: {topic}
Selected session duration: {duration} minutes.

Learner's latest message:
{user_text}
"""

    kwargs = {
        "model": GEMINI_MODEL,
        "input": context_prompt,
        "system_instruction": SMARTSPEAK_SYSTEM_PROMPT
    }

    if previous_interaction_id:
        kwargs["previous_interaction_id"] = previous_interaction_id

    response = gemini_client.interactions.create(**kwargs)

    return response


# ============================================================
# TWILIO SIGNATURE VALIDATION
# ============================================================

def validate_twilio_websocket(websocket: WebSocket) -> bool:

    if not TWILIO_AUTH_TOKEN:
        print("WARNING: TWILIO_AUTH_TOKEN is missing")
        return False

    signature = websocket.headers.get("x-twilio-signature")

    if not signature:
        print("Twilio signature missing")
        return False

    validator = RequestValidator(TWILIO_AUTH_TOKEN)

    request_url = BASE_URL + websocket.url.path

    if websocket.url.query:
        request_url += "?" + websocket.url.query

    try:

        valid = validator.validate(
            request_url,
            {},
            signature
        )

        print(
            f"Twilio WebSocket signature validation: {valid}"
        )

        return valid

    except Exception as e:

        print(
            f"Twilio signature validation error: {e}"
        )

        return False


# ============================================================
# COMMON SMARTSPEAK WEBSOCKET HANDLER
# ============================================================

async def handle_smartspeak_websocket(
    websocket: WebSocket,
    validate_signature: bool = True
):

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    if validate_signature:

        if not validate_twilio_websocket(websocket):

            await websocket.close(
                code=1008,
                reason="Invalid Twilio signature"
            )

            return

    # --------------------------------------------------------
    # ACCEPT CONNECTION
    # --------------------------------------------------------

    await websocket.accept()

    print("SmartSpeak WebSocket connected")

    # --------------------------------------------------------
    # SESSION STATE
    # --------------------------------------------------------

    previous_interaction_id = None

    name = "Learner"
    topic = "General Conversation"
    duration = 10

    call_sid = None

    # --------------------------------------------------------
    # CONVERSATION LOOP
    # --------------------------------------------------------

    try:

        while True:

            raw_message = await websocket.receive_text()

            print(
                f"WebSocket received: {raw_message}"
            )

            try:

                message = json.loads(raw_message)

            except json.JSONDecodeError:

                print("Invalid JSON received")

                continue

            message_type = message.get("type")

            # =================================================
            # SETUP
            # =================================================

            if message_type == "setup":

                call_sid = message.get("callSid")

                custom_parameters = (
                    message.get("customParameters") or {}
                )

                name = custom_parameters.get(
                    "name",
                    "Learner"
                )

                topic = custom_parameters.get(
                    "topic",
                    "General Conversation"
                )

                try:

                    duration = int(
                        custom_parameters.get(
                            "duration",
                            10
                        )
                    )

                except Exception:

                    duration = 10

                print(
                    "SmartSpeak session setup:"
                )

                print(
                    f"  Name: {name}"
                )

                print(
                    f"  Topic: {topic}"
                )

                print(
                    f"  Duration: {duration}"
                )

                print(
                    f"  Call SID: {call_sid}"
                )

                # IMPORTANT:
                # Do NOT send a greeting here.
                #
                # ConversationRelay's welcomeGreeting
                # already speaks the greeting.

                continue

            # =================================================
            # USER SPEECH / PROMPT
            # =================================================

            if message_type == "prompt":

                user_text = (
                    message.get("voicePrompt")
                    or ""
                ).strip()

                if not user_text:

                    continue

                print(
                    f"Learner: {user_text}"
                )

                # ------------------------------------------------
                # Ask Gemini
                # ------------------------------------------------

                try:

                    gemini_response = (
                        await asyncio.to_thread(
                            generate_gemini_response,
                            user_text,
                            previous_interaction_id,
                            name,
                            topic,
                            duration
                        )
                    )

                except Exception as e:

                    print(
                        f"Gemini error: {e}"
                    )

                    error_message = {
                        "type": "text",
                        "token": (
                            "Sorry, I had a small problem there. "
                            "Could you say that again?"
                        ),
                        "last": True,
                        "interruptible": True,
                        "preemptible": True
                    }

                    await websocket.send_text(
                        json.dumps(error_message)
                    )

                    continue

                # ------------------------------------------------
                # Save Gemini interaction ID
                # ------------------------------------------------

                previous_interaction_id = getattr(
                    gemini_response,
                    "id",
                    None
                )

                # ------------------------------------------------
                # Get response text
                # ------------------------------------------------

                ai_text = getattr(
                    gemini_response,
                    "output_text",
                    None
                )

                if not ai_text:

                    ai_text = (
                        "That's interesting. "
                        "Tell me a little more about that."
                    )

                ai_text = ai_text.strip()

                print(
                    f"AI: {ai_text}"
                )

                # ------------------------------------------------
                # Send response to Twilio
                # ------------------------------------------------

                response_message = {
                    "type": "text",
                    "token": ai_text,
                    "last": True,
                    "interruptible": True,
                    "preemptible": True,
                    "lang": "en-IN"
                }

                await websocket.send_text(
                    json.dumps(response_message)
                )

                continue

            # =================================================
            # USER INTERRUPTED AI
            # =================================================

            if message_type == "interrupt":

                print(
                    "Learner interrupted the AI"
                )

                continue

            # =================================================
            # DTMF
            # =================================================

            if message_type == "dtmf":

                digit = message.get("digit")

                print(
                    f"DTMF received: {digit}"
                )

                continue

            # =================================================
            # TWILIO ERROR
            # =================================================

            if message_type == "error":

                print(
                    f"Twilio error: {message}"
                )

                continue

            # =================================================
            # UNKNOWN MESSAGE
            # =================================================

            print(
                f"Unknown WebSocket message type: {message_type}"
            )

    except WebSocketDisconnect:

        print(
            "SmartSpeak WebSocket disconnected"
        )

    except Exception as e:

        print(
            f"WebSocket error: {e}"
        )

        try:

            await websocket.close(
                code=1011,
                reason="Internal server error"
            )

        except Exception:
            pass


# ============================================================
# PRODUCTION TWILIO WEBSOCKET
# ============================================================

@app.websocket("/ws")
async def production_websocket(
    websocket: WebSocket
):

    print(
        "Incoming production Twilio WebSocket"
    )

    await handle_smartspeak_websocket(
        websocket,
        validate_signature=True
    )


# ============================================================
# LOCAL DEVELOPMENT WEBSOCKET
# ============================================================

@app.websocket("/ws-test")
async def local_test_websocket(
    websocket: WebSocket
):

    print(
        "Incoming LOCAL SmartSpeak WebSocket test"
    )

    await handle_smartspeak_websocket(
        websocket,
        validate_signature=False
    )


# ============================================================
# LEGACY PROCESS ENDPOINT
# ============================================================

@app.post("/process")
def process_audio(
    text: str = Form(...)
):

    # Temporary endpoint retained for compatibility.
    # Real evaluation will be implemented after
    # the live voice pipeline is completed.

    return {
        "success": True,
        "message": "Legacy process endpoint",
        "text": text
    }


# ============================================================
# GEMINI TEST
# ============================================================

@app.get("/test-gemini")
def test_gemini():

    try:

        response = gemini_client.interactions.create(
            model=GEMINI_MODEL,
            input="Say hello in one friendly sentence."
        )

        return {
            "success": True,
            "response": response.output_text
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
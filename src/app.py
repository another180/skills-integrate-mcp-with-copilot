"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

TEACHERS_FILE = current_dir / "teachers.json"
SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
PASSWORD_HASH_ITERATIONS = 600_000
sessions: dict[str, tuple[str, float]] = {}


class LoginRequest(BaseModel):
    username: str
    password: str


def load_teacher_accounts() -> dict[str, str]:
    """Load configured teacher password hashes."""
    try:
        with TEACHERS_FILE.open(encoding="utf-8") as teachers_file:
            data = json.load(teachers_file)
    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail="Teacher accounts are not configured",
        ) from error
    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=500,
            detail="Teacher account configuration is invalid",
        ) from error

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, list):
        raise HTTPException(
            status_code=500,
            detail="Teacher account configuration is invalid",
        )

    accounts = {}
    for teacher in teachers:
        if (
            not isinstance(teacher, dict)
            or not isinstance(teacher.get("username"), str)
            or not isinstance(teacher.get("password_hash"), str)
        ):
            raise HTTPException(
                status_code=500,
                detail="Teacher account configuration is invalid",
            )
        accounts[teacher["username"]] = teacher["password_hash"]
    return accounts


def verify_password(password: str, password_hash: str) -> bool:
    """Verify the PBKDF2-SHA256 password hash created by create_teacher.py."""
    try:
        algorithm, iterations_text, salt, expected_hash = password_hash.split("$")
        iterations = int(iterations_text)
        if (
            algorithm != "pbkdf2_sha256"
            or iterations < 100_000
            or iterations > 2_000_000
        ):
            return False
        salt_bytes = bytes.fromhex(salt)
        expected_bytes = bytes.fromhex(expected_hash)
    except (ValueError, TypeError):
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt_bytes, iterations
    )
    return hmac.compare_digest(actual_hash, expected_bytes)


def require_teacher(request: Request) -> str:
    """Return the signed-in teacher or reject a protected operation."""
    session_id = request.cookies.get(SESSION_COOKIE)
    session = sessions.get(session_id) if session_id else None
    if session is None:
        raise HTTPException(status_code=401, detail="Teacher login required")

    username, expires_at = session
    if expires_at <= time.monotonic():
        sessions.pop(session_id, None)
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


def set_session_cookie(response: Response, request: Request, session_id: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/session")
def get_teacher_session(request: Request):
    """Report whether the current browser has an active teacher session."""
    session_id = request.cookies.get(SESSION_COOKIE)
    session = sessions.get(session_id) if session_id else None
    if session is None:
        return {"authenticated": False}

    username, expires_at = session
    if expires_at <= time.monotonic():
        sessions.pop(session_id, None)
        return {"authenticated": False}
    return {"authenticated": True, "username": username}


@app.post("/auth/login")
def login_teacher(
    credentials: LoginRequest,
    request: Request,
    response: Response,
):
    """Authenticate a teacher and issue an opaque browser session cookie."""
    password_hash = load_teacher_accounts().get(credentials.username)
    if password_hash is None or not verify_password(
        credentials.password, password_hash
    ):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    now = time.monotonic()
    for session_id, (_, expires_at) in list(sessions.items()):
        if expires_at <= now:
            sessions.pop(session_id, None)

    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = (
        credentials.username,
        now + SESSION_TTL_SECONDS,
    )
    set_session_cookie(response, request, session_id)
    return {"message": "Logged in", "username": credentials.username}


@app.post("/auth/logout")
def logout_teacher(request: Request, response: Response):
    """End the current teacher session."""
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        sessions.pop(session_id, None)
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}

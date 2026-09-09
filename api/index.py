import os
import json
import hmac
import hashlib
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, Form, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Calculus Hub API")

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
PUBLIC_DIR = BASE_DIR / "public"

# --- Static Directory Mounts ---
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if (PUBLIC_DIR / "notes").exists():
    app.mount("/notes", StaticFiles(directory=str(PUBLIC_DIR / "notes")), name="notes")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# --- Storage & Security Configuration ---
TEXTBOOK_CDN_URL = "https://nua0qfkaopphwwba.public.blob.vercel-storage.com/thomas.pdf"
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "calc_adm_change_me_in_vercel")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "super-secret-calc-hub-session-salt-2026").encode()
AUTH_COOKIE_NAME = "calc_hub_session"

def sign_session() -> str:
    return hmac.new(SESSION_SECRET, b"admin_authorized", hashlib.sha256).hexdigest()

def is_authenticated(request: Request) -> bool:
    cookie_val = request.cookies.get(AUTH_COOKIE_NAME)
    if not cookie_val:
        return False
    return hmac.compare_digest(cookie_val, sign_session())

# --- Pydantic Data Models ---
class PhysicalNote(BaseModel):
    title: str
    url: str

class DeepDiveBlock(BaseModel):
    section: str
    content: str

class Pillar(BaseModel):
    name: str
    desc: str

class Lecture(BaseModel):
    id: int
    date: str
    topic: str
    week: int = Field(ge=1, le=16)
    core_points: List[str]
    pillars: Optional[List[Pillar]] = []
    reading: Optional[str] = ""
    practice_problems: Optional[str] = ""
    practice_difficulty: Optional[str] = "Medium"  # Easy | Medium | Hard
    common_mistakes: Optional[List[str]] = []
    physical_notes: Optional[List[PhysicalNote]] = []
    deep_dive: Optional[List[DeepDiveBlock]] = []

class NextTopic(BaseModel):
    date: str
    topic: str
    status: str = "Upcoming"
    thomas_ref: Optional[str] = ""
    thomas_label: Optional[str] = None
    thomas_url: Optional[str] = ""
    focus_note: Optional[str] = ""

class UpcomingRow(BaseModel):
    day: str
    topic: str
    thomas_ref: Optional[str] = ""
    thomas_label: Optional[str] = None
    thomas_url: Optional[str] = ""
    problems: Optional[str] = ""

class DailySchedule(BaseModel):
    next_topic: Optional[NextTopic] = None
    upcoming_schedule: List[UpcomingRow] = []

class StudyPlanPhase(BaseModel):
    phase: str
    target: str
    topics: List[str]
    milestone: str

# --- Safe File Operations ---
def load_json(filename: str):
    path = DATA_DIR / filename
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Error] Failed to read {filename}: {e}")
        return None

def write_json(filename: str, payload: dict | list):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8-sig") as f:
        json.dump(payload, f, indent=2)

# --- Legacy & Direct PDF Redirect ---
@app.get("/books/thomas.pdf")
def redirect_textbook():
    return RedirectResponse(url=TEXTBOOK_CDN_URL, status_code=status.HTTP_302_FOUND)

# --- Primary Page Handlers (Matches all Vercel path variations) ---
@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/", response_class=HTMLResponse)
@app.get("/api/index", response_class=HTMLResponse)
@app.get("/api/index.py", response_class=HTMLResponse)
@app.get("/index.py", response_class=HTMLResponse)
def read_root(request: Request):
    raw_lectures = load_json("lectures.json") or []
    raw_schedule = load_json("daily_schedule.json") or {}
    raw_plan = load_json("study_plan.json") or []

    lectures = []
    for item in raw_lectures:
        try:
            lectures.append(Lecture(**item).model_dump())
        except Exception as e:
            print(f"[Warning] Skipping invalid lecture: {e}")

    daily = None
    if raw_schedule:
        try:
            daily = DailySchedule(**raw_schedule).model_dump()
        except Exception as e:
            print(f"[Warning] Invalid daily_schedule schema: {e}")

    study_plan = []
    for item in raw_plan:
        try:
            study_plan.append(StudyPlanPhase(**item).model_dump())
        except Exception as e:
            print(f"[Warning] Skipping invalid study plan item: {e}")

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "lectures": list(reversed(lectures)),
            "study_plan": study_plan,
            "daily": daily,
            "is_admin": is_authenticated(request)
        }
    )

# --- Direct Navigation Fallbacks ---
@app.get("/admin", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def handle_direct_auth_navigation():
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

# --- Authentication Routes ---
@app.post("/login")
def login(request: Request, response: Response, secret: str = Form(...)):
    if hmac.compare_digest(secret.strip(), ADMIN_SECRET):
        token = sign_session()
        resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
        is_https = request.url.scheme == "https"
        resp.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            samesite="lax",
            secure=is_https,
            max_age=60 * 60 * 24 * 7  # 7 days
        )
        return resp
    return RedirectResponse(url="/?login_error=1", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(AUTH_COOKIE_NAME)
    return resp

# --- Admin Mutation Routes ---
@app.post("/update-schedule")
def update_schedule(
    request: Request,
    date: str = Form(...),
    topic: str = Form(...),
    thomas_ref: str = Form(...),
    thomas_url: str = Form(f"{TEXTBOOK_CDN_URL}#page=17"),
    focus_note: str = Form("")
):
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    data = load_json("daily_schedule.json") or {}
    validated_next = NextTopic(
        date=date.strip(),
        topic=topic.strip(),
        status="Upcoming",
        thomas_ref=thomas_ref.strip(),
        thomas_url=thomas_url.strip(),
        focus_note=focus_note.strip()
    )

    data["next_topic"] = validated_next.model_dump()
    validated_schedule = DailySchedule(**data)
    write_json("daily_schedule.json", validated_schedule.model_dump())

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/add-lecture")
def add_lecture(
    request: Request,
    date: str = Form(...),
    topic: str = Form(...),
    week: int = Form(...),
    core_points: str = Form(...),
    reading: str = Form(""),
    practice_problems: str = Form(""),
    practice_difficulty: str = Form("Medium"),
    common_mistakes: str = Form("")
):
    if not is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    lectures = load_json("lectures.json") or []
    parsed_points = [p.strip() for p in core_points.split("\n") if p.strip()]
    parsed_mistakes = [m.strip() for m in common_mistakes.split("\n") if m.strip()]

    new_lecture = Lecture(
        id=len(lectures) + 1,
        date=date.strip(),
        topic=topic.strip(),
        week=week,
        core_points=parsed_points,
        reading=reading.strip(),
        practice_problems=practice_problems.strip(),
        practice_difficulty=practice_difficulty.strip(),
        common_mistakes=parsed_mistakes,
        physical_notes=[],
        deep_dive=[]
    )

    lectures.append(new_lecture.model_dump())
    write_json("lectures.json", lectures)

    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

# --- Universal Catch-All (Prevents raw 404 JSON for page routes) ---
@app.get("/{full_path:path}", response_class=HTMLResponse)
def catch_all(request: Request, full_path: str):
    if any(full_path.lower().endswith(ext) for ext in [".jpeg", ".jpg", ".png", ".pdf", ".css", ".js", ".ico"]):
        raise HTTPException(status_code=404, detail="Asset not found")
    return read_root(request)

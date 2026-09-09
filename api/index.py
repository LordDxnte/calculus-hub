import json
import re
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
PUBLIC_DIR = BASE_DIR / "public"

# Mount static and public books so they work both locally and on Vercel
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

if (PUBLIC_DIR / "books").exists():
    app.mount("/books", StaticFiles(directory=str(PUBLIC_DIR / "books")), name="books")
elif PUBLIC_DIR.exists():
    app.mount("/books", StaticFiles(directory=str(PUBLIC_DIR)), name="books")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

ADMIN_SECRET = "secretpass"

def read_json(filename: str):
    path = DATA_DIR / filename
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return {}
    return {}

@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/index.py", response_class=HTMLResponse)
def read_root(request: Request, admin: Optional[str] = None):
    lectures = read_json("lectures.json")
    if not isinstance(lectures, list):
        lectures = []
    
    study_plan = read_json("study_plan.json")
    if not isinstance(study_plan, list):
        study_plan = []
        
    daily_schedule = read_json("daily_schedule.json")
    
    is_admin = bool(admin and admin.strip() == ADMIN_SECRET)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "lectures": list(reversed(lectures)),
            "study_plan": study_plan,
            "daily": daily_schedule,
            "is_admin": is_admin,
            "admin_query": admin if is_admin else ""
        }
    )

@app.get("/reader", response_class=HTMLResponse)
def pdf_reader(request: Request, page: int = 1):
    return templates.TemplateResponse(
        request=request,
        name="reader.html",
        context={
            "page": page,
            "pdf_url": "/books/thomas.pdf"
        }
    )

@app.post("/update-schedule")
def update_schedule(
    date: str = Form(...),
    topic: str = Form(...),
    thomas_ref: str = Form(...),
    focus_note: str = Form(""),
    swokowski_ref: str = Form(""),
    admin_secret: str = Form("")
):
    path = DATA_DIR / "daily_schedule.json"
    data = read_json("daily_schedule.json")
    if not isinstance(data, dict):
        data = {}
    
    # Automatically direct links to /reader?page=N so mobile jumps to the exact page
    current_topic = data.get("next_topic", {})
    page_match = re.search(r"p\.?\s*(\d+)", thomas_ref, re.IGNORECASE)
    if page_match:
        thomas_url = f"/reader?page={page_match.group(1)}"
    else:
        thomas_url = current_topic.get("thomas_url", "/reader?page=1")

    data["next_topic"] = {
        "date": date.strip(),
        "topic": topic.strip(),
        "status": "Upcoming",
        "thomas_ref": thomas_ref.strip(),
        "thomas_url": thomas_url,
        "focus_note": focus_note.strip()
    }
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    redirect_url = f"/?admin={admin_secret}" if admin_secret else "/"
    return RedirectResponse(url=redirect_url, status_code=303)

@app.post("/add-lecture")
def add_lecture(
    date: str = Form(...),
    topic: str = Form(...),
    week: int = Form(...),
    core_points: str = Form(...),
    reading: str = Form(""),
    practice_problems: str = Form(""),
    admin_secret: str = Form("")
):
    path = DATA_DIR / "lectures.json"
    lectures = read_json("lectures.json")
    if not isinstance(lectures, list):
        lectures = []
    
    new_entry = {
        "id": len(lectures) + 1,
        "date": date.strip(),
        "topic": topic.strip(),
        "week": week,
        "core_points": [p.strip() for p in core_points.split("\n") if p.strip()],
        "reading": reading.strip(),
        "practice_problems": practice_problems.strip()
    }
    
    lectures.append(new_entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(lectures, f, indent=2)
        
    redirect_url = f"/?admin={admin_secret}" if admin_secret else "/"
    return RedirectResponse(url=redirect_url, status_code=303)
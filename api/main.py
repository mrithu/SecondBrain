"""
api/main.py
FastAPI application — the HTTP interface to the Second Brain system.
"""
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db.connection import get_pool, close_pool
import db.queries as q
from agents.orchestrator import run_orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await get_pool()
        print("DB pool warmed up successfully")
    except Exception as e:
        print(f"DB warmup failed, will retry on first request: {e}")
    yield
    await close_pool()

app = FastAPI(
    title="Second Brain API",
    description="Multi-agent productivity system backed by AlloyDB",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/app", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── REQUEST / RESPONSE MODELS ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    plan: list
    agent_outputs: dict

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    due_date: Optional[str] = None
    project: Optional[str] = None
    tags: Optional[list[str]] = []

class EventCreate(BaseModel):
    title: str
    start_time: str
    end_time: str
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[list[str]] = []
    event_type: str = "meeting"

class NoteCreate(BaseModel):
    title: str
    content: str
    tags: Optional[list[str]] = []


# ─── CHAT ENDPOINT (main orchestrator) ────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    result = await run_orchestrator(req.message, session_id)
    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        plan=result["plan"],
        agent_outputs=result["agent_outputs"],
    )


# ─── TASKS ────────────────────────────────────────────────────────────────────

@app.get("/tasks")
async def list_tasks(status: str = None, priority: str = None, project: str = None):
    return await q.list_tasks(status=status, priority=priority, project=project)

@app.get("/tasks/overdue")
async def overdue_tasks():
    return await q.get_overdue_tasks()

@app.post("/tasks")
async def create_task(body: TaskCreate):
    from dateutil.parser import parse as parse_dt
    due = parse_dt(body.due_date) if body.due_date else None
    return await q.create_task(body.title, body.description, body.priority, due, body.project, body.tags)

@app.patch("/tasks/{task_id}")
async def update_task(task_id: str, body: dict):
    result = await q.update_task(task_id, **body)
    if not result:
        raise HTTPException(404, "Task not found")
    return result


# ─── EVENTS ───────────────────────────────────────────────────────────────────

@app.get("/events")
async def list_events(from_dt: str = None, to_dt: str = None):
    from dateutil.parser import parse as parse_dt
    return await q.list_events(
        from_dt=parse_dt(from_dt) if from_dt else None,
        to_dt=parse_dt(to_dt) if to_dt else None,
    )

@app.post("/events")
async def create_event(body: EventCreate):
    from dateutil.parser import parse as parse_dt
    return await q.create_event(
        body.title, parse_dt(body.start_time), parse_dt(body.end_time),
        body.description, body.location, body.attendees, body.event_type
    )

@app.get("/events/free-slots")
async def free_slots(date: str, duration_minutes: int = 60):
    from dateutil.parser import parse as parse_dt
    return await q.find_free_slots(parse_dt(date), duration_minutes)


# ─── NOTES ────────────────────────────────────────────────────────────────────

@app.get("/notes")
async def list_notes(limit: int = 20):
    return await q.list_notes(limit=limit)

@app.get("/notes/search")
async def search_notes(q_str: str):
    return await q.search_notes(q_str)

@app.post("/notes")
async def create_note(body: NoteCreate):
    return await q.create_note(body.title, body.content, body.tags)


# ─── MEMORY ───────────────────────────────────────────────────────────────────

@app.get("/memory/{session_id}")
async def get_memory(session_id: str, limit: int = 20):
    return await q.get_session_history(session_id, limit)


# ─── HEALTH ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    pool = await get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    try:
        await pool.fetchval("SELECT 1")
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"DB error: {str(e)}")
    return {"status": "ok", "db": "alloydb", "timestamp": datetime.utcnow().isoformat()}

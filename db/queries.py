"""
db/queries.py
All AlloyDB queries for tasks, events, notes, and agent memory.
"""
import json
from datetime import datetime
from typing import Any
from db.connection import get_pool


# ─── TASKS ────────────────────────────────────────────────────────────────────

async def create_task(title: str, description: str = None, priority: str = "medium",
                      due_date: datetime = None, project: str = None, tags: list = None) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO tasks (title, description, priority, due_date, project, tags)
           VALUES ($1,$2,$3,$4,$5,$6) RETURNING *""",
        title, description, priority, due_date, project, tags or []
    )
    return dict(row)

async def list_tasks(status: str = None, priority: str = None, project: str = None) -> list[dict]:
    pool = await get_pool()
    conditions, params = [], []
    if status:
        params.append(status); conditions.append(f"status = ${len(params)}")
    if priority:
        params.append(priority); conditions.append(f"priority = ${len(params)}")
    if project:
        params.append(f"%{project}%"); conditions.append(f"project ILIKE ${len(params)}")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await pool.fetch(
        f"SELECT * FROM tasks {where} ORDER BY due_date NULLS LAST, priority DESC, created_at DESC",
        *params
    )
    return [dict(r) for r in rows]

async def update_task(task_id: str, **kwargs) -> dict | None:
    pool = await get_pool()
    allowed = {"title","description","status","priority","due_date","project","tags"}
    updates = {k: v for k, v in kwargs.items() if k in allowed and v is not None}
    if not updates:
        return None
    set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
    row = await pool.fetchrow(
        f"UPDATE tasks SET {set_clause} WHERE id = $1 RETURNING *",
        task_id, *updates.values()
    )
    return dict(row) if row else None

async def get_overdue_tasks() -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT * FROM tasks WHERE due_date < NOW() AND status NOT IN ('done','cancelled') ORDER BY due_date"
    )
    return [dict(r) for r in rows]


# ─── EVENTS ───────────────────────────────────────────────────────────────────

async def create_event(title: str, start_time: datetime, end_time: datetime,
                       description: str = None, location: str = None,
                       attendees: list = None, event_type: str = "meeting",
                       linked_task: str = None) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO events (title, description, start_time, end_time, location, attendees, event_type, linked_task)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING *""",
        title, description, start_time, end_time, location, attendees or [], event_type,
        linked_task
    )
    return dict(row)

async def list_events(from_dt: datetime = None, to_dt: datetime = None) -> list[dict]:
    pool = await get_pool()
    from_dt = from_dt or datetime.utcnow()
    rows = await pool.fetch(
        "SELECT * FROM events WHERE start_time >= $1"
        + (" AND start_time <= $2" if to_dt else "")
        + " ORDER BY start_time",
        *([from_dt, to_dt] if to_dt else [from_dt])
    )
    return [dict(r) for r in rows]

async def check_conflicts(start_time: datetime, end_time: datetime) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM events
           WHERE tstzrange(start_time, end_time) && tstzrange($1, $2)
           ORDER BY start_time""",
        start_time, end_time
    )
    return [dict(r) for r in rows]

async def find_free_slots(date: datetime, duration_minutes: int = 60) -> list[dict]:
    """Return free blocks on a given day (9am-6pm window)."""
    pool = await get_pool()
    day_start = date.replace(hour=9, minute=0, second=0, microsecond=0)
    day_end   = date.replace(hour=18, minute=0, second=0, microsecond=0)
    rows = await pool.fetch(
        "SELECT start_time, end_time FROM events WHERE start_time::date = $1::date ORDER BY start_time",
        date
    )
    busy = [(r["start_time"], r["end_time"]) for r in rows]
    free, cursor = [], day_start
    for b_start, b_end in busy:
        if (b_start - cursor).total_seconds() >= duration_minutes * 60:
            free.append({"start": cursor.isoformat(), "end": b_start.isoformat()})
        cursor = max(cursor, b_end)
    if (day_end - cursor).total_seconds() >= duration_minutes * 60:
        free.append({"start": cursor.isoformat(), "end": day_end.isoformat()})
    return free


# ─── NOTES ────────────────────────────────────────────────────────────────────

async def create_note(title: str, content: str, tags: list = None,
                      linked_task: str = None, linked_event: str = None) -> dict:
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO notes (title, content, tags, linked_task, linked_event)
           VALUES ($1,$2,$3,$4,$5) RETURNING *""",
        title, content, tags or [], linked_task, linked_event
    )
    return dict(row)

async def search_notes(query: str) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM notes
           WHERE title ILIKE $1 OR content ILIKE $1 OR $2 = ANY(tags)
           ORDER BY created_at DESC""",
        f"%{query}%", query
    )
    return [dict(r) for r in rows]

async def list_notes(limit: int = 20) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch("SELECT * FROM notes ORDER BY created_at DESC LIMIT $1", limit)
    return [dict(r) for r in rows]


# ─── AGENT MEMORY ─────────────────────────────────────────────────────────────

async def save_message(session_id: str, role: str, content: str,
                       agent_name: str = None, metadata: dict = None):
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO agent_memory (session_id, role, content, agent_name, metadata)
           VALUES ($1,$2,$3,$4,$5)""",
        session_id, role, content, agent_name,
        json.dumps(metadata) if metadata else None
    )

async def get_session_history(session_id: str, limit: int = 20) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT role, content, agent_name, created_at FROM agent_memory
           WHERE session_id = $1 ORDER BY created_at DESC LIMIT $2""",
        session_id, limit
    )
    return [dict(r) for r in reversed(rows)]

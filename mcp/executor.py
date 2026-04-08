"""
mcp/executor.py
Executes tool calls returned by Claude and routes them to AlloyDB queries.
"""
import json
from datetime import datetime
from dateutil.parser import parse as parse_dt
import db.queries as q


def _parse_dt(s: str | None) -> datetime | None:
    return parse_dt(s) if s else None


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Called when Claude returns a tool_use block.
    Returns a JSON string to be sent back as tool_result.
    """
    try:
        result = await _dispatch(tool_name, tool_input)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def _dispatch(name: str, inp: dict):
    # ── TASK TOOLS ─────────────────────────────────────────────────────────────
    if name == "create_task":
        return await q.create_task(
            title=inp["title"],
            description=inp.get("description"),
            priority=inp.get("priority", "medium"),
            due_date=_parse_dt(inp.get("due_date")),
            project=inp.get("project"),
            tags=inp.get("tags", []),
        )

    if name == "list_tasks":
        return await q.list_tasks(
            status=inp.get("status"),
            priority=inp.get("priority"),
            project=inp.get("project"),
        )

    if name == "update_task":
        return await q.update_task(
            task_id=inp["task_id"],
            status=inp.get("status"),
            priority=inp.get("priority"),
            title=inp.get("title"),
            description=inp.get("description"),
            due_date=_parse_dt(inp.get("due_date")),
            project=inp.get("project"),
            tags=inp.get("tags"),
        )

    if name == "get_overdue_tasks":
        return await q.get_overdue_tasks()

    # ── CALENDAR TOOLS ─────────────────────────────────────────────────────────
    if name == "create_event":
        return await q.create_event(
            title=inp["title"],
            start_time=_parse_dt(inp["start_time"]),
            end_time=_parse_dt(inp["end_time"]),
            description=inp.get("description"),
            location=inp.get("location"),
            attendees=inp.get("attendees", []),
            event_type=inp.get("event_type", "meeting"),
            linked_task=inp.get("linked_task"),
        )

    if name == "list_events":
        return await q.list_events(
            from_dt=_parse_dt(inp.get("from_dt")),
            to_dt=_parse_dt(inp.get("to_dt")),
        )

    if name == "check_conflicts":
        return await q.check_conflicts(
            start_time=_parse_dt(inp["start_time"]),
            end_time=_parse_dt(inp["end_time"]),
        )

    if name == "find_free_slots":
        return await q.find_free_slots(
            date=_parse_dt(inp["date"]),
            duration_minutes=inp.get("duration_minutes", 60),
        )

    # ── NOTES TOOLS ────────────────────────────────────────────────────────────
    if name == "create_note":
        return await q.create_note(
            title=inp["title"],
            content=inp["content"],
            tags=inp.get("tags", []),
            linked_task=inp.get("linked_task"),
            linked_event=inp.get("linked_event"),
        )

    if name == "search_notes":
        return await q.search_notes(query=inp["query"])

    if name == "list_notes":
        return await q.list_notes(limit=inp.get("limit", 10))

    raise ValueError(f"Unknown tool: {name}")

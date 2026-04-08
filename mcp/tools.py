"""
mcp/tools.py
Gemini tool definitions for all four sub-agents.
Uses google.genai.types.Tool + FunctionDeclaration.
"""
from google.genai import types

def _tool(*declarations: types.FunctionDeclaration) -> types.Tool:
    return types.Tool(function_declarations=list(declarations))


# ─── TASK TOOLS ───────────────────────────────────────────────────────────────

TASK_TOOLS = _tool(
    types.FunctionDeclaration(
        name="create_task",
        description="Create a new task with title, description, priority, due date, and project.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title":       types.Schema(type=types.Type.STRING, description="Short task title"),
                "description": types.Schema(type=types.Type.STRING, description="Detailed description"),
                "priority":    types.Schema(type=types.Type.STRING, enum=["low","medium","high","urgent"]),
                "due_date":    types.Schema(type=types.Type.STRING, description="ISO 8601 datetime e.g. 2025-04-10T17:00:00Z"),
                "project":     types.Schema(type=types.Type.STRING, description="Project name"),
                "tags":        types.Schema(type=types.Type.ARRAY,  items=types.Schema(type=types.Type.STRING)),
            },
            required=["title"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_tasks",
        description="List tasks, optionally filtered by status, priority, or project.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "status":   types.Schema(type=types.Type.STRING, enum=["pending","in_progress","done","cancelled"]),
                "priority": types.Schema(type=types.Type.STRING, enum=["low","medium","high","urgent"]),
                "project":  types.Schema(type=types.Type.STRING),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="update_task",
        description="Update an existing task's status, priority, due date, or other fields.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "task_id":     types.Schema(type=types.Type.STRING, description="UUID of the task"),
                "status":      types.Schema(type=types.Type.STRING, enum=["pending","in_progress","done","cancelled"]),
                "priority":    types.Schema(type=types.Type.STRING, enum=["low","medium","high","urgent"]),
                "title":       types.Schema(type=types.Type.STRING),
                "description": types.Schema(type=types.Type.STRING),
                "due_date":    types.Schema(type=types.Type.STRING),
                "project":     types.Schema(type=types.Type.STRING),
                "tags":        types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
            },
            required=["task_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_overdue_tasks",
        description="Retrieve all tasks past their due date that are not completed.",
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    ),
)


# ─── CALENDAR TOOLS ───────────────────────────────────────────────────────────

CALENDAR_TOOLS = _tool(
    types.FunctionDeclaration(
        name="create_event",
        description="Schedule a calendar event with title, time, location, and attendees.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title":       types.Schema(type=types.Type.STRING),
                "start_time":  types.Schema(type=types.Type.STRING, description="ISO 8601 datetime"),
                "end_time":    types.Schema(type=types.Type.STRING, description="ISO 8601 datetime"),
                "description": types.Schema(type=types.Type.STRING),
                "location":    types.Schema(type=types.Type.STRING),
                "attendees":   types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "event_type":  types.Schema(type=types.Type.STRING, enum=["meeting","focus","personal","deadline","reminder"]),
                "linked_task": types.Schema(type=types.Type.STRING, description="UUID of a related task"),
            },
            required=["title","start_time","end_time"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_events",
        description="List upcoming calendar events between two dates.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "from_dt": types.Schema(type=types.Type.STRING, description="ISO 8601 start datetime"),
                "to_dt":   types.Schema(type=types.Type.STRING, description="ISO 8601 end datetime"),
            },
        ),
    ),
    types.FunctionDeclaration(
        name="check_conflicts",
        description="Check if a proposed time slot conflicts with existing calendar events.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "start_time": types.Schema(type=types.Type.STRING),
                "end_time":   types.Schema(type=types.Type.STRING),
            },
            required=["start_time","end_time"],
        ),
    ),
    types.FunctionDeclaration(
        name="find_free_slots",
        description="Find free time blocks on a given day for scheduling.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "date":             types.Schema(type=types.Type.STRING, description="ISO 8601 date e.g. 2025-04-10"),
                "duration_minutes": types.Schema(type=types.Type.INTEGER, description="Minimum block length in minutes"),
            },
            required=["date"],
        ),
    ),
)


# ─── NOTES TOOLS ──────────────────────────────────────────────────────────────

NOTES_TOOLS = _tool(
    types.FunctionDeclaration(
        name="create_note",
        description="Save a note with title, content, and optional tags or linked task/event.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "title":        types.Schema(type=types.Type.STRING),
                "content":      types.Schema(type=types.Type.STRING),
                "tags":         types.Schema(type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)),
                "linked_task":  types.Schema(type=types.Type.STRING, description="UUID of related task"),
                "linked_event": types.Schema(type=types.Type.STRING, description="UUID of related event"),
            },
            required=["title","content"],
        ),
    ),
    types.FunctionDeclaration(
        name="search_notes",
        description="Search notes by keyword in title, content, or tags.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING, description="Search keyword or phrase"),
            },
            required=["query"],
        ),
    ),
    types.FunctionDeclaration(
        name="list_notes",
        description="List the most recent notes.",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "limit": types.Schema(type=types.Type.INTEGER),
            },
        ),
    ),
)
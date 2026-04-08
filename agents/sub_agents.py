"""
agents/sub_agents.py
Four specialized sub-agents using the Google Gemini SDK.
Each agent runs a full agentic loop: sends message → executes function calls → loops until text.
"""
import json
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from mcp_tools.tools import TASK_TOOLS, CALENDAR_TOOLS, NOTES_TOOLS
from mcp_tools.executor import execute_tool

load_dotenv()

client = genai.Client(
    vertexai=True,
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location="global",
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


async def _agent_loop(system: str, tools: types.Tool, user_message: str) -> str:
    """
    Core agentic loop shared by all sub-agents.
    Gemini pattern:
      1. Start a chat with a system instruction and tool config.
      2. Send user message.
      3. If response contains function_call parts → execute them → send results back as function_response.
      4. Repeat until a plain text response is returned.
    """
    config = types.GenerateContentConfig(
        system_instruction=system,
        tools=[tools],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO
            )
        ),
    )

    chat = client.aio.chats.create(model=MODEL, config=config)
    response = await chat.send_message(user_message)

    while True:
        # Collect any function calls in this response
        function_calls = [
            part.function_call
            for part in response.candidates[0].content.parts
            if part.function_call is not None
        ]

        if not function_calls:
            # No tool calls — extract text and return
            for part in response.candidates[0].content.parts:
                if part.text:
                    return part.text
            return ""

        # Execute all function calls and build function_response parts
        response_parts = []
        for fc in function_calls:
            result_str = await execute_tool(fc.name, dict(fc.args))
            result_data = json.loads(result_str)
            response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result_data},
                )
            )

        # Send all results back in one turn
        response = await chat.send_message(response_parts)


# ─── TASK AGENT ───────────────────────────────────────────────────────────────

TASK_SYSTEM = """You are the Task Agent in a personal productivity system.
Your job: create, update, list, and manage tasks stored in AlloyDB.

Guidelines:
- Always confirm what you created/updated.
- Infer priority from context: "urgent deadline" → urgent, "someday" → low.
- When breaking a goal into tasks, create all sub-tasks in one pass.
- Return a clean, structured summary of what was done."""

async def run_task_agent(instruction: str) -> str:
    return await _agent_loop(TASK_SYSTEM, TASK_TOOLS, instruction)


# ─── CALENDAR AGENT ───────────────────────────────────────────────────────────

CALENDAR_SYSTEM = """You are the Calendar Agent in a personal productivity system.
Your job: schedule events, find free slots, and detect conflicts in AlloyDB.

Guidelines:
- Always check for conflicts before confirming a new event.
- Suggest alternatives if a slot is taken.
- For "focus blocks", use event_type=focus and keep attendees empty.
- Prefer mornings for deep work blocks (9am–12pm) and afternoons for meetings.
- Return a confirmation with the exact time block scheduled."""

async def run_calendar_agent(instruction: str) -> str:
    return await _agent_loop(CALENDAR_SYSTEM, CALENDAR_TOOLS, instruction)


# ─── NOTES AGENT ──────────────────────────────────────────────────────────────

NOTES_SYSTEM = """You are the Notes Agent in a personal productivity system.
Your job: store, search, and retrieve notes from AlloyDB.

Guidelines:
- Always extract meaningful tags from content (project name, topics, people).
- When searching, try both keyword search and tag search.
- If a note is related to a task or event, link it.
- Return the note title and a short confirmation."""

async def run_notes_agent(instruction: str) -> str:
    return await _agent_loop(NOTES_SYSTEM, NOTES_TOOLS, instruction)


# ─── RESEARCH AGENT ───────────────────────────────────────────────────────────

RESEARCH_SYSTEM = """You are the Research Agent in a personal productivity system.
Your job: answer questions, summarize topics, and provide structured information.

Guidelines:
- Be concise and structured. Use bullet points for lists.
- If asked to create a plan (e.g. learning plan), break it into weekly milestones.
- Always suggest saving the output as a note via the Notes Agent.
- State your confidence level when uncertain."""

async def run_research_agent(instruction: str) -> str:
    config = types.GenerateContentConfig(system_instruction=RESEARCH_SYSTEM)
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=instruction,
        config=config,
    )
    return response.text
"""
agents/orchestrator.py
Primary orchestrator agent — powered by Gemini.
Receives user messages → decides which sub-agents to invoke → coordinates results → returns unified response.
"""
import json
import re
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv
from agents.sub_agents import (
    run_task_agent,
    run_calendar_agent,
    run_notes_agent,
    run_research_agent,
)
from db import queries as q

load_dotenv()

client = genai.Client(
    vertexai=True,
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location="global",
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

ORCHESTRATOR_SYSTEM = """You are the Orchestrator of a personal productivity AI called Second Brain.
You coordinate four specialized sub-agents:
  - task_agent     → creates, updates, lists, completes tasks
  - calendar_agent → schedules events, finds free slots, checks conflicts
  - notes_agent    → saves, searches, retrieves notes
  - research_agent → answers questions, builds plans, summarizes topics

Your job:
1. Understand the user's intent (may involve multiple agents).
2. Plan which agents to call, and in what order.
3. Call each agent with a precise, self-contained instruction.
4. Synthesize all results into a single coherent response.

ROUTING RULES — follow these strictly:
- "deadline", "set up my week", "plan my week" → MUST use BOTH task_agent AND calendar_agent
- "schedule", "block time", "find time", "sync" → calendar_agent first, then notes_agent if prep needed
- "overdue", "pending tasks", "what tasks" → task_agent only
- "note", "save", "remember this" → notes_agent only
- "research", "explain", "what is", "learning plan" → research_agent, then notes_agent to save it
- NEVER use research_agent for scheduling or task creation requests

Response format — always return VALID JSON only (no markdown fences, no preamble):
{
  "plan": ["step 1 description", "step 2 description", ...],
  "agents": [
    {"agent": "task_agent|calendar_agent|notes_agent|research_agent", "instruction": "..."},
    ...
  ],
  "summary_prompt": "A short prompt for generating the final user-facing summary"
}

Rules:
- Use multiple agents when the request spans concerns (e.g. create tasks AND schedule them).
- Run agents in dependency order: research first if you need content to save as notes.
- Keep each instruction self-contained — agents have no shared context.
- The summary_prompt should tell how to combine all agent outputs into a friendly reply."""

SYNTHESIZER_SYSTEM = """You are the final synthesizer in a multi-agent productivity system called Second Brain.
Given the outputs from multiple specialized agents, write a single, friendly, well-organized response.
Be concise. Use bullet points for lists of tasks/events. Add a brief summary at the top.
Do NOT mention internal agent names or implementation details."""


async def run_orchestrator(user_message: str, session_id: str) -> dict:
    """
    Main entry point. Returns:
    {
        "response": str,      # final user-facing text
        "plan": list,         # steps the orchestrator planned
        "agent_outputs": dict # raw outputs per agent (for transparency)
    }
    """
    # Load conversation history for context
    history = await q.get_session_history(session_id, limit=10)
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in history
    ) if history else "No prior conversation."

    # Step 1: Orchestrator decides the plan
    planning_prompt = f"""Conversation history:
{history_text}

Current user message: {user_message}

Respond with your JSON plan."""

    plan_response = await client.aio.models.generate_content(
        model=MODEL,
        contents=planning_prompt,
        config=types.GenerateContentConfig(
            system_instruction=ORCHESTRATOR_SYSTEM,
            response_mime_type="application/json",   # Gemini JSON mode
        ),
    )

    raw_plan = plan_response.text.strip()

    # Strip markdown fences if Gemini wraps in them anyway
    json_str = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_plan, flags=re.MULTILINE).strip()
    try:
        plan = json.loads(json_str)
    except json.JSONDecodeError:
        plan = {
            "plan": ["Answer directly"],
            "agents": [{"agent": "research_agent", "instruction": user_message}],
            "summary_prompt": "Summarize the research agent's response in a friendly way."
        }

    # Step 2: Execute each agent
    agent_outputs = {}
    for step in plan.get("agents", []):
        agent_name = step["agent"]
        instruction = step["instruction"]

        if agent_name == "task_agent":
            output = await run_task_agent(instruction)
        elif agent_name == "calendar_agent":
            output = await run_calendar_agent(instruction)
        elif agent_name == "notes_agent":
            output = await run_notes_agent(instruction)
        elif agent_name == "research_agent":
            output = await run_research_agent(instruction)
        else:
            output = f"Unknown agent: {agent_name}"

        agent_outputs[agent_name] = output

    # Step 3: Synthesize all outputs into one user-facing response
    synthesis_input = f"""User asked: {user_message}

Summary prompt from orchestrator: {plan.get('summary_prompt', '')}

Agent outputs:
{json.dumps(agent_outputs, indent=2)}

Write the final response to the user."""

    synthesis_response = await client.aio.models.generate_content(
        model=MODEL,
        contents=synthesis_input,
        config=types.GenerateContentConfig(system_instruction=SYNTHESIZER_SYSTEM),
    )

    final_response = synthesis_response.text

    # Step 4: Persist to AlloyDB memory
    await q.save_message(session_id, "user", user_message, agent_name="orchestrator")
    await q.save_message(
        session_id, "assistant", final_response, agent_name="orchestrator",
        metadata={"plan": plan.get("plan", []), "agents_called": list(agent_outputs.keys())}
    )

    return {
        "response": final_response,
        "plan": plan.get("plan", []),
        "agent_outputs": agent_outputs,
    }
"""
scripts/generate_seed_data.py
Generates realistic synthetic data and loads it into AlloyDB.
No Kaggle account needed.

Usage: python scripts/generate_seed_data.py
"""
import asyncio
import random
from datetime import datetime, timedelta
from faker import Faker
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()
fake = Faker()

PROJECTS = ["Website Redesign", "Q2 Marketing", "API Migration", "Team OKRs", "Personal", "Learning"]
TASK_TEMPLATES = [
    ("Write {topic} documentation", "high"),
    ("Review {topic} pull request", "medium"),
    ("Schedule {topic} sync with team", "medium"),
    ("Research {topic} alternatives", "low"),
    ("Set up {topic} monitoring", "high"),
    ("Refactor {topic} module", "medium"),
    ("Prepare {topic} presentation", "urgent"),
    ("Update {topic} dependencies", "low"),
    ("Design {topic} architecture", "high"),
    ("Test {topic} edge cases", "medium"),
]
TOPICS = ["API", "database", "frontend", "authentication", "caching", "CI/CD",
          "analytics", "onboarding", "reporting", "billing", "search", "notifications"]
STATUSES = ["pending", "in_progress", "done", "cancelled"]
STATUS_WEIGHTS = [0.45, 0.25, 0.25, 0.05]

EVENT_TITLES = [
    "Team standup", "1:1 with manager", "Sprint planning", "Design review",
    "Customer demo", "Architecture discussion", "Retrospective", "All-hands",
    "Code review session", "Learning hour", "Deep work block", "Lunch & learn",
]
EVENT_TYPES = ["meeting", "focus", "personal", "deadline", "reminder"]

NOTE_TEMPLATES = [
    ("Meeting notes: {event}", "Discussed {topic}. Action items:\n- {item1}\n- {item2}\n- {item3}"),
    ("Research: {topic}", "Key findings on {topic}:\n1. {finding1}\n2. {finding2}\n\nNext steps: {next}"),
    ("Decision log: {topic}", "Context: {ctx}\nDecision: {decision}\nRationale: {rationale}"),
    ("Reference: {topic} setup", "Steps to set up {topic}:\n1. Install dependencies\n2. Configure {cfg}\n3. Run {cmd}"),
    ("Weekly plan", "Goals this week:\n- {g1}\n- {g2}\n- {g3}\n\nFocus: {focus}"),
]


async def seed():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "second_brain"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )
    print("Connected. Seeding data...")

    now = datetime.utcnow()

    # ── TASKS (200) ────────────────────────────────────────────────────────────
    task_ids = []
    for _ in range(200):
        template, priority = random.choice(TASK_TEMPLATES)
        topic = random.choice(TOPICS)
        title = template.format(topic=topic)
        project = random.choice(PROJECTS)
        status = random.choices(STATUSES, STATUS_WEIGHTS)[0]
        days_offset = random.randint(-7, 21)
        due_date = now + timedelta(days=days_offset) if random.random() > 0.2 else None
        tags = random.sample(TOPICS, k=random.randint(1, 3))

        row = await conn.fetchrow(
            """INSERT INTO tasks (title, description, status, priority, due_date, project, tags)
               VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id""",
            title, fake.sentence(nb_words=12), status, priority, due_date, project, tags
        )
        task_ids.append(str(row["id"]))

    print(f"  ✅ {len(task_ids)} tasks created")

    # ── EVENTS (80) ────────────────────────────────────────────────────────────
    event_ids = []
    for _ in range(80):
        title = random.choice(EVENT_TITLES)
        etype = random.choice(EVENT_TYPES)
        days_ahead = random.randint(-3, 14)
        hour = random.choice([9, 10, 11, 13, 14, 15, 16])
        start = now.replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        duration = random.choice([30, 60, 90, 120])
        end = start + timedelta(minutes=duration)
        attendees = [fake.email() for _ in range(random.randint(0, 4))]
        linked = random.choice(task_ids) if random.random() > 0.7 else None

        row = await conn.fetchrow(
            """INSERT INTO events (title, description, start_time, end_time, location, attendees, event_type, linked_task)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""",
            title, fake.sentence(), start, end,
            fake.city() if random.random() > 0.5 else "Google Meet",
            attendees, etype, linked
        )
        event_ids.append(str(row["id"]))

    print(f"  ✅ {len(event_ids)} events created")

    # ── NOTES (50) ─────────────────────────────────────────────────────────────
    for _ in range(50):
        title_tmpl, content_tmpl = random.choice(NOTE_TEMPLATES)
        topic = random.choice(TOPICS)
        title = title_tmpl.format(
            event=random.choice(EVENT_TITLES), topic=topic
        )
        content = content_tmpl.format(
            topic=topic,
            item1=fake.sentence(), item2=fake.sentence(), item3=fake.sentence(),
            finding1=fake.sentence(), finding2=fake.sentence(),
            next=fake.sentence(),
            ctx=fake.sentence(), decision=fake.sentence(), rationale=fake.sentence(),
            cfg=f"{topic}.config.yaml", cmd=f"./run_{topic}.sh",
            g1=fake.sentence(), g2=fake.sentence(), g3=fake.sentence(),
            focus=topic,
        )
        tags = random.sample(TOPICS, k=random.randint(1, 3))
        linked_task = random.choice(task_ids) if random.random() > 0.6 else None
        linked_event = random.choice(event_ids) if random.random() > 0.6 else None

        await conn.execute(
            """INSERT INTO notes (title, content, tags, linked_task, linked_event)
               VALUES ($1,$2,$3,$4,$5)""",
            title, content, tags, linked_task, linked_event
        )

    print("  ✅ 50 notes created")
    await conn.close()
    print("\n🎉 Seed complete! AlloyDB is ready.")


if __name__ == "__main__":
    asyncio.run(seed())

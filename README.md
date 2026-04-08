# Second Brain — Multi-Agent Productivity OS

A multi-agent AI system built with Claude that manages tasks, schedules, and notes using AlloyDB as the structured data store and MCP for tool integration.

demo: [video](https://drive.google.com/file/d/10Wp3IANVp--_2_0sOgR2alaaCcedDFQw/view?usp=drive_link)

deck: [slides](https://github.com/mrithu/SecondBrain/blob/main/SecondBrain_MrithulaKL.pdf)

deployment: [site](https://secondbrain-1024066444984.us-central1.run.app/)

---

## Architecture

```
User (HTTP API / Frontend)
        │
        ▼
Orchestrator Agent          ← primary agent, routes intent
   ├── Task Agent           ← creates/updates/completes tasks
   ├── Calendar Agent       ← schedules events, detects conflicts
   ├── Notes Agent          ← stores and retrieves notes
   └── Research Agent       ← web search + summarization
        │
        ▼
AlloyDB (PostgreSQL-compatible)
   ├── tasks
   ├── events
   ├── notes
   └── agent_memory
```

---

## Dataset

### Where to get it
Use the **LifeOS Sample Dataset** — a synthetic personal productivity dataset on Kaggle:

1. **Kaggle: Personal Task & Calendar Dataset**
   - URL: https://www.kaggle.com/datasets/crawford/personal-todo-dataset
   - Alt: Generate synthetic data using `scripts/generate_seed_data.py` (included)

2. **For a richer demo**, combine with:
   - Google Tasks export (Settings → Export in Google Tasks)
   - Google Calendar export (.ics file from calendar.google.com/r/settings/export)
   - Use `scripts/import_google_export.py` to load these

### Recommended: Use the included seed generator (no Kaggle account needed)
```bash
python scripts/generate_seed_data.py
```
This generates 200 realistic tasks, 80 calendar events, and 50 notes seeded into AlloyDB.

---

## Prerequisites

- Python 3.11+
- Google Cloud account with AlloyDB enabled
- Anthropic API key
- Node.js 18+ (for MCP servers)

---

## Setup Steps

### Step 1 — Clone and install dependencies
```bash
git clone <your-repo>
cd second-brain
pip install -r requirements.txt
npm install   # installs MCP server packages
```

### Step 2 — Provision AlloyDB
```bash
# Enable AlloyDB API
gcloud services enable alloydb.googleapis.com

# Create cluster (replace REGION and PASSWORD)
gcloud alloydb clusters create second-brain-cluster \
  --region=us-central1 \
  --password=YOUR_DB_PASSWORD

# Create primary instance
gcloud alloydb instances create second-brain-primary \
  --cluster=second-brain-cluster \
  --region=us-central1 \
  --instance-type=PRIMARY \
  --cpu-count=2

# Get connection IP
gcloud alloydb instances describe second-brain-primary \
  --cluster=second-brain-cluster \
  --region=us-central1 \
  --format="value(ipAddress)"
```

### Step 3 — Configure environment
```bash
cp .env.example .env
# Fill in your values (see .env.example)
```

### Step 4 — Initialize database schema
```bash
python db/init_schema.py
```

### Step 5 — Seed with sample data
```bash
python scripts/generate_seed_data.py
```

### Step 6 — Start the API
```bash
uvicorn api.main:app --reload --port 8000
```

### Step 7 — Open the frontend
```bash
open frontend/index.html
# or serve with: python -m http.server 3000 --directory frontend
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Send a message to the orchestrator |
| GET | `/tasks` | List all tasks |
| GET | `/events` | List upcoming events |
| GET | `/notes` | List notes |
| GET | `/memory` | View agent memory/context |

---

## Example Prompts

```
"I have a project deadline Friday, set up my week"
"Schedule a team sync tomorrow at 3pm and add prep notes"
"What tasks are overdue?"
"Create a note about the API design decisions we made"
"Find time for a 2-hour deep work block this week"
```

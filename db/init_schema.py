"""
db/init_schema.py
Run once to create all tables in AlloyDB.
Usage: python db/init_schema.py
"""
import asyncio
import asyncpg
from dotenv import load_dotenv
import os

load_dotenv()

SCHEMA = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','in_progress','done','cancelled')),
    priority    TEXT NOT NULL DEFAULT 'medium'
                    CHECK (priority IN ('low','medium','high','urgent')),
    due_date    TIMESTAMPTZ,
    project     TEXT,
    tags        TEXT[],
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Calendar events table
CREATE TABLE IF NOT EXISTS events (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title        TEXT NOT NULL,
    description  TEXT,
    start_time   TIMESTAMPTZ NOT NULL,
    end_time     TIMESTAMPTZ NOT NULL,
    location     TEXT,
    attendees    TEXT[],
    event_type   TEXT DEFAULT 'meeting'
                     CHECK (event_type IN ('meeting','focus','personal','deadline','reminder')),
    linked_task  UUID REFERENCES tasks(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Notes table
CREATE TABLE IF NOT EXISTS notes (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       TEXT NOT NULL,
    content     TEXT NOT NULL,
    tags        TEXT[],
    linked_task UUID REFERENCES tasks(id) ON DELETE SET NULL,
    linked_event UUID REFERENCES events(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Agent memory — persisted context across conversations
CREATE TABLE IF NOT EXISTS agent_memory (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content     TEXT NOT NULL,
    agent_name  TEXT,
    metadata    JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memory_session ON agent_memory(session_id, created_at);

-- Auto-update updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER events_updated_at
    BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE OR REPLACE TRIGGER notes_updated_at
    BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
"""

async def init():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "second_brain"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
    )
    print("Connected to AlloyDB. Creating schema...")
    await conn.execute(SCHEMA)
    await conn.close()
    print("✅ Schema created successfully.")

if __name__ == "__main__":
    asyncio.run(init())

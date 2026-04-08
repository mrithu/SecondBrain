import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

_pool = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "second_brain"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            # ssl="disable",          # proxy handles encryption, don't double-SSL
            ssl="require",           
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

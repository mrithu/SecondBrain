import asyncpg
import os
import asyncio

from dotenv import load_dotenv

load_dotenv()
_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        for attempt in range(5):
            try:
                _pool = await asyncpg.create_pool(
                host=os.getenv("DB_HOST", "127.0.0.1"),
                port=int(os.getenv("DB_PORT", 5432)),
                database=os.getenv("DB_NAME", "second_brain"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD"),
                ssl=False,
                statement_cache_size=0
                )
                break
            except ConnectionRefusedError:
                await asyncio.sleep(2)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

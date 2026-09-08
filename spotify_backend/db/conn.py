import asyncpg
from typing import Optional
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

class DatabasePool:
    def __init__(self):
        self._pool: asyncpg.pool | None = None

    async def connect(self):
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=DATABASE_URL)
            return True
        raise False

    async def disconnect(self):
        if self._pool:
            await self._pool.close()
            return True

    async def get_pool(self):
        if not self._pool:
            raise RuntimeError("DB pool is not initialized")
        
        return self._pool


async def main():
    db = DatabasePool()

    if not await db.connect():
        return "Error"
    
    return "OK"

manager = DatabasePool()


if __name__ ==  "__main__":
    print(asyncio.run(main()))
    

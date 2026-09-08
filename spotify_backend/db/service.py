from db.conn import manager
import asyncpg
import asyncio
from datetime import datetime

class Database_work:
    def __init__(self):
       pass
    async def update_tokens(self, a_token: str, r_token: str, expire_data: datetime) -> None:
        pool = await manager.get_pool()
        async with pool.acquire() as conn:
            status = await conn.execute(
                "INSERT INTO tokens (access, refresh, expires_at) VALUES ($1, $2, $3)",
                a_token, r_token, expire_data
            )
            print(status)

    async def get_token(self):
        pool = await manager.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM tokens ORDER BY expires_at DESC LIMIT 1")
            if row:
                return row

db_work = Database_work()


async def main():
    await manager.connect()
    work = Database_work()
    print(await work.update_tokens("hi", "hello"))


if __name__ == "__main__":
    asyncio.run(main())

from db.service import db_work
from datetime import timezone, datetime, timedelta
from db.conn import manager
from db.service import db_work
import asyncio
import http_client

async def get_latest_token():
    data = await db_work.get_token()
    access = data['access']
    r_token = data['refresh']
    exp_data = data['expires_at']

    now = datetime.now(timezone.utc) 

    if now >= exp_data:
        session = http_client.get_sesison()
        async with session.get("http://127.0.0.1:8000/get-token-by-refresh", params={"r_token": r_token}) as response:
            if response.status != 200:
                return access
            data = await response.json()
            new_refresh_token = data.get("refresh_token", r_token)
            expire_data = datetime.now(timezone.utc) + timedelta(seconds=data['expires_in'])
            await db_work.update_tokens(data['access_token'], new_refresh_token, expire_data)
            return data['access_token']

    return access

async def main():
    await manager.connect()
    await get_latest_token()

if __name__ == "__main__":
    asyncio.run(main())

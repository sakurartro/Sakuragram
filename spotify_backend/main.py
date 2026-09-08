from fastapi import FastAPI
import uvicorn
from spotify_auth import router
from contextlib import asynccontextmanager
import http_client
import aiohttp
from endpoints import router as router_endpoints
from db.conn import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.connect()
    http_client.state["session"] = aiohttp.ClientSession()

    yield

    await http_client.state["session"].close()
    await manager.disconnect()


app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(router_endpoints)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

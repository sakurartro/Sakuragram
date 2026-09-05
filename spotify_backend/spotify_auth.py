import os
import secrets
from urllib.parse import urlencode

import aiohttp
from dotenv import load_dotenv


load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv(
    "SPOTIFY_REDIRECT_URI",
    "http://127.0.0.1:8000/callback",
)
SCOPES = "user-read-currently-playing user-read-playback-state"

_access_token: str | None = None


def check_configuration() -> None:
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError(
            "Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in spotify_backend/.env"
        )


def create_login_url() -> tuple[str, str]:
    check_configuration()
    state = secrets.token_urlsafe(24)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "scope": SCOPES,
            "redirect_uri": REDIRECT_URI,
            "state": state,
        }
    )
    return f"https://accounts.spotify.com/authorize?{query}", state


async def exchange_code(session: aiohttp.ClientSession, code: str) -> None:
    global _access_token

    check_configuration()
    async with session.post(
        "https://accounts.spotify.com/api/token",
        auth=aiohttp.BasicAuth(CLIENT_ID, CLIENT_SECRET),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    ) as response:
        payload = await response.json()
        if response.status != 200:
            message = payload.get("error_description", payload.get("error", "OAuth error"))
            raise RuntimeError(str(message))

    _access_token = payload["access_token"]


def get_access_token() -> str | None:
    return _access_token

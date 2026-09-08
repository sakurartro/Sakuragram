import aiohttp
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
import webbrowser
from dotenv import load_dotenv
import os
import secrets
import hashlib
import base64
from urllib.parse import urlencode
from http_client import get_sesison
from db.service import db_work
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=7))

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

SCOPES = [
    "user-read-private",
    "user-read-email",
    "user-top-read",
    "user-read-playback-state",
    "user-read-currently-playing",
    "user-modify-playback-state",
]

REDIRECT = "http://127.0.0.1:8000/callback"

oauth_sessions: dict[str, str] = {}

router = APIRouter()

def generate_verifer() -> str:
    return secrets.token_urlsafe(64)

def generate_code_challenge(verifer: str) -> str:
    digest = hashlib.sha256(
        verifer.encode("ascii")
    ).digest()

    challenge = (
        base64.urlsafe_b64encode(digest)
        .decode("ascii")
        .rstrip("=")
    )
    return challenge


@router.get("/login")
async def spotify_login():
    state = secrets.token_urlsafe(32)
    verifer = generate_verifer()
    challenge = generate_code_challenge(verifer)

    oauth_sessions[state] = verifer

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT,
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": challenge
    }

    spotify_url = (
        "https://accounts.spotify.com/authorize?"
        + urlencode(params)
    )
    return RedirectResponse(spotify_url)


@router.get("/callback")
async def recieve_callback(session: aiohttp.ClientSession = Depends(get_sesison), code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        raise HTTPException(
            status_code=400,
            detail=error
        )
    if not code:
        raise HTTPException(
            status_code=400,
            detail=error
        )

    if not state:
        raise HTTPException(
            status_code=400,
            detail=error
        )
    
    verifer = oauth_sessions.pop(state, None)

    if verifer is None:
        raise HTTPException(
            status_code=400,
            detail=error
        )
    async with session.post(
        "https://accounts.spotify.com/api/token",
        data = {
            "client_id": CLIENT_ID,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT,
            "code_verifier": verifer
        },
    ) as response:
        data = await response.json()
        if response.status != 200:
            raise HTTPException(
                status_code=400,
                detail=data
            )
    a_token = data['access_token']
    r_token = data['refresh_token']
    expire_data = datetime.now(TZ) + timedelta(seconds=data['expires_in'])
    await db_work.update_tokens(a_token=a_token, r_token=r_token, expire_data=expire_data)


@router.get("/get-token-by-refresh")
async def get_token_by_refresh(r_token: str, session: aiohttp.ClientSession = Depends(get_sesison)):
    params={
        "grant_type": "refresh_token",
        "refresh_token": r_token,
    }
    auth=aiohttp.BasicAuth(
        SPOTIFY_CLIENT_ID,
        SPOTIFY_CLIENT_SECRET,
    )
    async with session.post("https://accounts.spotify.com/api/token", auth=auth, data=params) as response:
        data = await response.json()
        if response.status != 200:
            raise HTTPException(status_code=response.status, detail=data)

        return data

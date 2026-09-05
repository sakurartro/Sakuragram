import secrets

import aiohttp
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from spotify_auth import create_login_url, exchange_code, get_access_token
from spotify_current_data_requsts import get_current_spotify_data

router = APIRouter()


@router.get("/login")
async def login():
    try:
        login_url, state = create_login_url()
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    response = RedirectResponse(login_url)
    response.set_cookie(
        "spotify_oauth_state",
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/callback", response_class=HTMLResponse)
async def callback(request: Request, code: str | None = None, state: str | None = None):
    expected_state = request.cookies.get("spotify_oauth_state")
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(status_code=400, detail="Invalid Spotify OAuth callback")

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            await exchange_code(session, code)
        except RuntimeError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return "Spotify connected. You can close this page and open /api/current."


@router.get("/api/current")
async def get_current_data():
    access_token = get_access_token()
    if not access_token:
        raise HTTPException(status_code=401, detail="Open /login and connect Spotify first")

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        return await get_current_spotify_data(session, access_token)

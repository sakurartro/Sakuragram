from fastapi import APIRouter, Depends, HTTPException
from http_client import get_sesison
import aiohttp
from models import CurrentData
from access_token import get_latest_token

router = APIRouter()

@router.get("/spotify/current", response_model=CurrentData)
async def get_current_song(session: aiohttp.ClientSession = Depends(get_sesison)):
    headers = {"Authorization": f"Bearer {await get_latest_token()}"}
    async with session.get("https://api.spotify.com/v1/me/player", headers=headers) as response:
        if response.status == 204:
            return CurrentData(playing=False, author="", song_name="")
        if response.status != 200:
            raise HTTPException(
                status_code=response.status,
                detail="Spotify playback state request failed",
            )

        data = await response.json()
        item = data.get("item") or {}
        artists = item.get("artists") or []
        return CurrentData(
            playing=bool(data.get("is_playing", False)),
            author=", ".join(
                artist.get("name", "")
                for artist in artists
                if artist.get("name")
            ),
            song_name=item.get("name", ""),
        )


@router.get("/spotify/pause")
async def pause_play(session: aiohttp.ClientSession = Depends(get_sesison)):
    headers = {"Authorization": f"Bearer {await get_latest_token()}"}
    async with session.put("https://api.spotify.com/v1/me/player/pause", headers=headers) as response:
        if response.status != 200:
            return response.status
        return "OK"

@router.get("/spotify/play")
async def resume_play(session: aiohttp.ClientSession = Depends(get_sesison)):
    headers = {"Authorization": f"Bearer {await get_latest_token()}"}
    async with session.put("https://api.spotify.com/v1/me/player/play", headers=headers) as response:
        if response.status != 200:
            return response.status
        return "OK"

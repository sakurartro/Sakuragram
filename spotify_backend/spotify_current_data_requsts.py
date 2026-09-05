import aiohttp
from fastapi import HTTPException


async def get_current_spotify_data(
    session: aiohttp.ClientSession,
    access_token: str,
):
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "User-Agent": "SakuraGram/1.0.0"
    }
    async with session.get(url, headers=headers) as response:
        if response.status == 204:
            return {"is_playing": False, "item": None}

        payload = await response.json()
        if response.status != 200:
            error = payload.get("error", {})
            message = error.get("message", "Spotify API request failed")
            raise HTTPException(status_code=response.status, detail=message)

        return payload

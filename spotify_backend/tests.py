import aiohttp


async def test_spotify():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://127.0.0.1:8000/api/current") as response:
                return await response.text()
        except Exception as e:
            return e
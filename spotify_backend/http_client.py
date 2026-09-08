import aiohttp

state = {"session": None}

def get_sesison() -> aiohttp.ClientSession:
    return state["session"]
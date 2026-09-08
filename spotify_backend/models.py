from pydantic import BaseModel

class CurrentData(BaseModel):
    playing: bool
    author: str
    song_name: str
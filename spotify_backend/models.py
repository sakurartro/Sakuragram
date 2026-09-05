from pydantic import BaseModel

class CurrentData(BaseModel):
    track: str
    singer: str
    timecode: str
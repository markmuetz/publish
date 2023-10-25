from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, validator


# Schema for publish settings.
class File(BaseModel):
    source: Path
    target: Path

    class Config:
        extra = 'forbid'


class CommonSettings(BaseModel):
    ensure_make: Optional[bool] = None
    user_prompt: Optional[bool] = None
    git_allow_uncommitted: Optional[bool] = None
    overwrite: Optional[bool] = None
    version: Optional[Literal['git_describe', 'user_supplied']] = None


class Destination(CommonSettings):
    files: List[File]

    @validator('files', pre=True)
    def check_files(cls, v):
        assert v, 'There must be at least one file to copy'
        return v

    class Config:
        extra = 'forbid'


class Archive(BaseModel):
    branch: str
    format: str
    prefix: str
    target: Path

    class Config:
        extra = 'forbid'


class PublishSettings(CommonSettings):
    destinations: Dict[str, Destination]
    archive: Optional[Archive] = None

    @validator('destinations', pre=True)
    def check_destinations(cls, v):
        assert v, 'There must be at least one destination'
        return v

    class Config:
        extra = 'forbid'

from pathlib import Path
from typing import List, Optional, Literal

from pydantic import BaseModel


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
    destination: str
    files: List[File]

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
    destinations: List[Destination]
    archive: Optional[Archive] = None

    class Config:
        extra = 'forbid'

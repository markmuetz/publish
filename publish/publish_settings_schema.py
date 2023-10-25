from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, validator


class BaseSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')


# Schema for publish settings.
class File(BaseSettings):
    source: Path
    target: Path


class CommonSettings(BaseSettings):
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


class Archive(BaseSettings):
    branch: str
    format: str
    prefix: str
    target: Path


class PublishSettings(CommonSettings):
    destinations: Dict[str, Destination]
    archive: Optional[Archive] = None

    @validator('destinations', pre=True)
    def check_destinations(cls, v):
        assert v, 'There must be at least one destination'
        return v

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


SHA256_PATTERN = re.compile(r'^[a-f0-9]{64}$')
FOLDER_PATTERN = re.compile(r'^/')


class FileBase(BaseModel):
    file_id: UUID
    owner_id: UUID
    bucket: str
    folder: str = "/"
    file_key: str
    original_name: str
    current_name: str
    content_type: str | None = Field(default=None, max_length=255)
    size_bytes: int
    sha256_hex: str = Field(min_length=64, max_length=64)

    @field_validator("size_bytes")
    @classmethod
    def size_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("size_bytes must be positive")
        return v

    @field_validator("sha256_hex")
    @classmethod
    def sha256_must_be_valid_hex(cls, v: str) -> str:
        if not SHA256_PATTERN.match(v):
            raise ValueError("sha256_hex must be exactly 64 lowercase hex characters")
        return v

    @field_validator("folder")
    @classmethod
    def folder_must_start_with_slash(cls, v: str) -> str:
        if not FOLDER_PATTERN.match(v):
            raise ValueError("folder must start with '/'")
        return v

    @model_validator(mode="after")
    def names_must_not_be_blank(self) -> "FileBase":
        if not self.original_name.strip():
            raise ValueError("original_name must not be blank")
        if not self.current_name.strip():
            raise ValueError("current_name must not be blank")
        return self


class FileCreate(FileBase):
    """Payload for inserting a new file row. file_id and timestamps are DB-generated."""
    pass


class FileUpdate(BaseModel):
    """Payload for updating mutable file fields. All fields optional."""
    current_name: str | None = None
    content_type: str | None = Field(default=None, max_length=255)
    folder: str | None = None

    @field_validator("current_name")
    @classmethod
    def current_name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("current_name must not be blank")
        return v

    @field_validator("folder")
    @classmethod
    def folder_must_start_with_slash(cls, v: str | None) -> str | None:
        if v is not None and not FOLDER_PATTERN.match(v):
            raise ValueError("folder must start with '/'")
        return v


class FileRecord(FileBase):
    """Full DB row returned from SELECT queries."""
    file_id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
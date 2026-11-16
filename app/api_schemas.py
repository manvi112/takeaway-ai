from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas import MeetingResult


class JobStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class MeetingCreate(BaseModel):
    transcript: str = Field(min_length=1, max_length=60000)
    meeting_date: date
    title: str | None = None


class MeetingCreated(BaseModel):
    id: str
    status: JobStatus


class MeetingOut(BaseModel):
    id: str
    status: JobStatus
    result: MeetingResult | None = None
    error: str | None = None

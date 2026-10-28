from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

_NO_OWNER = {"", "unknown", "unassigned", "none", "n/a", "na", "tbd", "null", "someone"}


class ActionItem(BaseModel):
    # Unexpected keys mean the model drifted from the schema: fail loudly and retry.
    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1, description="What needs to be done, one sentence.")
    owner: str | None = Field(
        default=None,
        description="Person named in the transcript as responsible. null if nobody was named.",
    )
    due_date: date | None = Field(
        default=None,
        strict=True,
        description="Deadline as an ISO date (YYYY-MM-DD). null if no deadline was stated.",
    )
    confidence: float = Field(
        ge=0, le=1, description="0 to 1: how sure you are this is a real commitment."
    )
    evidence: str = Field(
        min_length=1,
        description="Short quote copied word for word from the transcript that supports this item.",
    )

    @field_validator("owner", mode="before")
    @classmethod
    def normalise_owner(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            if value.lower() in _NO_OWNER:
                return None
        return value


class MeetingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, description="3 to 5 sentence summary of the meeting.")
    decisions: list[str] = Field(description="Decisions that were made. Empty list if none.")
    action_items: list[ActionItem] = Field(description="Commitments to act. Empty list if none.")

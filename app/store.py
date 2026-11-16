from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.api_schemas import JobStatus, MeetingOut
from app.config import get_settings
from app.schemas import MeetingResult


class Base(DeclarativeBase):
    pass


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(primary_key=True)
    status: Mapped[str]
    result_json: Mapped[str | None]
    error: Mapped[str | None]


_engine: Engine | None = None


def configure_engine(db_url: str) -> None:
    """Point the store at a database. Tests use this to get a throwaway one."""
    global _engine
    _engine = create_engine(db_url)


def get_engine() -> Engine:
    if _engine is None:
        configure_engine(get_settings().database_url)
    return _engine


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    Base.metadata.create_all(get_engine())


def to_row(job: MeetingOut) -> JobRow:
    return JobRow(
        id=job.id,
        status=job.status.value,
        result_json=job.result.model_dump_json() if job.result else None,
        error=job.error,
    )


def to_job(row: JobRow) -> MeetingOut:
    return MeetingOut(
        id=row.id,
        status=JobStatus(row.status),
        result=MeetingResult.model_validate_json(row.result_json) if row.result_json else None,
        error=row.error,
    )


def save_job(job: MeetingOut) -> None:
    with Session(get_engine()) as session:
        row = to_row(job)
        session.merge(row)
        session.commit()


def get_job(meeting_id: str) -> MeetingOut | None:
    with Session(get_engine()) as session:
        row = session.get(JobRow, meeting_id)
        if row is None:
            return None
        return to_job(row)

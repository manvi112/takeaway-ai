import logging

from app.api_schemas import JobStatus, MeetingCreate, MeetingOut
from app.extract import ExtractionError, extract_long
from app.store import save_job

logger = logging.getLogger(__name__)


def run_job(meeting_id: str, body: MeetingCreate) -> None:
    save_job(MeetingOut(id=meeting_id, status=JobStatus.running))
    try:
        result = extract_long(body.transcript, body.meeting_date.isoformat())
    except ExtractionError as e:
        logger.warning("Job %s failed: %s", meeting_id, e)
        save_job(
            MeetingOut(
                id=meeting_id,
                status=JobStatus.failed,
                error="The model did not return a valid result.",
            )
        )
    except Exception:
        logger.exception("Job %s failed with unexpected error", meeting_id)
        save_job(
            MeetingOut(
                id=meeting_id,
                status=JobStatus.failed,
                error="Internal error while processing this meeting.",
            )
        )
    else:
        save_job(MeetingOut(id=meeting_id, status=JobStatus.completed, result=result))

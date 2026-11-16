import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException

from app.api_schemas import JobStatus, MeetingCreate, MeetingCreated, MeetingOut
from app.jobs import run_job
from app.store import get_job, init_db, save_job


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Takeaway", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/meetings", response_model=MeetingCreated, status_code=202)
def create_meeting(body: MeetingCreate, background_tasks: BackgroundTasks):
    meeting_id = str(uuid.uuid4())
    job = MeetingOut(id=meeting_id, status=JobStatus.queued)
    save_job(job)
    background_tasks.add_task(run_job, meeting_id, body)
    return MeetingCreated(id=meeting_id, status=JobStatus.queued)


@app.get("/meetings/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: str):
    job = get_job(meeting_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return job

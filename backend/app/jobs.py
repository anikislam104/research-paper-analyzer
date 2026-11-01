import time
import uuid

from .config import settings
from .llm import LLMError
from .modes import HANDLERS

_jobs: dict[str, dict] = {}


def create(paper_id: str, mode: str) -> str:
    now = time.time()
    for k in [k for k, j in _jobs.items() if now - j["created"] > settings.cache_ttl_seconds]:
        del _jobs[k]
    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"id": job_id, "paper_id": paper_id, "mode": mode, "status": "running",
                     "progress": "Starting", "result": None, "error": None, "created": now}
    return job_id


def get(job_id: str) -> dict | None:
    return _jobs.get(job_id)


class Cancelled(Exception):
    pass


def cancel(job_id: str) -> bool:
    job = _jobs.get(job_id)
    if not job:
        return False
    job["cancelled"] = True
    if job["status"] == "running":
        job.update(status="cancelled", progress="Cancelled")
    return True


def run(job_id: str, paper: dict) -> None:
    job = _jobs[job_id]

    def progress(message: str) -> None:
        if job.get("cancelled"):
            raise Cancelled
        job["progress"] = message

    try:
        result = HANDLERS[job["mode"]](paper, progress)
        if not job.get("cancelled"):
            job["result"] = result
            job["status"] = "done"
    except Cancelled:
        pass
    except LLMError as exc:
        job.update(status="error", error=str(exc))
    except Exception:
        job.update(status="error", error="Analysis failed unexpectedly.")

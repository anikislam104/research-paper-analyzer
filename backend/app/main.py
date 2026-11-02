from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import jobs, store
from .config import settings
from .modes import HANDLERS, MODES
from .pdf import PdfError, extract_text
from .pptx_export import build_pptx

app = FastAPI(title="Paper Analyzer")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "model": settings.model}


@app.get("/api/modes")
def modes():
    return [{"id": k, "label": v, "available": k in HANDLERS} for k, v in MODES.items()]


class AnalyzeRequest(BaseModel):
    mode: str


@app.post("/api/papers/{paper_id}/analyze")
def analyze(paper_id: str, req: AnalyzeRequest, background: BackgroundTasks):
    if req.mode not in MODES:
        raise HTTPException(400, "Unknown mode.")
    if req.mode not in HANDLERS:
        raise HTTPException(501, "This mode is not implemented yet.")
    paper = store.get(paper_id)
    if paper is None:
        raise HTTPException(404, "Paper expired or not found. Please upload it again.")
    job_id = jobs.create(paper_id, req.mode)
    background.add_task(jobs.run, job_id, paper)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found.")
    return {k: job[k] for k in ("id", "mode", "status", "progress", "done", "total", "result", "error")}


@app.post("/api/jobs/{job_id}/cancel")
def job_cancel(job_id: str):
    if not jobs.cancel(job_id):
        raise HTTPException(404, "Job not found.")
    return {"status": "cancelled"}


@app.get("/api/jobs/{job_id}/pptx")
def job_pptx(job_id: str):
    job = jobs.get(job_id)
    result = job and job["result"]
    if not result or result.get("type") != "slides":
        raise HTTPException(404, "No slides available for this job.")
    data = build_pptx(result["title"], result["slides"])
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": 'attachment; filename="presentation.pptx"'},
    )


@app.post("/api/papers")
async def upload_paper(file: UploadFile = File(...)):
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB.")
    try:
        parsed = extract_text(data)
    except PdfError as exc:
        raise HTTPException(422, str(exc))
    paper_id = store.hash_bytes(data)
    store.put(paper_id, parsed)
    return {
        "paper_id": paper_id,
        "title": parsed["title"] or file.filename,
        "page_count": parsed["page_count"],
        "char_count": len(parsed["text"]),
        "preview": parsed["text"][:500],
    }

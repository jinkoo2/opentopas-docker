"""
OpenTOPAS REST + WebSocket API server.

Endpoints:
  POST   /jobs                  – submit a simulation (upload .txt param file)
  GET    /jobs                  – list all jobs
  GET    /jobs/{id}             – get job status & metadata
  DELETE /jobs/{id}             – cancel a running job
  GET    /jobs/{id}/results     – download output files as a zip archive
  WS     /ws/{id}               – stream stdout/stderr in real time
"""

import asyncio
import io
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TOPAS_SCRIPT = Path("/root/shellScripts/topas")
JOBS_ROOT = Path("/tmp/topas-jobs")
JOBS_ROOT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class JobRecord:
    def __init__(self, job_id: str, param_filename: str):
        self.job_id = job_id
        self.param_filename = param_filename
        self.status = JobStatus.queued
        self.created_at = datetime.now(timezone.utc)
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None
        self.return_code: Optional[int] = None
        self.work_dir = JOBS_ROOT / job_id
        self.log_file = self.work_dir / "topas.log"
        self.process: Optional[asyncio.subprocess.Process] = None
        # Subscribers waiting for log lines via WebSocket
        self._log_subscribers: List[asyncio.Queue] = []

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "param_filename": self.param_filename,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "return_code": self.return_code,
            "work_dir": str(self.work_dir),
        }


# In-memory job registry
_jobs: Dict[str, JobRecord] = {}


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="OpenTOPAS API", version="0.1.0")


# ---------------------------------------------------------------------------
# Background simulation runner
# ---------------------------------------------------------------------------


async def _run_simulation(job: JobRecord) -> None:
    """Launch TOPAS in a subprocess and stream its output to the log file
    and any connected WebSocket subscribers."""
    job.status = JobStatus.running
    job.started_at = datetime.now(timezone.utc)

    param_path = job.work_dir / job.param_filename

    try:
        proc = await asyncio.create_subprocess_exec(
            str(TOPAS_SCRIPT),
            str(param_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # merge stderr into stdout
            cwd=str(job.work_dir),
        )
        job.process = proc

        async with aiofiles.open(job.log_file, "w") as log_fh:
            assert proc.stdout is not None
            async for raw_line in proc.stdout:
                line = raw_line.decode(errors="replace")
                await log_fh.write(line)
                await log_fh.flush()
                # Broadcast to WebSocket subscribers
                for q in list(job._log_subscribers):
                    await q.put(line)

        await proc.wait()
        job.return_code = proc.returncode
        job.status = JobStatus.done if proc.returncode == 0 else JobStatus.failed

    except asyncio.CancelledError:
        if job.process and job.process.returncode is None:
            job.process.terminate()
            await job.process.wait()
        job.status = JobStatus.cancelled
        raise
    except Exception as exc:
        async with aiofiles.open(job.log_file, "a") as log_fh:
            await log_fh.write(f"\n[API ERROR] {exc}\n")
        job.status = JobStatus.failed
    finally:
        job.finished_at = datetime.now(timezone.utc)
        # Signal all WebSocket subscribers that the stream is done
        for q in list(job._log_subscribers):
            await q.put(None)  # sentinel


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/jobs", status_code=201)
async def submit_job(param_file: UploadFile = File(...)):
    """Upload a TOPAS .txt parameter file and start a simulation."""
    job_id = str(uuid.uuid4())
    job = JobRecord(job_id=job_id, param_filename=param_file.filename or "sim.txt")

    # Create working directory and save the uploaded file
    job.work_dir.mkdir(parents=True, exist_ok=True)
    dest = job.work_dir / job.param_filename
    async with aiofiles.open(dest, "wb") as f:
        content = await param_file.read()
        await f.write(content)

    _jobs[job_id] = job

    # Launch simulation as a background task (fire-and-forget)
    asyncio.create_task(_run_simulation(job))

    return job.to_dict()


@app.get("/jobs")
async def list_jobs():
    """Return a list of all jobs."""
    return [j.to_dict() for j in _jobs.values()]


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    """Return status and metadata for a single job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """Terminate a running job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.queued, JobStatus.running):
        raise HTTPException(
            status_code=409, detail=f"Cannot cancel job in status '{job.status}'"
        )
    if job.process and job.process.returncode is None:
        job.process.terminate()
        await job.process.wait()
    job.status = JobStatus.cancelled
    job.finished_at = datetime.now(timezone.utc)
    return job.to_dict()


@app.get("/jobs/{job_id}/results")
async def get_results(job_id: str):
    """Download all output files for a completed job as a zip archive."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.done, JobStatus.failed):
        raise HTTPException(
            status_code=409,
            detail=f"Results not available yet (status: {job.status})",
        )

    # Build zip in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in job.work_dir.iterdir():
            zf.write(f, arcname=f.name)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="job-{job_id}.zip"'},
    )


@app.websocket("/ws/{job_id}")
async def stream_logs(websocket: WebSocket, job_id: str):
    """Stream stdout/stderr of a running (or already-finished) job."""
    job = _jobs.get(job_id)
    if not job:
        await websocket.close(code=4004, reason="Job not found")
        return

    await websocket.accept()

    # If the job already finished, replay the log file and close
    if job.status in (JobStatus.done, JobStatus.failed, JobStatus.cancelled):
        if job.log_file.exists():
            async with aiofiles.open(job.log_file, "r") as f:
                async for line in f:
                    await websocket.send_text(line)
        await websocket.close()
        return

    # Subscribe to live output
    queue: asyncio.Queue = asyncio.Queue()
    job._log_subscribers.append(queue)
    try:
        while True:
            line = await queue.get()
            if line is None:  # sentinel – simulation finished
                break
            await websocket.send_text(line)
    except WebSocketDisconnect:
        pass
    finally:
        job._log_subscribers.discard(queue) if hasattr(
            job._log_subscribers, "discard"
        ) else (
            job._log_subscribers.remove(queue)
            if queue in job._log_subscribers
            else None
        )
        await websocket.close()

# OpenTOPAS API — Claude Code Guide

## Project overview
A FastAPI server that exposes OpenTOPAS Monte Carlo simulations as an async REST + WebSocket API.
Jobs are submitted by uploading a TOPAS `.txt` parameter file; output files are downloadable as a zip when the simulation finishes.

## Key files
| File | Purpose |
|---|---|
| `server.py` | FastAPI application — all routes and simulation runner |
| `test_client.py` | Async integration test (submit → stream → status → download) |
| `test_sim.txt` | Minimal 100-history proton simulation used for smoke testing |

## Running the server
```bash
cd /root/Applications/topas-api
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Auto-reload during development:
```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## Running the tests
```bash
# Server must already be running
python3 test_client.py

# Point at a custom parameter file
python3 test_client.py --param /path/to/my_sim.txt
```

## TOPAS integration
- Shell wrapper: `/root/shellScripts/topas`
- Geant4 data: `/root/Applications/GEANT4/G4DATA`
- TOPAS install: `/root/Applications/TOPAS/OpenTOPAS-install`
- Source code: `/root/Applications/TOPAS/OpenTOPAS`
- Job working directories: `/tmp/topas-jobs/{uuid}/`

## API surface
| Method | Path | Description |
|---|---|---|
| `POST` | `/jobs` | Submit simulation (multipart `param_file`) |
| `GET` | `/jobs` | List all jobs |
| `GET` | `/jobs/{id}` | Get job status & metadata |
| `DELETE` | `/jobs/{id}` | Cancel a running job |
| `GET` | `/jobs/{id}/results` | Download output zip |
| `WS` | `/ws/{id}` | Stream stdout/stderr in real time |

Interactive API docs are available at `http://localhost:8000/docs` when the server is running.

## Job states
`queued` → `running` → `done` | `failed` | `cancelled`

## Dependencies
Installed with `pip install --break-system-packages`:
- `fastapi`
- `uvicorn[standard]`
- `aiofiles`
- `python-multipart`
- `httpx`
- `websockets`

## Architecture notes
- Jobs run as `asyncio` background tasks — no external queue (Celery/Redis) needed for single-host use.
- stdout and stderr are merged and streamed line-by-line to both the log file and any connected WebSocket clients.
- Job state is stored in-memory (`_jobs` dict in `server.py`); a server restart loses job history but not the files under `/tmp/topas-jobs/`.
- The `/tmp/topas-jobs/` directory is not cleaned up automatically — add a cleanup cron or a `DELETE /jobs/{id}` extension if disk space is a concern.

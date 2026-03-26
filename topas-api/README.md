# OpenTOPAS API

A REST + WebSocket API that exposes [OpenTOPAS](https://github.com/OpenTOPAS/OpenTOPAS) Monte Carlo simulations as an async web service. Submit a TOPAS parameter file, stream live output, and download results — all over HTTP.

## Requirements

- Python 3.11+
- OpenTOPAS installed and accessible via `/root/shellScripts/topas`
- Python packages:

```bash
pip install fastapi "uvicorn[standard]" aiofiles python-multipart httpx websockets
```

## Quick start

**Start the server:**
```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

**Run the smoke test** (in a second terminal):
```bash
python3 test_client.py
```

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

## API

### Submit a simulation
```bash
curl -X POST http://localhost:8000/jobs \
     -F "param_file=@my_simulation.txt"
```
Returns a job object with a `job_id` UUID.

### Stream logs (WebSocket)
```bash
# Using wscat
wscat -c ws://localhost:8000/ws/<job_id>
```
Streams TOPAS stdout/stderr line by line until the simulation finishes.
Connecting to a finished job replays the full log immediately.

### Poll status
```bash
curl http://localhost:8000/jobs/<job_id>
```
`status` is one of: `queued` | `running` | `done` | `failed` | `cancelled`

### Download results
```bash
curl -OJ http://localhost:8000/jobs/<job_id>/results
```
Returns a zip archive containing the parameter file, all TOPAS output files, and `topas.log`.

### List all jobs
```bash
curl http://localhost:8000/jobs
```

### Cancel a running job
```bash
curl -X DELETE http://localhost:8000/jobs/<job_id>
```

## Example parameter file

A minimal simulation (`test_sim.txt`) is included. It fires 100 protons at a water phantom and completes in under a second:

```text
s:Ge/Phantom/Type     = "TsBox"
s:Ge/Phantom/Material = "G4_WATER"
...
i:So/TestBeam/NumberOfHistoriesInRun = 100
```

## Project layout

```
topas-api/
├── server.py       # FastAPI application
├── test_client.py  # Async integration test client
├── test_sim.txt    # Minimal smoke-test simulation
├── README.md
└── CLAUDE.md       # Notes for Claude Code
```

## How it works

```
Client
  │
  ├─ POST /jobs  ──► save param file ──► asyncio background task
  │                                           │
  │                                     subprocess: topas sim.txt
  │                                           │
  ├─ WS  /ws/{id} ◄── line-by-line stdout ◄──┤
  ├─ GET /jobs/{id}   (poll status)           │
  └─ GET /jobs/{id}/results ◄── zip ◄─────────┘
```

Jobs run as `asyncio` background tasks. State is in-memory; output files persist under `/tmp/topas-jobs/{uuid}/`.

## Extending

- **Authentication** — add an `api_key` dependency to routes.
- **Persistence** — replace the `_jobs` dict with SQLite/SQLModel.
- **Job queue** — drop in Celery + Redis for multi-worker scaling.
- **Cleanup** — add a `DELETE /jobs/{id}` that also removes the work directory.
- **Docker** — the OpenTOPAS source includes a `docker/` directory; wrap this API in the same image.

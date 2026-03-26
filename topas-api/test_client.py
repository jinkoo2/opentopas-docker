"""
OpenTOPAS API test client.

Usage:
  python test_client.py [--host HOST] [--port PORT] [--param PATH_TO_TXT]

Runs through the full job lifecycle:
  1. Submit a simulation
  2. Stream stdout via WebSocket until the job finishes
  3. Poll job status
  4. Download and list the result zip
"""

import argparse
import asyncio
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import websockets


BASE_URL = "http://roweb3:7778"
WS_URL   = "ws://roweb3:7778"

DEFAULT_PARAM = Path(__file__).parent / "test_sim.txt"

# Must match API_TOKEN in server.py
API_TOKEN = "topas-dev-a3f8c2d1-4b7e-4f9a-8c3d-2e1f5a6b7c8d"
AUTH_HEADERS = {"Authorization": f"Bearer {API_TOKEN}"}


# ── helpers ──────────────────────────────────────────────────────────────────

def ok(msg: str) -> None:
    print(f"  \033[32m✔\033[0m  {msg}")

def fail(msg: str) -> None:
    print(f"  \033[31m✘\033[0m  {msg}")
    sys.exit(1)

def info(msg: str) -> None:
    print(f"     {msg}")


# ── test steps ────────────────────────────────────────────────────────────────

async def test_submit(client: httpx.AsyncClient, param_path: Path) -> str:
    print("\n[1] Submit job")
    with open(param_path, "rb") as f:
        resp = await client.post(
            f"{BASE_URL}/jobs",
            files={"param_file": (param_path.name, f, "text/plain")},
            headers=AUTH_HEADERS,
        )
    if resp.status_code != 201:
        fail(f"Expected 201, got {resp.status_code}: {resp.text}")
    data = resp.json()
    job_id = data["job_id"]
    ok(f"Job submitted  id={job_id}  status={data['status']}")
    return job_id


async def test_stream_logs(job_id: str) -> None:
    print("\n[2] Stream logs via WebSocket")
    uri = f"{WS_URL}/ws/{job_id}?token={API_TOKEN}"
    line_count = 0
    try:
        async with websockets.connect(uri) as ws:
            async for message in ws:
                line = message.rstrip()
                if line:
                    info(line)
                    line_count += 1
    except Exception as exc:
        fail(f"WebSocket error: {exc}")
    ok(f"Log stream finished  ({line_count} lines received)")


async def test_get_status(client: httpx.AsyncClient, job_id: str) -> str:
    print("\n[3] Get job status")
    resp = await client.get(f"{BASE_URL}/jobs/{job_id}", headers=AUTH_HEADERS)
    if resp.status_code != 200:
        fail(f"Expected 200, got {resp.status_code}: {resp.text}")
    data = resp.json()
    status = data["status"]
    rc = data["return_code"]
    ok(f"Status={status}  return_code={rc}")
    if status == "failed":
        fail("Simulation reported as failed – check logs above.")
    return status


async def test_list_jobs(client: httpx.AsyncClient, job_id: str) -> None:
    print("\n[4] List all jobs")
    resp = await client.get(f"{BASE_URL}/jobs", headers=AUTH_HEADERS)
    if resp.status_code != 200:
        fail(f"Expected 200, got {resp.status_code}")
    jobs = resp.json()
    ids = [j["job_id"] for j in jobs]
    if job_id not in ids:
        fail(f"Our job {job_id} not found in list")
    ok(f"Found {len(jobs)} job(s) in registry  (ours is present)")


async def test_download_results(client: httpx.AsyncClient, job_id: str) -> None:
    print("\n[5] Download results zip")
    resp = await client.get(f"{BASE_URL}/jobs/{job_id}/results", headers=AUTH_HEADERS)
    if resp.status_code != 200:
        fail(f"Expected 200, got {resp.status_code}: {resp.text}")
    content_type = resp.headers.get("content-type", "")
    if "zip" not in content_type:
        fail(f"Expected zip content-type, got: {content_type}")

    buf = BytesIO(resp.content)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
    ok(f"Downloaded {len(resp.content) // 1024} KB zip  ({len(names)} files)")
    for name in names:
        info(f"  {name}")


# ── main ──────────────────────────────────────────────────────────────────────

async def run(param_path: Path) -> None:
    print("=" * 60)
    print(" OpenTOPAS API — integration test")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=300.0) as client:
        job_id = await test_submit(client, param_path)
        await test_stream_logs(job_id)
        status = await test_get_status(client, job_id)
        await test_list_jobs(client, job_id)
        if status in ("done", "failed"):
            await test_download_results(client, job_id)

    print("\n" + "=" * 60)
    print(" All tests passed.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenTOPAS API test client")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--param",
        type=Path,
        default=DEFAULT_PARAM,
        help="Path to a TOPAS .txt parameter file",
    )
    args = parser.parse_args()

    BASE_URL = f"http://{args.host}:{args.port}"
    WS_URL   = f"ws://{args.host}:{args.port}"

    asyncio.run(run(args.param))

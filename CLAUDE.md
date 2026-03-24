# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repo packages [OpenTOPAS](https://github.com/OpenTOPAS/OpenTOPAS) (a Geant4-based Monte Carlo particle simulation tool) into a Docker container with a browser-accessible LXDE desktop via noVNC.

## Key files

- `Dockerfile.debian12` — the active Dockerfile; `Dockerfile.ubuntu-not-tested` is kept for reference but not used
- `supervisord.conf` — defines the 4-process startup sequence inside the container
- `entrypoint.sh` — sets the VNC password from `VNC_PASS` env var at runtime, then hands off to supervisord
- `.env` — contains `VNC_PASS` (gitignored, never committed)

## Build and run

```bash
# Build image (takes 1-2+ hours — Geant4 and OpenTOPAS compile from source)
docker compose build

# Start container
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

## Connecting to the desktop

| Method | Address |
|---|---|
| Browser (noVNC) | `http://localhost:6080/vnc.html` |
| VNC client | `localhost:5900` |

Password is in `.env` as `VNC_PASS`.

## Architecture inside the container

`supervisord` runs as PID 1 and manages four processes in priority order:

1. **Xvfb** — virtual framebuffer (fake display `:1`)
2. **lxsession** — LXDE desktop (waits 2s for Xvfb)
3. **x11vnc** — VNC server on port 5900 (waits 4s)
4. **websockify** — noVNC web proxy on port 6080, serves `/usr/share/novnc/` (waits 5s)

## OpenTOPAS installation paths (inside container)

| Component | Path |
|---|---|
| Geant4 install | `/root/Applications/GEANT4/geant4-install` |
| Geant4 data | `/root/Applications/GEANT4/G4DATA` |
| GDCM install | `/root/Applications/GDCM/gdcm-install` |
| OpenTOPAS install | `/root/Applications/TOPAS/OpenTOPAS-install` |
| OpenTOPAS source | `/root/Applications/TOPAS/OpenTOPAS` |
| `topas` launcher | `/root/shellScripts/topas` |

## Running a simulation

Inside the container terminal:

```bash
topas /root/Applications/TOPAS/OpenTOPAS/examples/Basic/QtShapeTest.txt
```

## Debian 12 and Qt6

`Dockerfile.debian12` is based on `debian:12` because:
- The [OpenTOPAS quickstart guide](../OpenTOPAS/OpenTOPAS_quickStart_Debian.md) targets Debian 10/11/12
- Qt6 (required for visualization) is available in Debian 12 standard apt repos — no workarounds needed
- Earlier Ubuntu/Debian versions require `aqtinstall` or a PPA to get Qt6

## Changing the VNC password

Edit `.env`:
```
VNC_PASS=yournewpassword
```
Then restart: `docker compose down && docker compose up -d`

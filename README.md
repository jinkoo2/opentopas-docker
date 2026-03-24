# opentopas-docker

A Docker image that runs [OpenTOPAS](https://github.com/OpenTOPAS/OpenTOPAS) (a Geant4-based Monte Carlo particle simulation tool) with a full LXDE desktop accessible from a web browser via noVNC. No VNC client software required.

Built on **Debian 12 (Bookworm)**, following the [OpenTOPAS Debian quickstart guide](https://github.com/OpenTOPAS/OpenTOPAS/blob/master/OpenTOPAS_quickStart_Debian.md).

---

## Requirements

- [Docker](https://docs.docker.com/get-docker/) with Compose plugin
- ~30 GB free disk space (Geant4 data + compiled binaries)
- A modern web browser

---

## Setup

### 1. Clone this repository

```bash
git clone https://github.com/jinkoo2/opentopas-docker.git
cd opentopas-docker
```

### 2. Set your passwords

Create a `.env` file in the repo directory:

```
VNC_PASS=your_secure_vnc_password
CODE_SERVER_PASS=your_secure_codeserver_password
```

### 3. Build the image

> **Note:** This step compiles Geant4 and OpenTOPAS from source and will take **1–2+ hours** depending on your CPU.

```bash
docker compose build
```

### 4. Start the container

```bash
docker compose up -d
```

---

## Connecting to the desktop

| Service | URL | Password key |
|---|---|---|
| LXDE desktop (noVNC) | `http://localhost:6080/vnc.html` | `VNC_PASS` |
| Code editor (code-server) | `http://localhost:8080` | `CODE_SERVER_PASS` |
| VNC client | `localhost:5900` | `VNC_PASS` |

Passwords are set in `.env`.

---

## Running OpenTOPAS simulations

Open a terminal inside the desktop and use the `topas` command:

```bash
topas <path-to-parameter-file.txt>
```

### Example — built-in Qt visualization test

```bash
topas /root/Applications/TOPAS/OpenTOPAS/examples/Basic/QtShapeTest.txt
```

This opens a 3D Qt visualization of the geometry.

### Example — run your own simulation

Place your parameter files in the `workspace/` folder next to `docker-compose.yml` on your host machine. It is mounted inside the container at `/root/workspace/`:

```bash
topas /root/workspace/my_simulation.txt
```

Output files written to `/root/workspace/` are immediately accessible on your host.

### What the `topas` script does

The `topas` command at `/root/shellScripts/topas` is a thin wrapper that sets the required environment variables before calling the OpenTOPAS binary:

```bash
export TOPAS_G4_DATA_DIR=/root/Applications/GEANT4/G4DATA
export LD_LIBRARY_PATH=/root/Applications/TOPAS/OpenTOPAS-install/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/root/Applications/GEANT4/geant4-install/lib:$LD_LIBRARY_PATH
/root/Applications/TOPAS/OpenTOPAS-install/bin/topas "$@"
```

---

## Managing the container

```bash
# Start in background
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f

# Rebuild after Dockerfile changes
docker compose up --build -d
```

---

## Changing passwords

Edit `.env` and restart:

```
VNC_PASS=new_vnc_password
CODE_SERVER_PASS=new_codeserver_password
```

```bash
docker compose down && docker compose up -d
```

---

## Installation paths (inside container)

| Component | Path |
|---|---|
| OpenTOPAS binary | `/root/Applications/TOPAS/OpenTOPAS-install/bin/topas` |
| OpenTOPAS examples | `/root/Applications/TOPAS/OpenTOPAS/examples/` |
| Geant4 data files | `/root/Applications/GEANT4/G4DATA` |
| Shared workspace | `/root/workspace` (mounted from host) |

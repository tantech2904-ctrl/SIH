# ULPF Setup — Windows Quick Start

This is the fastest way to get ULPF running on a Windows machine.

## Just run one file

    scripts\setup_ulpf.bat

That's it. The script does everything else.

---

## What the script does

1. **Checks** whether you have Docker installed.
2. **If you have Docker** — it runs ULPF entirely in containers. Nothing
   else needs to be installed. This is the recommended path. Just make 
   sure to keep it running/open in the background, before running the 
   script.
3. **If you don't have Docker** — it offers to open the Docker Desktop
   download page, or to run ULPF in **local mode** using your existing
   Python and Node installations.
4. **Creates or refreshes** the `.env` configuration file at the project
   root, backing up any previous one.
5. **Starts everything** and shows a live progress bar.
6. **Opens ULPF in your browser** automatically.

The script does **not** modify any source files. It only writes to:

- `.env` at the project root (backed up if it already exists)
- `%USERPROFILE%\.ulpf\` — logs and setup state

---

## After setup

When setup completes, you'll see this on screen:

    Frontend: http://localhost:5173
    API:      http://localhost:8000
    API Docs: http://localhost:8000/docs

### First-time login

    Email:    admin@ulpf.local
    Password: ChangeMe_Admin123!

**Change these in Settings after you log in.**

---

## Stopping ULPF

    scripts\stop_ulpf.bat

This safely stops Docker containers and closes any local-mode windows.

---

## Re-running setup

The script is safe to run as many times as you like. On each run it will:

- Back up any existing `.env` to `.env.bak.YYYY-MM-DD-HH-mm-ss`.
- Re-create `.env` from `.env.example`.
- Re-check Docker and start the stack.

If you want to keep your custom settings, copy them somewhere safe before
re-running.

---

## Troubleshooting

**"Docker Compose failed"** — the most common causes:

- Docker Desktop is not running. Open it from the Start menu.
- Ports 5173, 8000, 5432, 6379, 9000 are in use by something else.
  Check with: `netstat -ano | findstr :5173`
- WSL2 needs updating. Run: `wsl --update` in an elevated PowerShell.

**"ULPF did not become ready in time"** — check the Docker logs:

    docker compose logs backend
    docker compose logs frontend

Or, in local mode, look at the "ULPF Backend" window for errors.

**"Python not found"** (local mode only) — install Python 3.11+ from
python.org. Make sure "Add Python to PATH" is checked during install.

**"Node not found"** (local mode only) — install Node 18+ from nodejs.org.

**Everything is broken and I want a fresh start** — delete these and
re-run setup:

    .env
    %USERPROFILE%\.ulpf\
    backend\venv\
    frontend\node_modules\

Then run `scripts\setup_ulpf.bat` again.

For Docker mode, you can also reset the database:

    docker compose down -v

**The setup log** at `%USERPROFILE%\.ulpf\install.log` records every
command the script ran. If you need help, that file has the full story.

---

## For the developer who wrote this

- Docker mode: uses `docker-compose.yml` unchanged.
- Local mode: uses `backend/venv` + `npm run dev` in `frontend/`.
- `.env` is always regenerated from `.env.example`. Backups are kept.
- The script never reads or writes inside `backend/app/` or
  `frontend/src/`.
- Idempotent — safe to run repeatedly.

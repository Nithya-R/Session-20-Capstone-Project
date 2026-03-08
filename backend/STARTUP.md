# Civic Lens — Startup Guide

## Prerequisites

- **Python 3.10+** with a virtual environment set up in `backend/venv/`
- **Node.js 18+** with npm
- **Environment variables** configured in `backend/.env` (see below)

---

## 1. Environment Variables

A template file `.env.example` is provided in the `backend/` folder with all required key names and descriptions.

**Copy it and fill in your values:**

```powershell
cd "C:\Users\Nithya\My Project - EAG\backend"
cp .env.example .env
```

Then open `backend/.env` and replace the placeholder values:

```env
GEMINI_API_KEY=your_google_gemini_api_key_here
HUGGINGFACE_API_TOKEN=your_huggingface_token_here
```

- `GEMINI_API_KEY` — **Required.** Used by all AI agents (lessons, quizzes, placement exam, curriculum generation). Get it from [Google AI Studio](https://aistudio.google.com/app/apikey).
- `HUGGINGFACE_API_TOKEN` — Optional. Only needed for the direct `/api/v1/llm/generate` endpoint.

> `.env` is git-ignored. Never commit it. Only `.env.example` is tracked in version control.

---

## 2. Backend

The backend is a FastAPI server running on port **8000**.

### Option A — PowerShell Script (recommended)

The `start.ps1` script automatically kills any process already using port 8000, then starts the server with auto-restart on crash.

```powershell
cd "C:\Users\Nithya\My Project - EAG\backend"
.\start.ps1
```

To use a different port:
```powershell
.\start.ps1 -Port 9000
```

### Option B — Manual (uvicorn directly)

```powershell
cd "C:\Users\Nithya\My Project - EAG\backend"
.\venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000 --reload
```

### Verify the backend is running

```
GET http://localhost:8000/health
```
Expected response: `{ "status": "healthy", "version": "0.1.0" }`

Interactive API docs: `http://localhost:8000/docs`

---

## 3. Frontend

The frontend is a React + Vite app running on port **5173**. It proxies all `/api/v1/` requests to the backend on port 8000.

### Install dependencies (first time only)

```powershell
cd "C:\Users\Nithya\My Project - EAG\frontend"
npm install
```

### Start the dev server

```powershell
cd "C:\Users\Nithya\My Project - EAG\frontend"
npm run dev
```

Open in browser: `http://localhost:5173`

---

## 4. Start Both (recommended workflow)

Open two terminal windows side by side:

**Terminal 1 — Backend:**
```powershell
cd "C:\Users\Nithya\My Project - EAG\backend"
.\start.ps1
```

**Terminal 2 — Frontend:**
```powershell
cd "C:\Users\Nithya\My Project - EAG\frontend"
npm run dev
```

Then open `http://localhost:5173` in your browser.

---

## 5. Stopping the Servers

- **Backend:** Press `Ctrl+C` in the PowerShell terminal running `start.ps1`.
- **Frontend:** Press `Ctrl+C` in the terminal running `npm run dev`.

### Force-kill backend if needed (e.g. port still in use)

```powershell
# Kill all Python processes
taskkill /F /IM python.exe

# Or kill just the process on port 8000
$pid = (Get-NetTCPConnection -LocalPort 8000).OwningProcess
Stop-Process -Id $pid -Force
```

---

## 6. Production Build (frontend)

To build an optimised static bundle:

```powershell
cd "C:\Users\Nithya\My Project - EAG\frontend"
npm run build
```

Output is in `frontend/dist/`. Serve it with any static file host or via the backend using FastAPI's `StaticFiles` mount.

# Career Copilot — How to Run the Application 🚀

This guide provides step-by-step instructions to run the **Career Copilot** backend, database, visual testing control center, and automated tests.

---

## 📋 Prerequisites
- **Python**: 3.11 or higher
- **Docker & Docker Compose** (for PostgreSQL + pgvector)
- **PowerShell** (on Windows) or Terminal (on macOS/Linux)

---

## ⚡ Quick Start (One-Time Setup)

### 1. Configure Environment
Copy the example environment file:
```powershell
Copy-Item .env.example .env
```

### 2. Set Up Python Virtual Environment
If not already created:
```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r backend/requirements.txt
```

---

## 🐘 1. Start the Database (PostgreSQL + pgvector)

Start the PostgreSQL 16 container with `pgvector` enabled:
```powershell
docker compose up -d
```

To check if the database container is healthy:
```powershell
docker compose ps
```

---

## 🚀 2. Start the Backend & Visual Dashboard

Run the FastAPI development server with auto-reload:

```powershell
$env:PYTHONPATH="backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Once running, access the following in your browser:
- **🎨 Visual Developer Control Center**: [http://localhost:8000](http://localhost:8000) or [http://localhost:8000/dashboard](http://localhost:8000/dashboard)
- **📖 Interactive API Documentation (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **🔍 Alternative Docs (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **💚 Health Check Endpoint**: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- **🐘 Database & pgvector Health**: [http://localhost:8000/api/health/db](http://localhost:8000/api/health/db)

---

## 🧪 3. Run Automated Tests

To execute the pytest test suite:
```powershell
.\.venv\Scripts\pytest.exe backend/tests/ -v
```

---

## 📂 4. Standalone Visual UI Testing

You can also view and test the Developer Control Center directly by opening:
- `file:///c:/Users/PERSONAL/OneDrive/Desktop/GenAI notes/Career_copilot/frontend/index.html`

It features:
- **Real-Time API Testing Console**: Test `/api/health`, `/api/health/db`, and future endpoints with live latency readout.
- **System Health Monitor**: Visual pills showing FastAPI server status and PostgreSQL readiness.
- **Modular Monolith Map**: Visual breakdown of all 8 domain modules.
- **Active Roadmap Progress**: Live tracker of development phases.

---

## 🛠️ Useful Commands Cheat Sheet

| Action | PowerShell Command |
| :--- | :--- |
| **Start DB** | `docker compose up -d` |
| **Stop DB** | `docker compose down` |
| **Run API** | `$env:PYTHONPATH="backend"; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload` |
| **Run Tests** | `.\.venv\Scripts\pytest.exe backend/tests/ -v` |
| **Generate Migration** | `cd backend; ..\.venv\Scripts\alembic.exe revision --autogenerate -m "description"` |
| **Apply Migrations** | `cd backend; ..\.venv\Scripts\alembic.exe upgrade head` |

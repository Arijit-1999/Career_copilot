# Career Copilot — Project Overview

## 1. Vision & Purpose
Career Copilot is a personal-first AI career assistant that discovers high-match jobs, understands multiple target career paths, matches candidates against verified experience, identifies skill gaps, minimally tailors honest resumes, assists with applications, and tracks outcomes.

## 2. Core Architectural Decisions
- **Pattern**: Modular Monolith using FastAPI.
- **Data Persistence**: PostgreSQL 16 + `pgvector` for semantic indexing and structured relational storage.
- **ORM & Migrations**: SQLAlchemy 2.0 (Async) + Alembic.
- **LLM Layer**: Gateway abstraction supporting Gemini, OpenRouter, and Ollama.
- **Automation Layer**: Playwright for session-assisted browser interactions with human takeover.
- **Zero Hallucination Policy**: Resumes and applications only use `VERIFIED` facts from the Candidate Fact Bank.

## 3. Technology Stack
- **Backend Framework**: FastAPI (Python 3.11+)
- **Validation**: Pydantic v2 & Pydantic-Settings
- **Database**: PostgreSQL 16 + `pgvector` extension
- **Database Drivers**: `asyncpg` (async runtime) & `psycopg2-binary` (Alembic sync migrations)
- **Logging**: Structlog / standard structured logging
- **Testing**: pytest, pytest-asyncio, httpx
- **Containerization**: Docker Compose

## 4. Key Domain Modules
- `app/candidate`: Candidate profile, verified skill taxonomy, fact bank.
- `app/career_profiles`: Search profiles, role expansion, natural language intent.
- `app/jobs`: Job ingestion, deduplication, normalization, freshness scoring.
- `app/matching`: Multi-stage matching funnel, gap detection, explainability.
- `app/resumes`: Master resume management, minimal JD-targeted tailoring, validation.
- `app/applications`: Application lifecycle tracking and state management.
- `app/browser`: Playwright automation and platform adapters (LinkedIn, Naukri, Indeed).
- `app/llm`: Multi-provider gateway and token usage tracking.

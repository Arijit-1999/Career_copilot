# Career Copilot — Engineering Build Plan & Task Specification

## 1. Operating Rules for AI Coding Agents
1. Always check `docs/CURRENT_TASK.md` before writing code.
2. Maintain modular monolith boundaries (do not create microservices).
3. Do not invent candidate experience or skills (`VERIFIED` status required for resume generation).
4. Run tests and verify acceptance criteria before concluding a task.
5. Update `docs/ROADMAP.md`, `docs/CURRENT_TASK.md`, and append to `docs/SESSION_LOG.md`.

---

## 2. Phase-by-Phase Task Breakdown

### Phase 0: Foundation
- **FOUND-001**: Repository initialization, `.gitignore`, `.env.example`, and directory structure.
- **FOUND-002**: Context trackers in `docs/` (`PROJECT.md`, `BUILD_PLAN.md`, `ROADMAP.md`, `CURRENT_TASK.md`, `DECISIONS.md`, `SESSION_LOG.md`).
- **FOUND-003**: Agent development workspace skill (`.agents/skills/career-copilot-development/SKILL.md`).
- **FOUND-004**: Python project packaging & dependencies (`pyproject.toml`).
- **FOUND-005**: Docker Compose configuration for PostgreSQL 16 + pgvector (`docker-compose.yml`, `docker/postgres/init-pgvector.sql`).
- **FOUND-006**: Core settings (`app/core/config.py`), structured logging (`app/core/logging.py`), and base exceptions (`app/core/exceptions.py`).
- **FOUND-007**: Async database engine & session factory (`app/core/database.py`).
- **FOUND-008**: Alembic migration setup (`alembic.ini`, `alembic/env.py`).
- **FOUND-009**: FastAPI application entrypoint & lifespan management (`app/main.py`).
- **FOUND-010**: Health check endpoints (`/api/health`, `/api/health/db`) and router setup.
- **FOUND-011**: Pytest configuration (`tests/conftest.py`) and initial test suite.
- **FOUND-012**: Phase 0 completion verification and test execution.

### Phase 1: Candidate Intelligence
- **CAND-001**: Candidate profile domain models & schema.
- **CAND-002**: Skill state machine (`VERIFIED`, `CLAIMED`, `LEARNING`, `TARGET`, `NOT_RELEVANT`).
- **CAND-003**: Resume Fact Bank (experiences, projects, achievements, metrics).
- **CAND-004**: Candidate CRUD & fact management service and API endpoints.
- **CAND-005**: Unit & integration tests for candidate profile and facts.

### Phase 2: Career Targets & Intent Expansion
- **TGT-001**: Career/search profile domain model (target roles, preferences, salary, location).
- **TGT-002**: Multi-target profile management API.
- **TGT-003**: Career Intent Agent for natural-language role expansion.
- **TGT-004**: Search profile tests & validation.

### Phase 3: Job Pipeline (Ingestion, Normalization & Deduplication)
- **JOB-001**: Normalized Job domain model and database table.
- **JOB-002**: Job Source adapter interface.
- **JOB-003**: Job Normalization service (dates, salary, location, remote).
- **JOB-004**: Multi-signal Deduplication engine (source ID, canonical URL, company/title hash, content hash).
- **JOB-005**: Freshness scoring utility.
- **JOB-006**: Job ingestion API & pipeline tests.

### Phase 4: Job Understanding & Skill Extraction
- **UND-001**: Structured JD extraction schemas (required vs preferred skills, seniority, education).
- **UND-002**: Tech stack & skill tagger.
- **UND-003**: Job requirement analyzer service.
- **UND-004**: Integration tests for JD understanding.

### Phase 5: Matching Engine
- **MATCH-001**: Matching domain model & scoring schemas.
- **MATCH-002**: Deterministic hard filters (location, work mode, experience).
- **MATCH-003**: Skill matrix & gap detector.
- **MATCH-004**: Transferable skill analyzer.
- **MATCH-005**: Vector embedding similarity with `pgvector`.
- **MATCH-006**: LLM deep reasoning for shortlisted jobs.
- **MATCH-007**: Explainable match report generator.
- **MATCH-008**: Comprehensive matching pipeline tests.

### Phase 6: Resume Intelligence & Tailoring
- **RES-001**: Master resume document data model.
- **RES-002**: JD-targeted fact selection engine.
- **RES-003**: Minimal-change resume generator.
- **RES-004**: Zero-hallucination truth validator.
- **RES-005**: Human review & edit workflow.
- **RES-006**: Resume generation tests.

### Phase 7: Browser Acquisition & Platform Adapters
- **BRW-001**: Playwright browser controller foundation.
- **BRW-002**: Persistent session management (safe auth).
- **BRW-003**: Naukri job adapter.
- **BRW-004**: LinkedIn job adapter.
- **BRW-005**: Indeed job adapter.
- **BRW-006**: Human takeover and CAPTCHA handoff mechanism.

### Phase 8: Application Assistance
- **APP-001**: Application preparation workflow & form field mapper.
- **APP-002**: Permitted automation vs human handoff router.
- **APP-003**: Application lifecycle state machine (`DISCOVERED` $\to$ `OFFER`).
- **APP-004**: Application assistant tests.

### Phase 9: Tracking, Analytics & Feedback Loop
- **TRK-001**: Application tracking database models & API.
- **TRK-002**: Outcome logger & response tracker.
- **TRK-003**: Search performance & skill gap analytics.
- **TRK-004**: Outcome analytics tests.

### Phase 10: Hardening, Security & Stabilization
- **STAB-001**: LLM token tracking & cost control limits.
- **STAB-002**: Security audit (credentials, session cookies, input sanitation).
- **STAB-003**: End-to-end integration workflow test.
- **STAB-004**: Final V1 documentation and operational guide.

# Career Copilot — Project Roadmap

## Phase 0: Foundation
- [x] **FOUND-001**: Initialize repository structure, `.gitignore`, `.env.example`, and directory layout.
- [x] **FOUND-002**: Context trackers in `docs/` (`PROJECT.md`, `BUILD_PLAN.md`, `ROADMAP.md`, `CURRENT_TASK.md`, `DECISIONS.md`, `SESSION_LOG.md`).
- [x] **FOUND-003**: Agent development workspace skill (`.agents/skills/career-copilot-development/SKILL.md`).
- [x] **FOUND-004**: Python project packaging & dependencies (`pyproject.toml`).
- [x] **FOUND-005**: Docker Compose configuration for PostgreSQL 16 + pgvector (`docker-compose.yml`, `docker/postgres/init-pgvector.sql`).
- [x] **FOUND-006**: Core settings (`app/core/config.py`), structured logging (`app/core/logging.py`), and base exceptions (`app/core/exceptions.py`).
- [x] **FOUND-007**: Async database engine & session factory (`app/core/database.py`).
- [x] **FOUND-008**: Alembic migration setup (`alembic.ini`, `alembic/env.py`).
- [x] **FOUND-009**: FastAPI application entrypoint & lifespan management (`app/main.py`).
- [x] **FOUND-010**: Health check endpoints (`/api/health`, `/api/health/db`) and router setup.
- [x] **FOUND-011**: Pytest configuration (`tests/conftest.py`) and initial test suite.
- [x] **FOUND-012**: Phase 0 completion verification and test execution.

## Phase 1: Candidate Intelligence
- [x] **CAND-001**: Candidate profile domain models & schema.
- [x] **CAND-002**: Skill state machine (`VERIFIED`, `CLAIMED`, `LEARNING`, `TARGET`, `NOT_RELEVANT`).
- [x] **CAND-003**: Resume Fact Bank (experiences, projects, achievements, metrics).
- [x] **CAND-004**: Candidate CRUD & fact management service and API endpoints.
- [x] **CAND-005**: Unit & integration tests for candidate profile and facts.

## Phase 2: Career Targets & Intent Expansion
- [x] **TGT-001**: Career/search profile domain model (target roles, preferences, salary, location).
- [x] **TGT-002**: Multi-target profile management API.
- [x] **TGT-003**: Career Intent Agent for natural-language role expansion.
- [x] **TGT-004**: Search profile tests & validation.

## Phase 3: Job Pipeline (Ingestion, Normalization & Deduplication)
- [x] **JOB-001**: Normalized Job domain model and database table.
- [x] **JOB-002**: Job Source adapter interface.
- [x] **JOB-003**: Job Normalization service (dates, salary, location, remote).
- [x] **JOB-004**: Multi-signal Deduplication engine (source ID, canonical URL, company/title hash, content hash).
- [x] **JOB-005**: Freshness scoring utility.
- [x] **JOB-006**: Job ingestion API & pipeline tests.

## Phase 4: Job Understanding & Skill Extraction
- [x] **UND-001**: Structured JD extraction schemas (required vs preferred skills, seniority, education).
- [x] **UND-002**: Tech stack & skill tagger.
- [x] **UND-003**: Job requirement analyzer service.
- [x] **UND-004**: Integration tests for JD understanding.

## Phase 5: Matching Engine
- [x] **MATCH-001**: Matching domain model & scoring schemas (`app/matching/models.py`, `app/matching/schemas.py`).
- [x] **MATCH-002**: Deterministic hard filters (location, work mode, experience boundaries, salary floor).
- [x] **MATCH-003**: Skill matrix & gap detector with state-weighted credits (`VERIFIED`, `CLAIMED`, `LEARNING`).
- [x] **MATCH-004**: Transferable skill analyzer & weighted composite scoring breakdown.
- [x] **MATCH-005**: Vector embedding similarity schema & hybrid scoring integration.
- [x] **MATCH-006**: LLM deep reasoning & candidate target profile expansion hooks.
- [x] **MATCH-007**: Explainable match report generator (`highlights`, `concerns`, `reasoning_summary`).
- [x] **MATCH-008**: Comprehensive matching pipeline tests (unit & API integration tests).

## Phase 6: Resume Intelligence & Tailoring
- [x] **RES-001**: Master resume document data model (`app/resumes/models.py`, `app/resumes/schemas.py`).
- [x] **RES-002**: JD-targeted fact selection engine (`app/resumes/fact_selector.py`).
- [x] **RES-003**: Minimal-change resume generator (`app/resumes/generator.py`).
- [x] **RES-004**: Zero-hallucination truth validator (`app/resumes/validator.py`).
- [x] **RES-005**: Human review & edit workflow (`app/resumes/service.py`, `app/resumes/router.py`).
- [x] **RES-006**: Resume generation tests (unit & API integration tests).

## Phase 7: Browser Acquisition & Platform Adapters
- [ ] **BRW-001**: Playwright browser controller foundation.
- [ ] **BRW-002**: Persistent session management (safe auth).
- [ ] **BRW-003**: Naukri job adapter.
- [ ] **BRW-004**: LinkedIn job adapter.
- [ ] **BRW-005**: Indeed job adapter.
- [ ] **BRW-006**: Human takeover and CAPTCHA handoff mechanism.

## Phase 8: Application Assistance
- [ ] **APP-001**: Application preparation workflow & form field mapper.
- [ ] **APP-002**: Permitted automation vs human handoff router.
- [ ] **APP-003**: Application lifecycle state machine (`DISCOVERED` $\to$ `OFFER`).
- [ ] **APP-004**: Application assistant tests.

## Phase 9: Tracking, Analytics & Feedback Loop
- [ ] **TRK-001**: Application tracking database models & API.
- [ ] **TRK-002**: Outcome logger & response tracker.
- [ ] **TRK-003**: Search performance & skill gap analytics.
- [ ] **TRK-004**: Outcome analytics tests.

## Phase 10: Hardening, Security & Stabilization
- [ ] **STAB-001**: LLM token tracking & cost control limits.
- [ ] **STAB-002**: Security audit (credentials, session cookies, input sanitation).
- [ ] **STAB-003**: End-to-end integration workflow test.
- [ ] **STAB-004**: Final V1 documentation and operational guide.

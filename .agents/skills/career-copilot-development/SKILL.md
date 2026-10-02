---
name: career-copilot-development
description: Workflow and operating guide for developing Career Copilot. Use this skill when implementing features, checking project state, writing tests, or updating task roadmaps in the Career Copilot codebase.
---

# Career Copilot — Agent Self-Development & Continuity Skill

## Purpose
This skill gives any AI coding agent the exact protocol to seamlessly resume and advance the Career Copilot project across separate sessions without losing context or hallucinating state.

---

## 🔁 How to Resume a New Session (Step-by-Step)

When starting or resuming work in a new session:
1. **Read Persistent Trackers (in this order)**:
   - `docs/CURRENT_TASK.md` — Identifies the exact active task and acceptance criteria.
   - `docs/SESSION_LOG.md` — Read the latest entry to see what was just finished.
   - `docs/ROADMAP.md` — Check the overall phase status.
   - `docs/PROJECT.md` & `docs/DECISIONS.md` — Understand architectural rules (Modular Monolith, pgvector, Zero-Hallucination).
2. **Verify Environment**:
   - Run existing tests to verify system stability:
     ```powershell
     .\.venv\Scripts\pytest.exe backend/tests/ -v
     ```
3. **Execute ONLY the Active Task**:
   - Implement the minimal, robust solution for the task in `docs/CURRENT_TASK.md`.
   - Keep code within domain boundaries (`backend/app/<domain>/`).
   - Never invent candidate facts or bypass skill verification rules.
4. **Write & Run Tests**:
   - Add unit and integration tests under `backend/tests/`.
   - Ensure all tests pass with 100% success rate.
5. **Update Trackers & Record Session**:
   - Check off completed task in `docs/ROADMAP.md`.
   - Update `docs/CURRENT_TASK.md` to point to the next task.
   - Append an entry in `docs/SESSION_LOG.md` detailing:
     - Date & Task ID
     - What was created/modified
     - Test results
     - Next task recommendation
6. **Stop & Hand Over**:
   - Summarize changes to the user and stop. Do not start the next major task without confirmation.

---

## 📐 Architecture Rules to Always Enforce
- **Framework**: FastAPI + SQLAlchemy 2.0 (Async) + Pydantic v2.
- **Persistence**: PostgreSQL 16 + `pgvector`.
- **Skill States**: Must be one of `VERIFIED`, `CLAIMED`, `LEARNING`, `TARGET`, `NOT_RELEVANT`.
- **Resume Integrity**: Only `VERIFIED` facts/skills may be used for tailored resumes.
- **LLM Usage**: All LLM calls must go through `app.llm.gateway`, never raw vendor SDKs in business logic.

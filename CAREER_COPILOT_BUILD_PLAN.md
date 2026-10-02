# Career Copilot — V1 Build Specification & Development Operating Guide

## 1. Document Purpose

This document is the engineering source of truth for building the first version of **Career Copilot**.

Career Copilot is a personal-first AI career assistant that discovers relevant jobs, understands different career targets, matches jobs against the candidate's verified experience, identifies skill gaps, prepares minimally tailored resumes, assists with applications, and tracks application outcomes.

The V1 is intentionally designed to be:
- local-first;
- low-cost;
- backend-first;
- modular but not microservices-based;
- resumable across coding sessions;
- provider-independent for LLM usage;
- extensible toward a future multi-user product.

This document is written so that an AI coding agent such as Antigravity can execute the project in small, independently testable tasks.

---

# 2. Product Vision

## 2.1 Core problem

Job searching is repetitive and fragmented:

1. A candidate has to search multiple job platforms.
2. The same job can appear on multiple platforms.
3. Job descriptions use different terminology for similar roles.
4. Candidates may target multiple related roles.
5. Matching based only on keywords produces poor results.
6. Resumes often need targeted customization for different JDs.
7. AI can accidentally invent skills or experience.
8. Applications and outcomes are difficult to track.
9. Manual browser interaction is repetitive.

Career Copilot should reduce this work while keeping the candidate in control.

## 2.2 Core product principle

The system should optimize for:

> **Quality and relevance of opportunities, not the maximum number of applications.**

---

# 3. V1 Goals

V1 must be able to:

1. Maintain a structured candidate profile.
2. Maintain a verified resume fact bank.
3. Support multiple career/search profiles.
4. Allow natural-language career goals.
5. Expand vague career goals into possible related roles.
6. Discover and ingest jobs.
7. Normalize job descriptions.
8. Deduplicate jobs.
9. Track job freshness.
10. Understand job requirements.
11. Match jobs against candidate experience.
12. Identify skill gaps.
13. Identify transferable skills.
14. Explain why a job matches or does not match.
15. Tailor a resume for a specific JD.
16. Preserve the candidate's core resume identity.
17. Prevent fabricated experience.
18. Ask the candidate before treating a missing skill as existing experience.
19. Track applications.
20. Provide a human-in-the-loop application workflow.
21. Maintain a compact development tracker so development can resume after interruption.

---

# 4. V1 Non-Goals

Do NOT build these initially:

- Full SaaS/multi-tenant product.
- Microservices.
- Kubernetes/EKS.
- AWS production deployment.
- Complex subscription/billing system.
- Advanced frontend.
- Interview preparation.
- Fully autonomous application submission everywhere.
- Large distributed event infrastructure.
- Kafka.
- Complex agent orchestration frameworks unless a real need emerges.
- Training/fine-tuning a custom LLM.
- Expensive hosted vector database.

These may be future capabilities.

---

# 5. Product Constraints

## 5.1 Initial user

Personal-first.

The first user is the developer/candidate.

The data model should still include a user boundary so the system can become multi-user later.

## 5.2 Budget

Target:

> **₹0–₹1,000 for the first 1–2 months.**

Prefer:
- local execution;
- free tiers;
- open-source software;
- local models where practical;
- cheap APIs only when needed.

Do not spend money before identifying an actual bottleneck.

## 5.3 Existing local environment

Already available:
- Python
- Node.js
- Docker
- Antigravity IDE/coding agent

Use these rather than introducing unnecessary tools.

---

# 6. Architecture Direction

## 6.1 V1 architecture

Use a **modular monolith**.

Do not implement microservices in V1.

Logical domains should have clear boundaries so they can be extracted later if necessary.

```text
                         Career Copilot
                              |
                         FastAPI Backend
                              |
       +----------------------+----------------------+
       |          |           |          |           |
   Candidate   Search       Jobs      Matching    Resume
       |          |           |          |           |
       +----------+-----------+----------+-----------+
                              |
                        Application
                              |
                         PostgreSQL
                         + pgvector
                              |
                    Browser / LLM adapters
```

## 6.2 Architecture rule

> Start simple. Preserve clear domain boundaries. Do not introduce distributed infrastructure until a demonstrated requirement exists.

---

# 7. Technology Baseline

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- pytest

## Database

- PostgreSQL
- pgvector

## Containers

- Docker
- Docker Compose for local development

## Browser automation

- Playwright

## Frontend

Minimal UI only.

The frontend must not become the focus of V1.

## LLM

Use an abstraction layer.

Potential providers:
- Gemini
- OpenRouter
- Ollama/local models
- Other inexpensive providers as evaluated later

Do not couple business logic directly to one provider.

---

# 8. LLM Architecture

Business code must call an internal interface.

Example:

```python
result = llm.generate(...)
```

Business modules must NOT directly depend on a single provider SDK.

Recommended structure:

```text
backend/
└── llm/
    ├── base.py
    ├── gateway.py
    ├── schemas.py
    └── providers/
        ├── gemini.py
        ├── openrouter.py
        └── ollama.py
```

Provider implementations may be added incrementally.

## 8.1 LLM cost principle

Do not send every job to an expensive LLM.

Use a staged pipeline:

```text
Raw jobs
   |
Deterministic filtering
   |
Embeddings / similarity
   |
Candidate shortlist
   |
LLM analysis
   |
Deep reasoning only for strongest candidates
```

---

# 9. Candidate Intelligence

## 9.1 Candidate profile

Candidate profile should contain:

- basic profile;
- career history;
- target roles;
- location preferences;
- work-mode preferences;
- salary preferences where provided;
- experience;
- projects;
- certifications;
- verified skills;
- learning skills;
- target skills;
- rejected/not-relevant skills.

## 9.2 Resume Fact Bank

The resume must not be treated as one unstructured document only.

Create structured facts:

```text
Experience
Project
Skill
Achievement
Certification
Technology
Responsibility
Metric
```

Each fact should have provenance where practical.

Example:

```text
Skill: AWS S3
Status: VERIFIED
Source: Resume / Candidate confirmation
```

---

# 10. Skill State Model

A skill may have one of these states:

```text
VERIFIED
CLAIMED
LEARNING
TARGET
NOT_RELEVANT
```

## Rules

Only VERIFIED skills may automatically be represented as existing candidate experience.

If a JD contains a missing skill, the system must not silently add it.

Instead it should identify it as a skill gap.

If the candidate says they have experience, collect evidence and update the skill.

If they do not have experience, it can become TARGET or LEARNING, but must not be represented as existing experience.

---

# 11. Multiple Career/Search Profiles

The candidate is not restricted to one role.

Examples:

```text
AWS Data Engineer
Python Backend Developer
Python Application Developer
SQL Developer
Cloud Application Engineer
```

A user may create multiple search profiles.

Each profile can contain:
- role names;
- alternative role names;
- required skills;
- preferred skills;
- excluded skills;
- locations;
- remote/hybrid/onsite preference;
- salary preference;
- experience range;
- job freshness preference;
- custom natural-language description.

---

# 12. Career Intent Agent

Input:

> "I want something around Python and AWS, but I am not sure what exact role."

Output:

```text
Possible roles:
- Python Backend Engineer
- AWS Application Developer
- Cloud Application Engineer
- AWS Data Engineer
- Python Data Engineer
```

The system must present these as suggestions.

It must not silently create a search profile without user confirmation.

---

# 13. Job Acquisition

Major intended sources:
- LinkedIn
- Naukri
- Indeed

Architecture:

```text
JobAcquisitionService
        |
        +-- NaukriAdapter
        +-- LinkedInAdapter
        +-- IndeedAdapter
```

Each adapter must have a common interface.

Example:

```python
class JobSourceAdapter:
    async def search(self, search_request):
        ...

    async def get_job(self, job_reference):
        ...
```

Do not build platform-specific assumptions into the matching engine.

---

# 14. Browser Automation

Browser automation is a capability layer, not the business logic.

Use Playwright.

The candidate may manually log into a website using their own browser/session.

The system may then perform permitted search/data collection/application assistance through the browser workflow.

Important:
- Do not store raw passwords.
- Do not bypass CAPTCHA.
- Do not bypass security controls.
- Respect platform terms and technical restrictions.
- When automation cannot safely or appropriately continue, hand control back to the user.

The application workflow must support:

```text
AUTOMATED
HUMAN_REVIEW_REQUIRED
HUMAN_HANDOFF
COMPLETED
FAILED
```

---

# 15. Job Data Model

Normalize all sources into a common job representation.

Minimum fields:

```text
job_id
source
source_job_id
title
company
location
work_mode
employment_type
salary
description
requirements
preferred_skills
required_skills
experience_requirement
posted_at
first_seen_at
last_seen_at
application_url
raw_content_reference
content_hash
status
```

---

# 16. Job Deduplication

The same job may appear on multiple platforms.

Deduplication should use multiple signals:

1. Source job ID where available.
2. Canonical application URL.
3. Company + normalized title + location.
4. Description similarity.
5. Content hash for exact duplicates.

Never assume two jobs are duplicates based only on title.

---

# 17. Job Freshness

Use:

```text
<24 hours      VERY_FRESH
1–3 days       FRESH
4–7 days       RECENT
8–14 days      OLDER
>14 days       LOW_PRIORITY
```

Freshness is one ranking factor, not the only factor.

---

# 18. Job Understanding

Extract:
- job title;
- role family;
- seniority;
- required skills;
- preferred skills;
- responsibilities;
- years of experience;
- education requirements;
- location;
- work mode;
- salary;
- employment type;
- certifications;
- domain requirements;
- implicit technical requirements where confidently inferable.

The extraction result must be structured and validated.

---

# 19. Matching Engine

Do not produce only:

```text
87% match
```

Produce explainable dimensions.

```text
Current Fit
Skill Gaps
Transferable Skills
Role Alignment
Experience Alignment
Location Alignment
Other Constraints
```

Example:

```text
Current Fit:
Python ✓
AWS ✓
SQL ✓
Spark ✓

Skill Gaps:
Airflow
Snowflake

Transferable:
Existing AWS data pipeline experience
Existing Spark experience
```

The system should provide evidence for important conclusions.

---

# 20. Matching Pipeline

Recommended:

```text
Candidate
    +
Search Profile
    +
Normalized Job
        |
        v
Hard filters
        |
        v
Keyword / rule matching
        |
        v
Embedding similarity
        |
        v
Structured requirement comparison
        |
        v
LLM reasoning for shortlisted jobs
        |
        v
Explainable match result
```

Do not rely entirely on an LLM.

---

# 21. Resume Tailoring

## 21.1 Master resume

Maintain a canonical master resume.

A tailored resume is a derived artifact.

```text
Master Resume
     +
Candidate Facts
     +
Job Description
     +
Search Profile
     |
     v
Tailoring Engine
     |
     v
JD-specific Resume
```

## 21.2 Tailoring rules

The system may:
- reorder sections;
- reorder skills;
- emphasize relevant projects;
- rewrite wording;
- improve clarity;
- use JD terminology where truthful;
- select more relevant bullets;
- modify the summary;
- remove less relevant information.

The system must NOT:
- invent experience;
- invent projects;
- invent employers;
- invent metrics;
- claim unverified skills;
- change the candidate's fundamental career history;
- turn target/learning skills into existing skills.

## 21.3 Minimal-change principle

The tailored resume should remain recognizably the candidate's resume.

It should not become a completely different resume for every JD.

---

# 22. New Skill Confirmation Workflow

If a JD requires a skill that is not verified:

```text
Skill detected:
Airflow

Current status:
Not present in verified profile.

Question:
Do you have actual experience with Airflow?

Options:
1. Yes — provide/confirm evidence
2. No — mark as target
3. No — ignore for this search
```

Only after confirmation may the system update the candidate's verified profile.

---

# 23. Resume Validation

Every generated resume should pass validation.

Checks:
- no invented employers;
- no invented dates;
- no invented projects;
- no invented skills;
- no invented metrics;
- no unsupported claims;
- original career history preserved;
- required sections present;
- JD keywords used only when supported.

---

# 24. Application Workflow

Hybrid model:

```text
Job
 |
Match
 |
Resume tailored
 |
Application prepared
 |
+-------------------------------+
|                               |
v                               v
Automation permitted       Human approval
|                               |
v                               v
Automated action            Human handoff
|                               |
+---------------+---------------+
                |
                v
        Application Tracker
```

The system should never assume that because the user is logged in, unlimited automation is appropriate.

---

# 25. Application Tracking

Minimum lifecycle:

```text
DISCOVERED
SHORTLISTED
REVIEWED
RESUME_PREPARED
APPLICATION_PREPARED
APPLIED
RECRUITER_CONTACTED
INTERVIEW
REJECTED
OFFER
WITHDRAWN
```

Store:
- job;
- candidate;
- search profile;
- resume version;
- application date;
- source;
- status;
- notes;
- user feedback.

---

# 26. Feedback Loop

Future matching quality should improve from application outcomes.

Track:

```text
Job
Search Profile
Match Explanation
Resume Version
Applied?
Response?
Interview?
Outcome
```

Eventually analyze:
- which roles produce interviews;
- which job sources produce useful jobs;
- which skills repeatedly appear;
- which gaps occur repeatedly;
- which resume tailoring patterns correlate with responses.

Do not infer causation from small samples.

---

# 27. Database Design Principles

Use PostgreSQL.

Initial logical entities:

```text
users
candidate_profiles
career_profiles
resume_documents
resume_facts
skills
candidate_skills
jobs
job_skills
job_sources
job_matches
resume_versions
applications
application_events
llm_runs
```

Use foreign keys and timestamps.

Do not over-normalize before there is a demonstrated need.

---

# 28. API Design Principles

Use REST initially.

Example groups:

```text
/api/v1/candidate
/api/v1/career-profiles
/api/v1/resumes
/api/v1/jobs
/api/v1/matches
/api/v1/applications
/api/v1/search
```

Keep domain logic out of route handlers.

Recommended flow:

```text
Router
  |
Service
  |
Repository
  |
Database
```

---

# 29. Repository Structure

Recommended starting structure:

```text
career-copilot/
|
├── docs/
│   ├── PROJECT.md
│   ├── BUILD_PLAN.md
│   ├── ROADMAP.md
│   ├── CURRENT_TASK.md
│   ├── DECISIONS.md
│   └── SESSION_LOG.md
|
├── .agents/
│   └── skills/
│       └── career-copilot-development/
│           └── SKILL.md
|
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── candidate/
│   │   ├── career_profiles/
│   │   ├── resumes/
│   │   ├── jobs/
│   │   ├── matching/
│   │   ├── applications/
│   │   ├── browser/
│   │   ├── llm/
│   │   └── common/
│   |
│   └── tests/
|
├── frontend/
├── docker/
├── scripts/
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# 30. Development Operating Model

The project must be built in small tasks.

Never assign:

> "Build the matching engine."

Instead split it:

```text
MATCH-001 Create matching domain model
MATCH-002 Create skill comparison utility
MATCH-003 Implement hard requirement matching
MATCH-004 Implement skill gap detection
MATCH-005 Implement transferable skill representation
MATCH-006 Add embedding similarity
MATCH-007 Add LLM reasoning
MATCH-008 Create match explanation
MATCH-009 Add matching tests
MATCH-010 Integration test
```

Each task should have:
- objective;
- inputs;
- expected outputs;
- files/modules;
- dependencies;
- acceptance criteria;
- tests;
- known constraints.

---

# 31. Development Tracker

The project uses six lightweight context files.

## PROJECT.md

Stable project context.

## BUILD_PLAN.md

Detailed engineering specification and task definitions.

## ROADMAP.md

Completion checklist.

## CURRENT_TASK.md

Only the active task.

## DECISIONS.md

Architectural decisions.

## SESSION_LOG.md

Short record of what happened during each coding session.

These files are the project's persistent memory.

---

# 32. Agent Context Rules

The coding agent should read:

At project start:

```text
PROJECT.md
BUILD_PLAN.md
ROADMAP.md
DECISIONS.md
CURRENT_TASK.md
```

During normal implementation:

```text
PROJECT.md
CURRENT_TASK.md
relevant source files
relevant tests
DECISIONS.md when needed
```

Do not load the entire project into context unnecessarily.

---

# 33. Mandatory Coding-Agent Rules

The coding agent MUST:

1. Read `CURRENT_TASK.md` before coding.
2. Understand existing implementation before modifying it.
3. Implement only the current task.
4. Avoid unrelated refactoring.
5. Avoid introducing unnecessary dependencies.
6. Write/update tests with implementation.
7. Run relevant tests.
8. Preserve working functionality.
9. Never fabricate candidate information.
10. Never add unverified candidate skills.
11. Never silently expand task scope.
12. Update project trackers after completing the task.
13. Record blockers.
14. Stop when acceptance criteria are met.

---

# 34. Task Completion Protocol

When a task is complete:

```text
1. Run relevant tests.
2. Run formatting/linting if configured.
3. Verify acceptance criteria.
4. Update ROADMAP.md.
5. Update CURRENT_TASK.md.
6. Append a short SESSION_LOG.md entry.
7. Identify the next task.
8. Stop.
```

The agent must not automatically begin the next major task.

---

# 35. Model Usage Strategy

Use the cheapest capable model.

## Low complexity

Use a fast/cheap model for:
- boilerplate;
- CRUD;
- configuration;
- simple tests;
- documentation;
- formatting.

## Medium complexity

Use a stronger/medium reasoning model for:
- normal feature implementation;
- database relationships;
- integrations;
- debugging;
- browser workflows.

## High complexity

Use the strongest available reasoning model for:
- architecture;
- difficult bugs;
- matching design;
- resume integrity;
- security;
- major refactoring;
- code review.

Do not use the strongest model for every task.

---

# 36. UI Strategy

UI is secondary.

V1 UI should support:
1. Candidate profile.
2. Search profiles.
3. Job list.
4. Job details.
5. Match explanation.
6. Resume tailoring/review.
7. Application tracking.

Avoid advanced design work until backend workflows are proven.

---

# 37. Testing Strategy

Testing is mandatory.

## Unit tests

For:
- skill classification;
- job normalization;
- deduplication;
- freshness;
- matching;
- resume validation;
- state transitions.

## Integration tests

For:
- database;
- API;
- job ingestion;
- LLM gateway;
- browser adapter interfaces.

## End-to-end tests

Only for critical workflows.

Example:

```text
Create candidate
    |
Create career profile
    |
Ingest job
    |
Analyze job
    |
Match candidate
    |
Generate tailored resume
    |
Track application
```

---

# 38. Security Principles

Never commit:
- passwords;
- API keys;
- browser session secrets;
- cookies;
- tokens;
- personal credentials.

Use `.env` locally.

Commit only `.env.example`.

Browser session data must be treated as sensitive.

---

# 39. Observability

V1 should have basic:
- structured logs;
- request IDs where useful;
- error logging;
- LLM usage logging;
- job ingestion logs;
- browser workflow logs.

Track LLM calls:

```text
provider
model
operation
input token estimate if available
output token estimate if available
latency
success/failure
```

Do not store sensitive prompts or candidate information unnecessarily.

---

# 40. Cost Control

Cost controls should exist before production.

Track:

```text
LLM requests
LLM tokens
provider
model
estimated cost
jobs processed
jobs deeply analyzed
resume generations
```

Use caching where safe.

Avoid re-analyzing identical job descriptions.

Use content hashes.

---

# 41. Implementation Phases

## Phase 0 — Foundation

- Repository
- Python project
- FastAPI
- Docker
- PostgreSQL
- pgvector
- configuration
- logging
- testing
- tracker files

## Phase 1 — Candidate Intelligence

- Candidate profile
- Resume document
- Resume facts
- Skills
- Skill states
- Candidate skill relationships

## Phase 2 — Career/Search Profiles

- Search profile
- Multiple target roles
- Natural-language career intent
- Role expansion
- Search preferences

## Phase 3 — Job Pipeline

- Job model
- Source model
- Job ingestion interface
- Normalization
- Deduplication
- Freshness
- Storage

## Phase 4 — Job Understanding

- JD extraction
- Requirement classification
- Skill extraction
- Experience extraction
- Work-mode extraction

## Phase 5 — Matching

- Hard filters
- Skill matching
- Gap detection
- Transferability
- Embedding similarity
- LLM reasoning
- Explainability

## Phase 6 — Resume Intelligence

- Master resume
- Resume facts
- JD-aware selection
- Tailoring
- Keyword alignment
- Validation
- Human review

## Phase 7 — Browser Acquisition

- Playwright foundation
- Browser profile
- Manual authentication
- Platform adapter interface
- Naukri
- LinkedIn
- Indeed

## Phase 8 — Application Assistance

- Application preparation
- Form mapping
- Human handoff
- Permitted automation
- Application state

## Phase 9 — Tracking & Feedback

- Application history
- Outcomes
- User feedback
- Search performance
- Skill gap analytics

## Phase 10 — V1 Stabilization

- Security
- Error handling
- Cost optimization
- Test coverage
- Documentation
- Backup/recovery

---

# 42. Future Direction — Explicitly Not V1

If V1 proves useful, possible future evolution:

```text
Modular Monolith
      |
      v
Measure actual bottlenecks
      |
      v
Extract only necessary services
      |
      v
AWS deployment
      |
      v
Optional agent runtime/platform
      |
      v
Multi-user product
```

Possible future AWS components:
- ECS/Fargate
- RDS PostgreSQL
- S3
- SQS
- EventBridge
- Secrets Manager
- CloudWatch
- Cognito
- AgentCore or equivalent agent infrastructure

These are future options, not V1 requirements.

---

# 43. Definition of V1 Success

V1 is successful when the user can:

```text
1. Define multiple career targets.
2. Maintain a verified candidate profile.
3. Provide/import a master resume.
4. Ingest jobs.
5. See normalized jobs.
6. Identify duplicates.
7. Understand job requirements.
8. See current fit.
9. See skill gaps.
10. See transferable skills.
11. Understand why a job is recommended.
12. Generate a minimally tailored resume.
13. Verify the changes.
14. Prepare an application.
15. Track the application.
```

The system does NOT need fully autonomous application submission to be considered a successful V1.

---

# 44. Immediate Development Order

The first implementation tasks should be:

```text
FOUND-001 Repository initialization
FOUND-002 Python project configuration
FOUND-003 FastAPI application skeleton
FOUND-004 Environment configuration
FOUND-005 Docker Compose
FOUND-006 PostgreSQL
FOUND-007 pgvector
FOUND-008 Database connection
FOUND-009 Alembic
FOUND-010 Logging
FOUND-011 pytest
FOUND-012 Health endpoint
FOUND-013 Base project error handling
FOUND-014 Agent development skill
FOUND-015 Tracker validation
```

Only after these pass should we begin candidate intelligence.

---

# 45. AI Coding Agent Startup Prompt

Use this when starting Antigravity:

```text
You are the implementation agent for the Career Copilot project.

Before making any changes:

1. Read docs/PROJECT.md.
2. Read docs/BUILD_PLAN.md.
3. Read docs/ROADMAP.md.
4. Read docs/DECISIONS.md.
5. Read docs/CURRENT_TASK.md.
6. Review the existing repository structure and relevant implementation.

Your source of truth is the project documentation and current repository state.

Execute ONLY the task specified in CURRENT_TASK.md.

Do not:
- implement future tasks;
- introduce microservices;
- introduce unnecessary infrastructure;
- rewrite working code without a reason;
- add dependencies without justification;
- fabricate candidate information;
- silently add unverified candidate skills;
- expand scope.

For the current task:

1. Understand the acceptance criteria.
2. Inspect existing code before modifying it.
3. Implement the smallest clean solution.
4. Add/update tests.
5. Run relevant tests.
6. Fix failures caused by your changes.
7. Verify the acceptance criteria.
8. Update docs/ROADMAP.md.
9. Update docs/CURRENT_TASK.md.
10. Append a concise entry to docs/SESSION_LOG.md.
11. Report what was changed, tests run, blockers, and the recommended next task.
12. Stop.

Do not start the next task automatically.
```

---

# 46. Resume-After-Interruption Prompt

For the next day/session:

```text
Resume the Career Copilot project.

Read:
- docs/PROJECT.md
- docs/CURRENT_TASK.md
- docs/ROADMAP.md
- docs/DECISIONS.md
- the latest entry in docs/SESSION_LOG.md

Inspect the current repository state and git diff/status.

Continue ONLY the current task in CURRENT_TASK.md.

Do not redo completed work.

Run the relevant tests before making assumptions about the implementation.

When the current task is complete:
- update the tracker;
- record the session;
- identify the next task;
- stop.
```

---

# 47. Final Engineering Principle

The project should follow:

> **Small task → implement → test → verify → record → stop → resume.**

The goal is not to build the entire system in one AI session.

The goal is to make every session produce a small, verified, recoverable improvement.

# Architecture Decision Records (ADRs)

## ADR-001: Modular Monolith vs Microservices
- **Date**: 2026-10-02
- **Status**: Accepted
- **Context**: Career Copilot needs clear domain boundaries (candidate, jobs, matching, resumes, applications) without unnecessary distributed system complexity or networking overhead in V1.
- **Decision**: Implement a Modular Monolith architecture in FastAPI with clean domain package separation (`app/candidate`, `app/jobs`, `app/matching`, etc.) under a unified application context.
- **Consequences**: Easy local development and testing, unified transactions, zero RPC latency, while keeping clean boundaries for potential future extraction.

---

## ADR-002: PostgreSQL + pgvector for Hybrid Data & Semantic Search
- **Date**: 2026-10-02
- **Status**: Accepted
- **Context**: The system requires structured relational storage (profiles, facts, applications, tracking) alongside vector embeddings for semantic job description and skill matching.
- **Decision**: Use PostgreSQL 16 with the `pgvector` extension as the single unified persistence engine.
- **Consequences**: Avoids managing and paying for a separate vector database (e.g. Pinecone/Qdrant) during V1, enabling atomic joins between relational and vector queries.

---

## ADR-003: LLM Provider Abstraction Gateway
- **Date**: 2026-10-02
- **Status**: Accepted
- **Context**: Business code should not be tightly coupled to a single vendor SDK (e.g., Google GenAI, OpenAI, or local Ollama).
- **Decision**: Create an internal gateway interface (`app/llm/base.py` and `app/llm/gateway.py`) that abstracts model calls, handles fallbacks, and tracks token usage.
- **Consequences**: Can switch or mix providers seamlessly based on cost/latency requirements without altering domain logic.

---

## ADR-004: Zero-Hallucination & Verified Skill State Machine
- **Date**: 2026-10-02
- **Status**: Accepted
- **Context**: Generative AI tools frequently invent fake candidate experience or skills to match a job description.
- **Decision**: Enforce a strict state machine on all skills (`VERIFIED`, `CLAIMED`, `LEARNING`, `TARGET`, `NOT_RELEVANT`). Only `VERIFIED` skills and facts can be written to generated resumes.
- **Consequences**: Absolute truth integrity in generated job applications. Missing requirements are recorded as skill gaps, not fabricated experience.

---

## ADR-005: User Data Storage, Local Persistence & UI-Driven Search Criteria Control
- **Date**: 2026-10-03
- **Status**: Accepted
- **Context**: Users need transparent data storage, automated parsing of uploaded resume PDFs into searchable keywords and target roles, local file preservation in the repository, and full UI agency to add/edit keywords, target roles, and search filters.
- **Decision**: 
  1. Store user-uploaded PDF resumes in `data/uploads/resumes/` and support local JSON snapshots/exports in `data/exports/`.
  2. Parse uploaded resumes to extract structured facts, keywords, and inferred target titles, feeding them into `CandidateProfile` and `CareerProfile` search targets.
  3. Support Docker PostgreSQL + pgvector for relational/semantic storage with local JSON export/import capability.
  4. Provide full UI controls allowing users to interactively add, modify, and refine keywords, target job titles, locations, salary filters, and skill states.
- **Consequences**: User data is preserved locally in the repo, fully customizable from the UI, and transparently synced with both the database and local files.


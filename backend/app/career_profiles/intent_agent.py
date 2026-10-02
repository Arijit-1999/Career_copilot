"""Career Intent Expansion Agent with token-efficient deterministic ontology."""

import re
from typing import List, Dict, Set, Tuple
from app.career_profiles.schemas import IntentExpansionResponse, SuggestedRoleDetail


# Curated Tech & Role Ontology
ROLE_TAXONOMY: Dict[str, Dict] = {
    "Python Backend Engineer": {
        "keywords": ["python", "fastapi", "django", "flask", "backend", "rest", "api", "sqlalchemy", "asyncio", "postgres", "sql"],
        "core_skills": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL", "Docker", "REST APIs"],
        "alternatives": ["Python Application Developer", "Backend Developer", "Cloud Application Engineer", "Python Microservices Developer"],
        "category": "Backend"
    },
    "AWS Data Engineer": {
        "keywords": ["aws", "data", "pipeline", "etl", "s3", "glue", "redshift", "spark", "pyspark", "athena", "lambda", "airflow"],
        "core_skills": ["Python", "AWS", "PySpark", "SQL", "AWS Glue", "AWS Redshift", "Airflow"],
        "alternatives": ["Data Platform Engineer", "Cloud Data Engineer", "Python Data Engineer", "Big Data Developer"],
        "category": "Data Engineering"
    },
    "Cloud Application Engineer": {
        "keywords": ["cloud", "aws", "azure", "gcp", "serverless", "lambda", "docker", "microservices", "cloud-native"],
        "core_skills": ["Python", "AWS", "Docker", "Serverless", "Terraform", "CI/CD"],
        "alternatives": ["AWS Solutions Engineer", "Backend Cloud Developer", "Platform Software Engineer"],
        "category": "Cloud"
    },
    "AI / GenAI Application Developer": {
        "keywords": ["ai", "genai", "llm", "rag", "langchain", "embeddings", "vector", "pgvector", "openai", "gemini", "prompt"],
        "core_skills": ["Python", "FastAPI", "LLM APIs", "RAG Architecture", "Vector Databases", "LangChain"],
        "alternatives": ["GenAI Engineer", "AI Solutions Developer", "Applied AI Engineer"],
        "category": "AI / ML"
    },
    "Full Stack Python Developer": {
        "keywords": ["full stack", "fullstack", "react", "vue", "javascript", "frontend", "typescript", "ui", "html", "css"],
        "core_skills": ["Python", "FastAPI", "JavaScript", "TypeScript", "React", "PostgreSQL"],
        "alternatives": ["Web Application Developer", "Full Stack Software Engineer"],
        "category": "Full Stack"
    },
    "DevOps / Platform Engineer": {
        "keywords": ["devops", "ci/cd", "kubernetes", "k8s", "docker", "terraform", "helm", "ansible", "jenkins", "github actions"],
        "core_skills": ["Docker", "Kubernetes", "Terraform", "CI/CD", "Linux", "Python/Bash"],
        "alternatives": ["Site Reliability Engineer (SRE)", "Cloud Infrastructure Engineer"],
        "category": "DevOps"
    }
}


class CareerIntentAgent:
    """Expands natural language career goals into structured target roles without wasteful LLM calls."""

    @staticmethod
    def expand_intent(query: str) -> IntentExpansionResponse:
        """Analyzes query against the ontology and returns ranked role suggestions."""
        normalized_text = query.lower()
        words = set(re.findall(r"\b[a-z0-9+#.-]+\b", normalized_text))

        role_scores: List[Tuple[str, float, Dict]] = []

        for role_title, meta in ROLE_TAXONOMY.items():
            matched_keywords = [kw for kw in meta["keywords"] if kw in normalized_text or kw in words]
            if matched_keywords:
                # Calculate relevance score based on keyword coverage
                score = min(1.0, len(matched_keywords) / max(2.5, len(meta["keywords"]) * 0.4))
                role_scores.append((role_title, score, meta))

        # Sort by score descending
        role_scores.sort(key=lambda x: x[1], reverse=True)

        if not role_scores:
            # Fallback to general software engineering if no specific match
            role_scores = [
                ("Python Backend Engineer", 0.6, ROLE_TAXONOMY["Python Backend Engineer"]),
                ("Cloud Application Engineer", 0.5, ROLE_TAXONOMY["Cloud Application Engineer"])
            ]

        primary_roles: List[str] = []
        alternative_roles_set: Set[str] = set()
        recommended_skills_set: Set[str] = set()
        role_details: List[SuggestedRoleDetail] = []

        for role_title, score, meta in role_scores[:3]:
            primary_roles.append(role_title)
            for alt in meta["alternatives"]:
                alternative_roles_set.add(alt)
            for sk in meta["core_skills"]:
                recommended_skills_set.add(sk)

            role_details.append(
                SuggestedRoleDetail(
                    role_title=role_title,
                    relevance_score=round(score, 2),
                    primary_skills=meta["core_skills"],
                    rationale=f"High alignment with keywords detected in career intent query ({meta['category']})."
                )
            )

        # Remove primary roles from alternatives
        for p in primary_roles:
            alternative_roles_set.discard(p)

        return IntentExpansionResponse(
            original_query=query,
            primary_roles=primary_roles,
            alternative_roles=sorted(list(alternative_roles_set))[:5],
            recommended_skills=sorted(list(recommended_skills_set)),
            role_details=role_details,
            expansion_method="deterministic_ontology"
        )

"""Deterministic, zero-token skill tagger, section segmenter, and seniority analyzer."""

import re
from typing import Dict, List, Optional, Set, Tuple
from app.extraction.enums import (
    SeniorityLevel,
    RequirementCategory,
    RequirementImportance
)
from app.extraction.schemas import ExtractedRequirement, JobUnderstandingResult


# Comprehensive Canonical Skill & Tech Dictionary
# format: canonical_name -> (aliases/regex_terms, category, default_display_name)
SKILL_ONTOLOGY = {
    # Programming Languages
    "python": (["python", "py3"], RequirementCategory.LANGUAGE, "Python"),
    "javascript": (["javascript", "js", "ecmascript"], RequirementCategory.LANGUAGE, "JavaScript"),
    "typescript": (["typescript", "ts"], RequirementCategory.LANGUAGE, "TypeScript"),
    "golang": (["golang", "go"], RequirementCategory.LANGUAGE, "Go"),
    "rust": (["rust"], RequirementCategory.LANGUAGE, "Rust"),
    "java": (["java"], RequirementCategory.LANGUAGE, "Java"),
    "c++": (["c\\+\\+", "cpp"], RequirementCategory.LANGUAGE, "C++"),
    "c#": (["c#", "csharp", "\\.net"], RequirementCategory.LANGUAGE, "C#"),
    "sql": (["sql", "t-sql", "pl-sql", "plsql"], RequirementCategory.LANGUAGE, "SQL"),
    "scala": (["scala"], RequirementCategory.LANGUAGE, "Scala"),
    "ruby": (["ruby", "ruby on rails"], RequirementCategory.LANGUAGE, "Ruby"),
    "kotlin": (["kotlin"], RequirementCategory.LANGUAGE, "Kotlin"),
    "swift": (["swift"], RequirementCategory.LANGUAGE, "Swift"),

    # Web & Backend Frameworks
    "fastapi": (["fastapi", "fast-api"], RequirementCategory.FRAMEWORK, "FastAPI"),
    "django": (["django", "drf", "django rest framework"], RequirementCategory.FRAMEWORK, "Django"),
    "flask": (["flask"], RequirementCategory.FRAMEWORK, "Flask"),
    "react": (["react", "reactjs", "react.js"], RequirementCategory.FRAMEWORK, "React"),
    "next.js": (["nextjs", "next.js", "next js"], RequirementCategory.FRAMEWORK, "Next.js"),
    "vue": (["vue", "vuejs", "vue.js"], RequirementCategory.FRAMEWORK, "Vue.js"),
    "angular": (["angular", "angularjs"], RequirementCategory.FRAMEWORK, "Angular"),
    "node.js": (["nodejs", "node.js", "node"], RequirementCategory.FRAMEWORK, "Node.js"),
    "express": (["express", "expressjs", "express.js"], RequirementCategory.FRAMEWORK, "Express"),
    "nest.js": (["nestjs", "nest.js"], RequirementCategory.FRAMEWORK, "NestJS"),
    "spring boot": (["spring boot", "springboot", "spring framework"], RequirementCategory.FRAMEWORK, "Spring Boot"),
    "graphql": (["graphql", "apollo"], RequirementCategory.FRAMEWORK, "GraphQL"),
    "grpc": (["grpc", "protobuf"], RequirementCategory.FRAMEWORK, "gRPC"),

    # Databases & Storage
    "postgresql": (["postgresql", "postgres", "psql"], RequirementCategory.DATABASE, "PostgreSQL"),
    "mysql": (["mysql"], RequirementCategory.DATABASE, "MySQL"),
    "mongodb": (["mongodb", "mongo"], RequirementCategory.DATABASE, "MongoDB"),
    "redis": (["redis"], RequirementCategory.DATABASE, "Redis"),
    "elasticsearch": (["elasticsearch", "elastic search", "opensearch"], RequirementCategory.DATABASE, "Elasticsearch"),
    "dynamodb": (["dynamodb", "dynamo db"], RequirementCategory.DATABASE, "DynamoDB"),
    "cassandra": (["cassandra"], RequirementCategory.DATABASE, "Cassandra"),
    "snowflake": (["snowflake"], RequirementCategory.DATABASE, "Snowflake"),
    "bigquery": (["bigquery", "big query"], RequirementCategory.DATABASE, "BigQuery"),
    "sqlite": (["sqlite"], RequirementCategory.DATABASE, "SQLite"),

    # Vector Databases & Search
    "pgvector": (["pgvector"], RequirementCategory.VECTOR_SEARCH, "pgvector"),
    "pinecone": (["pinecone"], RequirementCategory.VECTOR_SEARCH, "Pinecone"),
    "qdrant": (["qdrant"], RequirementCategory.VECTOR_SEARCH, "Qdrant"),
    "weaviate": (["weaviate"], RequirementCategory.VECTOR_SEARCH, "Weaviate"),
    "chromadb": (["chroma", "chromadb"], RequirementCategory.VECTOR_SEARCH, "ChromaDB"),
    "faiss": (["faiss"], RequirementCategory.VECTOR_SEARCH, "FAISS"),
    "milvus": (["milvus"], RequirementCategory.VECTOR_SEARCH, "Milvus"),

    # Cloud, DevOps & Infrastructure
    "aws": (["aws", "amazon web services"], RequirementCategory.CLOUD_DEVOPS, "AWS"),
    "azure": (["azure", "microsoft azure"], RequirementCategory.CLOUD_DEVOPS, "Azure"),
    "gcp": (["gcp", "google cloud", "google cloud platform"], RequirementCategory.CLOUD_DEVOPS, "GCP"),
    "docker": (["docker", "containerization", "containers"], RequirementCategory.CLOUD_DEVOPS, "Docker"),
    "kubernetes": (["kubernetes", "k8s"], RequirementCategory.CLOUD_DEVOPS, "Kubernetes"),
    "terraform": (["terraform", "iac", "infrastructure as code"], RequirementCategory.CLOUD_DEVOPS, "Terraform"),
    "ansible": (["ansible"], RequirementCategory.CLOUD_DEVOPS, "Ansible"),
    "ci/cd": (["ci/cd", "cicd", "github actions", "gitlab ci", "jenkins"], RequirementCategory.CLOUD_DEVOPS, "CI/CD"),
    "linux": (["linux", "ubuntu", "debian", "centos"], RequirementCategory.CLOUD_DEVOPS, "Linux"),
    "kafka": (["kafka", "apache kafka"], RequirementCategory.CLOUD_DEVOPS, "Kafka"),
    "rabbitmq": (["rabbitmq", "rabbit mq"], RequirementCategory.CLOUD_DEVOPS, "RabbitMQ"),

    # AI, ML & LLM Engineering
    "llm": (["llm", "llms", "large language models", "generative ai", "genai", "gen-ai"], RequirementCategory.AI_ML, "LLM / Generative AI"),
    "langchain": (["langchain", "langgraph"], RequirementCategory.AI_ML, "LangChain"),
    "llamaindex": (["llamaindex", "llama-index"], RequirementCategory.AI_ML, "LlamaIndex"),
    "rag": (["rag", "retrieval augmented generation", "retrieval-augmented generation"], RequirementCategory.AI_ML, "RAG"),
    "pytorch": (["pytorch", "torch"], RequirementCategory.AI_ML, "PyTorch"),
    "tensorflow": (["tensorflow", "keras"], RequirementCategory.AI_ML, "TensorFlow"),
    "scikit-learn": (["scikit-learn", "sklearn"], RequirementCategory.AI_ML, "scikit-learn"),
    "pandas": (["pandas"], RequirementCategory.AI_ML, "Pandas"),
    "numpy": (["numpy"], RequirementCategory.AI_ML, "NumPy"),
    "huggingface": (["huggingface", "hugging face", "transformers"], RequirementCategory.AI_ML, "Hugging Face"),
    "prompt engineering": (["prompt engineering", "prompt optimization"], RequirementCategory.AI_ML, "Prompt Engineering"),
    "agentic workflows": (["agentic", "ai agents", "autonomous agents", "multi-agent"], RequirementCategory.AI_ML, "AI Agents"),

    # Tools & Methodologies
    "git": (["git", "github", "gitlab"], RequirementCategory.TOOL, "Git"),
    "playwright": (["playwright"], RequirementCategory.TOOL, "Playwright"),
    "selenium": (["selenium"], RequirementCategory.TOOL, "Selenium"),
    "pytest": (["pytest", "unit testing", "tdd"], RequirementCategory.TOOL, "Pytest"),
    "microservices": (["microservices", "microservice architecture", "distributed systems"], RequirementCategory.METHODOLOGY, "Microservices"),
    "system design": (["system design", "scalability", "high concurrency", "low latency"], RequirementCategory.METHODOLOGY, "System Design"),
    "agile": (["agile", "scrum", "kanban"], RequirementCategory.METHODOLOGY, "Agile/Scrum")
}


class DeterministicTagger:
    """Zero-token heuristic parser for job descriptions."""

    def __init__(self):
        # Precompile regexes for fast ontology matching
        self._compiled_skills: List[Tuple[str, re.Pattern, RequirementCategory, str]] = []
        for canonical, (aliases, category, display_name) in SKILL_ONTOLOGY.items():
            pattern_parts = []
            for alias in aliases:
                # Handle special characters like c++, c#, .net
                if "+" in alias or "#" in alias or "." in alias:
                    pattern_parts.append(r"(?:(?<=\s)|(?<=^)|(?<=[(\[,]))" + re.escape(alias) + r"(?=[)\]\s,.;:]|$)")
                else:
                    pattern_parts.append(r"\b" + re.escape(alias) + r"\b")
            combined_pattern = re.compile("|".join(pattern_parts), re.IGNORECASE)
            self._compiled_skills.append((canonical, combined_pattern, category, display_name))

    def segment_sections(self, text: str) -> Dict[str, str]:
        """Splits job description into Requirements, Preferred, Responsibilities, and General."""
        sections: Dict[str, str] = {
            "mandatory": "",
            "preferred": "",
            "responsibilities": "",
            "general": ""
        }

        lines = text.split("\n")
        current_section = "general"

        mandatory_header = re.compile(
            r"^(?:(?:what you bring|what you need|requirements|minimum qualifications|basic qualifications|must have|skills required|qualifications|what we are looking for|who you are)[\s:]*)",
            re.IGNORECASE
        )
        preferred_header = re.compile(
            r"^(?:(?:preferred qualifications|nice to have|good to have|bonus points|preferred skills|additional skills|plus points)[\s:]*)",
            re.IGNORECASE
        )
        responsibilities_header = re.compile(
            r"^(?:(?:responsibilities|what you will do|what you'll do|the role|key responsibilities|day in the life|your mission)[\s:]*)",
            re.IGNORECASE
        )

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if mandatory_header.search(stripped):
                current_section = "mandatory"
                continue
            elif preferred_header.search(stripped):
                current_section = "preferred"
                continue
            elif responsibilities_header.search(stripped):
                current_section = "responsibilities"
                continue

            sections[current_section] += line + "\n"

        return sections

    def infer_seniority(self, title: str, description: str) -> SeniorityLevel:
        """Infers seniority level from job title and description text."""
        combined = f"{title} {description[:400]}".upper()

        if re.search(r"\b(INTERN|INTERNSHIP|TRAINEE|FRESHER)\b", combined):
            return SeniorityLevel.INTERN
        elif re.search(r"\b(DIRECTOR|VP|HEAD OF|CHIEF)\b", combined):
            return SeniorityLevel.DIRECTOR
        elif re.search(r"\b(PRINCIPAL|DISTINGUISHED)\b", combined):
            return SeniorityLevel.PRINCIPAL
        elif re.search(r"\b(STAFF)\b", combined):
            return SeniorityLevel.STAFF
        elif re.search(r"\b(LEAD|TECH LEAD|TEAM LEAD)\b", combined):
            return SeniorityLevel.LEAD
        elif re.search(r"\b(SENIOR|SR\.|SR )\b", combined):
            return SeniorityLevel.SENIOR
        elif re.search(r"\b(JUNIOR|JR\.|JR |ASSOCIATE|ENTRY LEVEL|ENTRY-LEVEL)\b", combined):
            return SeniorityLevel.JUNIOR
        elif re.search(r"\b(MID|MID-LEVEL|INTERMEDIATE)\b", combined):
            return SeniorityLevel.MID

        # Fallback to title keywords
        if "SENIOR" in title.upper() or "SR" in title.upper():
            return SeniorityLevel.SENIOR
        elif "LEAD" in title.upper():
            return SeniorityLevel.LEAD

        return SeniorityLevel.MID

    def extract_experience_range(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Extracts minimum and maximum years of experience mentioned in text."""
        # e.g., "4-7 years of experience", "5 to 8 years", "3+ years"
        range_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:-|TO|\s+TO\s+)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:YEARS|YRS|YR)",
            text,
            re.IGNORECASE
        )
        if range_match:
            return float(range_match.group(1)), float(range_match.group(2))

        single_match = re.search(
            r"(?:MINIMUM|AT LEAST)?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:YEARS|YRS|YR)(?:\s+OF\s+EXPERIENCE)?",
            text,
            re.IGNORECASE
        )
        if single_match:
            val = float(single_match.group(1))
            return val, None

        return None, None

    def extract_education(self, text: str) -> List[str]:
        """Extracts standard degree/education qualifications mentioned in JD."""
        education_matches: List[str] = []
        patterns = [
            (r"\b(?:ph\.?d|doctorate)\b(?:\s+in\s+[a-zA-Z\s,]+)?", "PhD in Computer Science / Related Field"),
            (r"\b(?:master(?:'s)?|ms|m\.?tech|m\.?e\.?|mca)\b(?:\s+degree)?(?:\s+in\s+[a-zA-Z\s,]+)?", "Master's Degree (MS / M.Tech / MCA)"),
            (r"\b(?:bachelor(?:'s)?|bs|b\.?tech|b\.?e\.?|bca)\b(?:\s+degree)?(?:\s+in\s+[a-zA-Z\s,]+)?", "Bachelor's Degree (BS / B.Tech / BE)"),
            (r"\bdegree\s+in\s+(?:computer\s+science|engineering|it|software|stem|related\s+field)\b", "Degree in Computer Science or STEM")
        ]
        text_lower = text.lower()
        for pat, label in patterns:
            if re.search(pat, text_lower) and label not in education_matches:
                education_matches.append(label)
        return education_matches

    def analyze_jd(self, title: str, description: str, company: Optional[str] = None) -> JobUnderstandingResult:
        """Executes zero-token deterministic extraction across job description."""
        seniority = self.infer_seniority(title, description)
        sections = self.segment_sections(description)
        min_exp, max_exp = self.extract_experience_range(description)
        education = self.extract_education(description)

        extracted_reqs: List[ExtractedRequirement] = []
        required_skills: Set[str] = set()
        preferred_skills: Set[str] = set()
        all_tags: Set[str] = set()
        domains: Set[str] = set()

        seen_canonical: Set[str] = set()

        # 1. Match skills in mandatory section
        for canonical, pattern, category, display_name in self._compiled_skills:
            if pattern.search(sections["mandatory"]):
                seen_canonical.add(canonical)
                required_skills.add(display_name)
                all_tags.add(display_name)
                extracted_reqs.append(
                    ExtractedRequirement(
                        skill_name=display_name,
                        canonical_name=canonical,
                        category=category,
                        importance=RequirementImportance.MANDATORY
                    )
                )

        # 2. Match skills in preferred section
        for canonical, pattern, category, display_name in self._compiled_skills:
            if canonical in seen_canonical:
                continue
            if pattern.search(sections["preferred"]):
                seen_canonical.add(canonical)
                preferred_skills.add(display_name)
                all_tags.add(display_name)
                extracted_reqs.append(
                    ExtractedRequirement(
                        skill_name=display_name,
                        canonical_name=canonical,
                        category=category,
                        importance=RequirementImportance.PREFERRED
                    )
                )

        # 3. Match remaining skills in title and entire description
        for canonical, pattern, category, display_name in self._compiled_skills:
            if canonical in seen_canonical:
                continue
            if pattern.search(title) or pattern.search(description):
                seen_canonical.add(canonical)
                # If found in title or general text and not marked preferred, default to required
                required_skills.add(display_name)
                all_tags.add(display_name)
                extracted_reqs.append(
                    ExtractedRequirement(
                        skill_name=display_name,
                        canonical_name=canonical,
                        category=category,
                        importance=RequirementImportance.MANDATORY
                    )
                )

        # Infer broad domains
        cat_counts = {}
        for req in extracted_reqs:
            cat_counts[req.category.value] = cat_counts.get(req.category.value, 0) + 1

        if cat_counts.get("AI_ML", 0) > 0 or cat_counts.get("VECTOR_SEARCH", 0) > 0:
            domains.add("AI & Machine Learning")
        if cat_counts.get("FRAMEWORK", 0) > 0 or cat_counts.get("LANGUAGE", 0) > 0:
            domains.add("Backend Engineering")
        if cat_counts.get("CLOUD_DEVOPS", 0) > 0:
            domains.add("Cloud & Infrastructure")

        # Extract responsibilities snippet lines
        responsibilities = []
        for line in sections["responsibilities"].split("\n"):
            line_clean = line.strip().lstrip("•-*").strip()
            if len(line_clean) > 15:
                responsibilities.append(line_clean)
            if len(responsibilities) >= 5:
                break

        return JobUnderstandingResult(
            seniority=seniority,
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            required_skills=sorted(list(required_skills)),
            preferred_skills=sorted(list(preferred_skills)),
            extracted_tags=sorted(list(all_tags)),
            requirements=extracted_reqs,
            responsibilities=responsibilities,
            education_requirements=education,
            domains=sorted(list(domains)),
            confidence_score=0.95
        )


# Global singleton tagger instance
tagger = DeterministicTagger()

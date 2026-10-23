import re
from typing import List, Dict, Any, Tuple, Optional, Set
from app.schemas.knowledge_graph import ExtractedEntity, ExtractedRelationship

# Canonical Technology Mapping
TECH_ALIASES: Dict[str, str] = {
    "python": "Python",
    "python3": "Python",
    "py": "Python",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "react": "React",
    "reactjs": "React",
    "react.js": "React",
    "vue": "Vue",
    "vuejs": "Vue",
    "angular": "Angular",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node": "Node.js",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "express": "Express",
    "docker": "Docker",
    "dockerfile": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "neo4j": "Neo4j",
    "neo 4j": "Neo4j",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mysql": "MySQL",
    "sqlite": "SQLite",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "Google Cloud",
    "google cloud": "Google Cloud",
    "azure": "Azure",
    "git": "Git",
    "github": "GitHub",
    "graphql": "GraphQL",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "keras": "Keras",
    "scikit-learn": "Scikit-Learn",
    "sklearn": "Scikit-Learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "kafka": "Apache Kafka",
    "celery": "Celery",
    "rabbitmq": "RabbitMQ",
    "alembic": "Alembic",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "vite": "Vite",
    "tailwind": "TailwindCSS",
    "tailwindcss": "TailwindCSS",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    "golang": "Go",
    "rust": "Rust",
    "java": "Java",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "csharp": "C#",
}

# Known Skills Mapping
SKILL_ALIASES: Dict[str, str] = {
    "python": "Python",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "natural language processing": "Natural Language Processing",
    "nlp": "Natural Language Processing",
    "data science": "Data Science",
    "system design": "System Design",
    "microservices": "Microservices",
    "devops": "DevOps",
    "cloud computing": "Cloud Computing",
    "api development": "API Development",
    "full stack development": "Full Stack Development",
    "frontend engineering": "Frontend Engineering",
    "backend engineering": "Backend Engineering",
    "graph algorithms": "Graph Algorithms",
    "database design": "Database Design",
    "sql": "SQL",
    "nosql": "NoSQL",
    "data engineering": "Data Engineering",
    "prompt engineering": "Prompt Engineering",
    "knowledge graphs": "Knowledge Graphs",
    "retrieval augmented generation": "RAG",
    "rag": "RAG",
    "ci/cd": "CI/CD",
    "test driven development": "TDD",
    "agile": "Agile Development",
}

# Known Topics Mapping
TOPIC_ALIASES: Dict[str, str] = {
    "artificial intelligence": "Artificial Intelligence",
    "ai": "Artificial Intelligence",
    "machine learning": "Machine Learning",
    "distributed systems": "Distributed Systems",
    "knowledge management": "Knowledge Management",
    "cybersecurity": "Cybersecurity",
    "graph theory": "Graph Theory",
    "vector search": "Vector Search",
    "information retrieval": "Information Retrieval",
    "software architecture": "Software Architecture",
    "agentic workflows": "Agentic Workflows",
}

# Known Companies
KNOWN_COMPANIES = {
    "google": "Google",
    "meta": "Meta",
    "amazon": "Amazon",
    "apple": "Apple",
    "microsoft": "Microsoft",
    "netflix": "Netflix",
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "deepmind": "Google DeepMind",
    "nvidia": "NVIDIA",
    "stripe": "Stripe",
    "uber": "Uber",
    "airbnb": "Airbnb",
    "github": "GitHub",
    "nexus": "Nexus AI",
}

# Known Job Titles
KNOWN_JOBS = [
    "software engineer",
    "senior software engineer",
    "frontend developer",
    "backend developer",
    "full stack engineer",
    "data scientist",
    "machine learning engineer",
    "ai engineer",
    "devops engineer",
    "product manager",
    "system architect",
    "data engineer",
    "research scientist",
]

class GraphExtractor:
    """Extracts entities and typed relationships from text with normalization and deduplication."""

    @staticmethod
    def normalize_entity_name(name: str, label: str) -> Tuple[str, str]:
        """Returns (canonical_name, normalized_key)."""
        raw = name.strip()
        lowered = raw.lower()

        if label == "Technology":
            canonical = TECH_ALIASES.get(lowered, raw.title())
            return canonical, canonical.lower()

        elif label == "Skill":
            canonical = SKILL_ALIASES.get(lowered, TECH_ALIASES.get(lowered, raw.title()))
            return canonical, canonical.lower()

        elif label == "Topic":
            canonical = TOPIC_ALIASES.get(lowered, raw.title())
            return canonical, canonical.lower()

        elif label == "Company":
            canonical = KNOWN_COMPANIES.get(lowered, raw.title())
            return canonical, canonical.lower()

        elif label == "Job":
            return raw.title(), lowered

        elif label == "Project":
            # Preserve capitalization or title case
            return raw.strip(), lowered

        elif label in ("Task", "Goal", "Event", "Document", "User"):
            return raw.strip(), lowered

        return raw.strip(), lowered

    def extract_entities_and_relationships(
        self,
        text: str,
        user_name: str = "User",
        document_name: Optional[str] = None
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """Run multi-layer entity and relationship extraction over raw text."""
        entities_dict: Dict[Tuple[str, str], ExtractedEntity] = {}
        relationships_set: Set[Tuple[str, str, str, str, str]] = set()
        relationships_list: List[ExtractedRelationship] = []

        def add_entity(label: str, name: str, props: Optional[Dict[str, Any]] = None) -> ExtractedEntity:
            canonical, norm_key = self.normalize_entity_name(name, label)
            key = (label, norm_key)
            if key not in entities_dict:
                entities_dict[key] = ExtractedEntity(
                    label=label,
                    name=canonical,
                    normalized_name=norm_key,
                    properties=props or {}
                )
            elif props:
                entities_dict[key].properties.update(props)
            return entities_dict[key]

        def add_relationship(
            src_label: str, src_name: str,
            rel_type: str,
            tgt_label: str, tgt_name: str,
            props: Optional[Dict[str, Any]] = None
        ):
            src_canon, src_norm = self.normalize_entity_name(src_name, src_label)
            tgt_canon, tgt_norm = self.normalize_entity_name(tgt_name, tgt_label)

            rel_key = (src_label, src_norm, rel_type, tgt_label, tgt_norm)
            if rel_key not in relationships_set:
                relationships_set.add(rel_key)
                relationships_list.append(ExtractedRelationship(
                    source_label=src_label,
                    source_name=src_canon,
                    relationship_type=rel_type,
                    target_label=tgt_label,
                    target_name=tgt_canon,
                    properties=props or {}
                ))

        # Always add the primary User node
        user_entity = add_entity("User", user_name)

        # If document name provided, add Document entity
        doc_entity = None
        if document_name:
            doc_entity = add_entity("Document", document_name, {"source": "upload"})

        # 1. Tech & Skill dictionary scanning
        text_lower = text.lower()
        for tech_alias, canonical_tech in TECH_ALIASES.items():
            pattern = rf'\b{re.escape(tech_alias)}\b'
            if re.search(pattern, text_lower):
                add_entity("Technology", canonical_tech)
                if doc_entity:
                    add_relationship("Document", doc_entity.name, "MENTIONS", "Technology", canonical_tech)

        for skill_alias, canonical_skill in SKILL_ALIASES.items():
            pattern = rf'\b{re.escape(skill_alias)}\b'
            if re.search(pattern, text_lower):
                add_entity("Skill", canonical_skill)
                if doc_entity:
                    add_relationship("Document", doc_entity.name, "MENTIONS", "Skill", canonical_skill)

        for company_alias, canonical_company in KNOWN_COMPANIES.items():
            pattern = rf'\b{re.escape(company_alias)}\b'
            if re.search(pattern, text_lower):
                add_entity("Company", canonical_company)
                if doc_entity:
                    add_relationship("Document", doc_entity.name, "MENTIONS", "Company", canonical_company)

        for topic_alias, canonical_topic in TOPIC_ALIASES.items():
            pattern = rf'\b{re.escape(topic_alias)}\b'
            if re.search(pattern, text_lower):
                add_entity("Topic", canonical_topic)
                if doc_entity:
                    add_relationship("Document", doc_entity.name, "MENTIONS", "Topic", canonical_topic)

        # 2. Relationship Extraction via Semantic Patterns

        # A. USER -> OWNS -> PROJECT
        # e.g., "my project Nexus AI", "project: Nexus AI", "developed Nexus AI", "working on Project Alpha"
        project_patterns = [
            r'(?:my project|project name|working on project|working on|developed project|project:)\s*[:"]?\s*([A-Za-z0-9\s_-]{3,35})(?:["\n,.]|$)',
            r'([A-Za-z0-9\s_-]{3,25})\s+is a project',
            r'(?:project)\s+["\']([^"\']+)["\']',
        ]
        extracted_projects = set()
        for pat in project_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                proj_name = match.group(1).strip()
                if proj_name.lower() not in {"this", "the", "that", "a", "an", "new", "our"}:
                    add_entity("Project", proj_name)
                    add_relationship("User", user_entity.name, "OWNS", "Project", proj_name)
                    extracted_projects.add(proj_name)
                    if doc_entity:
                        add_relationship("Document", doc_entity.name, "DESCRIBES", "Project", proj_name)

        # B. PROJECT -> USES -> TECHNOLOGY
        # e.g., "Nexus AI uses Python, FastAPI, and Neo4j", "built with Python and React", "stack: React, Node.js"
        project_tech_patterns = [
            r'(?:project\s+)?["\']?([A-Za-z0-9\s_-]{2,30})["\']?\s+(?:uses|is built with|built with|utilizes|leverages)\s+([^.\n]+)',
            r'(?:technologies|tech stack|built with|uses)\s*:\s*([^.\n]+)',
        ]
        for pat in project_tech_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                if match.lastindex == 2:
                    p_name = match.group(1).strip()
                    techs_str = match.group(2)
                    proj_cand = p_name if p_name.lower() not in {"we", "it", "this", "system"} else (list(extracted_projects)[0] if extracted_projects else "Nexus AI")
                else:
                    techs_str = match.group(1)
                    proj_cand = list(extracted_projects)[0] if extracted_projects else "Nexus AI"

                add_entity("Project", proj_cand)
                add_relationship("User", user_entity.name, "OWNS", "Project", proj_cand)

                # Split technologies
                for raw_tech in re.split(r'[,|/&]|\band\b', techs_str):
                    clean_t = raw_tech.strip()
                    if clean_t.lower() in TECH_ALIASES:
                        canonical_tech = TECH_ALIASES[clean_t.lower()]
                        add_entity("Technology", canonical_tech)
                        add_relationship("Project", proj_cand, "USES", "Technology", canonical_tech)
                    elif len(clean_t) > 1 and clean_t.lower() not in {"and", "with", "using", "the", "a"}:
                        add_entity("Technology", clean_t)
                        add_relationship("Project", proj_cand, "USES", "Technology", clean_t)

        # Direct sentences like: "Projects: Project Alpha (uses Python)"
        inline_tech_matches = re.finditer(r'([A-Za-z0-9\s_-]+)\s+uses\s+([A-Za-z0-9\s,#+]+)', text, re.IGNORECASE)
        for match in inline_tech_matches:
            subject = match.group(1).strip()
            techs = match.group(2).strip()
            if subject.lower() not in {"he", "she", "it", "who", "they", "user"}:
                add_entity("Project", subject)
                add_relationship("User", user_entity.name, "OWNS", "Project", subject)
                for t in re.split(r'[,&]|\band\b', techs):
                    t_clean = t.strip()
                    if t_clean.lower() in TECH_ALIASES:
                        canon = TECH_ALIASES[t_clean.lower()]
                        add_entity("Technology", canon)
                        add_relationship("Project", subject, "USES", "Technology", canon)
                    elif len(t_clean) > 1:
                        add_entity("Technology", t_clean)
                        add_relationship("Project", subject, "USES", "Technology", t_clean)

        # C. USER -> KNOWS -> SKILL
        # e.g., "User knows Python", "I am proficient in React", "Skills: Python, Machine Learning"
        skill_patterns = [
            r'(?:user knows|i know|skilled in|proficient in|expertise in|experience with|skills? include)\s+([^.\n]+)',
            r'(?:skills|technical skills|core competencies)\s*:\s*([^.\n]+)',
        ]
        for pat in skill_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                skills_str = match.group(1)
                for s in re.split(r'[,|/&]|\band\b', skills_str):
                    s_clean = s.strip()
                    if s_clean.lower() in SKILL_ALIASES:
                        canon_skill = SKILL_ALIASES[s_clean.lower()]
                        add_entity("Skill", canon_skill)
                        add_relationship("User", user_entity.name, "KNOWS", "Skill", canon_skill)
                    elif s_clean.lower() in TECH_ALIASES:
                        canon_tech = TECH_ALIASES[s_clean.lower()]
                        add_entity("Skill", canon_tech)
                        add_relationship("User", user_entity.name, "KNOWS", "Skill", canon_tech)
                    elif len(s_clean) > 2 and s_clean.lower() not in {"and", "or", "the", "with"}:
                        add_entity("Skill", s_clean)
                        add_relationship("User", user_entity.name, "KNOWS", "Skill", s_clean)

        # Direct: "User knows [Skill]"
        direct_knows = re.finditer(r'user\s+knows\s+([A-Za-z0-9#+.\s,]+)', text, re.IGNORECASE)
        for m in direct_knows:
            sk_str = m.group(1).strip()
            for s in re.split(r'[,&]|\band\b', sk_str):
                s_c = s.strip()
                if s_c:
                    add_entity("Skill", s_c)
                    add_relationship("User", user_entity.name, "KNOWS", "Skill", s_c)

        # D. JOB -> REQUIRES -> SKILL
        # e.g., "Software Engineer requires Python and SQL", "Data Scientist requires Machine Learning"
        job_req_patterns = [
            r'([A-Za-z\s]+(?:Engineer|Developer|Scientist|Architect|Manager|Analyst))\s+(?:requires|demands|requires skills? in|seeking experience in)\s+([^.\n]+)',
            r'Job\s+["\']?([^"\']+)["\']?\s+requires\s+([^.\n]+)',
        ]
        for pat in job_req_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                job_title = match.group(1).strip()
                req_skills = match.group(2).strip()
                add_entity("Job", job_title)
                for s in re.split(r'[,|/&]|\band\b', req_skills):
                    s_clean = s.strip()
                    if s_clean:
                        add_entity("Skill", s_clean)
                        add_relationship("Job", job_title, "REQUIRES", "Skill", s_clean)

        # Also detect known job mentions
        for kj in KNOWN_JOBS:
            if re.search(rf'\b{re.escape(kj)}\b', text_lower):
                add_entity("Job", kj.title())

        # E. DOCUMENT -> DESCRIBES -> PROJECT
        # e.g., "Document describes Project Nexus AI", "This document outlines the Nexus AI architecture"
        doc_desc_patterns = [
            r'(?:document|spec|architecture overview)\s+(?:describes|outlines|details|covers)\s+(?:project\s+)?["\']?([A-Za-z0-9\s_-]{2,30})["\']?',
            r'([A-Za-z0-9\s_-]{2,30})\s+(?:architecture|system design|documentation)',
        ]
        if doc_entity:
            for pat in doc_desc_patterns:
                for match in re.finditer(pat, text, re.IGNORECASE):
                    p_name = match.group(1).strip()
                    if p_name.lower() not in {"the", "this", "our", "a", "an", "system"}:
                        add_entity("Project", p_name)
                        add_relationship("User", user_entity.name, "OWNS", "Project", p_name)
                        add_relationship("Document", doc_entity.name, "DESCRIBES", "Project", p_name)

        # F. TASK -> SUPPORTS -> GOAL
        # e.g., "Task 'Build Neo4j' supports Goal 'Master Knowledge Graphs'", "Task: [T] supports [G]"
        task_goal_patterns = [
            r'Task\s+["\']?([^"\']+)["\']?\s+(?:supports|contributes to|advances)\s+(?:Goal\s+)?["\']?([^"\'.\n]+)["\']?',
            r'([A-Za-z0-9\s_-]+)\s+supports goal\s+([A-Za-z0-9\s_-]+)',
            r'([A-Za-z0-9\s_-]+)\s+supports\s+([A-Za-z0-9\s_-]+)\s+goal',
        ]
        for pat in task_goal_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                t_name = match.group(1).strip()
                g_name = match.group(2).strip()
                add_entity("Task", t_name)
                add_entity("Goal", g_name)
                add_relationship("Task", t_name, "SUPPORTS", "Goal", g_name)
                add_relationship("User", user_entity.name, "HAS_GOAL", "Goal", g_name)

        # G. EVENT -> RELATES_TO -> PROJECT
        # e.g., "Meeting relates to Project Nexus AI", "Event: Sprint Planning relates to Nexus AI"
        event_patterns = [
            r'(?:Event\s+)?["\']?([A-Za-z0-9\s_-]+(?:Meeting|Planning|Review|Demo|Sprint|Call|Interview|Conference))["\']?\s+(?:relates to|for|about)\s+(?:Project\s+)?["\']?([A-Za-z0-9\s_-]+)["\']?',
            r'Event\s+["\']?([^"\']+)["\']?\s+relates to\s+(?:Project\s+)?["\']?([^"\']+)["\']?',
        ]
        for pat in event_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                e_name = match.group(1).strip()
                p_name = match.group(2).strip()
                add_entity("Event", e_name)
                add_entity("Project", p_name)
                add_relationship("Event", e_name, "RELATES_TO", "Project", p_name)
                add_relationship("User", user_entity.name, "OWNS", "Project", p_name)

        # H. USER -> WORKS_AT -> COMPANY
        company_work_patterns = [
            r'(?:work at|employed at|working at|engineer at|scientist at)\s+([A-Za-z0-9\s]+)',
        ]
        for pat in company_work_patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                comp_cand = match.group(1).strip().split()[0]
                if comp_cand.lower() in KNOWN_COMPANIES:
                    canon_comp = KNOWN_COMPANIES[comp_cand.lower()]
                    add_entity("Company", canon_comp)
                    add_relationship("User", user_entity.name, "WORKS_AT", "Company", canon_comp)

        return list(entities_dict.values()), relationships_list

graph_extractor = GraphExtractor()

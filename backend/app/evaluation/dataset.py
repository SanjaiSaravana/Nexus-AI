"""Evaluation dataset for NEXUS AI RAG benchmarks."""

EVAL_DOCUMENTS = [
    {
        "filename": "engineer_resume.txt",
        "content": (
            "Alex Mercer - Senior Distributed Systems Engineer\n"
            "Summary: 8+ years designing high-throughput data platforms, agentic systems, and cloud infrastructure.\n"
            "Technical Skills:\n"
            "- Programming Languages: Python, Go, Rust, TypeScript, SQL\n"
            "- Machine Learning & RAG: PyTorch, pgvector, LangChain, Hybrid Search, Reciprocal Rank Fusion\n"
            "- Infrastructure: Docker, Kubernetes, PostgreSQL, Redis, Kafka\n"
            "Experience:\n"
            "Staff Engineer at AI Core Inc (2022 - Present):\n"
            "- Architected real-time RAG pipeline serving 5M daily queries with sub-100ms latency.\n"
            "- Reduced vector search memory footprint by 40% using optimized quantization.\n"
            "Senior Backend Engineer at CloudScale (2018 - 2022):\n"
            "- Built async microservices with FastAPI and PostgreSQL handling 50k req/sec.\n"
            "Education:\n"
            "M.S. in Computer Science, Stanford University (2018)\n"
            "B.S. in Software Engineering, University of Washington (2016)"
        )
    },
    {
        "filename": "project_nexus_spec.md",
        "content": (
            "# NEXUS AI Product Specification\n"
            "## Architecture Overview\n"
            "NEXUS AI is an agentic personal intelligence platform built with FastAPI, PostgreSQL, and React.\n"
            "Phase 1 establishes the production core with strict user isolation, projects, tasks, and goals.\n"
            "Phase 2 adds Document Intelligence and Hybrid RAG with citations and anti-hallucination.\n"
            "## Security Constraints\n"
            "Tenant isolation is enforced on every query. Users can never view or search another user's documents.\n"
            "All passwords use bcrypt hashing with 12 salt rounds."
        )
    }
]

EVAL_BENCHMARK_CASES = [
    {
        "id": "q1",
        "query": "What are my strongest technical skills?",
        "expected_doc": "engineer_resume.txt",
        "expected_keywords": ["python", "go", "rust", "typescript", "pytorch", "pgvector"],
        "is_answerable": True
    },
    {
        "id": "q2",
        "query": "Where did I work and what did I build at AI Core Inc?",
        "expected_doc": "engineer_resume.txt",
        "expected_keywords": ["ai core inc", "rag pipeline", "vector search"],
        "is_answerable": True
    },
    {
        "id": "q3",
        "query": "What architecture is used for NEXUS AI and how is tenant isolation enforced?",
        "expected_doc": "project_nexus_spec.md",
        "expected_keywords": ["fastapi", "postgresql", "react", "tenant isolation", "user isolation"],
        "is_answerable": True
    },
    {
        "id": "q4_negative",
        "query": "What is the capital city of ancient Atlantis and the recipe for dragon fire potion?",
        "expected_doc": None,
        "expected_keywords": [],
        "is_answerable": False
    },
    {
        "id": "q5_negative",
        "query": "What is the CEO salary of Google in the year 2045?",
        "expected_doc": None,
        "expected_keywords": [],
        "is_answerable": False
    }
]

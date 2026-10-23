"""
Evaluation datasets for NEXUS AI RAG benchmarks and Multi-Agent Orchestrator benchmarks.
Includes grounded corpora, expected ground truths, negative cases, and agent operational scenarios.
"""

from typing import Dict, Any, List

# =============================================================================
# 1. RAG EVALUATION DATASET
# =============================================================================

RAG_BENCHMARK_DOCUMENTS: List[Dict[str, str]] = [
    {
        "filename": "senior_engineer_resume.txt",
        "content": (
            "Alex Mercer - Senior Distributed Systems & AI Platform Engineer\n"
            "Summary: 8+ years designing high-throughput data platforms, agentic systems, and cloud infrastructure.\n"
            "Core Competencies:\n"
            "- Programming Languages: Python, Go, Rust, TypeScript, SQL\n"
            "- AI & RAG Engineering: PyTorch, pgvector, Neo4j, Hybrid Search, Reciprocal Rank Fusion, LangChain\n"
            "- Cloud & Distributed Systems: Docker, Kubernetes, PostgreSQL, Redis, Kafka, AWS, GCP\n"
            "Professional Experience:\n"
            "Staff AI Infrastructure Engineer at AI Core Inc (2022 - Present):\n"
            "- Architected real-time multi-tenant hybrid RAG pipeline serving 5M daily queries with sub-80ms p95 latency.\n"
            "- Decreased vector database footprint by 40% through product quantization and dynamic caching.\n"
            "- Led design of human-in-the-loop autonomous tool execution with fine-grained audit logging.\n"
            "Senior Backend Engineer at CloudScale (2018 - 2022):\n"
            "- Developed high-throughput microservices using FastAPI, SQLAlchemy Async, and Redis Streams handling 50k req/sec.\n"
            "Education:\n"
            "- M.S. in Computer Science, Stanford University (2018)\n"
            "- B.S. in Software Engineering, University of Washington (2016)\n"
        )
    },
    {
        "filename": "nexus_architecture_spec.md",
        "content": (
            "# NEXUS AI System Architecture Specification\n"
            "## Core Infrastructure\n"
            "NEXUS AI is built with a React 19 frontend, FastAPI async backend, PostgreSQL 16 with pgvector, and Neo4j graph database.\n"
            "The platform enforces strict multi-tenant isolation at the query level across all storage engines.\n"
            "## Multi-Agent Architecture\n"
            "The system employs a hierarchical multi-agent structure managed by a Central Orchestrator:\n"
            "1. Planner Agent: Decomposes complex user requests into ordered operational subtasks.\n"
            "2. Research Agent: Orchestrates hybrid RAG vector search and Neo4j knowledge graph traversals.\n"
            "3. Memory Agent: Selectively retrieves semantic, episodic, procedural, and working memories.\n"
            "4. Project Agent: Cross-references project metadata and technical skills against job requirements.\n"
            "5. Task Agent: Converts actionable milestones into database tasks with due dates.\n"
            "## Safety & Tool Calling\n"
            "All sensitive tool executions require human-in-the-loop confirmation. The system creates an ActionProposal\n"
            "with risk level assessment (low, medium, high) and logs full audit entries upon execution.\n"
        )
    },
    {
        "filename": "security_and_compliance.md",
        "content": (
            "# Security & Compliance Policy\n"
            "## Password & Authentication Standards\n"
            "All passwords must be hashed using bcrypt with a work factor of 12 salt rounds.\n"
            "Authentication tokens utilize JWT signed with HMAC-SHA256 and expire after 24 hours.\n"
            "## Data Retention & Anti-Spam\n"
            "Proactive recommendations enforce a default daily cap of 5 notifications per user.\n"
            "Dismissed recommendations are suppressed for 24 hours to prevent notification fatigue.\n"
        )
    }
]

RAG_BENCHMARK_CASES: List[Dict[str, Any]] = [
    {
        "id": "rag_01_resume_skills",
        "query": "What are my core technical skills and programming languages?",
        "expected_docs": ["senior_engineer_resume.txt"],
        "expected_context_snippets": [
            "Programming Languages: Python, Go, Rust, TypeScript, SQL",
            "AI & RAG Engineering: PyTorch, pgvector, Neo4j, Hybrid Search"
        ],
        "expected_keywords": ["python", "go", "rust", "typescript", "pgvector", "neo4j"],
        "expected_answer": "Your core programming languages include Python, Go, Rust, TypeScript, and SQL, with expertise in AI and RAG engineering (PyTorch, pgvector, Neo4j, Hybrid Search, and RRF).",
        "is_answerable": True
    },
    {
        "id": "rag_02_work_history",
        "query": "What systems did I architect at AI Core Inc and what latency was achieved?",
        "expected_docs": ["senior_engineer_resume.txt"],
        "expected_context_snippets": [
            "Architected real-time multi-tenant hybrid RAG pipeline serving 5M daily queries with sub-80ms p95 latency.",
            "Decreased vector database footprint by 40%"
        ],
        "expected_keywords": ["ai core inc", "hybrid rag", "5m daily", "80ms", "quantization"],
        "expected_answer": "At AI Core Inc, you architected a real-time multi-tenant hybrid RAG pipeline handling 5M daily queries with sub-80ms p95 latency and reduced vector memory footprint by 40%.",
        "is_answerable": True
    },
    {
        "id": "rag_03_architecture_orchestrator",
        "query": "How does the multi-agent system in NEXUS AI decompose requests and enforce human approval?",
        "expected_docs": ["nexus_architecture_spec.md"],
        "expected_context_snippets": [
            "Planner Agent: Decomposes complex user requests into ordered operational subtasks.",
            "All sensitive tool executions require human-in-the-loop confirmation. The system creates an ActionProposal"
        ],
        "expected_keywords": ["planner agent", "actionproposal", "human-in-the-loop", "central orchestrator"],
        "expected_answer": "The Planner Agent decomposes complex requests into ordered operational subtasks. Sensitive actions require human-in-the-loop confirmation via ActionProposal objects.",
        "is_answerable": True
    },
    {
        "id": "rag_04_security_tokens",
        "query": "What password hashing algorithm and token expiration time does NEXUS use?",
        "expected_docs": ["security_and_compliance.md"],
        "expected_context_snippets": [
            "All passwords must be hashed using bcrypt with a work factor of 12 salt rounds.",
            "Authentication tokens utilize JWT signed with HMAC-SHA256 and expire after 24 hours."
        ],
        "expected_keywords": ["bcrypt", "12 salt rounds", "jwt", "24 hours"],
        "expected_answer": "NEXUS uses bcrypt with 12 salt rounds for password hashing, and JWT tokens that expire after 24 hours.",
        "is_answerable": True
    },
    {
        "id": "rag_05_negative_atlantis",
        "query": "What is the secret recipe for dragon fire potion used in ancient Atlantis?",
        "expected_docs": [],
        "expected_context_snippets": [],
        "expected_keywords": [],
        "expected_answer": "I couldn't find sufficient information in your connected knowledge.",
        "is_answerable": False
    },
    {
        "id": "rag_06_negative_stock_2050",
        "query": "What was the stock price of Apple on December 25, 2055?",
        "expected_docs": [],
        "expected_context_snippets": [],
        "expected_keywords": [],
        "expected_answer": "I couldn't find sufficient information in your connected knowledge.",
        "is_answerable": False
    }
]


# =============================================================================
# 2. AGENT EVALUATION BENCHMARK DATASET
# =============================================================================

AGENT_BENCHMARK_CASES: List[Dict[str, Any]] = [
    {
        "id": "agent_01_flagship_interview",
        "task_name": "Flagship Interview Preparation Workflow",
        "user_prompt": "I have an interview tomorrow. Help me prepare.",
        "expected_intent": "interview_preparation",
        "expected_planning_steps": [
            "detect_intent_and_deadline",
            "find_interview_event",
            "retrieve_job_description",
            "extract_job_requirements",
            "retrieve_resume_and_projects",
            "compare_skills",
            "generate_interview_topics",
            "create_preparation_plan",
            "save_tasks_and_calendar_action"
        ],
        "expected_tools": ["calendar_tool", "document_tool", "task_tool"],
        "expected_output_elements": ["preparation_plan", "time_blocks", "tasks", "calendar_proposal"],
        "expected_success": True
    },
    {
        "id": "agent_02_calendar_conflict",
        "task_name": "Calendar Conflict Resolution",
        "user_prompt": "I have overlapping meetings on my calendar. Please resolve the conflict.",
        "expected_intent": "calendar_conflict_resolution",
        "expected_planning_steps": [
            "get_events",
            "detect_conflicts",
            "find_free_slots",
            "propose_rescheduling"
        ],
        "expected_tools": ["calendar_tool"],
        "expected_output_elements": ["conflict_details", "suggested_free_slot"],
        "expected_success": True
    },
    {
        "id": "agent_03_task_decomposition",
        "task_name": "Strategic Goal Milestone Decomposition",
        "user_prompt": "Break down my goal 'Launch Production Multi-Tenant Platform' into prioritized actionable milestones.",
        "expected_intent": "goal_decomposition",
        "expected_planning_steps": [
            "get_goal_details",
            "decompose_milestones",
            "calculate_priority",
            "create_tasks"
        ],
        "expected_tools": ["task_tool"],
        "expected_output_elements": ["milestones", "priority_scores", "created_tasks"],
        "expected_success": True
    },
    {
        "id": "agent_04_missing_resource_fallback",
        "task_name": "Graceful Fallback on Missing Job Description",
        "user_prompt": "I have an interview tomorrow at StartupX for Backend Lead, but I haven't uploaded the job description.",
        "expected_intent": "interview_preparation",
        "expected_planning_steps": [
            "detect_intent",
            "check_job_description",
            "handle_missing_resource_gracefully",
            "request_upload_or_use_general_skills"
        ],
        "expected_tools": ["document_tool"],
        "expected_output_elements": ["missing_resource_notice", "general_preparation_topics"],
        "expected_success": True
    }
]

# 02 — Repository Structure

## Monorepo Layout

```
nexus-ai/
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                    # Lint, type-check, test on every PR
│   │   ├── cd-staging.yml            # Deploy to staging on merge to main
│   │   ├── cd-production.yml         # Deploy to production on release tag
│   │   └── evaluate.yml              # Nightly AI evaluation pipeline
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docs/                             # ← Architecture documentation (this folder)
│   ├── 00_overview.md
│   ├── 01_architecture.md
│   ├── 02_repository_structure.md
│   ├── 03_database_design.md
│   ├── 04_ai_architecture.md
│   ├── 05_rag_architecture.md
│   ├── 06_memory_architecture.md
│   ├── 07_knowledge_graph.md
│   ├── 08_agent_architecture.md
│   ├── 09_api_architecture.md
│   ├── 10_security.md
│   ├── 11_deployment.md
│   ├── 12_development_phases.md
│   ├── 13_testing_strategy.md
│   ├── 14_evaluation_strategy.md
│   └── 15_phase1_checklist.md
│
├── frontend/                         # React + TypeScript + Vite
│   ├── public/
│   ├── src/
│   │   ├── api/                      # API client (axios/fetch wrappers)
│   │   │   ├── client.ts
│   │   │   ├── chat.ts
│   │   │   ├── documents.ts
│   │   │   ├── tasks.ts
│   │   │   └── calendar.ts
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatWindow.tsx
│   │   │   │   ├── MessageBubble.tsx
│   │   │   │   ├── CitationCard.tsx
│   │   │   │   └── PermissionDialog.tsx
│   │   │   ├── dashboard/
│   │   │   │   ├── GoalCard.tsx
│   │   │   │   ├── TaskList.tsx
│   │   │   │   ├── CalendarWidget.tsx
│   │   │   │   └── AIInsightCard.tsx
│   │   │   ├── documents/
│   │   │   │   ├── DocumentUploader.tsx
│   │   │   │   ├── DocumentViewer.tsx
│   │   │   │   └── ChunkHighlighter.tsx
│   │   │   ├── graph/
│   │   │   │   ├── KnowledgeGraphViewer.tsx
│   │   │   │   └── EntityCard.tsx
│   │   │   └── shared/
│   │   │       ├── Button.tsx
│   │   │       ├── Modal.tsx
│   │   │       └── Loader.tsx
│   │   ├── hooks/
│   │   │   ├── useChat.ts
│   │   │   ├── useSSE.ts
│   │   │   └── usePermission.ts
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   ├── Chat.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Documents.tsx
│   │   │   ├── KnowledgeGraph.tsx
│   │   │   └── Settings.tsx
│   │   ├── store/                    # Zustand or Redux Toolkit
│   │   │   ├── authStore.ts
│   │   │   ├── chatStore.ts
│   │   │   └── settingsStore.ts
│   │   ├── types/
│   │   │   ├── api.d.ts
│   │   │   └── entities.d.ts
│   │   ├── utils/
│   │   │   ├── format.ts
│   │   │   └── stream.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── backend/                          # Python FastAPI
│   ├── alembic/
│   │   ├── versions/                 # Migration files
│   │   └── env.py
│   ├── app/
│   │   ├── api/                      # Route handlers
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── chat.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── calendar.py
│   │   │   │   ├── goals.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── memories.py
│   │   │   │   ├── knowledge_graph.py
│   │   │   │   ├── permissions.py
│   │   │   │   └── users.py
│   │   │   └── health.py
│   │   ├── core/                     # Config, security, dependencies
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── dependencies.py
│   │   │   └── exceptions.py
│   │   ├── db/                       # Database layer
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── user.py
│   │   │       ├── document.py
│   │   │       ├── task.py
│   │   │       ├── goal.py
│   │   │       ├── project.py
│   │   │       ├── event.py
│   │   │       ├── conversation.py
│   │   │       ├── memory.py
│   │   │       ├── agent_run.py
│   │   │       ├── permission.py
│   │   │       └── audit_log.py
│   │   ├── schemas/                  # Pydantic schemas
│   │   │   ├── chat.py
│   │   │   ├── document.py
│   │   │   ├── task.py
│   │   │   ├── goal.py
│   │   │   ├── memory.py
│   │   │   └── agent.py
│   │   ├── services/                 # Business logic services
│   │   │   ├── document_service.py
│   │   │   ├── task_service.py
│   │   │   ├── goal_service.py
│   │   │   ├── calendar_service.py
│   │   │   └── user_service.py
│   │   ├── ai/                       # AI subsystems
│   │   │   ├── orchestrator/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py
│   │   │   │   ├── intent_detector.py
│   │   │   │   └── context_builder.py
│   │   │   ├── agents/
│   │   │   │   ├── base_agent.py
│   │   │   │   ├── planner_agent.py
│   │   │   │   ├── research_agent.py
│   │   │   │   ├── memory_agent.py
│   │   │   │   ├── project_agent.py
│   │   │   │   ├── task_agent.py
│   │   │   │   ├── calendar_agent.py
│   │   │   │   └── execution_agent.py
│   │   │   ├── rag/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pipeline.py
│   │   │   │   ├── chunker.py
│   │   │   │   ├── embedder.py
│   │   │   │   ├── retriever.py
│   │   │   │   ├── reranker.py
│   │   │   │   └── citation_builder.py
│   │   │   ├── memory/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── memory_engine.py
│   │   │   │   ├── semantic_memory.py
│   │   │   │   ├── episodic_memory.py
│   │   │   │   ├── procedural_memory.py
│   │   │   │   └── working_memory.py
│   │   │   ├── knowledge_graph/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── kg_engine.py
│   │   │   │   ├── entity_extractor.py
│   │   │   │   └── relationship_extractor.py
│   │   │   ├── llm/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py
│   │   │   │   ├── openai_provider.py
│   │   │   │   ├── anthropic_provider.py
│   │   │   │   ├── gemini_provider.py
│   │   │   │   └── ollama_provider.py
│   │   │   ├── embeddings/
│   │   │   │   ├── base.py
│   │   │   │   ├── openai_embedder.py
│   │   │   │   ├── cohere_embedder.py
│   │   │   │   └── local_embedder.py
│   │   │   ├── tools/
│   │   │   │   ├── base_tool.py
│   │   │   │   ├── document_tool.py
│   │   │   │   ├── calendar_tool.py
│   │   │   │   ├── task_tool.py
│   │   │   │   ├── email_tool.py
│   │   │   │   ├── github_tool.py
│   │   │   │   ├── web_search_tool.py
│   │   │   │   └── code_tool.py
│   │   │   ├── evaluation/
│   │   │   │   ├── evaluator.py
│   │   │   │   ├── metrics.py
│   │   │   │   └── judge_llm.py
│   │   │   └── safety/
│   │   │       ├── input_guard.py
│   │   │       └── output_guard.py
│   │   ├── workers/                  # Background job workers
│   │   │   ├── document_processor.py
│   │   │   ├── memory_consolidator.py
│   │   │   ├── kg_builder.py
│   │   │   └── proactive_engine.py
│   │   └── main.py                   # FastAPI app factory
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── e2e/
│   │   └── ai_eval/
│   ├── pyproject.toml
│   ├── Makefile
│   └── alembic.ini
│
├── infra/                            # Infrastructure as code
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   └── worker.Dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.override.yml   # Local dev overrides
│   ├── docker-compose.prod.yml       # Production overrides
│   └── nginx/
│       └── nginx.conf
│
├── scripts/
│   ├── setup_dev.sh                  # One-command dev environment setup
│   ├── seed_db.py                    # Seed development data
│   ├── run_eval.py                   # Run AI evaluation suite
│   └── migrate.sh
│
├── evaluations/                      # AI evaluation datasets and prompts
│   ├── datasets/
│   │   ├── rag_qa.json
│   │   ├── intent_classification.json
│   │   └── planning_benchmarks.json
│   ├── prompts/
│   │   └── judge_prompts.yaml
│   └── results/                      # Gitignored evaluation outputs
│
├── .env.example
├── .gitignore
├── README.md
└── CONTRIBUTING.md
```

---

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monorepo | Yes | Shared types, easier refactoring, atomic commits |
| Backend framework | FastAPI | Async-first, auto OpenAPI docs, Pydantic integration |
| Frontend framework | React + Vite | Fast HMR, TypeScript support, Tailwind compatible |
| ORM | SQLAlchemy 2 | Async support, Pydantic integration, mature ecosystem |
| Task queue | Celery + Redis | Reliable, battle-tested, good monitoring |
| LLM abstraction | Custom provider pattern | Avoid vendor lock-in |
| Config management | Pydantic Settings | Type-safe, env-based, no secrets in code |

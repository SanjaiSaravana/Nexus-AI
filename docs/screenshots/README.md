# NEXUS AI — Screenshots & Visual Assets

This directory contains visual demonstrations and mockup diagrams of the NEXUS AI web application interface for GitHub and portfolio presentations.

## Available Screenshots

1. **`dashboard.svg`**: Executive productivity dashboard with proactive recommendations, completion meters, and strategic goals.
2. **`knowledge_graph.svg`**: Interactive force-directed Neo4j Knowledge Graph canvas explorer and node property drawer.
3. **`chat.svg`**: Real-time streaming AI chat interface with multi-agent activity indicators, knowledge vault uploader, and clickable citations.
4. **`evaluation.svg`**: AI evaluation console with RAG benchmark gauges and 7-stage distributed waterfall execution traces.
5. **`memory.svg`**: 4-tier cognitive memory cards (Semantic, Episodic, Procedural, Working) with importance meters and type filters.
6. **`actions.svg`**: Controlled action confirmation cards (human-in-the-loop approval) and sanitized immutable audit log viewer.

## Capturing Live UI Screenshots

To capture live production PNG screenshots directly from the web client:

1. Launch the full stack using Docker:
   ```bash
   docker compose up --build
   ```
2. Navigate to [http://localhost:3000](http://localhost:3000) (or [http://localhost:5173](http://localhost:5173) in local dev mode).
3. Log in with user credentials and navigate through each page:
   - Dashboard (`/dashboard`)
   - Knowledge Graph (`/knowledge-graph`)
   - Chat (`/chat`)
   - Evaluation (`/evaluation`)
   - Memory (`/memory`)
   - Actions (`/actions`)
4. Capture 1920x1080 full-resolution screenshots and save them into this directory (`docs/screenshots/`).

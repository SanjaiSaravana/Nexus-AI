# Phase 9: AI Evaluation, Observability & MLOps

NEXUS AI incorporates production-grade AI evaluation, distributed execution tracing, real-time telemetry, and MLOps tracking powered by MLflow.

---

## 1. RAG Evaluation Engine

The RAG evaluation suite (`app.evaluation.rag_evaluator.RAGEvaluator`) benchmarks retrieval and generation performance against golden test datasets (`app.evaluation.datasets.RAG_BENCHMARK_CASES`):

| Metric | Target | Formula / Logic | Description |
|---|---|---|---|
| **Context Precision** | $\ge 90\%$ | $\frac{\text{Relevant Retrieved Chunks}}{\text{Total Retrieved Chunks}}$ | Measures signal-to-noise ratio in retrieved context. Penalizes irrelevant chunks. |
| **Context Recall** | $\ge 90\%$ | $\frac{\text{Ground Truth Items Retrieved}}{\text{Total Ground Truth Items}}$ | Measures whether the retrieval pipeline captured all key facts and source documents. |
| **Answer Relevance** | $\ge 95\%$ | Fact coverage & semantic alignment | Measures whether the LLM directly addresses the question or correctly triggers anti-hallucination. |
| **Faithfulness** | $\ge 95\%$ | $\frac{\text{Grounded Claims}}{\text{Total Claims in Answer}}$ | Measures factual consistency; ensures no ungrounded claims are fabricated. |
| **Citation Accuracy** | $\ge 95\%$ | $\frac{\text{Valid Citations}}{\text{Total Citations}}$ | Verifies citations point to actual source documents with verbatim excerpt verification. |

### Anti-Hallucination Guardrail
Adversarial and unanswerable queries (e.g., out-of-domain, missing data) are evaluated to ensure the system strictly outputs:
> *"I couldn't find sufficient information in your connected knowledge."*

---

## 2. Multi-Agent Evaluation Engine

The Agent evaluation suite (`app.evaluation.agent_evaluator.AgentEvaluator`) evaluates operational multi-step workflows against benchmark scenarios:

| Metric | Target | Description |
|---|---|---|
| **Task Success Rate** | $\ge 95\%$ | Percentage of autonomous workflows that successfully achieve user goals without unhandled exceptions. |
| **Planning Accuracy** | $\ge 90\%$ | Measures whether the Planner Agent's decomposed subtasks include all necessary operational stages in valid sequential order. |
| **Tool Selection Accuracy** | $\ge 95\%$ | F1 score of invoked tools vs. required tools (calendar, documents, tasks, memory) without spurious tool execution. |
| **Execution Success** | $\ge 98\%$ | Percentage of attempted tool invocations and action proposals that execute cleanly. |
| **Failure Rate** | $\le 5\%$ | Proportion of runs that fail or abort ($1 - \text{Task Success Rate}$). |

---

## 3. System Metrics & Telemetry

Continuous runtime telemetry is tracked in real-time by `app.observability.metrics.SystemMetricsTracker`:

- **Latency Percentiles**: End-to-end duration tracking: `p50`, `p95`, `p99`, and average latency.
- **Token Usage**: Granular tracking across `prompt_tokens`, `completion_tokens`, and `total_tokens`.
- **Retrieval Latency**: Millisecond timings for dense vector search, BM25 lexical search, RRF reranking, and Neo4j graph traversals.
- **Tool Latency**: Breakdown by individual tool (`calendar_tool`, `document_tool`, `task_tool`, `memory_tool`, etc.).
- **Error Tracking**: Total error count, availability rate, error categorization, and rolling error log.
- **Model Usage Breakdown**: Call count and token distribution across models (`gpt-4o`, `gpt-4o-mini`, `text-embedding-3-small`).
- **Estimated Cost**: Dynamically computed in USD based on tracked token consumption and model rate cards.

---

## 4. Observability & Distributed Tracing

Execution flows are structured as waterfall spans by `app.observability.tracer.ObservabilityTracer`, tracing every transaction through the complete 7-stage lifecycle:

$$\text{User Request} \longrightarrow \text{Intent Detection} \longrightarrow \text{Retrieval} \longrightarrow \text{Agent} \longrightarrow \text{Tool} \longrightarrow \text{LLM} \longrightarrow \text{Final Response}$$

### Span Structure
Every span captures:
- `span_id` & `parent_span_id`: Establishes waterfall hierarchy.
- `name` & `type`: Step classification (`user_request`, `intent`, `retrieval`, `agent`, `tool`, `llm`, `response`).
- `start_time`, `end_time`, `duration_ms`: Execution timings.
- `status`: `running`, `success`, or `error`.
- `inputs` & `outputs`: Sanitized request and response payloads.
- `metadata`: Token consumption, confidence scores, model names, and error traces.

---

## 5. MLflow Integration & Model Registry

Powered by `app.mlops.mlflow_service.MLflowService` with native MLflow 3.17.1 integration:

### 1. Tracked Experiments
1. `model_experiments`: LLM temperature, system prompt variations, few-shot prompting strategies.
2. `embedding_experiments`: Vector dimensions (384), model families, cosine similarity thresholds.
3. `retrieval_experiments`: Hybrid search weighting ($k=60$, dense 0.7, sparse 0.3).
4. `recommendation_experiments`: Priority engine weighting grids and dismissal rates.
5. `evaluation_results`: Automated benchmark test suite runs logging complete metric suites.

### 2. Versioned Artifact Registry
Strict versioning across 5 asset types:
- **Prompts**: Versioned templates (`interview_prep_prompt v2.1`, `proactive_detection_prompt v1.4`, `rag_query_rewriter v1.0`).
- **Models**: Production & Staging model versions (`nexus-orchestrator v1.2`, `nexus-planner-fast v1.0`).
- **Embeddings**: Active vectorizer models (`text-embedding-3-small v1.0`, `bge-small-en-v1.5 v1.1`).
- **Rerankers**: RRF parameters and cross-encoders (`rrf-hybrid-reranker v1.2`).
- **Recommendation Models**: Multi-factor priority weighting calibrations (`multi-factor-priority-engine v1.0`).

---

## 6. Developer & Admin Evaluation Dashboard

Accessible in the web application via `/evaluation` (navigation item in sidebar):
- **Live Observability Status**: Status indicators and latency pills.
- **Top Metric Cards**: Latency percentiles, Token usage, Estimated cost, Agent success rate, RAG precision/recall.
- **Interactive Tabs**:
  1. **RAG Evaluation**: 5-metric gauges and case-by-case benchmark inspection table.
  2. **Agent Evaluation**: Multi-agent operational metrics and benchmark runs breakdown.
  3. **Waterfall Tracing**: Interactive waterfall visualizer showing span timing bars, status badges, and expandable JSON inspectors for inputs/outputs/metadata. Single-click **Generate Trace** button.
  4. **System Metrics**: Latency distribution, model token allocations, tool latencies, and error telemetry.
  5. **MLflow & Registry**: Logged experiment runs with metrics, and versioned assets registry cards.

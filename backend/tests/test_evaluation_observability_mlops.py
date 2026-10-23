"""
Comprehensive Test Suite for Phase 9:
- RAG Evaluation (Context Precision, Context Recall, Answer Relevance, Faithfulness, Citation Accuracy)
- Agent Evaluation (Task Success Rate, Planning Accuracy, Tool Selection Accuracy, Execution Success, Failure Rate)
- System Metrics (Latency, Tokens, Retrieval Latency, Tool Latency, Errors, Cost Estimation)
- Observability & Waterfall Tracing (User request -> Intent -> Retrieval -> Agent -> Tool -> LLM -> Final response)
- MLflow Experiment Tracking & Registry Versioning
- Full REST API Endpoints Lifecycle
"""

import pytest
from app.evaluation.rag_evaluator import rag_evaluator, RAGEvaluator
from app.evaluation.agent_evaluator import agent_evaluator, AgentEvaluator
from app.observability.metrics import system_metrics, SystemMetricsTracker
from app.observability.tracer import tracer, ObservabilityTracer
from app.mlops.mlflow_service import mlflow_service
from app.evaluation.runner import evaluation_runner
from app.services.rag_service import ANTI_HALLUCINATION_RESPONSE


# =============================================================================
# 1. RAG EVALUATOR UNIT TESTS
# =============================================================================

def test_rag_context_precision_and_recall():
    class MockDoc:
        def __init__(self, fn): self.filename = fn
    class MockChunk:
        def __init__(self, content, fn):
            self.content = content
            self.document = MockDoc(fn)

    chunks = [
        (MockChunk("Alex Mercer is a Senior Distributed Systems Engineer skilled in Python and Rust.", "resume.txt"), 0.95),
        (MockChunk("Irrelevant general introduction without key facts.", "random.txt"), 0.40)
    ]

    expected_keywords = ["python", "rust", "distributed systems"]
    expected_docs = ["resume.txt"]
    expected_snippets = ["Alex Mercer is a Senior Distributed Systems Engineer"]

    # 1. Precision: 1 of 2 chunks is relevant -> 0.50
    precision = rag_evaluator.evaluate_context_precision(
        retrieved_chunks_with_scores=chunks,
        expected_keywords=expected_keywords,
        expected_docs=expected_docs
    )
    assert precision == 0.5

    # 2. Recall: Found expected doc and expected snippet -> 1.0
    recall = rag_evaluator.evaluate_context_recall(
        retrieved_chunks_with_scores=chunks,
        expected_snippets=expected_snippets,
        expected_docs=expected_docs
    )
    assert recall == 1.0


def test_rag_answer_relevance_and_faithfulness():
    answer = "Alex Mercer is skilled in Python and Rust with 8 years of distributed systems experience."
    context = "Alex Mercer - Senior Distributed Systems Engineer. Skills: Python, Rust, Go. 8 years experience."
    expected_keywords = ["python", "rust", "distributed systems"]

    # 1. Answer Relevance
    rel = rag_evaluator.evaluate_answer_relevance(
        answer=answer,
        expected_keywords=expected_keywords,
        expected_answer="Alex Mercer knows Python and Rust.",
        is_answerable=True
    )
    assert rel == 1.0

    # 2. Faithfulness
    faith = rag_evaluator.evaluate_faithfulness(
        answer=answer,
        context=context,
        is_answerable=True
    )
    assert faith >= 0.85

    # 3. Negative query triggers anti-hallucination guard properly
    neg_rel = rag_evaluator.evaluate_answer_relevance(
        answer=ANTI_HALLUCINATION_RESPONSE,
        expected_keywords=[],
        expected_answer=ANTI_HALLUCINATION_RESPONSE,
        is_answerable=False
    )
    assert neg_rel == 1.0


def test_rag_citation_accuracy():
    class MockCitation:
        def __init__(self, doc, excerpt):
            self.document_name = doc
            self.excerpt = excerpt

    context = "Alex Mercer has architected real-time RAG pipelines serving 5M daily queries."
    citations = [
        MockCitation("resume.txt", "Alex Mercer has architected real-time RAG pipelines")
    ]

    acc = rag_evaluator.evaluate_citation_accuracy(
        citations=citations,
        expected_docs=["resume.txt"],
        retrieved_context=context,
        is_answerable=True
    )
    assert acc == 1.0


# =============================================================================
# 2. AGENT EVALUATOR UNIT TESTS
# =============================================================================

def test_agent_planning_and_tool_selection():
    expected_steps = [
        "detect_intent_and_deadline",
        "find_interview_event",
        "retrieve_job_description",
        "create_preparation_plan"
    ]
    actual_steps = [
        "detect intent and deadline",
        "find interview event in calendar",
        "retrieve job description from vault",
        "create preparation plan and time blocks"
    ]

    plan_acc = agent_evaluator.evaluate_planning_accuracy(
        actual_steps=actual_steps,
        expected_steps=expected_steps
    )
    assert plan_acc == 1.0

    # Tool selection accuracy
    expected_tools = ["calendar_tool", "document_tool", "task_tool"]
    actual_tools = ["calendar_tool", "document_tool", "task_tool"]
    tool_acc = agent_evaluator.evaluate_tool_selection_accuracy(
        actual_tools_used=actual_tools,
        expected_tools=expected_tools
    )
    assert tool_acc == 1.0

    # Partial / noisy tool selection
    noisy_tools = ["calendar_tool", "document_tool", "email_tool"]
    partial_acc = agent_evaluator.evaluate_tool_selection_accuracy(
        actual_tools_used=noisy_tools,
        expected_tools=expected_tools
    )
    assert 0.0 < partial_acc < 1.0


def test_agent_execution_and_failure_rate():
    tool_results = [
        {"status": "success", "tool": "calendar_tool"},
        {"status": "pending_confirmation", "tool": "task_tool"},
        {"status": "error", "error": "Database lock timeout"}
    ]
    exec_acc = agent_evaluator.evaluate_execution_success(tool_results)
    assert exec_acc == 0.667

    # Full run evaluation
    run_eval = agent_evaluator.evaluate_run(
        actual_output={
            "success": True,
            "planning_steps": ["step1", "step2"],
            "tools_used": ["calendar_tool"],
            "tool_results": [{"status": "success"}]
        },
        benchmark_case={
            "id": "case_1",
            "task_name": "Test Task",
            "expected_planning_steps": ["step1", "step2"],
            "expected_tools": ["calendar_tool"],
            "expected_success": True
        }
    )
    assert run_eval["task_success"] == 1.0
    assert run_eval["failure_rate"] == 0.0


# =============================================================================
# 3. SYSTEM METRICS UNIT TESTS
# =============================================================================

def test_system_metrics_tracker():
    tracker = SystemMetricsTracker(max_history=50)

    # Record request latencies
    tracker.record_request_latency(100.0)
    tracker.record_request_latency(200.0)
    tracker.record_request_latency(300.0)

    # Record retrieval and tool latencies
    tracker.record_retrieval_latency(25.0)
    tracker.record_tool_latency("calendar_tool", 45.0)

    # Record token usage
    tracker.record_token_usage("gpt-4o", prompt_tokens=1000, completion_tokens=500)

    # Record error
    tracker.record_error("timeout_error", "Request timed out")

    summary = tracker.get_summary()
    assert "latency" in summary
    assert summary["latency"]["p50_ms"] > 0
    assert summary["latency"]["p95_ms"] > 0
    assert summary["token_usage"]["total_tokens"] > 0
    assert summary["estimated_cost_usd"] > 0
    assert "calendar_tool" in summary["tool_latency"]
    assert summary["errors"]["total_errors"] >= 1


# =============================================================================
# 4. OBSERVABILITY & TRACING UNIT TESTS
# =============================================================================

def test_observability_pipeline_trace():
    custom_tracer = ObservabilityTracer()
    trace = custom_tracer.create_pipeline_trace(
        user_prompt="I have an interview tomorrow. Help me prepare.",
        intent_name="interview_preparation",
        retrieval_query="Google Staff Engineer job description",
        retrieved_count=4,
        agent_name="Multi-Agent Orchestrator",
        tool_name="calendar_tool",
        tool_action="get_free_slots",
        llm_model="gpt-4o",
        final_answer="Created interview preparation plan.",
        user_id="test-user-id"
    )

    assert trace.status == "success"
    assert trace.duration_ms > 0
    assert len(trace.spans) == 7

    # Verify pipeline span sequence
    span_types = [s.span_type for s in trace.spans]
    assert span_types == ["user_request", "intent", "retrieval", "agent", "tool", "llm", "response"]

    # Verify span hierarchy
    assert trace.spans[0].parent_span_id is None
    assert trace.spans[1].parent_span_id == trace.spans[0].span_id  # Intent under Request
    assert trace.spans[2].parent_span_id == trace.spans[1].span_id  # Retrieval under Intent

    # Check trace retrieval
    stored = custom_tracer.get_trace(trace.trace_id)
    assert stored is not None
    assert stored["trace_id"] == trace.trace_id


# =============================================================================
# 5. MLFLOW EXPERIMENTS & REGISTRY TESTS
# =============================================================================

def test_mlflow_experiments_and_registry():
    # 1. Log run to model_experiments
    run = mlflow_service.log_run(
        experiment_name="model_experiments",
        run_name="test_model_run",
        params={"model": "gpt-4o", "temperature": 0.2},
        metrics={"latency_ms": 150.0, "accuracy": 0.98}
    )
    assert run["run_id"] is not None
    assert run["status"] == "FINISHED"

    # 2. Check list_experiments
    exps = mlflow_service.list_experiments()
    exp_names = [e["experiment_name"] for e in exps]
    assert "model_experiments" in exp_names
    assert "embedding_experiments" in exp_names
    assert "retrieval_experiments" in exp_names
    assert "recommendation_experiments" in exp_names
    assert "evaluation_results" in exp_names

    # 3. Check version registry
    reg = mlflow_service.get_registry()
    assert "prompts" in reg
    assert "models" in reg
    assert "embeddings" in reg
    assert "rerankers" in reg
    assert "recommendation_models" in reg

    # Register new prompt version
    new_prompt = mlflow_service.register_version(
        category="prompts",
        item={"name": "test_prompt", "version": "v1.0", "stage": "Development"}
    )
    assert new_prompt["name"] == "test_prompt"


# =============================================================================
# 6. REST API LIFECYCLE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_evaluation_observability_api_lifecycle(client, user_a_headers):
    # 1. Run evaluation benchmark
    eval_res = await client.post("/evaluation/run", headers=user_a_headers)
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert "rag_evaluation" in eval_data
    assert "agent_evaluation" in eval_data
    assert "mlflow_run_id" in eval_data

    # Verify RAG metrics
    rag_metrics = eval_data["rag_evaluation"]["metrics"]
    assert "context_precision" in rag_metrics
    assert "context_recall" in rag_metrics
    assert "answer_relevance" in rag_metrics
    assert "faithfulness" in rag_metrics
    assert "citation_accuracy" in rag_metrics
    assert rag_metrics["context_precision"] >= 0.80

    # Verify Agent metrics
    agent_metrics = eval_data["agent_evaluation"]["metrics"]
    assert "task_success_rate" in agent_metrics
    assert "planning_accuracy" in agent_metrics
    assert "tool_selection_accuracy" in agent_metrics
    assert "execution_success" in agent_metrics
    assert "failure_rate" in agent_metrics

    # 2. GET /evaluation/summary
    summary_res = await client.get("/evaluation/summary", headers=user_a_headers)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert "system_metrics" in summary_data

    # 3. GET /observability/metrics
    metrics_res = await client.get("/observability/metrics", headers=user_a_headers)
    assert metrics_res.status_code == 200
    metrics_data = metrics_res.json()
    assert "latency" in metrics_data
    assert "token_usage" in metrics_data
    assert "estimated_cost_usd" in metrics_data

    # 4. Observability Traces
    demo_trace_res = await client.post("/observability/traces/demo", headers=user_a_headers)
    assert demo_trace_res.status_code == 200
    trace_obj = demo_trace_res.json()
    trace_id = trace_obj["trace_id"]
    assert len(trace_obj["spans"]) == 7

    list_traces_res = await client.get("/observability/traces", headers=user_a_headers)
    assert list_traces_res.status_code == 200
    assert any(t["trace_id"] == trace_id for t in list_traces_res.json())

    trace_detail_res = await client.get(f"/observability/traces/{trace_id}", headers=user_a_headers)
    assert trace_detail_res.status_code == 200
    assert trace_detail_res.json()["trace_id"] == trace_id

    # 5. MLOps Experiments & Registry
    exp_res = await client.get("/mlops/experiments", headers=user_a_headers)
    assert exp_res.status_code == 200
    assert len(exp_res.json()) >= 5

    reg_res = await client.get("/mlops/registry", headers=user_a_headers)
    assert reg_res.status_code == 200
    assert "prompts" in reg_res.json()
    assert "recommendation_models" in reg_res.json()

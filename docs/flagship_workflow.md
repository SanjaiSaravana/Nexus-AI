# 🎯 Flagship NEXUS Workflow: Interview Preparation

This document details the architecture, execution lifecycle, human-in-the-loop safeguards, and graceful failure fallbacks for the flagship NEXUS workflow:

> **User Request:** `"I have an interview tomorrow. Help me prepare."`

---

## 🏛️ Architecture Overview

The flagship workflow coordinates across **8 agentic domains**, the **Knowledge Vault (RAG)**, **Neo4j Knowledge Graph**, **Episodic Memory**, **Persistent Task Management**, **Calendar Tooling**, and the **Controlled Action Execution Engine (HITL)**.

```mermaid
flowchart TD
    User([User Prompt: "I have an interview tomorrow. Help me prepare."]) --> S1[Step 1: Detect Intent, Deadline, Priority]
    S1 --> S2[Step 2: Find Interview Event]
    S2 --> S3[Step 3: Extract Company & Role]
    S3 --> S4[Step 4: Retrieve Job Description from Vault]
    S4 --> S5[Step 5: Extract Required Skills & Responsibilities]
    S5 --> S6[Step 6: Retrieve Resume, DB Projects, & Memories]
    S6 --> S7[Step 7: Build Skill Comparison Matrix]
    S7 --> S8[Step 8: Identify Strong, Weak, & Missing Skills]
    S8 --> S9[Step 9: Generate Anticipated Interview Topics]
    S9 --> S10[Step 10: Generate Personalized Time-Boxed Plan]
    S10 --> S11[Step 11: Persist 4 Actionable Tasks to DB]
    S10 --> S12[Step 12: Discover Free Calendar Slots]
    S11 & S12 --> S13[Step 13: Stage Calendar Action Proposal]
    S13 --> S14{Step 14: User Confirmation}
    S14 -- Approved --> S14A[Execute Calendar Event & Write Audit Log]
    S14 -- Rejected --> S14B[Record Rejection in Audit Trail]
    S13 --> S15[Step 15: Store Episodic Memory]
    S15 --> S16[Step 16: Synthesize Executive Summary]
```

---

## 📋 The 16 Steps Explained

| Step | Operation | Description | NEXUS Component |
| :--- | :--- | :--- | :--- |
| **1** | **Detect** | Intent: `Interview Preparation`, Deadline: `Tomorrow`, Priority: `High` | `PlannerAgent` / Workflow Router |
| **2** | **Find Interview Event** | Queries `CalendarEvent` table for scheduled interview | `CalendarTool` / DB query |
| **3** | **Find Company & Role** | Parses company and role from event, message, or user profile | Entity Extractor |
| **4** | **Retrieve Job Description** | Ingests job description from Knowledge Vault documents or RAG chunks | `RAGService` / `DocumentChunk` |
| **5** | **Extract Requirements** | Extracts required skills, responsibilities, technologies, experience | Text Analysis Engine |
| **6** | **Retrieve User Profile** | Retrieves candidate resume, `Project` records, and memories | `MemoryService`, `Project` DB |
| **7** | **Build Skill Comparison** | Compares job requirements against verified user skills | Competency Matrix Generator |
| **8** | **Identify Gaps** | Classifies strong areas, weak areas, and missing skills | Gap Analysis Engine |
| **9** | **Generate Topics** | Produces high-yield interview questions & STAR narratives | Topic Synthesizer |
| **10** | **Personalized Plan** | Structured time blocks (6:00–7:00 SQL, 7:15–8:15 System Design, etc.) | Schedule Optimizer |
| **11** | **Convert to Tasks** | Persists 4 actionable tasks directly to `tasks` database table | `Task` Model Persistence |
| **12** | **Find Calendar Slots** | Queries free time intervals via `calendar_tool.get_free_slots` | `CalendarTool` |
| **13** | **Propose Calendar Action** | Staged proposal (`requires_confirmation=True`, `status="pending"`) | `ActionManager` (HITL Guardrail) |
| **14** | **Create Approved Events** | On user confirmation, executes event creation & logs audit record | `ActionManager.approve_action` |
| **15** | **Store Meaningful Memory**| Saves episodic memory capturing preparation session & goals | `MemoryService.deduplicate_and_store` |
| **16** | **Return Final Summary** | Synthesizes comprehensive markdown readiness briefing | Orchestrator Synthesis |

---

## 💬 UI Activity Streaming Sequence

When the user queries via chat (`/chat/stream`), the Server-Sent Events (SSE) pipe emits the exact activity status sequence:

1. `Understanding request...`
2. `Finding interview...`
3. `Reading job description...`
4. `Analyzing your skills...`
5. `Checking relevant projects...`
6. `Identifying skill gaps...`
7. `Creating preparation plan...`
8. `Waiting for calendar approval...`
9. `Completed.`

These status messages update the active agent orchestrator indicator in real-time, accompanied by history badges and dynamic loading animations.

---

## 🛡️ Human-in-the-Loop Confirmation (Step 13 & 14)

Per NEXUS security guidelines: **Never perform sensitive external actions without confirmation.**

1. Creating calendar events is classified as a sensitive productivity action (`RiskLevel.HIGH`).
2. NEXUS stages an `ActionProposal` with `status="pending"`.
3. The Chat UI and `/actions` page immediately render the **Action Confirmation Card**:
   ```
   NEXUS wants to create_event:
   Interview Preparation: SQL & System Design Blocks
   Tomorrow: 6:00 PM – 9:30 PM
   [Approve] [Reject]
   ```
4. Clicking `[Approve]` calls `POST /api/v1/actions/proposals/{id}/approve` (or `POST /api/v1/workflows/interview-prep/approve-calendar/{id}`), creating the event in `calendar_events` and recording an audit record in `audit_logs`.

---

## 🛟 Graceful Degradation & Failure Handling

The flagship workflow was rigorously tested against all 7 failure scenarios:

| Failure Mode | Injected Fault | System Graceful Degradation Behavior |
| :--- | :--- | :--- |
| **1. No interview found** | No matching event in calendar | Infers target technical screening session (Tomorrow 10:00 AM) and notes adaptation in briefing. |
| **2. Job description missing** | No JD document in Knowledge Vault | Synthesizes industry-standard senior engineering requirements for the target role & company. |
| **3. Resume missing** | No resume uploaded | Analyzes candidate competencies directly from active database projects, graph relations, and memories. |
| **4. Calendar unavailable** | Calendar tool offline / database timeout | Catches error, provides recommended evening study window (6:00–9:30 PM), and continues without crashing. |
| **5. LLM failure** | AI provider rate-limit or outage | Activates deterministic rule-based synthesis template, guaranteeing complete 16-step response. |
| **6. Retrieval failure** | Vector similarity index error | Falls back to internal domain knowledge primings and local database records. |
| **7. Tool failure** | Task/proposal persistence error | Records tool failure in proposal/audit log, gracefully returning full preparation plan and remediation. |

---

## 🧪 Verification & Test Suite

The workflow is covered by dedicated tests in `backend/tests/test_flagship_workflow.py`:

```bash
# Run the complete flagship test suite
pytest tests/test_flagship_workflow.py -v
```

**Test Results:**
- `test_flagship_workflow_16_steps_end_to_end`: **PASSED**
- `test_failure_case_no_interview_found`: **PASSED**
- `test_failure_case_job_description_missing`: **PASSED**
- `test_failure_case_resume_missing`: **PASSED**
- `test_failure_case_calendar_unavailable`: **PASSED**
- `test_failure_case_llm_failure`: **PASSED**
- `test_failure_case_retrieval_failure`: **PASSED**
- `test_failure_case_tool_failure`: **PASSED**
- `test_api_workflows_interview_prep_and_calendar_approval`: **PASSED**
- `test_chat_query_interview_prep_workflow`: **PASSED**
- `test_chat_stream_interview_prep_workflow_ui_activities`: **PASSED**

**Full Backend Suite:** 63/63 tests passing (100%).

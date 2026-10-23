# Phase 6: Secure Tool Calling & Controlled Action Execution

## Overview

NEXUS AI Phase 6 introduces an enterprise-grade secure tool execution framework and human-in-the-loop action system. While autonomous agents can formulate plans, propose events, draft emails, and recommend system modifications, **no sensitive or external action is executed without explicit human approval**.

---

## 1. Action System Lifecycle

The action system enforces a rigorous 7-stage workflow:

```text
Agent wants action
       ↓
Permission check
       ↓
Action proposal
       ↓
User confirmation (Approve / Reject)
       ↓
Tool execution
       ↓
Result capture
       ↓
Sanitized Audit log
```

1. **Permission Check**: Verifies that the requested action conforms to the tool's declared permission scopes (e.g., `calendar:write`, `email:send`, `task:write`).
2. **Risk Evaluation & Proposal**:
   - `read_only` / `low` risk operations (e.g., reading calendar events or searching documents) can be auto-executed safely.
   - `medium`, `high`, and `critical` risk operations (e.g., creating calendar meetings, dispatching emails, filing GitHub issues) generate an **`ActionProposal`** stored in `pending` status.
3. **User Confirmation**: The user inspects the proposal via the Confirmation UI (`/actions` or in `/chat`) and explicitly clicks **[Approve]** or **[Reject]**.
4. **Tool Execution**: Upon approval, the registered tool executes the validated action with user context and database isolation.
5. **Result & Status**: The proposal record transitions to `executed` or `failed`, storing the execution payload and error details (if any).
6. **Immutable Audit Logging**: Every proposal, approval, execution, or rejection is immutably recorded in the `audit_logs` table with all credentials, tokens, and secrets automatically redacted.

---

## 2. Tool Schema Specification

Every tool registered in `ToolRegistry` implements the `BaseTool` abstraction with complete JSON schemas:

| Field | Description | Example |
|---|---|---|
| `name` | Unique tool identifier | `"calendar"`, `"task"`, `"email"` |
| `description` | Human and LLM readable capability summary | `"Manage user calendar events, detect free slots..."` |
| `category` | Domain classification | `"productivity"`, `"communication"`, `"developer"` |
| `risk_level` | Risk classification | `read_only`, `low`, `medium`, `high`, `critical` |
| `requires_confirmation` | Boolean flag enforcing mandatory user confirmation | `True` for calendar, email, GitHub |
| `permissions` | Granular permission scopes required | `["calendar:read", "calendar:write"]` |
| `input_schema` | Pydantic JSON schema of input parameters | Generated via `model_json_schema()` |
| `output_schema` | Pydantic JSON schema of return payload | Generated via `model_json_schema()` |
| `error_handling` | Graceful error trapping and formatted execution timing | `ToolExecutionResult(success=False, error="...")` |

---

## 3. Registered Tool Domains (9 Domains)

NEXUS AI Phase 6 provides full abstractions across all 9 requested domains with local/mock fallback providers when external OAuth credentials are not configured:

1. **Calendar Tool (`calendar`)**:
   - `get_events(start_time, end_time)`: Retrieves user calendar events.
   - `get_free_slots(start_time, end_time, duration_minutes)`: Scans between busy intervals to identify open time slots.
   - `create_event(title, start_time, end_time, location, event_type)`: Validates chronology (`start_time < end_time`) and schedules event.
   - `update_event(event_id, title, ...)`: Modifies existing events.
   - `delete_event(event_id)`: Removes calendar events.
2. **Task Tool (`task`)**:
   - `create_task(title, description, priority, due_date, project_id)`: Creates actionable items.
   - `update_task(task_id, title, status, priority)`: Updates task properties.
   - `complete_task(task_id)`: Marks task completed with completion timestamp.
   - `delete_task(task_id)`: Deletes tasks with cascade safety.
3. **Email Tool (`email`)**:
   - `send_email(to_address, subject, body, cc)`: Simulated local mock SMTP delivery requiring user approval.
   - `draft_email(to_address, subject, body)`: Saves drafts locally.
   - `list_inbox()`: Lists mock incoming emails and interview invites.
4. **GitHub Tool (`github`)**:
   - `create_issue(repo, title, body, labels)`: High-risk external action proposing GitHub issues with local mock GitHub fallback.
   - `list_repositories()`: Lists connected developer repositories.
5. **Document Tool (`documents`)**:
   - `search_documents(query, top_k)`: Semantic chunk retrieval from user vault.
   - `list_documents()`: Lists uploaded files and metadata.
6. **Memory Tool (`memory`)**:
   - `search_memories(query, top_k)`: Multi-signal personalized memory recall.
   - `create_memory(content, memory_type, importance)`: Persists high-salience memories.
   - `delete_memory(memory_id)`: Removes memory records.
7. **Projects Tool (`projects`)**:
   - `list_projects()`: Lists active projects and task loads.
   - `create_project(name, description, status)`: Creates new project workspaces.
8. **Knowledge Graph Tool (`knowledge_graph`)**:
   - `query_graph(query)`: Cypher and semantic graph retrieval.
   - `get_neighborhood(node_id, hops)`: Subgraph neighborhood extraction.
   - `sync_database()`: Relational DB to Neo4j graph synchronization.
9. **Search Tool (`search`)**:
   - `search(query)`: Curated technical and architectural knowledge lookup.

---

## 4. Confirmation UI Specification

When an agent proposes an action requiring confirmation, the UI displays a structured approval card:

```text
┌──────────────────────────────────────────────────────────────┐
│  ⚠️ ACTION PROPOSAL • CALENDAR                     HIGH RISK  │
│                                                              │
│  NEXUS wants to create:                                      │
│  Interview Preparation                                       │
│                                                              │
│  Tomorrow                                                    │
│  6:00 PM – 7:00 PM                                           │
│                                                              │
│  [Approve]                                         [Reject]  │
└──────────────────────────────────────────────────────────────┘
```

- Accessible via the dedicated **Actions & Audit** page (`/actions`).
- Directly integrated into the **AI Chat** interface (`/chat`) as a high-visibility banner above the message input so users never miss an external action proposal during conversation.

---

## 5. Security & Audit Trail

### Zero Hard-Coded Credentials
External integrations (SMTP, GitHub, Google Calendar) use local fallback providers by default. When production OAuth credentials are provided via environment variables, tools seamlessly bridge to real APIs.

### Automated Secret Sanitization
Before any parameter dict is recorded in `audit_logs` or displayed in the history, `sanitize_parameters()` recursively scrubs all sensitive keys:
- `password`, `token`, `secret`, `authorization`, `auth`, `api_key`, `credentials`, `access_token`, `key`
All matching values are replaced with `"******"`.

### Audit Log Record Schema
- `id`: Unique GUID
- `user_id`: Tenant identifier
- `action`: Specific tool function executed
- `tool`: Domain name (calendar, email, etc.)
- `parameters`: Sanitized JSON payload
- `approval_status`: `"auto_approved"`, `"approved"`, `"rejected"`
- `status`: `"success"`, `"failed"`, `"rejected"`
- `result`: Execution return data (or error message)
- `created_at`: UTC timestamp

---

## 6. Automated Testing

The Phase 6 test suite in `backend/tests/test_tools_and_actions.py` verifies:
- `test_tool_registry_contains_all_required_domains`: Complete schema definition across all 9 domains.
- `test_action_proposal_and_permission_checks`: Proposal creation and pending state enforcement.
- `test_action_approval_and_execution_lifecycle`: Full approval -> execution -> audit log cycle.
- `test_action_rejection_flow`: Explicit user rejection with rejection reason.
- `test_tool_validation_and_failed_execution`: Chronological validation (`start_time < end_time`) and failed status handling.
- `test_audit_log_secret_sanitization`: Recursive masking of sensitive tokens, passwords, and keys.
- `test_calendar_tool_crud_and_free_slots`: Event CRUD and free-slot gap detection.
- `test_task_tool_crud`: Task creation, update, completion, and deletion.
- `test_email_and_github_mock_tools`: Mock SMTP and GitHub issue tracking.
- `test_multi_tenant_isolation_for_actions_and_calendar`: Cross-tenant action approval denial (404 Not Found).

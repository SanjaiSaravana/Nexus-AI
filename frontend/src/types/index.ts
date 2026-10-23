export interface Profile {
  id: string;
  user_id: string;
  full_name: string | null;
  bio: string | null;
  preferences: {
    theme?: string;
    notifications_enabled?: boolean;
    [key: string]: any;
  };
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  username: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  profile?: Profile | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  status: 'active' | 'completed' | 'archived' | 'on_hold' | string;
  start_date: string | null;
  end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

export interface Task {
  id: string;
  user_id: string;
  project_id: string | null;
  title: string;
  description: string | null;
  status: 'todo' | 'in_progress' | 'completed' | 'blocked' | string;
  priority: 'low' | 'medium' | 'high' | 'urgent' | string;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  title: string;
  description?: string;
  project_id?: string | null;
  status?: string;
  priority?: string;
  due_date?: string | null;
}

export interface TaskUpdate {
  title?: string;
  description?: string;
  project_id?: string | null;
  status?: string;
  priority?: string;
  due_date?: string | null;
}

export interface Goal {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  category: 'career' | 'learning' | 'personal' | 'fitness' | 'financial' | string;
  status: 'active' | 'completed' | 'on_hold' | 'cancelled' | string;
  progress_pct: number;
  target_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface GoalCreate {
  title: string;
  description?: string;
  category?: string;
  status?: string;
  progress_pct?: number;
  target_date?: string | null;
}

export interface GoalUpdate {
  title?: string;
  description?: string;
  category?: string;
  status?: string;
  progress_pct?: number;
  target_date?: string | null;
}

export interface DashboardStats {
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  in_progress_tasks: number;
  completion_rate: number;
  active_projects_count: number;
  active_goals_count: number;
  average_goal_progress: number;
}

export interface AIRecommendation {
  id: string;
  user_id: string;
  category: string;
  title: string;
  recommendation: string;
  reason: string;
  priority_score: number;
  priority_level: 'urgent' | 'high' | 'medium' | 'low' | string;
  related_goal: string | null;
  related_deadline: string | null;
  action_type: string | null;
  action_payload: Record<string, any>;
  status: 'active' | 'dismissed' | 'executed' | string;
  created_at: string;
  dismissed_at?: string | null;
}

export interface ProactivePreferences {
  enabled: boolean;
  frequency: 'immediate' | 'hourly' | 'daily' | string;
  max_daily_recommendations: number;
  muted_categories: string[];
}

export interface DashboardOverview {
  stats: DashboardStats;
  todays_tasks: Task[];
  upcoming_tasks: Task[];
  active_projects: Project[];
  active_goals: Goal[];
  ai_recommendations?: AIRecommendation[];
}

// Phase 2: Documents & RAG
export interface DocumentItem {
  id: string;
  user_id: string;
  filename: string;
  document_type: string;
  file_size: number;
  status: string;
  chunk_count: number;
  doc_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  message: string;
  document: DocumentItem;
  chunks_created: number;
}

export interface Citation {
  citation_id: string;
  document_id: string;
  document_name: string;
  chunk_id: string;
  page_number?: number | null;
  section?: string | null;
  excerpt: string;
  relevance_score: number;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations: Citation[];
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  message_count?: number;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface ChatQueryRequest {
  message: string;
  conversation_id?: string;
  document_ids?: string[];
  top_k?: number;
}

export interface ChatQueryResponse {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
}

// Phase 3: Memory Types
export type MemoryType = 'semantic' | 'episodic' | 'procedural' | 'working';

export interface MemoryItem {
  id: string;
  user_id: string;
  memory_type: MemoryType;
  content: string;
  importance: number;
  source: string;
  source_id?: string | null;
  mem_metadata: {
    entities?: string[];
    reason?: string;
    [key: string]: any;
  };
  access_count: number;
  last_accessed_at: string;
  created_at: string;
  updated_at: string;
}

export interface MemoryCreate {
  content: string;
  memory_type: string;
  importance: number;
  source?: string;
  source_id?: string | null;
  mem_metadata?: Record<string, any>;
}

export interface MemoryUpdate {
  content?: string;
  memory_type?: string;
  importance?: number;
  mem_metadata?: Record<string, any>;
}

export interface MemoryStats {
  total: number;
  semantic_count: number;
  episodic_count: number;
  procedural_count: number;
  working_count: number;
  avg_importance: number;
}

// Phase 4: Knowledge Graph Types
export type EntityLabel =
  | 'User'
  | 'Project'
  | 'Skill'
  | 'Technology'
  | 'Document'
  | 'Task'
  | 'Goal'
  | 'Event'
  | 'Company'
  | 'Job'
  | 'Topic';

export interface GraphNode {
  id: string;
  label: EntityLabel | string;
  name: string;
  properties: Record<string, any>;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphQueryResponse {
  query: string;
  intent: string;
  cypher: string;
  answer: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphStats {
  total_nodes: number;
  total_edges: number;
  node_counts: Record<string, number>;
  edge_counts: Record<string, number>;
}

export interface GraphSyncResponse {
  message: string;
  synced_nodes: number;
  synced_edges: number;
}

// Phase 5: Multi-Agent Types
export type AgentType =
  | 'planner'
  | 'research'
  | 'memory'
  | 'project'
  | 'task'
  | 'calendar'
  | 'execution'
  | 'orchestrator';

export type AgentStatus = 'pending' | 'running' | 'completed' | 'failed' | 'retried' | 'skipped';

export interface AgentActivityItem {
  agent: AgentType | string;
  message: string;
}

export interface SubTaskItem {
  step: number;
  title: string;
  description: string;
  assigned_agent: AgentType | string;
  status: string;
}

export interface PlannerOutput {
  intent: string;
  goal: string;
  summary: string;
  subtasks: SubTaskItem[];
  required_agents: string[];
}

export interface AgentState {
  run_id: string;
  agent: AgentType;
  input: Record<string, any>;
  output?: Record<string, any> | null;
  status: AgentStatus;
  start_time?: string;
  end_time?: string;
  errors?: string | null;
  retries: number;
}

export interface OrchestrationRequest {
  message: string;
  conversation_id?: string;
  document_ids?: string[];
  auto_execute_tasks?: boolean;
  auto_schedule_calendar?: boolean;
}

export interface OrchestrationResult {
  run_id: string;
  intent: string;
  plan: PlannerOutput;
  agent_states: AgentState[];
  final_response: string;
  citations: Citation[];
  created_tasks: any[];
  suggested_calendar_events: any[];
  execution_summary: Record<string, any>;
}

// Phase 6: Tools, Action Proposals & Audit Log
export interface ToolDefinition {
  name: string;
  description: string;
  category: string;
  risk_level: 'read_only' | 'low' | 'medium' | 'high' | 'critical';
  requires_confirmation: boolean;
  permissions: string[];
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
}

export interface ActionProposal {
  id: string;
  user_id: string;
  action_type: string;
  tool_name: string;
  title: string;
  description?: string | null;
  parameters: Record<string, any>;
  risk_level: string;
  requires_confirmation: boolean;
  status: 'pending' | 'approved' | 'rejected' | 'executed' | 'failed';
  result?: Record<string, any> | null;
  rejection_reason?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  executed_at?: string | null;
}

export interface AuditLogItem {
  id: string;
  user_id: string;
  action: string;
  tool: string;
  parameters: Record<string, any>;
  approval_status: string;
  status: string;
  result?: Record<string, any> | null;
  error_message?: string | null;
  proposal_id?: string | null;
  created_at: string;
}

export interface CalendarEventItem {
  id: string;
  user_id: string;
  title: string;
  description?: string | null;
  start_time: string;
  end_time: string;
  location?: string | null;
  event_type: string;
  is_all_day: boolean;
  created_at: string;
  updated_at: string;
}

// Phase 9: AI Evaluation, Observability & MLOps
export interface RAGEvalMetrics {
  context_precision: number;
  context_recall: number;
  answer_relevance: number;
  faithfulness: number;
  citation_accuracy: number;
}

export interface RAGEvalCase {
  case_id: string;
  query: string;
  is_answerable: boolean;
  context_precision: number;
  context_recall: number;
  answer_relevance: number;
  faithfulness: number;
  citation_accuracy: number;
  latency_ms: number;
}

export interface RAGEvalResponse {
  timestamp: string;
  total_cases: number;
  metrics: RAGEvalMetrics;
  cases: RAGEvalCase[];
}

export interface AgentEvalMetrics {
  task_success_rate: number;
  planning_accuracy: number;
  tool_selection_accuracy: number;
  execution_success: number;
  failure_rate: number;
}

export interface AgentEvalCase {
  case_id: string;
  task_name: string;
  task_success: number;
  planning_accuracy: number;
  tool_selection_accuracy: number;
  execution_success: number;
  failure_rate: number;
  tools_used: string[];
  step_count: number;
}

export interface AgentEvalResponse {
  timestamp: string;
  total_cases: number;
  metrics: AgentEvalMetrics;
  cases: AgentEvalCase[];
}

export interface LatencyMetrics {
  avg_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  sample_count: number;
}

export interface ToolLatencyItem {
  count: number;
  avg_ms: number;
  p95_ms: number;
}

export interface SystemMetrics {
  timestamp: string;
  latency: LatencyMetrics;
  retrieval_latency: {
    avg_ms: number;
    sample_count: number;
  };
  tool_latency: Record<string, ToolLatencyItem>;
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  estimated_cost_usd: number;
  model_usage: {
    calls: Record<string, number>;
    tokens: Record<string, { prompt: number; completion: number; total: number }>;
  };
  errors: {
    total_errors: number;
    error_rate: number;
    by_type: Record<string, number>;
    recent: any[];
  };
  success_rate: number;
  failure_rate: number;
}

export interface TraceSpan {
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  type: 'user_request' | 'intent' | 'retrieval' | 'agent' | 'tool' | 'llm' | 'response' | string;
  start_time: string;
  end_time?: string | null;
  duration_ms: number;
  status: 'running' | 'success' | 'error';
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  error_message?: string | null;
  metadata: Record<string, any>;
}

export interface Trace {
  trace_id: string;
  user_id?: string | null;
  title: string;
  start_time: string;
  end_time?: string | null;
  duration_ms: number;
  status: string;
  span_count: number;
  spans: TraceSpan[];
}

export interface TraceListItem {
  trace_id: string;
  title: string;
  start_time: string;
  duration_ms: number;
  status: string;
  span_count: number;
  user_id?: string | null;
}

export interface MLflowRun {
  run_id: string;
  experiment_name: string;
  run_name: string;
  params: Record<string, any>;
  metrics: Record<string, number>;
  tags: Record<string, string>;
  status: string;
  created_at: string;
}

export interface MLflowExperiment {
  experiment_name: string;
  run_count: number;
  latest_run?: MLflowRun | null;
}

export interface ModelRegistryItem {
  name: string;
  version: string;
  stage: string;
  updated_at: string;
  description?: string;
  [key: string]: any;
}

export interface ModelRegistry {
  prompts: ModelRegistryItem[];
  models: ModelRegistryItem[];
  embeddings: ModelRegistryItem[];
  rerankers: ModelRegistryItem[];
  recommendation_models: ModelRegistryItem[];
}

export interface EvaluationSummary {
  timestamp: string;
  duration_ms?: number;
  mlflow_run_id?: string;
  rag_evaluation: RAGEvalResponse;
  agent_evaluation: AgentEvalResponse;
  system_metrics: SystemMetrics;
}





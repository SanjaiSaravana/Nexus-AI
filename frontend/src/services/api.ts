import type {
  TokenResponse,
  User,
  Profile,
  Project,
  ProjectCreate,
  ProjectUpdate,
  Task,
  TaskCreate,
  TaskUpdate,
  Goal,
  GoalCreate,
  GoalUpdate,
  DashboardOverview,
  DocumentItem,
  DocumentUploadResponse,
  Citation,
  Conversation,
  ChatQueryRequest,
  ChatQueryResponse,
  MemoryItem,
  MemoryCreate,
  MemoryUpdate,
  MemoryStats,
  GraphData,
  GraphStats,
  GraphQueryResponse,
  GraphSyncResponse,
  AgentActivityItem,
  OrchestrationRequest,
  OrchestrationResult,
  ToolDefinition,
  ActionProposal,
  AuditLogItem,
  CalendarEventItem,
  AIRecommendation,
  ProactivePreferences,
  EvaluationSummary,
  RAGEvalResponse,
  AgentEvalResponse,
  SystemMetrics,
  Trace,
  TraceListItem,
  MLflowExperiment,
  MLflowRun,
  ModelRegistry,
} from '../types';

const API_BASE = ''; // Uses Vite proxy or Nginx reverse proxy

function getAuthHeader(): Record<string, string> {
  const token = localStorage.getItem('nexus_token');
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...getAuthHeader(),
    ...((options.headers as Record<string, string>) || {}),
  };

  if (!isFormData && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return null as T;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem('nexus_token');
    }
    let errorMsg = 'An unexpected error occurred';
    if (data) {
      if (typeof data.detail === 'string') {
        errorMsg = data.detail;
      } else if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
      } else if (data.message) {
        errorMsg = data.message;
      }
    }
    throw new Error(errorMsg);
  }

  return data as T;
}

export const api = {
  // Auth
  auth: {
    register: (data: { email: string; password: string; username?: string }) =>
      request<TokenResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    login: (data: { email: string; password: string }) =>
      request<TokenResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
  },

  // Users
  users: {
    getMe: () => request<User>('/users/me'),
    updateProfile: (data: { full_name?: string; bio?: string; preferences?: any }) =>
      request<Profile>('/users/me/profile', {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
  },

  // Projects
  projects: {
    list: (statusFilter?: string) => {
      const query = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : '';
      return request<Project[]>(`/projects${query}`);
    },
    create: (data: ProjectCreate) =>
      request<Project>('/projects', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => request<Project>(`/projects/${id}`),
    update: (id: string, data: ProjectUpdate) =>
      request<Project>(`/projects/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/projects/${id}`, {
        method: 'DELETE',
      }),
  },

  // Tasks
  tasks: {
    list: (params?: { project_id?: string; status_filter?: string; priority_filter?: string }) => {
      const search = new URLSearchParams();
      if (params?.project_id) search.append('project_id', params.project_id);
      if (params?.status_filter) search.append('status_filter', params.status_filter);
      if (params?.priority_filter) search.append('priority_filter', params.priority_filter);
      const qs = search.toString();
      return request<Task[]>(`/tasks${qs ? `?${qs}` : ''}`);
    },
    create: (data: TaskCreate) =>
      request<Task>('/tasks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => request<Task>(`/tasks/${id}`),
    update: (id: string, data: TaskUpdate) =>
      request<Task>(`/tasks/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/tasks/${id}`, {
        method: 'DELETE',
      }),
  },

  // Goals
  goals: {
    list: (params?: { category?: string; status_filter?: string }) => {
      const search = new URLSearchParams();
      if (params?.category) search.append('category', params.category);
      if (params?.status_filter) search.append('status_filter', params.status_filter);
      const qs = search.toString();
      return request<Goal[]>(`/goals${qs ? `?${qs}` : ''}`);
    },
    create: (data: GoalCreate) =>
      request<Goal>('/goals', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => request<Goal>(`/goals/${id}`),
    update: (id: string, data: GoalUpdate) =>
      request<Goal>(`/goals/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: string) =>
      request<void>(`/goals/${id}`, {
        method: 'DELETE',
      }),
  },

  // Dashboard
  dashboard: {
    getOverview: () => request<DashboardOverview>('/dashboard/overview'),
  },

  // Phase 2: Documents
  documents: {
    upload: (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      return request<DocumentUploadResponse>('/documents/upload', {
        method: 'POST',
        body: formData,
      });
    },
    list: () => request<DocumentItem[]>('/documents'),
    get: (id: string) => request<DocumentItem>(`/documents/${id}`),
    delete: (id: string) => request<void>(`/documents/${id}`, { method: 'DELETE' }),
  },

  // Phase 2: Chat & RAG
  chat: {
    query: (data: ChatQueryRequest) =>
      request<ChatQueryResponse>('/chat/query', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    listConversations: () => request<Conversation[]>('/chat/conversations'),
    getConversation: (id: string) => request<Conversation>(`/chat/conversations/${id}`),
    deleteConversation: (id: string) => request<void>(`/chat/conversations/${id}`, { method: 'DELETE' }),
    streamQuery: async (
      data: ChatQueryRequest,
      onToken: (tok: string) => void,
      onCitations: (cits: Citation[]) => void,
      onDone: () => void,
      onError: (err: any) => void,
      onActivity?: (act: AgentActivityItem) => void
    ) => {
      try {
        const response = await fetch(`${API_BASE}/chat/stream`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...getAuthHeader(),
          },
          body: JSON.stringify(data),
        });

        if (!response.ok) {
          const errData = await response.json().catch(() => null);
          throw new Error(errData?.detail || 'Streaming failed');
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        if (!reader) throw new Error('No readable stream available');

        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
              try {
                const payload = JSON.parse(trimmed.slice(6));
                if (payload.type === 'token') {
                  onToken(payload.content);
                } else if (payload.type === 'activity') {
                  if (onActivity) onActivity({ agent: payload.agent, message: payload.message });
                } else if (payload.type === 'citations') {
                  onCitations(payload.citations);
                } else if (payload.type === 'done') {
                  onDone();
                }
              } catch {
                // ignore parsing error for chunk
              }
            }
          }
        }
        onDone();
      } catch (err) {
        onError(err);
      }
    },
  },

  // Phase 3: Personalized Memory System
  memories: {
    list: (params?: { memory_type?: string; search?: string; min_importance?: number }) => {
      const search = new URLSearchParams();
      if (params?.memory_type) search.append('memory_type', params.memory_type);
      if (params?.search) search.append('search', params.search);
      if (params?.min_importance !== undefined) search.append('min_importance', params.min_importance.toString());
      const qs = search.toString();
      return request<MemoryItem[]>(`/memories${qs ? `?${qs}` : ''}`);
    },
    getStats: () => request<MemoryStats>('/memories/stats'),
    create: (data: MemoryCreate) =>
      request<MemoryItem>('/memories', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => request<MemoryItem>(`/memories/${id}`),
    update: (id: string, data: MemoryUpdate) =>
      request<MemoryItem>(`/memories/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: string) => request<void>(`/memories/${id}`, { method: 'DELETE' }),
  },

  // Phase 4: Neo4j Knowledge Graph System
  knowledgeGraph: {
    getGraph: (params?: { label?: string; search?: string; limit?: number }) => {
      const search = new URLSearchParams();
      if (params?.label) search.append('label', params.label);
      if (params?.search) search.append('search', params.search);
      if (params?.limit) search.append('limit', params.limit.toString());
      const qs = search.toString();
      return request<GraphData>(`/knowledge-graph${qs ? `?${qs}` : ''}`);
    },
    getNeighborhood: (params?: { node_id?: string; depth?: number; limit?: number }) => {
      const search = new URLSearchParams();
      if (params?.node_id) search.append('node_id', params.node_id);
      if (params?.depth) search.append('depth', params.depth.toString());
      if (params?.limit) search.append('limit', params.limit.toString());
      const qs = search.toString();
      return request<GraphData>(`/knowledge-graph/neighborhood${qs ? `?${qs}` : ''}`);
    },
    getStats: () => request<GraphStats>('/knowledge-graph/stats'),
    query: (query: string) =>
      request<GraphQueryResponse>('/knowledge-graph/query', {
        method: 'POST',
        body: JSON.stringify({ query }),
      }),
    sync: () =>
      request<GraphSyncResponse>('/knowledge-graph/sync', {
        method: 'POST',
      }),
    extract: (text: string, document_name?: string, persist: boolean = false) =>
      request<{ entities: any[]; relationships: any[] }>(`/knowledge-graph/extract?persist=${persist}`, {
        method: 'POST',
        body: JSON.stringify({ text, document_name }),
      }),
    deleteNode: (nodeId: string) =>
      request<void>(`/knowledge-graph/nodes/${nodeId}`, { method: 'DELETE' }),
    clear: () =>
      request<void>('/knowledge-graph/clear', { method: 'DELETE' }),
  },

  // Phase 5: Multi-Agent System
  agents: {
    orchestrate: (data: OrchestrationRequest) =>
      request<OrchestrationResult>('/agents/orchestrate', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    getRun: (runId: string) => request<OrchestrationResult>(`/agents/runs/${runId}`),
    listDefinitions: () => request<{ agents: any[]; count: number }>('/agents/definitions'),
  },

  // Phase 6: Tools & Action System
  actions: {
    listTools: () => request<ToolDefinition[]>('/actions/tools'),
    propose: (data: { tool_name: string; action_type: string; title: string; description?: string; parameters: Record<string, any> }) =>
      request<ActionProposal>('/actions/propose', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    listProposals: (statusFilter?: string) => {
      const q = statusFilter ? `?status_filter=${encodeURIComponent(statusFilter)}` : '';
      return request<ActionProposal[]>(`/actions/proposals${q}`);
    },
    approveProposal: (id: string) =>
      request<ActionProposal>(`/actions/proposals/${id}/approve`, {
        method: 'POST',
      }),
    rejectProposal: (id: string, reason?: string) =>
      request<ActionProposal>(`/actions/proposals/${id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ approved: false, reason }),
      }),
    listAuditLogs: (limit: number = 50) =>
      request<AuditLogItem[]>(`/actions/audit-logs?limit=${limit}`),
  },

  // Calendar
  calendar: {
    listEvents: (params?: { start_time?: string; end_time?: string }) => {
      const search = new URLSearchParams();
      if (params?.start_time) search.append('start_time', params.start_time);
      if (params?.end_time) search.append('end_time', params.end_time);
      const qs = search.toString();
      return request<CalendarEventItem[]>(`/calendar/events${qs ? `?${qs}` : ''}`);
    },
    getFreeSlots: (date?: string) => {
      const q = date ? `?date=${encodeURIComponent(date)}` : '';
      return request<{ free_slots: any[]; count: number }>(`/calendar/free-slots${q}`);
    },
    createEvent: (data: { title: string; description?: string; start_time: string; end_time: string; location?: string; event_type?: string; is_all_day?: boolean }) =>
      request<CalendarEventItem>('/calendar/events', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    deleteEvent: (id: string) =>
      request<void>(`/calendar/events/${id}`, { method: 'DELETE' }),
  },

  // Phase 8: Proactive Intelligence & AI Recommendations
  recommendations: {
    list: () => request<AIRecommendation[]>('/recommendations'),
    generate: () => request<AIRecommendation[]>('/recommendations/generate', { method: 'POST' }),
    dismiss: (id: string) => request<AIRecommendation>(`/recommendations/${id}/dismiss`, { method: 'POST' }),
    act: (id: string, payload?: Record<string, any>) =>
      request<any>(`/recommendations/${id}/act`, {
        method: 'POST',
        body: payload ? JSON.stringify(payload) : undefined,
      }),
    getPreferences: () => request<ProactivePreferences>('/recommendations/preferences'),
    updatePreferences: (data: Partial<ProactivePreferences>) =>
      request<ProactivePreferences>('/recommendations/preferences', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },

  // Workflows
  workflows: {
    runInterviewPrep: (message: string) =>
      request<OrchestrationResult>('/workflows/interview-prep', {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
    approveCalendar: (proposalId: string) =>
      request<ActionProposal>(`/workflows/interview-prep/approve-calendar/${proposalId}`, {
        method: 'POST',
      }),
  },

  // Phase 9: AI Evaluation, Observability & MLOps
  evaluation: {
    run: () => request<EvaluationSummary>('/evaluation/run', { method: 'POST' }),
    getSummary: () => request<EvaluationSummary>('/evaluation/summary'),
    getRag: () => request<RAGEvalResponse>('/evaluation/rag'),
    getAgent: () => request<AgentEvalResponse>('/evaluation/agent'),
  },

  observability: {
    getTraces: (limit: number = 20, status?: string) => {
      const q = status ? `?limit=${limit}&status=${encodeURIComponent(status)}` : `?limit=${limit}`;
      return request<TraceListItem[]>(`/observability/traces${q}`);
    },
    getTrace: (traceId: string) => request<Trace>(`/observability/traces/${traceId}`),
    triggerDemoTrace: () => request<Trace>('/observability/traces/demo', { method: 'POST' }),
    getMetrics: () => request<SystemMetrics>('/observability/metrics'),
  },

  mlops: {
    getExperiments: () => request<MLflowExperiment[]>('/mlops/experiments'),
    getExperimentRuns: (experimentName: string, limit: number = 20) =>
      request<MLflowRun[]>(`/mlops/experiments/${encodeURIComponent(experimentName)}/runs?limit=${limit}`),
    getRegistry: () => request<ModelRegistry>('/mlops/registry'),
  },
};




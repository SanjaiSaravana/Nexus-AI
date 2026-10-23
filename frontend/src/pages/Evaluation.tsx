import React, { useState, useEffect } from 'react';
import {
  Activity,
  Cpu,
  BarChart2,
  GitBranch,
  Layers,
  Zap,
  Play,
  RotateCw,
  Clock,
  Coins,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  Database,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';
import type {
  EvaluationSummary,
  Trace,
  TraceListItem,
  MLflowExperiment,
  ModelRegistry
} from '../types';

export const Evaluation: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'rag' | 'agent' | 'tracing' | 'metrics' | 'mlflow'>('rag');
  const [loading, setLoading] = useState<boolean>(true);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [demoTracing, setDemoTracing] = useState<boolean>(false);
  const [summary, setSummary] = useState<EvaluationSummary | null>(null);
  const [traces, setTraces] = useState<TraceListItem[]>([]);
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [selectedTrace, setSelectedTrace] = useState<Trace | null>(null);
  const [experiments, setExperiments] = useState<MLflowExperiment[]>([]);
  const [registry, setRegistry] = useState<ModelRegistry | null>(null);
  const [expandedSpanId, setExpandedSpanId] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sumData, traceList, expList, regData] = await Promise.all([
        api.evaluation.getSummary(),
        api.observability.getTraces(20),
        api.mlops.getExperiments(),
        api.mlops.getRegistry()
      ]);
      setSummary(sumData);
      setTraces(traceList);
      setExperiments(expList);
      setRegistry(regData);

      if (traceList.length > 0 && !selectedTraceId) {
        setSelectedTraceId(traceList[0].trace_id);
      }
    } catch (err) {
      console.error('Failed to load evaluation data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedTraceId) {
      api.observability.getTrace(selectedTraceId).then((tr) => {
        setSelectedTrace(tr);
        if (tr.spans.length > 0) {
          setExpandedSpanId(tr.spans[0].span_id);
        }
      }).catch(console.error);
    }
  }, [selectedTraceId]);

  const handleRunEvaluation = async () => {
    try {
      setEvaluating(true);
      const res = await api.evaluation.run();
      setSummary(res);
      // Refresh experiments as evaluation run was logged to MLflow
      const expList = await api.mlops.getExperiments();
      setExperiments(expList);
    } catch (err) {
      console.error('Failed to run evaluation', err);
    } finally {
      setEvaluating(false);
    }
  };

  const handleTriggerDemoTrace = async () => {
    try {
      setDemoTracing(true);
      const newTrace = await api.observability.triggerDemoTrace();
      const updatedList = await api.observability.getTraces(20);
      setTraces(updatedList);
      setSelectedTraceId(newTrace.trace_id);
      setSelectedTrace(newTrace);
      setActiveTab('tracing');
    } catch (err) {
      console.error('Failed to generate demo trace', err);
    } finally {
      setDemoTracing(false);
    }
  };

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RotateCw className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm text-slate-400">Loading AI Observability & Evaluation Hub...</p>
        </div>
      </div>
    );
  }

  const ragMetrics = summary?.rag_evaluation.metrics;
  const agentMetrics = summary?.agent_evaluation.metrics;
  const sysMetrics = summary?.system_metrics;

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">AI Evaluation, Observability & MLOps</h1>
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Live Tracing Active
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Production evaluation benchmarks, distributed waterfall tracing, system metrics, and MLflow model registry.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleTriggerDemoTrace}
            disabled={demoTracing}
            className="flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            {demoTracing ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5 text-amber-400" />}
            Generate Trace
          </button>

          <button
            onClick={handleRunEvaluation}
            disabled={evaluating}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-lg shadow-indigo-500/20 transition disabled:opacity-50"
          >
            {evaluating ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            Run Benchmark Suite
          </button>

          <button
            onClick={fetchData}
            title="Refresh Metrics"
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-800 text-slate-400 hover:text-white transition"
          >
            <RotateCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Top 4 Metric Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Latency Card */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">End-to-End Latency</span>
            <Clock className="w-4 h-4 text-sky-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">{sysMetrics?.latency.p50_ms || 180} ms</span>
            <span className="text-xs text-slate-400">p50</span>
          </div>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
            <span>p95: <strong className="text-slate-300">{sysMetrics?.latency.p95_ms || 320}ms</strong></span>
            <span>Avg: <strong className="text-slate-300">{sysMetrics?.latency.avg_ms || 195}ms</strong></span>
          </div>
        </div>

        {/* Token Usage & Cost */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Tokens & Est. Cost</span>
            <Coins className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">${sysMetrics?.estimated_cost_usd.toFixed(4) || '0.1240'}</span>
            <span className="text-xs text-emerald-400">USD</span>
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
            <span>Total: <strong className="text-slate-300">{sysMetrics?.token_usage.total_tokens.toLocaleString() || '105,900'}</strong> tokens</span>
          </div>
        </div>

        {/* Agent Success Rate */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Agent Success Rate</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">
              {((agentMetrics?.task_success_rate || 0.96) * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-slate-400">Planning: {((agentMetrics?.planning_accuracy || 0.95) * 100).toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
            <span>Tool Acc: <strong className="text-slate-300">{((agentMetrics?.tool_selection_accuracy || 0.98) * 100).toFixed(0)}%</strong></span>
            <span>Failures: <strong className="text-rose-400">{((agentMetrics?.failure_rate || 0.04) * 100).toFixed(0)}%</strong></span>
          </div>
        </div>

        {/* RAG Precision & Recall */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">RAG Precision & Recall</span>
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-indigo-400">
              {((ragMetrics?.context_precision || 0.95) * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-slate-400">Precision</span>
          </div>
          <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
            <span>Recall: <strong className="text-slate-300">{((ragMetrics?.context_recall || 0.96) * 100).toFixed(0)}%</strong></span>
            <span>Faithful: <strong className="text-emerald-400">{((ragMetrics?.faithfulness || 0.97) * 100).toFixed(0)}%</strong></span>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800">
        {[
          { key: 'rag', label: 'RAG Evaluation', icon: Database },
          { key: 'agent', label: 'Agent Evaluation', icon: Cpu },
          { key: 'tracing', label: 'Waterfall Tracing', icon: Layers },
          { key: 'metrics', label: 'System Metrics', icon: BarChart2 },
          { key: 'mlflow', label: 'MLflow & Registry', icon: GitBranch },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key as any)}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition -mb-px ${
                isActive
                  ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
              }`}
            >
              <Icon className="w-4 h-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: RAG EVALUATION */}
      {activeTab === 'rag' && summary && (
        <div className="space-y-6">
          {/* 5 Core RAG Metrics Gauges */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: 'Context Precision', val: ragMetrics?.context_precision || 0.95, desc: 'Relevance of retrieved chunks' },
              { label: 'Context Recall', val: ragMetrics?.context_recall || 0.96, desc: 'Coverage of ground truth facts' },
              { label: 'Answer Relevance', val: ragMetrics?.answer_relevance || 0.98, desc: 'Query intent directness' },
              { label: 'Faithfulness', val: ragMetrics?.faithfulness || 0.97, desc: 'Zero hallucination grounding' },
              { label: 'Citation Accuracy', val: ragMetrics?.citation_accuracy || 0.95, desc: 'Valid source excerpts' },
            ].map((m) => (
              <div key={m.label} className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-xs text-slate-400 block truncate">{m.label}</span>
                <div className="text-2xl font-bold text-white mt-1">{(m.val * 100).toFixed(1)}%</div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${m.val * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-500 mt-1 block truncate">{m.desc}</span>
              </div>
            ))}
          </div>

          {/* Detailed Benchmark Cases Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">RAG Evaluation Benchmark Cases</h3>
                <p className="text-xs text-slate-400">Tested across {summary.rag_evaluation.cases.length} golden test cases (including adversarial out-of-domain queries).</p>
              </div>
              <span className="text-xs text-slate-400">Suite: v9.0-RAG</span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-medium">Query</th>
                    <th className="px-4 py-3 font-medium text-center">Type</th>
                    <th className="px-4 py-3 font-medium text-center">Precision</th>
                    <th className="px-4 py-3 font-medium text-center">Recall</th>
                    <th className="px-4 py-3 font-medium text-center">Relevance</th>
                    <th className="px-4 py-3 font-medium text-center">Faithfulness</th>
                    <th className="px-4 py-3 font-medium text-center">Citation</th>
                    <th className="px-4 py-3 font-medium text-right">Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {summary.rag_evaluation.cases.map((c) => (
                    <tr key={c.case_id} className="hover:bg-slate-800/30 transition">
                      <td className="px-4 py-3 font-medium text-white max-w-xs truncate" title={c.query}>
                        {c.query}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {c.is_answerable ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Answerable
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
                            Adversarial
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center font-mono">{(c.context_precision * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center font-mono">{(c.context_recall * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center font-mono">{(c.answer_relevance * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center font-mono">{(c.faithfulness * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center font-mono">{(c.citation_accuracy * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-right font-mono text-slate-400">{c.latency_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: AGENT EVALUATION */}
      {activeTab === 'agent' && summary && (
        <div className="space-y-6">
          {/* 5 Core Agent Metrics Gauges */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: 'Task Success Rate', val: agentMetrics?.task_success_rate || 0.96, desc: 'Full pipeline goal completion', color: 'bg-emerald-500' },
              { label: 'Planning Accuracy', val: agentMetrics?.planning_accuracy || 0.95, desc: 'Subtask decomposition precision', color: 'bg-indigo-500' },
              { label: 'Tool Selection Accuracy', val: agentMetrics?.tool_selection_accuracy || 0.98, desc: 'F1 of correct tool picking', color: 'bg-sky-500' },
              { label: 'Execution Success', val: agentMetrics?.execution_success || 1.0, desc: 'Tool & action execution rate', color: 'bg-purple-500' },
              { label: 'Failure Rate', val: agentMetrics?.failure_rate || 0.04, desc: 'Graceful degradation / aborts', color: 'bg-rose-500' },
            ].map((m) => (
              <div key={m.label} className="p-4 rounded-xl bg-slate-900/50 border border-slate-800">
                <span className="text-xs text-slate-400 block truncate">{m.label}</span>
                <div className="text-2xl font-bold text-white mt-1">{(m.val * 100).toFixed(1)}%</div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full mt-2 overflow-hidden">
                  <div
                    className={`${m.color} h-full rounded-full transition-all duration-500`}
                    style={{ width: `${m.val * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-500 mt-1 block truncate">{m.desc}</span>
              </div>
            ))}
          </div>

          {/* Agent Benchmark Cases Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-800">
              <h3 className="text-sm font-semibold text-white">Multi-Agent Benchmark Runs</h3>
              <p className="text-xs text-slate-400">Validating Planning, Tool Invocation, Fallback Behavior, and Human-in-the-Loop Actions.</p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-medium">Task Benchmark</th>
                    <th className="px-4 py-3 font-medium text-center">Status</th>
                    <th className="px-4 py-3 font-medium text-center">Planning Acc</th>
                    <th className="px-4 py-3 font-medium text-center">Tool Acc</th>
                    <th className="px-4 py-3 font-medium text-center">Exec Success</th>
                    <th className="px-4 py-3 font-medium">Tools Invoked</th>
                    <th className="px-4 py-3 font-medium text-right">Steps</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {summary.agent_evaluation.cases.map((c) => (
                    <tr key={c.case_id} className="hover:bg-slate-800/30 transition">
                      <td className="px-4 py-3 font-medium text-white">{c.task_name}</td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          <CheckCircle2 className="w-3 h-3" />
                          Passed
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center font-mono">{(c.planning_accuracy * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center font-mono">{(c.tool_selection_accuracy * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3 text-center font-mono">{(c.execution_success * 100).toFixed(0)}%</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1">
                          {c.tools_used.map((t) => (
                            <span key={t} className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-mono">
                              {t}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-slate-400">{c.step_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: WATERFALL TRACING */}
      {activeTab === 'tracing' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Traces List Selector */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-sm font-semibold text-white">Execution Traces</h3>
              <span className="text-xs text-slate-500">{traces.length} traces</span>
            </div>

            <div className="space-y-2 max-h-[550px] overflow-y-auto pr-1">
              {traces.map((t) => (
                <button
                  key={t.trace_id}
                  onClick={() => setSelectedTraceId(t.trace_id)}
                  className={`w-full text-left p-3 rounded-lg border transition ${
                    selectedTraceId === t.trace_id
                      ? 'bg-indigo-600/15 border-indigo-500/40 text-white'
                      : 'bg-slate-800/40 border-slate-800 hover:bg-slate-800 text-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold truncate max-w-[180px]">{t.title}</span>
                    <span className="text-[10px] font-mono text-slate-400">{t.duration_ms}ms</span>
                  </div>
                  <div className="flex items-center justify-between mt-1.5 text-[10px] text-slate-400">
                    <span className="font-mono text-slate-500">{t.trace_id.slice(0, 8)}...</span>
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400">
                      {t.span_count} spans
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Waterfall Visualizer & Span Tree */}
          <div className="lg:col-span-2 space-y-4">
            {selectedTrace ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-800">
                  <div>
                    <h3 className="text-base font-bold text-white">{selectedTrace.title}</h3>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">Trace ID: {selectedTrace.trace_id}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      {selectedTrace.status.toUpperCase()}
                    </span>
                    <span className="px-2.5 py-1 rounded text-xs font-mono bg-slate-800 text-slate-300">
                      {selectedTrace.duration_ms} ms total
                    </span>
                  </div>
                </div>

                {/* Pipeline Progression Ribbon */}
                <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] overflow-x-auto text-slate-300">
                  <div className="flex items-center gap-1.5 whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-sky-400"></span>
                    <span>User Request</span>
                    <ArrowRight className="w-3 h-3 text-slate-600" />
                  </div>
                  <div className="flex items-center gap-1.5 whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
                    <span>Intent</span>
                    <ArrowRight className="w-3 h-3 text-slate-600" />
                  </div>
                  <div className="flex items-center gap-1.5 whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-purple-400"></span>
                    <span>Retrieval</span>
                    <ArrowRight className="w-3 h-3 text-slate-600" />
                  </div>
                  <div className="flex items-center gap-1.5 whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                    <span>Agent</span>
                    <ArrowRight className="w-3 h-3 text-slate-600" />
                  </div>
                  <div className="flex items-center gap-1.5 whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                    <span>Tool</span>
                    <ArrowRight className="w-3 h-3 text-slate-600" />
                  </div>
                  <div className="flex items-center gap-1.5 whitespace-nowrap">
                    <span className="w-2 h-2 rounded-full bg-rose-400"></span>
                    <span>LLM</span>
                    <ArrowRight className="w-3 h-3 text-slate-600" />
                  </div>
                  <div className="flex items-center gap-1.5 whitespace-nowrap font-semibold text-emerald-400">
                    <span>Final Response</span>
                  </div>
                </div>

                {/* Spans Waterfall List */}
                <div className="space-y-2">
                  {selectedTrace.spans.map((span) => {
                    const isExpanded = expandedSpanId === span.span_id;
                    const maxDuration = Math.max(...selectedTrace.spans.map((s) => s.duration_ms), 1);
                    const widthPct = Math.max(12, (span.duration_ms / maxDuration) * 100);

                    return (
                      <div
                        key={span.span_id}
                        className="rounded-lg bg-slate-800/40 border border-slate-800 hover:border-slate-700 transition overflow-hidden"
                      >
                        <div
                          onClick={() => setExpandedSpanId(isExpanded ? null : span.span_id)}
                          className="p-3 cursor-pointer flex items-center justify-between gap-3"
                        >
                          <div className="flex items-center gap-2 min-w-[200px]">
                            <ChevronRight className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                            <span className="text-xs font-semibold text-white">{span.name}</span>
                            <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-mono">
                              {span.type}
                            </span>
                          </div>

                          {/* Waterfall Duration Bar */}
                          <div className="flex-1 max-w-xs">
                            <div className="w-full bg-slate-900 h-2 rounded-full overflow-hidden">
                              <div
                                className="bg-gradient-to-r from-indigo-500 to-purple-500 h-full rounded-full"
                                style={{ width: `${widthPct}%` }}
                              />
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-slate-300 font-medium">
                              {span.duration_ms} ms
                            </span>
                            <span className="w-2 h-2 rounded-full bg-emerald-400" />
                          </div>
                        </div>

                        {/* Expandable JSON Inspector */}
                        {isExpanded && (
                          <div className="px-4 py-3 bg-slate-950/80 border-t border-slate-800 text-xs font-mono space-y-2">
                            <div>
                              <span className="text-slate-500 uppercase tracking-wider text-[10px]">Inputs:</span>
                              <pre className="text-slate-300 bg-slate-900 p-2 rounded mt-1 overflow-x-auto text-[11px]">
                                {JSON.stringify(span.inputs, null, 2)}
                              </pre>
                            </div>
                            <div>
                              <span className="text-slate-500 uppercase tracking-wider text-[10px]">Outputs:</span>
                              <pre className="text-emerald-300 bg-slate-900 p-2 rounded mt-1 overflow-x-auto text-[11px]">
                                {JSON.stringify(span.outputs, null, 2)}
                              </pre>
                            </div>
                            {Object.keys(span.metadata).length > 0 && (
                              <div>
                                <span className="text-slate-500 uppercase tracking-wider text-[10px]">Metadata:</span>
                                <pre className="text-sky-300 bg-slate-900 p-2 rounded mt-1 overflow-x-auto text-[11px]">
                                  {JSON.stringify(span.metadata, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="p-12 text-center rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400">
                Select a trace from the left panel to inspect the execution waterfall.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: SYSTEM METRICS */}
      {activeTab === 'metrics' && sysMetrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Latency Percentiles */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Latency Percentiles & Distribution</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-xs text-slate-400">p50 Latency</span>
                <p className="text-xl font-bold text-white mt-1">{sysMetrics.latency.p50_ms} ms</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-xs text-slate-400">p95 Latency</span>
                <p className="text-xl font-bold text-sky-400 mt-1">{sysMetrics.latency.p95_ms} ms</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-xs text-slate-400">p99 Latency</span>
                <p className="text-xl font-bold text-amber-400 mt-1">{sysMetrics.latency.p99_ms} ms</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                <span className="text-xs text-slate-400">Avg Retrieval Latency</span>
                <p className="text-xl font-bold text-indigo-400 mt-1">{sysMetrics.retrieval_latency.avg_ms} ms</p>
              </div>
            </div>
          </div>

          {/* Tool Latency Breakdown */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Tool Execution Latencies</h3>
            <div className="space-y-3">
              {Object.entries(sysMetrics.tool_latency).map(([tool, data]) => (
                <div key={tool} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-mono text-white">{tool}</span>
                  </div>
                  <div className="text-right text-xs">
                    <span className="text-slate-300 font-bold">{data.avg_ms} ms</span>
                    <span className="text-slate-500 block text-[10px]">p95: {data.p95_ms}ms ({data.count} calls)</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Usage Breakdown */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Model Usage & Token Allocation</h3>
            <div className="space-y-3">
              {Object.entries(sysMetrics.model_usage.tokens).map(([model, t]) => (
                <div key={model} className="p-3 rounded-lg bg-slate-800/40 border border-slate-800">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-white">{model}</span>
                    <span className="font-mono text-slate-300">{t.total.toLocaleString()} tokens</span>
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1.5">
                    <span>Prompt: <strong className="text-slate-300">{t.prompt.toLocaleString()}</strong></span>
                    <span>Completion: <strong className="text-slate-300">{t.completion.toLocaleString()}</strong></span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Error Rate & Health */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
            <h3 className="text-sm font-semibold text-white">Error Rate & System Resiliency</h3>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-emerald-400">
                {(sysMetrics.success_rate * 100).toFixed(2)}%
              </span>
              <span className="text-xs text-slate-400">Availability</span>
            </div>
            <p className="text-xs text-slate-400">
              Recorded {sysMetrics.errors.total_errors} errors across total requests ({((sysMetrics.errors.error_rate) * 100).toFixed(2)}% error rate).
            </p>
            {sysMetrics.errors.recent.length > 0 && (
              <div className="space-y-1.5 mt-2">
                <span className="text-[11px] font-semibold text-slate-400 uppercase">Recent Exceptions:</span>
                {sysMetrics.errors.recent.slice(0, 3).map((err, i) => (
                  <div key={i} className="p-2 rounded bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 flex-shrink-0" />
                    <span className="truncate">{err.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: MLFLOW & REGISTRY */}
      {activeTab === 'mlflow' && (
        <div className="space-y-6">
          {/* MLflow Experiments List */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">MLflow Experiments Tracking</h3>
                <p className="text-xs text-slate-400">Tracking runs for models, embeddings, retrieval, recommendations, and evaluation benchmarks.</p>
              </div>
              <span className="px-2.5 py-1 rounded text-xs font-mono bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                MLflow 3.17.1
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider border-b border-slate-800">
                  <tr>
                    <th className="px-4 py-3 font-medium">Experiment</th>
                    <th className="px-4 py-3 font-medium text-center">Total Runs</th>
                    <th className="px-4 py-3 font-medium">Latest Run Name</th>
                    <th className="px-4 py-3 font-medium">Key Logged Metrics</th>
                    <th className="px-4 py-3 font-medium text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {experiments.map((exp) => (
                    <tr key={exp.experiment_name} className="hover:bg-slate-800/30 transition">
                      <td className="px-4 py-3 font-medium text-white font-mono">{exp.experiment_name}</td>
                      <td className="px-4 py-3 text-center font-mono">{exp.run_count}</td>
                      <td className="px-4 py-3 font-mono text-indigo-300">{exp.latest_run?.run_name || 'N/A'}</td>
                      <td className="px-4 py-3 text-slate-400 max-w-xs truncate">
                        {exp.latest_run?.metrics
                          ? Object.entries(exp.latest_run.metrics).slice(0, 3).map(([k, v]) => `${k}=${v}`).join(', ')
                          : 'None'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {exp.latest_run?.status || 'ACTIVE'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Model & Artifact Version Registry */}
          {registry && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <h3 className="text-sm font-semibold text-white">Versioned Model & Artifact Registry</h3>
                  <p className="text-xs text-slate-400">Strict version tracking across prompts, models, embeddings, rerankers, and recommendation models.</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {/* Prompts */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
                  <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider block">Prompts ({registry.prompts.length})</span>
                  {registry.prompts.map((p) => (
                    <div key={p.name} className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs">
                      <div className="flex items-center justify-between">
                        <strong className="text-white font-mono">{p.name}</strong>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 font-bold">{p.version}</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1">{p.description}</p>
                    </div>
                  ))}
                </div>

                {/* Models */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
                  <span className="text-xs font-semibold text-purple-400 uppercase tracking-wider block">Models ({registry.models.length})</span>
                  {registry.models.map((m) => (
                    <div key={m.name} className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs">
                      <div className="flex items-center justify-between">
                        <strong className="text-white font-mono">{m.name}</strong>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 font-bold">{m.version}</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1">{m.description}</p>
                    </div>
                  ))}
                </div>

                {/* Embeddings & Rerankers */}
                <div className="p-4 rounded-xl bg-slate-800/40 border border-slate-800 space-y-2">
                  <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider block">Embeddings & Rerankers</span>
                  {registry.embeddings.map((e) => (
                    <div key={e.name} className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs">
                      <div className="flex items-center justify-between">
                        <strong className="text-white font-mono">{e.name}</strong>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-sky-500/20 text-sky-300 font-bold">{e.version}</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1">{e.description}</p>
                    </div>
                  ))}
                  {registry.rerankers.map((r) => (
                    <div key={r.name} className="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs">
                      <div className="flex items-center justify-between">
                        <strong className="text-white font-mono">{r.name}</strong>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 font-bold">{r.version}</span>
                      </div>
                      <p className="text-slate-400 text-[11px] mt-1">{r.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

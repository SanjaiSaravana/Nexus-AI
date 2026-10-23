import React, { useEffect, useState } from 'react';
import { 
  CheckCircle2, 
  Circle, 
  Clock, 
  Target, 
  FolderKanban, 
  TrendingUp, 
  ListTodo, 
  Calendar, 
  ArrowUpRight, 
  Plus, 
  RefreshCw,
  AlertCircle,
  Sparkles,
  Zap,
  Settings,
  X as CloseIcon,
  Sliders
} from 'lucide-react';
import { api } from '../services/api';
import type { DashboardOverview, Task, AIRecommendation, ProactivePreferences } from '../types';
import { StatCard } from '../components/StatCard';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { EmptyState } from '../components/EmptyState';

interface DashboardProps {
  onNavigate: (path: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [data, setData] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Proactive Intelligence State
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [preferences, setPreferences] = useState<ProactivePreferences | null>(null);
  const [showPreferencesModal, setShowPreferencesModal] = useState(false);
  const [refreshingRecs, setRefreshingRecs] = useState(false);
  const [actingOnId, setActingOnId] = useState<string | null>(null);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  const fetchOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const overview = await api.dashboard.getOverview();
      setData(overview);
      if (overview.ai_recommendations) {
        setRecommendations(overview.ai_recommendations);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard overview');
    } finally {
      setLoading(false);
    }
  };

  const loadPreferences = async () => {
    try {
      const prefs = await api.recommendations.getPreferences();
      setPreferences(prefs);
    } catch {
      // silent
    }
  };

  useEffect(() => {
    fetchOverview();
    loadPreferences();
  }, []);

  const handleRefreshRecommendations = async () => {
    try {
      setRefreshingRecs(true);
      const fresh = await api.recommendations.generate();
      setRecommendations(fresh);
    } catch (err: any) {
      alert(`Error scanning proactive intelligence: ${err.message}`);
    } finally {
      setRefreshingRecs(false);
    }
  };

  const handleDismissRecommendation = async (id: string) => {
    try {
      // Optimistic update
      setRecommendations((prev) => prev.filter((r) => r.id !== id));
      await api.recommendations.dismiss(id);
    } catch (err: any) {
      alert(`Error dismissing recommendation: ${err.message}`);
      fetchOverview();
    }
  };

  const handleActOnRecommendation = async (rec: AIRecommendation) => {
    setActingOnId(rec.id);
    setActionSuccessMsg(null);
    try {
      await api.recommendations.act(rec.id);
      setRecommendations((prev) => prev.filter((r) => r.id !== rec.id));

      if (rec.action_type === 'create_preparation_plan') {
        setActionSuccessMsg('Interview preparation plan generated! Tasks have been persisted, and a calendar action proposal is waiting in chat/actions for your confirmation.');
      } else {
        setActionSuccessMsg(`Action executed: ${rec.title}`);
      }

      // Refresh overview data
      await fetchOverview();
    } catch (err: any) {
      alert(`Action error: ${err.message}`);
    } finally {
      setActingOnId(null);
    }
  };

  const handleSavePreferences = async (newPrefs: Partial<ProactivePreferences>) => {
    try {
      const updated = await api.recommendations.updatePreferences(newPrefs);
      setPreferences(updated);
      setShowPreferencesModal(false);
      handleRefreshRecommendations();
    } catch (err: any) {
      alert(`Error saving preferences: ${err.message}`);
    }
  };

  const toggleTaskCompletion = async (task: Task) => {
    try {
      const newStatus = task.status === 'completed' ? 'todo' : 'completed';
      await api.tasks.update(task.id, { status: newStatus });
      fetchOverview();
    } catch (err: any) {
      alert(`Error updating task: ${err.message}`);
    }
  };

  const incrementGoalProgress = async (goalId: string, currentPct: number) => {
    try {
      const nextPct = Math.min(100, currentPct + 10);
      await api.goals.update(goalId, { 
        progress_pct: nextPct,
        status: nextPct === 100 ? 'completed' : 'active'
      });
      fetchOverview();
    } catch (err: any) {
      alert(`Error updating goal: ${err.message}`);
    }
  };

  if (loading && !data) {
    return (
      <div>
        <div className="stat-grid">
          <LoadingSkeleton count={4} height="95px" />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px', marginTop: '24px' }}>
          <LoadingSkeleton count={3} height="180px" />
          <LoadingSkeleton count={3} height="180px" />
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Top action bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
            Executive Dashboard
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Real-time intelligence on your workflow, milestones, and goals
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary btn-sm" onClick={fetchOverview} title="Refresh metrics">
            <RefreshCw size={14} />
            <span>Refresh</span>
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => onNavigate('/tasks')}>
            <Plus size={14} />
            <span>New Task</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '12px 16px',
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.25)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--accent-rose)',
          fontSize: '0.875rem',
          marginBottom: '24px'
        }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {actionSuccessMsg && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          borderRadius: 'var(--radius-md)',
          color: '#10b981',
          fontSize: '0.875rem',
          marginBottom: '20px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} />
            <span>{actionSuccessMsg}</span>
          </div>
          <button
            onClick={() => setActionSuccessMsg(null)}
            style={{ background: 'transparent', border: 'none', color: '#10b981', cursor: 'pointer' }}
          >
            <CloseIcon size={14} />
          </button>
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="stat-grid" style={{ marginBottom: '24px' }}>
        <StatCard
          label="Total Tasks"
          value={data?.stats.total_tasks || 0}
          icon={ListTodo}
          iconColor="#6366f1"
          iconBg="rgba(99, 102, 241, 0.12)"
          subtext={`${data?.stats.completed_tasks || 0} completed`}
        />
        <StatCard
          label="Task Completion"
          value={`${data?.stats.completion_rate || 0}%`}
          icon={TrendingUp}
          iconColor="#10b981"
          iconBg="rgba(16, 185, 129, 0.12)"
          subtext={`${data?.stats.pending_tasks || 0} pending`}
        />
        <StatCard
          label="Active Projects"
          value={data?.stats.active_projects_count || 0}
          icon={FolderKanban}
          iconColor="#06b6d4"
          iconBg="rgba(6, 182, 212, 0.12)"
          subtext="Under management"
        />
        <StatCard
          label="Goal Progress"
          value={`${data?.stats.average_goal_progress || 0}%`}
          icon={Target}
          iconColor="#a855f7"
          iconBg="rgba(168, 85, 247, 0.12)"
          subtext={`${data?.stats.active_goals_count || 0} active goals`}
        />
      </div>

      {/* =========================================================================
          PHASE 8: AI Recommendations Section (Proactive Intelligence)
         ========================================================================= */}
      <div className="card" style={{
        marginBottom: '28px',
        padding: '20px 24px',
        background: 'linear-gradient(135deg, rgba(30, 27, 75, 0.35) 0%, rgba(15, 23, 42, 0.8) 100%)',
        border: '1px solid rgba(99, 102, 241, 0.35)',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.25)'
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              boxShadow: '0 0 16px rgba(99, 102, 241, 0.5)'
            }}>
              <Sparkles size={20} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 800, letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
                  AI Recommendations
                </h3>
                <span style={{
                  fontSize: '0.68rem',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: 'rgba(99, 102, 241, 0.2)',
                  color: 'var(--primary)',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em'
                }}>
                  Proactive Intelligence
                </span>
              </div>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                NEXUS detects upcoming deadlines, preparation gaps, conflicting events, and inactive goals
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '0.75rem', padding: '6px 12px' }}
              onClick={() => setShowPreferencesModal(true)}
              title="Anti-spam & notification preferences"
            >
              <Settings size={14} />
              <span>Preferences</span>
            </button>
            <button
              className="btn btn-secondary btn-sm"
              style={{ fontSize: '0.75rem', padding: '6px 12px' }}
              onClick={handleRefreshRecommendations}
              title="Scan for proactive intelligence"
              disabled={refreshingRecs}
            >
              <RefreshCw size={14} className={refreshingRecs ? 'animate-spin' : ''} style={{ animation: refreshingRecs ? 'spin 1s linear infinite' : 'none' }} />
              <span>{refreshingRecs ? 'Scanning...' : 'Scan Now'}</span>
            </button>
          </div>
        </div>

        {/* List of Recommendations */}
        {recommendations.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '28px 20px',
            borderRadius: 'var(--radius-md)',
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px dashed var(--border-subtle)',
            color: 'var(--text-muted)',
            fontSize: '0.85rem'
          }}>
            <CheckCircle2 size={24} style={{ color: '#10b981', margin: '0 auto 8px auto', display: 'block' }} />
            <span>NEXUS proactive intelligence is actively monitoring your workflow. No urgent preparation gaps or conflicts detected.</span>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {recommendations.map((rec) => {
              const priorityColor = rec.priority_level === 'urgent'
                ? '#ef4444'
                : (rec.priority_level === 'high' ? '#f59e0b' : 'var(--primary)');
              const priorityBg = rec.priority_level === 'urgent'
                ? 'rgba(239, 68, 68, 0.12)'
                : (rec.priority_level === 'high' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(99, 102, 241, 0.12)');

              return (
                <div
                  key={rec.id}
                  style={{
                    background: 'rgba(15, 23, 42, 0.85)',
                    border: `1px solid ${priorityColor}40`,
                    borderRadius: 'var(--radius-md)',
                    padding: '16px 18px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '16px' }}>
                    <div style={{ flex: 1 }}>
                      {/* Priority & Title */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                        <span style={{
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '6px',
                          background: priorityBg,
                          color: priorityColor,
                          textTransform: 'uppercase',
                          letterSpacing: '0.04em'
                        }}>
                          {rec.priority_level} ({(rec.priority_score * 100).toFixed(0)}%)
                        </span>
                        <h4 style={{ fontSize: '0.98rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                          {rec.title}
                        </h4>
                      </div>

                      {/* Recommendation text */}
                      <p style={{ fontSize: '0.92rem', color: 'var(--text-primary)', lineHeight: 1.55, marginBottom: '6px' }}>
                        "{rec.recommendation}"
                      </p>

                      {/* Reason */}
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ color: '#a855f7', fontWeight: 600 }}>💡 Reason:</span>
                        <span>{rec.reason}</span>
                      </p>
                    </div>

                    {/* Action & Dismiss buttons */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                      {rec.action_type && (
                        <button
                          className="btn btn-primary btn-sm"
                          style={{
                            background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 100%)',
                            fontSize: '0.8rem',
                            padding: '6px 14px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            fontWeight: 600
                          }}
                          onClick={() => handleActOnRecommendation(rec)}
                          disabled={actingOnId === rec.id}
                        >
                          <Zap size={14} />
                          <span>
                            {actingOnId === rec.id ? 'Creating Plan...' : (rec.action_type === 'create_preparation_plan' ? 'Create Preparation Plan' : 'Take Action')}
                          </span>
                        </button>
                      )}
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{
                          padding: '6px 10px',
                          fontSize: '0.78rem',
                          color: 'var(--text-muted)'
                        }}
                        onClick={() => handleDismissRecommendation(rec.id)}
                        title="Dismiss recommendation"
                      >
                        <CloseIcon size={14} />
                        <span>Dismiss</span>
                      </button>
                    </div>
                  </div>

                  {/* Metadata Pills: related goal, related deadline, category */}
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    alignItems: 'center',
                    gap: '12px',
                    paddingTop: '8px',
                    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                    fontSize: '0.75rem',
                    color: 'var(--text-muted)'
                  }}>
                    {rec.related_goal && (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <span>🎯 Related Goal:</span>
                        <strong style={{ color: 'var(--text-primary)' }}>{rec.related_goal}</strong>
                      </span>
                    )}
                    {rec.related_deadline && (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <span>⏰ Deadline:</span>
                        <strong style={{ color: '#f59e0b' }}>{rec.related_deadline}</strong>
                      </span>
                    )}
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      <span>🏷️ Context:</span>
                      <strong style={{ color: 'var(--primary)' }}>{rec.category.replace(/_/g, ' ')}</strong>
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Two Column Layout: Today's Tasks & Upcoming Deadlines */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px', marginBottom: '28px' }}>
        
        {/* Today's Tasks */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ color: 'var(--primary)' }}>
                <CheckCircle2 size={20} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Today's Tasks</h3>
            </div>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('/tasks')}
              style={{ fontSize: '0.75rem', padding: '4px 8px' }}
            >
              View All <ArrowUpRight size={12} />
            </button>
          </div>

          {(!data?.todays_tasks || data.todays_tasks.length === 0) ? (
            <EmptyState
              icon={CheckCircle2}
              title="No Tasks for Today"
              description="You are all caught up! Create a new task to keep making progress."
              actionText="Add Task"
              onAction={() => onNavigate('/tasks')}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {data.todays_tasks.map((task) => (
                <div
                  key={task.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
                    <button
                      onClick={() => toggleTaskCompletion(task)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: task.status === 'completed' ? 'var(--accent-emerald)' : 'var(--text-muted)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        flexShrink: 0
                      }}
                    >
                      {task.status === 'completed' ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                    </button>
                    <div style={{ overflow: 'hidden' }}>
                      <p style={{
                        fontSize: '0.875rem',
                        fontWeight: 500,
                        textDecoration: task.status === 'completed' ? 'line-through' : 'none',
                        color: task.status === 'completed' ? 'var(--text-muted)' : 'var(--text-primary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        {task.title}
                      </p>
                      {task.due_date && (
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                          <Clock size={12} /> Due {task.due_date}
                        </span>
                      )}
                    </div>
                  </div>
                  <span className={`badge badge-${task.priority}`} style={{ flexShrink: 0, textTransform: 'capitalize' }}>
                    {task.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Upcoming Tasks */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ color: 'var(--accent-cyan)' }}>
                <Calendar size={20} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Upcoming Deadlines</h3>
            </div>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('/tasks')}
              style={{ fontSize: '0.75rem', padding: '4px 8px' }}
            >
              View All <ArrowUpRight size={12} />
            </button>
          </div>

          {(!data?.upcoming_tasks || data.upcoming_tasks.length === 0) ? (
            <EmptyState
              icon={Calendar}
              title="No Upcoming Deadlines"
              description="No tasks due in the next 7 days. Plan ahead by adding target dates."
              actionText="View Tasks"
              onAction={() => onNavigate('/tasks')}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {data.upcoming_tasks.map((task) => (
                <div
                  key={task.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', overflow: 'hidden' }}>
                    <div style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', flexShrink: 0 }}>
                      <Clock size={16} />
                    </div>
                    <div style={{ overflow: 'hidden' }}>
                      <p style={{
                        fontSize: '0.875rem',
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis'
                      }}>
                        {task.title}
                      </p>
                      <span style={{ fontSize: '0.75rem', color: 'var(--accent-amber)', display: 'block', marginTop: '2px' }}>
                        Due {task.due_date}
                      </span>
                    </div>
                  </div>
                  <span className={`badge badge-${task.priority}`} style={{ flexShrink: 0, textTransform: 'capitalize' }}>
                    {task.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Grid: Active Projects & Active Goals */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        
        {/* Active Projects */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ color: 'var(--accent-cyan)' }}>
                <FolderKanban size={20} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Active Projects</h3>
            </div>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('/projects')}
              style={{ fontSize: '0.75rem', padding: '4px 8px' }}
            >
              All Projects <ArrowUpRight size={12} />
            </button>
          </div>

          {(!data?.active_projects || data.active_projects.length === 0) ? (
            <EmptyState
              icon={FolderKanban}
              title="No Active Projects"
              description="Start a project to organize tasks, documents, and technical milestones."
              actionText="Create Project"
              onAction={() => onNavigate('/projects')}
            />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '10px' }}>
              {data.active_projects.map((proj) => (
                <div
                  key={proj.id}
                  onClick={() => onNavigate('/projects')}
                  style={{
                    padding: '14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                    e.currentTarget.style.background = 'rgba(6, 182, 212, 0.04)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {proj.name}
                    </h4>
                    <span className="badge badge-primary" style={{ fontSize: '0.7rem', textTransform: 'capitalize' }}>
                      {proj.status}
                    </span>
                  </div>
                  {proj.description && (
                    <p style={{
                      fontSize: '0.8rem',
                      color: 'var(--text-secondary)',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      lineHeight: 1.5
                    }}>
                      {proj.description}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Goals & Progress */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ color: 'var(--accent-purple)' }}>
                <Target size={20} />
              </div>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700 }}>Strategic Goals</h3>
            </div>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigate('/goals')}
              style={{ fontSize: '0.75rem', padding: '4px 8px' }}
            >
              All Goals <ArrowUpRight size={12} />
            </button>
          </div>

          {(!data?.active_goals || data.active_goals.length === 0) ? (
            <EmptyState
              icon={Target}
              title="No Active Goals"
              description="Define strategic objectives to track high-level personal and career progress."
              actionText="Set Goal"
              onAction={() => onNavigate('/goals')}
            />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {data.active_goals.map((goal) => (
                <div
                  key={goal.id}
                  style={{
                    padding: '14px',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div>
                      <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {goal.title}
                      </h4>
                      <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                        {goal.category}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--accent-purple)' }}>
                        {goal.progress_pct}%
                      </span>
                      {goal.progress_pct < 100 && (
                        <button
                          onClick={() => incrementGoalProgress(goal.id, goal.progress_pct)}
                          style={{
                            background: 'rgba(168, 85, 247, 0.1)',
                            border: '1px solid rgba(168, 85, 247, 0.3)',
                            color: 'var(--accent-purple)',
                            borderRadius: '4px',
                            padding: '2px 6px',
                            fontSize: '0.7rem',
                            cursor: 'pointer',
                            fontWeight: 600
                          }}
                          title="Add 10% progress"
                        >
                          +10%
                        </button>
                      )}
                    </div>
                  </div>
                  {/* Progress Bar */}
                  <div style={{
                    width: '100%',
                    height: '6px',
                    borderRadius: '3px',
                    background: 'rgba(255, 255, 255, 0.06)',
                    overflow: 'hidden'
                  }}>
                    <div style={{
                      width: `${goal.progress_pct}%`,
                      height: '100%',
                      borderRadius: '3px',
                      background: 'linear-gradient(90deg, #6366f1, #a855f7)',
                      transition: 'width 0.4s ease'
                    }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* =========================================================================
          Notification & Anti-Spam Preferences Modal
         ========================================================================= */}
      {showPreferencesModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(4px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-card)',
            borderRadius: 'var(--radius-lg)',
            width: '100%',
            maxWidth: '520px',
            padding: '24px',
            boxShadow: 'var(--shadow-xl)',
            display: 'flex',
            flexDirection: 'column',
            gap: '18px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sliders size={18} style={{ color: 'var(--primary)' }} />
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                  Proactive Intelligence Preferences
                </h3>
              </div>
              <button
                onClick={() => setShowPreferencesModal(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <CloseIcon size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Control recommendation frequency and anti-spam limits. NEXUS respects your focus and never spams.
            </p>

            {/* Toggle Enable/Disable Proactive Suggestions */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 14px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)'
            }}>
              <div>
                <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>Enable Proactive Suggestions</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Allow NEXUS to identify deadlines, preparation gaps, and conflicts
                </div>
              </div>
              <input
                type="checkbox"
                checked={preferences?.enabled ?? true}
                onChange={(e) => setPreferences((prev) => prev ? { ...prev, enabled: e.target.checked } : null)}
                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
              />
            </div>

            {/* Frequency Control */}
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Recommendation Frequency
              </label>
              <select
                className="input"
                style={{ width: '100%', fontSize: '0.85rem' }}
                value={preferences?.frequency || 'daily'}
                onChange={(e) => setPreferences((prev) => prev ? { ...prev, frequency: e.target.value } : null)}
              >
                <option value="immediate">Immediate (Real-time detection as events occur)</option>
                <option value="hourly">Hourly Digest (Up to once per hour)</option>
                <option value="daily">Daily Digest (Once per day, recommended)</option>
              </select>
            </div>

            {/* Max Daily Recommendations Limit */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Max Daily Recommendations Limit
                </label>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--primary)' }}>
                  {preferences?.max_daily_recommendations || 5} per day
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                value={preferences?.max_daily_recommendations || 5}
                onChange={(e) => setPreferences((prev) => prev ? { ...prev, max_daily_recommendations: parseInt(e.target.value) } : null)}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                <span>1 (Minimal)</span>
                <span>5 (Balanced)</span>
                <span>15 (Comprehensive)</span>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowPreferencesModal(false)}
              >
                Cancel
              </button>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => {
                  if (preferences) {
                    handleSavePreferences(preferences);
                  }
                }}
              >
                Save Preferences
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

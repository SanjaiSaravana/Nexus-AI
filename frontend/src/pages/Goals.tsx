import React, { useEffect, useState } from 'react';
import { 
  Target, 
  Plus, 
  Calendar, 
  Edit2, 
  Trash2, 
  AlertCircle, 
  Loader2,
  CheckCircle,
  Award
} from 'lucide-react';
import { api } from '../services/api';
import type { Goal, GoalCreate, GoalUpdate } from '../types';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

export const Goals: React.FC = () => {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);

  // Form states
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('personal');
  const [status, setStatus] = useState('active');
  const [progressPct, setProgressPct] = useState(0);
  const [targetDate, setTargetDate] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchGoals = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.goals.list({
        category: categoryFilter === 'all' ? undefined : categoryFilter,
        status_filter: statusFilter === 'all' ? undefined : statusFilter,
      });
      setGoals(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load goals');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGoals();
  }, [categoryFilter, statusFilter]);

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setCategory('personal');
    setStatus('active');
    setProgressPct(0);
    setTargetDate('');
    setSelectedGoal(null);
  };

  const handleOpenCreate = () => {
    resetForm();
    setIsCreateOpen(true);
  };

  const handleOpenEdit = (goal: Goal) => {
    setSelectedGoal(goal);
    setTitle(goal.title);
    setDescription(goal.description || '');
    setCategory(goal.category);
    setStatus(goal.status);
    setProgressPct(goal.progress_pct);
    setTargetDate(goal.target_date || '');
    setIsEditOpen(true);
  };

  const adjustProgress = async (goal: Goal, delta: number) => {
    try {
      const nextVal = Math.max(0, Math.min(100, goal.progress_pct + delta));
      const nextStatus = nextVal === 100 ? 'completed' : goal.status === 'completed' ? 'active' : goal.status;
      await api.goals.update(goal.id, {
        progress_pct: nextVal,
        status: nextStatus,
      });
      fetchGoals();
    } catch (err: any) {
      alert(`Error updating progress: ${err.message}`);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    try {
      setSubmitting(true);
      const payload: GoalCreate = {
        title: title.trim(),
        description: description.trim() || undefined,
        category,
        status,
        progress_pct: Number(progressPct),
        target_date: targetDate || undefined,
      };
      await api.goals.create(payload);
      setIsCreateOpen(false);
      resetForm();
      fetchGoals();
    } catch (err: any) {
      alert(`Error creating goal: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedGoal || !title.trim()) return;

    try {
      setSubmitting(true);
      const payload: GoalUpdate = {
        title: title.trim(),
        description: description.trim() || undefined,
        category,
        status,
        progress_pct: Number(progressPct),
        target_date: targetDate || undefined,
      };
      await api.goals.update(selectedGoal.id, payload);
      setIsEditOpen(false);
      resetForm();
      fetchGoals();
    } catch (err: any) {
      alert(`Error updating goal: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string, goalTitle: string) => {
    if (!confirm(`Are you sure you want to delete goal "${goalTitle}"?`)) return;

    try {
      await api.goals.delete(id);
      fetchGoals();
    } catch (err: any) {
      alert(`Error deleting goal: ${err.message}`);
    }
  };

  const categories = ['all', 'career', 'learning', 'personal', 'fitness', 'financial'];

  return (
    <div>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
            Strategic Goals
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Define key performance milestones and accelerate execution
          </p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenCreate}>
          <Plus size={16} />
          <span>New Goal</span>
        </button>
      </div>

      {/* Categories & Status Filters */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`btn btn-sm ${categoryFilter === cat ? 'btn-primary' : 'btn-secondary'}`}
              style={{ borderRadius: '9999px', textTransform: 'capitalize' }}
            >
              {cat}
            </button>
          ))}
        </div>

        <select
          className="form-select"
          style={{ width: 'auto', minWidth: '130px', padding: '6px 12px', fontSize: '0.825rem' }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="all">All Statuses</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="on_hold">On Hold</option>
          <option value="cancelled">Cancelled</option>
        </select>
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

      {loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
          <LoadingSkeleton count={3} height="180px" />
        </div>
      ) : goals.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Target}
            title="No Goals Found"
            description="You don't have any strategic goals registered. Create one to visualize your milestone progress!"
            actionText="Create Goal"
            onAction={handleOpenCreate}
          />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
          {goals.map((goal) => {
            const isFinished = goal.progress_pct === 100 || goal.status === 'completed';

            return (
              <div key={goal.id} className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '10px', marginBottom: '8px' }}>
                    <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {goal.title}
                    </h3>
                    <span className={`badge badge-${goal.status}`}>
                      {goal.status}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <span style={{
                      fontSize: '0.725rem',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: 'rgba(168, 85, 247, 0.12)',
                      color: 'var(--accent-purple)',
                      border: '1px solid rgba(168, 85, 247, 0.25)',
                      textTransform: 'capitalize'
                    }}>
                      {goal.category}
                    </span>

                    {goal.target_date && (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        <Calendar size={12} />
                        <span>Target: {goal.target_date}</span>
                      </span>
                    )}
                  </div>

                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '16px', minHeight: '38px' }}>
                    {goal.description || 'No description provided.'}
                  </p>
                </div>

                <div>
                  {/* Progress bar and counter */}
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)', fontWeight: 500 }}>Progress</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.875rem', fontWeight: 800, color: isFinished ? 'var(--accent-emerald)' : 'var(--accent-cyan)' }}>
                          {goal.progress_pct}%
                        </span>
                        {isFinished && <Award size={15} style={{ color: 'var(--accent-emerald)' }} />}
                      </div>
                    </div>

                    <div className="progress-container">
                      <div
                        className="progress-bar-fill"
                        style={{
                          width: `${goal.progress_pct}%`,
                          background: isFinished ? 'var(--accent-emerald)' : 'linear-gradient(90deg, #6366f1, #06b6d4)'
                        }}
                      />
                    </div>

                    {/* Quick increment / decrement */}
                    <div style={{ display: 'flex', gap: '6px', marginTop: '8px' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '3px 8px', fontSize: '0.725rem', flex: 1 }}
                        onClick={() => adjustProgress(goal, -10)}
                        disabled={goal.progress_pct <= 0}
                      >
                        -10%
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '3px 8px', fontSize: '0.725rem', flex: 1 }}
                        onClick={() => adjustProgress(goal, 10)}
                        disabled={goal.progress_pct >= 100}
                      >
                        +10%
                      </button>
                    </div>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '8px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleOpenEdit(goal)}
                      title="Edit goal"
                    >
                      <Edit2 size={13} />
                      <span>Edit</span>
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDelete(goal.id, goal.title)}
                      title="Delete goal"
                    >
                      <Trash2 size={13} />
                      <span>Delete</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Goal Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Create Strategic Goal">
        <form onSubmit={handleCreateSubmit}>
          <div className="form-group">
            <label className="form-label">Goal Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Master Agentic Distributed Architectures"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              placeholder="Milestone criteria, target KPIs, notes..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select
                className="form-select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="career">Career</option>
                <option value="learning">Learning</option>
                <option value="personal">Personal</option>
                <option value="fitness">Fitness</option>
                <option value="financial">Financial</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="on_hold">On Hold</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label className="form-label">Current Progress</label>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>{progressPct}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={progressPct}
              onChange={(e) => setProgressPct(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Target Completion Date</label>
            <input
              type="date"
              className="form-input"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />
          </div>

          <div className="modal-footer" style={{ margin: '20px -24px -24px -24px' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
              <span>Create Goal</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Goal Modal */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title="Edit Goal">
        <form onSubmit={handleEditSubmit}>
          <div className="form-group">
            <label className="form-label">Goal Title *</label>
            <input
              type="text"
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select
                className="form-select"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="career">Career</option>
                <option value="learning">Learning</option>
                <option value="personal">Personal</option>
                <option value="fitness">Fitness</option>
                <option value="financial">Financial</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="on_hold">On Hold</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label className="form-label">Current Progress</label>
              <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>{progressPct}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="5"
              value={progressPct}
              onChange={(e) => setProgressPct(Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--primary)', cursor: 'pointer' }}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Target Completion Date</label>
            <input
              type="date"
              className="form-input"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
            />
          </div>

          <div className="modal-footer" style={{ margin: '20px -24px -24px -24px' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsEditOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
              <span>Save Changes</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

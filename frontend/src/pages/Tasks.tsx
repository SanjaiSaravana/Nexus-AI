import React, { useEffect, useState } from 'react';
import { 
  CheckSquare, 
  Plus, 
  Circle, 
  CheckCircle2, 
  Clock, 
  Edit2, 
  Trash2, 
  Filter, 
  FolderKanban, 
  AlertCircle, 
  Loader2,
  CheckCircle
} from 'lucide-react';
import { api } from '../services/api';
import type { Task, TaskCreate, TaskUpdate, Project } from '../types';
import { Modal } from '../components/Modal';
import { EmptyState } from '../components/EmptyState';
import { LoadingSkeleton } from '../components/LoadingSkeleton';

export const Tasks: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [projectFilter, setProjectFilter] = useState<string>('all');

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);

  // Form states
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [projectId, setProjectId] = useState<string>('');
  const [status, setStatus] = useState('todo');
  const [priority, setPriority] = useState('medium');
  const [dueDate, setDueDate] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [tasksData, projectsData] = await Promise.all([
        api.tasks.list({
          status_filter: statusFilter === 'all' ? undefined : statusFilter,
          priority_filter: priorityFilter === 'all' ? undefined : priorityFilter,
          project_id: projectFilter === 'all' ? undefined : projectFilter,
        }),
        api.projects.list(),
      ]);

      setTasks(tasksData);
      setProjects(projectsData);
    } catch (err: any) {
      setError(err.message || 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter, priorityFilter, projectFilter]);

  const resetForm = () => {
    setTitle('');
    setDescription('');
    setProjectId('');
    setStatus('todo');
    setPriority('medium');
    setDueDate('');
    setSelectedTask(null);
  };

  const handleOpenCreate = () => {
    resetForm();
    setIsCreateOpen(true);
  };

  const handleOpenEdit = (task: Task) => {
    setSelectedTask(task);
    setTitle(task.title);
    setDescription(task.description || '');
    setProjectId(task.project_id || '');
    setStatus(task.status);
    setPriority(task.priority);
    setDueDate(task.due_date || '');
    setIsEditOpen(true);
  };

  const handleToggleCompletion = async (task: Task) => {
    try {
      const nextStatus = task.status === 'completed' ? 'todo' : 'completed';
      await api.tasks.update(task.id, { status: nextStatus });
      fetchData();
    } catch (err: any) {
      alert(`Error updating task: ${err.message}`);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    try {
      setSubmitting(true);
      const payload: TaskCreate = {
        title: title.trim(),
        description: description.trim() || undefined,
        project_id: projectId || null,
        status,
        priority,
        due_date: dueDate || null,
      };
      await api.tasks.create(payload);
      setIsCreateOpen(false);
      resetForm();
      fetchData();
    } catch (err: any) {
      alert(`Error creating task: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTask || !title.trim()) return;

    try {
      setSubmitting(true);
      const payload: TaskUpdate = {
        title: title.trim(),
        description: description.trim() || undefined,
        project_id: projectId || null,
        status,
        priority,
        due_date: dueDate || null,
      };
      await api.tasks.update(selectedTask.id, payload);
      setIsEditOpen(false);
      resetForm();
      fetchData();
    } catch (err: any) {
      alert(`Error updating task: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string, taskTitle: string) => {
    if (!confirm(`Are you sure you want to delete task "${taskTitle}"?`)) return;

    try {
      await api.tasks.delete(id);
      fetchData();
    } catch (err: any) {
      alert(`Error deleting task: ${err.message}`);
    }
  };

  const getProjectName = (pId: string | null) => {
    if (!pId) return null;
    const match = projects.find((p) => p.id === pId);
    return match ? match.name : null;
  };

  return (
    <div>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
            Tasks Orchestration
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Track actionable tasks, deadlines, and priorities
          </p>
        </div>
        <button className="btn btn-primary" onClick={handleOpenCreate}>
          <Plus size={16} />
          <span>New Task</span>
        </button>
      </div>

      {/* Filters bar */}
      <div className="card" style={{ padding: '16px', marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            <Filter size={16} />
            <span>Filters:</span>
          </div>

          <select
            className="form-select"
            style={{ width: 'auto', minWidth: '130px', padding: '6px 12px', fontSize: '0.825rem' }}
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="all">All Statuses</option>
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="blocked">Blocked</option>
          </select>

          <select
            className="form-select"
            style={{ width: 'auto', minWidth: '130px', padding: '6px 12px', fontSize: '0.825rem' }}
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option value="all">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <select
            className="form-select"
            style={{ width: 'auto', minWidth: '150px', padding: '6px 12px', fontSize: '0.825rem' }}
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
          >
            <option value="all">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
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

      {loading ? (
        <LoadingSkeleton count={4} height="70px" />
      ) : tasks.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={CheckSquare}
            title="No Tasks Found"
            description="No tasks match your current filter parameters. Create a new task to get started."
            actionText="Create Task"
            onAction={handleOpenCreate}
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {tasks.map((task) => {
            const projName = getProjectName(task.project_id);
            const isCompleted = task.status === 'completed';

            return (
              <div
                key={task.id}
                className="card"
                style={{
                  padding: '16px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '16px',
                  flexWrap: 'wrap',
                  opacity: isCompleted ? 0.75 : 1,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flex: '1', minWidth: '240px' }}>
                  <button
                    onClick={() => handleToggleCompletion(task)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: isCompleted ? 'var(--accent-emerald)' : 'var(--text-muted)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      flexShrink: 0
                    }}
                  >
                    {isCompleted ? <CheckCircle2 size={20} /> : <Circle size={20} />}
                  </button>

                  <div>
                    <div style={{
                      fontSize: '0.975rem',
                      fontWeight: 600,
                      color: isCompleted ? 'var(--text-muted)' : 'var(--text-primary)',
                      textDecoration: isCompleted ? 'line-through' : 'none',
                      marginBottom: '4px'
                    }}>
                      {task.title}
                    </div>

                    {task.description && (
                      <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                        {task.description}
                      </p>
                    )}

                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                      {projName && (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          fontSize: '0.725rem',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: 'rgba(6, 182, 212, 0.1)',
                          color: 'var(--accent-cyan)',
                          border: '1px solid rgba(6, 182, 212, 0.25)'
                        }}>
                          <FolderKanban size={11} />
                          <span>{projName}</span>
                        </span>
                      )}

                      {task.due_date && (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          <Clock size={12} />
                          <span>Due: {task.due_date}</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span className={`badge badge-${task.status}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                  <span className={`badge badge-${task.priority}`}>
                    {task.priority}
                  </span>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '8px' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ padding: '6px' }}
                      onClick={() => handleOpenEdit(task)}
                      title="Edit task"
                    >
                      <Edit2 size={13} />
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      style={{ padding: '6px' }}
                      onClick={() => handleDelete(task.id, task.title)}
                      title="Delete task"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Task Modal */}
      <Modal isOpen={isCreateOpen} onClose={() => setIsCreateOpen(false)} title="Create New Task">
        <form onSubmit={handleCreateSubmit}>
          <div className="form-group">
            <label className="form-label">Task Title *</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Implement authentication middleware"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              placeholder="Details or acceptance criteria..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Associated Project</label>
            <select
              className="form-select"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            >
              <option value="">No Project (Independent)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select
                className="form-select"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="blocked">Blocked</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Due Date</label>
            <input
              type="date"
              className="form-input"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>

          <div className="modal-footer" style={{ margin: '20px -24px -24px -24px' }}>
            <button type="button" className="btn btn-secondary" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
              <span>Create Task</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Task Modal */}
      <Modal isOpen={isEditOpen} onClose={() => setIsEditOpen(false)} title="Edit Task">
        <form onSubmit={handleEditSubmit}>
          <div className="form-group">
            <label className="form-label">Task Title *</label>
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

          <div className="form-group">
            <label className="form-label">Associated Project</label>
            <select
              className="form-select"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            >
              <option value="">No Project (Independent)</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select
                className="form-select"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="blocked">Blocked</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Due Date</label>
            <input
              type="date"
              className="form-input"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
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

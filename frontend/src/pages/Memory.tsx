import React, { useState, useEffect, useCallback } from 'react';
import { 
  Brain, 
  Sparkles, 
  Plus, 
  Search, 
  Trash2, 
  Edit3, 
  Layers, 
  Calendar, 
  Activity, 
  Sliders, 
  AlertCircle, 
  CheckCircle2, 
  Loader2, 
  Tag, 
  TrendingUp,
  X
} from 'lucide-react';
import { api } from '../services/api';
import type { MemoryItem, MemoryType, MemoryStats, MemoryCreate, MemoryUpdate } from '../types';

export const Memory: React.FC = () => {
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Filters
  const [activeType, setActiveType] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [minImportance, setMinImportance] = useState<number>(0.0);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);
  const [modalForm, setModalForm] = useState<{
    content: string;
    memory_type: MemoryType;
    importance: number;
    source: string;
  }>({
    content: '',
    memory_type: 'semantic',
    importance: 0.8,
    source: 'manual'
  });
  const [saving, setSaving] = useState(false);

  // Delete modal state
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchMemories = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: any = {};
      if (activeType !== 'all') params.memory_type = activeType;
      if (searchQuery.trim()) params.search = searchQuery.trim();
      if (minImportance > 0) params.min_importance = minImportance;

      const [data, statsData] = await Promise.all([
        api.memories.list(params),
        api.memories.getStats()
      ]);

      setMemories(data);
      setStats(statsData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load memories');
    } finally {
      setLoading(false);
    }
  }, [activeType, searchQuery, minImportance]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchMemories();
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleOpenCreateModal = () => {
    setEditingMemory(null);
    setModalForm({
      content: '',
      memory_type: 'semantic',
      importance: 0.8,
      source: 'manual'
    });
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (mem: MemoryItem) => {
    setEditingMemory(mem);
    setModalForm({
      content: mem.content,
      memory_type: mem.memory_type,
      importance: mem.importance,
      source: mem.source
    });
    setIsModalOpen(true);
  };

  const handleSaveModal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalForm.content.trim()) return;

    try {
      setSaving(true);
      setError(null);

      if (editingMemory) {
        const updateData: MemoryUpdate = {
          content: modalForm.content.trim(),
          memory_type: modalForm.memory_type,
          importance: modalForm.importance
        };
        await api.memories.update(editingMemory.id, updateData);
        setActionSuccess('Memory updated successfully');
      } else {
        const createData: MemoryCreate = {
          content: modalForm.content.trim(),
          memory_type: modalForm.memory_type,
          importance: modalForm.importance,
          source: modalForm.source
        };
        await api.memories.create(createData);
        setActionSuccess('New memory consolidated successfully');
      }

      setIsModalOpen(false);
      await fetchMemories();
      setTimeout(() => setActionSuccess(null), 3000);
    } catch (err: any) {
      setError(err?.message || 'Failed to save memory');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      setDeletingId(id);
      await api.memories.delete(id);
      setMemories(prev => prev.filter(m => m.id !== id));
      setActionSuccess('Memory deleted permanently');
      setTimeout(() => setActionSuccess(null), 3000);
      const newStats = await api.memories.getStats();
      setStats(newStats);
    } catch (err: any) {
      setError(err?.message || 'Failed to delete memory');
    } finally {
      setDeletingId(null);
    }
  };

  const getTypeBadgeStyle = (type: string) => {
    switch (type) {
      case 'semantic':
        return {
          bg: 'rgba(99, 102, 241, 0.15)',
          border: 'rgba(99, 102, 241, 0.3)',
          color: '#818cf8',
          label: 'Semantic Fact'
        };
      case 'episodic':
        return {
          bg: 'rgba(168, 85, 247, 0.15)',
          border: 'rgba(168, 85, 247, 0.3)',
          color: '#c084fc',
          label: 'Episodic Event'
        };
      case 'procedural':
        return {
          bg: 'rgba(16, 185, 129, 0.15)',
          border: 'rgba(16, 185, 129, 0.3)',
          color: '#34d399',
          label: 'Procedural Workflow'
        };
      case 'working':
        return {
          bg: 'rgba(245, 158, 11, 0.15)',
          border: 'rgba(245, 158, 11, 0.3)',
          color: '#fbbf24',
          label: 'Working Context'
        };
      default:
        return {
          bg: 'rgba(148, 163, 184, 0.15)',
          border: 'rgba(148, 163, 184, 0.3)',
          color: '#94a3b8',
          label: type
        };
    }
  };

  return (
    <div className="page-container" style={{ padding: '32px 40px', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '28px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #6366f1, #a855f7)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 8px 16px rgba(99, 102, 241, 0.25)'
            }}>
              <Brain size={22} color="#ffffff" />
            </div>
            <h1 style={{ fontSize: '26px', fontWeight: 700, margin: 0, color: '#f8fafc' }}>
              Personalized AI Memory
            </h1>
          </div>
          <p style={{ margin: 0, color: '#94a3b8', fontSize: '14px', maxWidth: '750px' }}>
            Continuous cognitive intelligence across sessions. Retains semantic facts, episodic milestones, procedural workflows, and active working context.
          </p>
        </div>

        <button 
          onClick={handleOpenCreateModal}
          className="btn-primary"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 18px',
            borderRadius: '10px',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            color: '#fff',
            border: 'none',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
          }}
        >
          <Plus size={18} />
          Add Memory
        </button>
      </div>

      {/* Action Messages */}
      {actionSuccess && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          background: 'rgba(16, 185, 129, 0.15)',
          border: '1px solid rgba(16, 185, 129, 0.3)',
          color: '#34d399',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '20px',
          fontSize: '14px'
        }}>
          <CheckCircle2 size={18} />
          {actionSuccess}
        </div>
      )}

      {error && (
        <div style={{
          padding: '12px 16px',
          borderRadius: '8px',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#f87171',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '20px',
          fontSize: '14px'
        }}>
          <AlertCircle size={18} />
          {error}
        </div>
      )}

      {/* Stats Summary Bar */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        marginBottom: '28px'
      }}>
        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          borderRadius: '14px',
          padding: '18px 20px',
          backdropFilter: 'blur(12px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#94a3b8', fontSize: '13px', marginBottom: '8px' }}>
            <Layers size={16} /> Total Memories
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            {stats ? stats.total : 0}
          </div>
        </div>

        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(99, 102, 241, 0.2)',
          borderRadius: '14px',
          padding: '18px 20px',
          backdropFilter: 'blur(12px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#818cf8', fontSize: '13px', marginBottom: '8px' }}>
            <Sparkles size={16} /> Semantic Facts
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            {stats ? stats.semantic_count : 0}
          </div>
        </div>

        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(168, 85, 247, 0.2)',
          borderRadius: '14px',
          padding: '18px 20px',
          backdropFilter: 'blur(12px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#c084fc', fontSize: '13px', marginBottom: '8px' }}>
            <Calendar size={16} /> Episodic Events
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            {stats ? stats.episodic_count : 0}
          </div>
        </div>

        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(16, 185, 129, 0.2)',
          borderRadius: '14px',
          padding: '18px 20px',
          backdropFilter: 'blur(12px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#34d399', fontSize: '13px', marginBottom: '8px' }}>
            <Sliders size={16} /> Procedural Habits
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            {stats ? stats.procedural_count : 0}
          </div>
        </div>

        <div style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(245, 158, 11, 0.2)',
          borderRadius: '14px',
          padding: '18px 20px',
          backdropFilter: 'blur(12px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#fbbf24', fontSize: '13px', marginBottom: '8px' }}>
            <Activity size={16} /> Working Context
          </div>
          <div style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc' }}>
            {stats ? stats.working_count : 0}
          </div>
        </div>
      </div>

      {/* Controls & Filter Toolbar */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.65)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '14px',
        padding: '16px 20px',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        marginBottom: '24px'
      }}>
        {/* Type Pills */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {[
            { id: 'all', label: 'All Memories' },
            { id: 'semantic', label: 'Semantic (Facts)' },
            { id: 'episodic', label: 'Episodic (Events)' },
            { id: 'procedural', label: 'Procedural (Habits)' },
            { id: 'working', label: 'Working (Context)' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveType(tab.id)}
              style={{
                padding: '7px 14px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s',
                border: activeType === tab.id ? '1px solid #6366f1' : '1px solid rgba(255, 255, 255, 0.08)',
                background: activeType === tab.id ? 'rgba(99, 102, 241, 0.2)' : 'rgba(30, 41, 59, 0.5)',
                color: activeType === tab.id ? '#f8fafc' : '#94a3b8'
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search & Importance Slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
            <input 
              type="text"
              placeholder="Search memories..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                padding: '8px 12px 8px 36px',
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                background: 'rgba(30, 41, 59, 0.8)',
                color: '#f8fafc',
                fontSize: '13px',
                width: '220px'
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: '#94a3b8' }}>Min Importance:</span>
            <select
              value={minImportance}
              onChange={(e) => setMinImportance(parseFloat(e.target.value))}
              style={{
                padding: '7px 10px',
                borderRadius: '8px',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                background: 'rgba(30, 41, 59, 0.8)',
                color: '#f8fafc',
                fontSize: '13px',
                cursor: 'pointer'
              }}
            >
              <option value="0.0">All (0%)</option>
              <option value="0.5">Moderate (&gt; 50%)</option>
              <option value="0.75">High (&gt; 75%)</option>
              <option value="0.9">Critical (&gt; 90%)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Memory Cards Grid */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 0' }}>
          <Loader2 size={36} className="spin" color="#6366f1" />
          <p style={{ marginTop: '16px', color: '#94a3b8', fontSize: '14px' }}>Recalling cognitive intelligence...</p>
        </div>
      ) : memories.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '60px 20px',
          background: 'rgba(30, 41, 59, 0.4)',
          borderRadius: '16px',
          border: '1px dashed rgba(255, 255, 255, 0.12)'
        }}>
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            background: 'rgba(99, 102, 241, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto'
          }}>
            <Brain size={28} color="#818cf8" />
          </div>
          <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
            No memories match your query
          </h3>
          <p style={{ color: '#94a3b8', fontSize: '14px', maxWidth: '480px', margin: '0 auto 20px auto' }}>
            Share facts, preferences, or past milestones during chat, or manually add entries to configure the AI memory engine.
          </p>
          <button
            onClick={handleOpenCreateModal}
            className="btn-primary"
            style={{
              padding: '9px 18px',
              borderRadius: '8px',
              background: '#6366f1',
              color: '#fff',
              border: 'none',
              fontWeight: 500,
              cursor: 'pointer'
            }}
          >
            Consolidate New Memory
          </button>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
          gap: '20px'
        }}>
          {memories.map(mem => {
            const badge = getTypeBadgeStyle(mem.memory_type);
            const impPct = Math.round(mem.importance * 100);

            return (
              <div 
                key={mem.id}
                style={{
                  background: 'rgba(30, 41, 59, 0.55)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '14px',
                  padding: '20px',
                  backdropFilter: 'blur(10px)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  transition: 'transform 0.2s, border-color 0.2s',
                  position: 'relative'
                }}
              >
                <div>
                  {/* Card Header: Type Badge & Importance */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                    <span style={{
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 600,
                      background: badge.bg,
                      border: `1px solid ${badge.border}`,
                      color: badge.color
                    }}>
                      {badge.label}
                    </span>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <TrendingUp size={14} color="#94a3b8" />
                      <span style={{ fontSize: '12px', fontWeight: 600, color: impPct >= 80 ? '#34d399' : '#fbbf24' }}>
                        {impPct}%
                      </span>
                    </div>
                  </div>

                  {/* Memory Content */}
                  <div style={{
                    fontSize: '15px',
                    fontWeight: 500,
                    lineHeight: '1.5',
                    color: '#f8fafc',
                    marginBottom: '14px'
                  }}>
                    {mem.content}
                  </div>

                  {/* Entities Tags */}
                  {mem.mem_metadata?.entities && mem.mem_metadata.entities.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '14px' }}>
                      {mem.mem_metadata.entities.map((ent, idx) => (
                        <span 
                          key={idx}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            fontSize: '11px',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: 'rgba(255, 255, 255, 0.05)',
                            color: '#cbd5e1'
                          }}
                        >
                          <Tag size={10} /> {ent}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Footer: Metadata & Actions */}
                <div style={{
                  paddingTop: '12px',
                  borderTop: '1px solid rgba(255, 255, 255, 0.06)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    Source: <span style={{ color: '#94a3b8' }}>{mem.source}</span> • Accessed: {mem.access_count}x
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button
                      onClick={() => handleOpenEditModal(mem)}
                      title="Edit Memory"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#94a3b8',
                        cursor: 'pointer',
                        padding: '4px',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#818cf8')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
                    >
                      <Edit3 size={15} />
                    </button>

                    <button
                      onClick={() => handleDelete(mem.id)}
                      disabled={deletingId === mem.id}
                      title="Delete Memory"
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: '#94a3b8',
                        cursor: 'pointer',
                        padding: '4px',
                        borderRadius: '4px',
                        display: 'flex',
                        alignItems: 'center'
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = '#f87171')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
                    >
                      {deletingId === mem.id ? (
                        <Loader2 size={15} className="spin" color="#f87171" />
                      ) : (
                        <Trash2 size={15} />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add / Edit Memory Modal */}
      {isModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(6px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            background: '#1e293b',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            borderRadius: '16px',
            width: '100%',
            maxWidth: '540px',
            padding: '28px',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Brain size={20} color="#818cf8" />
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600, color: '#f8fafc' }}>
                  {editingMemory ? 'Edit Memory' : 'Add Personalized Memory'}
                </h3>
              </div>
              <button 
                onClick={() => setIsModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveModal}>
              {/* Type Select */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#cbd5e1', marginBottom: '6px' }}>
                  Memory Type
                </label>
                <select
                  value={modalForm.memory_type}
                  onChange={(e) => setModalForm(prev => ({ ...prev, memory_type: e.target.value as MemoryType }))}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: '#0f172a',
                    color: '#f8fafc',
                    fontSize: '14px'
                  }}
                >
                  <option value="semantic">Semantic Memory — Facts & Technical Skills</option>
                  <option value="episodic">Episodic Memory — Past Events & Milestones</option>
                  <option value="procedural">Procedural Memory — Preferences & Working Patterns</option>
                  <option value="working">Working Memory — Current Active Task Context</option>
                </select>
              </div>

              {/* Content Textarea */}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 500, color: '#cbd5e1', marginBottom: '6px' }}>
                  Memory Content (Third-Person Fact)
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder={
                    modalForm.memory_type === 'semantic' ? 'e.g., User knows Python, Kubernetes, and PostgreSQL.' :
                    modalForm.memory_type === 'episodic' ? 'e.g., User previously completed the cloud database migration in 2026.' :
                    modalForm.memory_type === 'procedural' ? 'e.g., User prefers concise code with type hints and dark mode.' :
                    'e.g., User is currently debugging Phase 3 AI memory consolidation.'
                  }
                  value={modalForm.content}
                  onChange={(e) => setModalForm(prev => ({ ...prev, content: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    background: '#0f172a',
                    color: '#f8fafc',
                    fontSize: '14px',
                    resize: 'vertical'
                  }}
                />
              </div>

              {/* Importance Slider */}
              <div style={{ marginBottom: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <label style={{ fontSize: '13px', fontWeight: 500, color: '#cbd5e1' }}>
                    Importance Score
                  </label>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#818cf8' }}>
                    {Math.round(modalForm.importance * 100)}%
                  </span>
                </div>
                <input 
                  type="range"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  value={modalForm.importance}
                  onChange={(e) => setModalForm(prev => ({ ...prev, importance: parseFloat(e.target.value) }))}
                  style={{ width: '100%', accentColor: '#6366f1' }}
                />
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{
                    padding: '9px 16px',
                    borderRadius: '8px',
                    background: 'rgba(255, 255, 255, 0.08)',
                    color: '#cbd5e1',
                    border: 'none',
                    fontWeight: 500,
                    cursor: 'pointer'
                  }}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={saving || !modalForm.content.trim()}
                  style={{
                    padding: '9px 20px',
                    borderRadius: '8px',
                    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                    color: '#fff',
                    border: 'none',
                    fontWeight: 600,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    opacity: saving ? 0.7 : 1
                  }}
                >
                  {saving && <Loader2 size={16} className="spin" />}
                  {editingMemory ? 'Save Changes' : 'Consolidate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

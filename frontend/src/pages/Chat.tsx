import React, { useState, useEffect, useRef } from 'react';
import { 
  Bot, 
  Send, 
  UploadCloud, 
  FileText, 
  Trash2, 
  Sparkles, 
  Plus, 
  AlertCircle, 
  Loader2, 
  ChevronRight,
  Database,
  MessageSquare,
  BookOpen,
  Cpu,
  CheckCircle2,
  ShieldAlert,
  Check,
  X as CloseIcon
} from 'lucide-react';
import { api } from '../services/api';
import type { DocumentItem, ChatMessage, Conversation, Citation, AgentActivityItem, ActionProposal } from '../types';

export const Chat: React.FC = () => {
  // Document state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Conversation state
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  // Input & Streaming state
  const [inputText, setInputText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingCitations, setStreamingCitations] = useState<Citation[]>([]);
  const [currentActivity, setCurrentActivity] = useState<AgentActivityItem | null>(null);
  const [activityHistory, setActivityHistory] = useState<AgentActivityItem[]>([]);
  const [pendingProposals, setPendingProposals] = useState<ActionProposal[]>([]);

  // Active citation preview
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const loadPendingProposals = async () => {
    try {
      const p = await api.actions.listProposals('pending');
      setPendingProposals(p);
    } catch {
      // silent
    }
  };

  const loadConversation = async (convId: string) => {
    try {
      setActiveConvId(convId);
      const conv = await api.chat.getConversation(convId);
      setMessages(conv.messages || []);
    } catch (err: any) {
      console.error('Failed to load conversation messages:', err);
    }
  };

  // Load initial documents and conversations
  const loadData = async () => {
    try {
      const [docs, convs] = await Promise.all([
        api.documents.list(),
        api.chat.listConversations(),
      ]);
      setDocuments(docs);
      setConversations(convs);
      await loadPendingProposals();

      // Auto load first conversation if exists and none active
      if (convs.length > 0 && !activeConvId) {
        loadConversation(convs[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load knowledge vault:', err);
    }
  };

  const handleApproveProposal = async (id: string) => {
    try {
      await api.actions.approveProposal(id);
      await loadPendingProposals();
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    }
  };

  const handleRejectProposal = async (id: string) => {
    try {
      await api.actions.rejectProposal(id, 'User rejected from chat');
      await loadPendingProposals();
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    setUploading(true);
    try {
      await api.documents.upload(file);
      const docs = await api.documents.list();
      setDocuments(docs);
    } catch (err: any) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDocument = async (id: string, name: string) => {
    if (!confirm(`Delete document "${name}" and its chunks?`)) return;
    try {
      await api.documents.delete(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      setSelectedDocIds((prev) => prev.filter((dId) => dId !== id));
    } catch (err: any) {
      alert(`Delete error: ${err.message}`);
    }
  };

  const handleStartNewConversation = () => {
    setActiveConvId(null);
    setMessages([]);
    setStreamingContent('');
    setStreamingCitations([]);
  };

  const handleDeleteConversation = async (convId: string) => {
    if (!confirm('Delete this conversation history?')) return;
    try {
      await api.chat.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) {
        handleStartNewConversation();
      }
    } catch (err: any) {
      alert(`Error deleting conversation: ${err.message}`);
    }
  };

  const handleSendMessage = async (msgToSend?: string) => {
    const text = (msgToSend || inputText).trim();
    if (!text || isStreaming) return;

    setInputText('');
    setUploadError(null);

    // Optimistically append user message
    const tempUserMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      conversation_id: activeConvId || '',
      role: 'user',
      content: text,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    setIsStreaming(true);
    setStreamingContent('');
    setStreamingCitations([]);
    setCurrentActivity(null);
    setActivityHistory([]);

    try {
      // Use SSE streaming with Multi-Agent activity tracking
      await api.chat.streamQuery(
        {
          message: text,
          conversation_id: activeConvId || undefined,
          document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
          top_k: 5,
        },
        (token) => {
          setStreamingContent((prev) => prev + token);
        },
        (citations) => {
          setStreamingCitations(citations);
        },
        async () => {
          // Stream completed
          setIsStreaming(false);
          setCurrentActivity(null);
          // Refresh conversation list and current messages
          const convs = await api.chat.listConversations();
          setConversations(convs);
          await loadPendingProposals();
          if (convs.length > 0) {
            const current = activeConvId || convs[0].id;
            setActiveConvId(current);
            const loaded = await api.chat.getConversation(current);
            setMessages(loaded.messages || []);
          }
          setStreamingContent('');
          setStreamingCitations([]);
        },
        (err) => {
          setIsStreaming(false);
          setCurrentActivity(null);
          alert(`Query error: ${err.message || 'Request failed'}`);
        },
        (activity) => {
          setCurrentActivity(activity);
          setActivityHistory((prev) => {
            const exists = prev.some((a) => a.agent === activity.agent && a.message === activity.message);
            return exists ? prev : [...prev, activity];
          });
        }
      );
    } catch (err: any) {
      setIsStreaming(false);
      setCurrentActivity(null);
      alert(`Query error: ${err.message}`);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const promptStarters = [
    "I have an interview tomorrow. Help me prepare.",
    "Analyze my projects and build an execution plan",
    "What are my strongest technical skills and experiences?",
    "Summarize my uploaded resume and system architecture knowledge"
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: '24px', minHeight: 'calc(100vh - 120px)' }}>
      {/* LEFT PANEL: Knowledge Vault & Document Manager */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Knowledge Vault Uploader */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ color: 'var(--primary)' }}>
                <Database size={18} />
              </div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Knowledge Vault</h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {documents.length} docs
            </span>
          </div>

          <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', marginBottom: '14px' }}>
            Upload personal documents for semantic search & RAG retrieval.
          </p>

          {/* Upload Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            style={{
              border: '2px dashed var(--border-card)',
              borderRadius: 'var(--radius-md)',
              padding: '18px 12px',
              textAlign: 'center',
              cursor: 'pointer',
              background: 'rgba(255, 255, 255, 0.01)',
              transition: 'all 0.2s ease',
              marginBottom: '16px'
            }}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                handleFileUpload(e.dataTransfer.files[0]);
              }
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept=".pdf,.docx,.txt,.md,.csv"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
            />
            {uploading ? (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                <Loader2 size={24} className="animate-spin" style={{ color: 'var(--primary)', animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>Parsing & Embedding...</span>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px' }}>
                <UploadCloud size={24} style={{ color: 'var(--text-muted)' }} />
                <span style={{ fontSize: '0.825rem', fontWeight: 600 }}>Click or Drag to Upload</span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>PDF, DOCX, TXT, MD, CSV</span>
              </div>
            )}
          </div>

          {uploadError && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 10px',
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(244, 63, 94, 0.1)',
              color: 'var(--accent-rose)',
              fontSize: '0.75rem',
              marginBottom: '12px'
            }}>
              <AlertCircle size={14} style={{ flexShrink: 0 }} />
              <span>{uploadError}</span>
            </div>
          )}

          {/* Connected Documents List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '220px', overflowY: 'auto' }}>
            {documents.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '16px 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                No documents connected yet.
              </div>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-sm)',
                    background: 'rgba(255, 255, 255, 0.02)',
                    border: '1px solid var(--border-subtle)',
                    fontSize: '0.8rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
                    <FileText size={15} style={{ color: 'var(--accent-cyan)', flexShrink: 0 }} />
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {doc.filename}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {doc.chunk_count} chunks • {formatFileSize(doc.file_size)}
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDeleteDocument(doc.id, doc.filename)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '4px' }}
                    title="Remove document"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Conversation History */}
        <div className="card" style={{ padding: '20px', flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ color: 'var(--accent-purple)' }}>
                <MessageSquare size={18} />
              </div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>Chat History</h3>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              style={{ padding: '4px 8px', fontSize: '0.75rem' }}
              onClick={handleStartNewConversation}
            >
              <Plus size={12} />
              <span>New</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '240px', overflowY: 'auto' }}>
            {conversations.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '16px 0', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                No past conversations.
              </div>
            ) : (
              conversations.map((c) => (
                <div
                  key={c.id}
                  onClick={() => loadConversation(c.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-sm)',
                    background: activeConvId === c.id ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                    border: activeConvId === c.id ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: activeConvId === c.id ? 600 : 400 }}>
                    {c.title}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteConversation(c.id);
                    }}
                    style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: '2px' }}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL: AI Chat Experience */}
      <div className="card" style={{ display: 'flex', flexDirection: 'column', padding: '0', overflow: 'hidden' }}>
        {/* Chat Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(0, 0, 0, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white'
            }}>
              <Bot size={20} />
            </div>
            <div>
              <div style={{ fontSize: '0.95rem', fontWeight: 700 }}>NEXUS Document Intelligence</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '5px' }}>
                <span className="status-dot" style={{ width: '6px', height: '6px' }} />
                <span>RAG Hybrid Search Active • Strict Tenant Isolation</span>
              </div>
            </div>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={handleStartNewConversation}
            style={{ fontSize: '0.75rem' }}
          >
            <Plus size={14} />
            <span>New Chat</span>
          </button>
        </div>

        {/* Chat Message Stream */}
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {messages.length === 0 && !isStreaming ? (
            <div style={{
              margin: 'auto',
              maxWidth: '540px',
              textAlign: 'center',
              padding: '32px 16px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center'
            }}>
              <div className="empty-icon-ring" style={{ width: '60px', height: '60px', marginBottom: '16px' }}>
                <Sparkles size={28} />
              </div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '8px' }}>
                Ask NEXUS about your documents
              </h2>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.6 }}>
                Upload your resume, technical specifications, notes, or data sheets. NEXUS will retrieve exact passages and answer with structured citations.
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', width: '100%' }}>
                {promptStarters.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendMessage(prompt)}
                    style={{
                      textAlign: 'left',
                      padding: '12px 14px',
                      borderRadius: 'var(--radius-md)',
                      background: 'rgba(255, 255, 255, 0.03)',
                      border: '1px solid var(--border-subtle)',
                      color: 'var(--text-primary)',
                      fontSize: '0.8rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--primary)';
                      e.currentTarget.style.background = 'rgba(99, 102, 241, 0.08)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--border-subtle)';
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                    }}
                  >
                    <span>{prompt}</span>
                    <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    maxWidth: '100%'
                  }}
                >
                  <div
                    style={{
                      maxWidth: '82%',
                      padding: '14px 18px',
                      borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                      background: msg.role === 'user' 
                        ? 'linear-gradient(135deg, #4f46e5, #6366f1)' 
                        : 'rgba(18, 24, 38, 0.95)',
                      border: msg.role === 'user' ? 'none' : '1px solid var(--border-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.9rem',
                      lineHeight: 1.6,
                      boxShadow: 'var(--shadow-sm)',
                      whiteSpace: 'pre-wrap'
                    }}
                  >
                    {msg.content}
                  </div>

                  {/* Assistant Citations */}
                  {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                    <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {msg.citations.map((c) => (
                        <button
                          key={c.citation_id}
                          onClick={() => setActiveCitation(c)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: 'rgba(99, 102, 241, 0.1)',
                            border: '1px solid rgba(99, 102, 241, 0.25)',
                            color: 'var(--primary)',
                            fontSize: '0.725rem',
                            fontWeight: 600,
                            cursor: 'pointer'
                          }}
                        >
                          <BookOpen size={12} />
                          <span>{c.document_name} (Page {c.page_number || 1})</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              {/* Real-time Streaming Assistant Bubble with Multi-Agent UI */}
              {isStreaming && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', maxWidth: '82%', gap: '10px' }}>
                  {/* High-level Agent Activity Status (Safe, No CoT) */}
                  {(currentActivity || activityHistory.length > 0) && (
                    <div
                      style={{
                        padding: '10px 16px',
                        borderRadius: '12px',
                        background: 'rgba(99, 102, 241, 0.08)',
                        border: '1px solid rgba(99, 102, 241, 0.25)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '8px',
                        width: '100%'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <Cpu size={15} style={{ color: 'var(--primary)' }} />
                          <span style={{ fontSize: '0.775rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                            Nexus Multi-Agent Orchestrator
                          </span>
                        </div>
                        {currentActivity && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 8px #10b981' }} />
                            <span style={{ fontSize: '0.725rem', color: '#10b981', fontWeight: 600 }}>Active</span>
                          </div>
                        )}
                      </div>

                      {/* Current Activity Message */}
                      {currentActivity ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-primary)', fontSize: '0.85rem', fontWeight: 500 }}>
                          <Loader2 size={14} className="animate-spin" style={{ animation: 'spin 1s linear infinite', color: 'var(--primary)' }} />
                          <span>{currentActivity.message}</span>
                        </div>
                      ) : (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                          <CheckCircle2 size={14} style={{ color: '#10b981' }} />
                          <span>Agents completed execution</span>
                        </div>
                      )}

                      {/* High-level completed steps summary pills */}
                      {activityHistory.length > 1 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                          {activityHistory.map((act, idx) => (
                            <span
                              key={idx}
                              style={{
                                fontSize: '0.7rem',
                                padding: '2px 8px',
                                borderRadius: '6px',
                                background: act.message === currentActivity?.message ? 'rgba(99, 102, 241, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                                color: act.message === currentActivity?.message ? 'var(--primary)' : 'var(--text-muted)',
                                border: '1px solid rgba(255, 255, 255, 0.08)'
                              }}
                            >
                              {act.message}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div
                    style={{
                      width: '100%',
                      padding: '14px 18px',
                      borderRadius: '18px 18px 18px 4px',
                      background: 'rgba(18, 24, 38, 0.95)',
                      border: '1px solid var(--border-card)',
                      color: 'var(--text-primary)',
                      fontSize: '0.9rem',
                      lineHeight: 1.6,
                      boxShadow: 'var(--shadow-sm)',
                      whiteSpace: 'pre-wrap'
                    }}
                  >
                    {streamingContent || (
                      <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)' }}>
                        <Loader2 size={16} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
                        <span>{currentActivity ? currentActivity.message : "Synthesizing multi-agent intelligence..."}</span>
                      </span>
                    )}
                  </div>

                  {streamingCitations.length > 0 && (
                    <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {streamingCitations.map((c) => (
                        <span
                          key={c.citation_id}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '4px 10px',
                            borderRadius: '6px',
                            background: 'rgba(99, 102, 241, 0.1)',
                            border: '1px solid rgba(99, 102, 241, 0.25)',
                            color: 'var(--primary)',
                            fontSize: '0.725rem',
                            fontWeight: 600
                          }}
                        >
                          <BookOpen size={12} />
                          <span>{c.document_name}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Citation Detail Inspector Drawer */}
        {activeCitation && (
          <div style={{
            padding: '14px 20px',
            background: 'rgba(99, 102, 241, 0.08)',
            borderTop: '1px solid rgba(99, 102, 241, 0.2)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: '16px',
            fontSize: '0.8rem'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <span style={{ fontWeight: 700, color: 'var(--primary)' }}>
                  Citation Source: {activeCitation.document_name}
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  Page {activeCitation.page_number || 1} • {activeCitation.section || 'General'}
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                  Score: {(activeCitation.relevance_score * 100).toFixed(0)}%
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                "{activeCitation.excerpt}"
              </p>
            </div>
            <button
              onClick={() => setActiveCitation(null)}
              className="btn btn-secondary btn-sm"
              style={{ padding: '2px 8px', fontSize: '0.7rem' }}
            >
              Close
            </button>
          </div>
        )}

        {/* Action Confirmation Banner */}
        {pendingProposals.length > 0 && (
          <div style={{
            padding: '14px 20px',
            background: 'rgba(245, 158, 11, 0.08)',
            borderTop: '1px solid rgba(245, 158, 11, 0.3)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b', fontSize: '0.85rem', fontWeight: 600 }}>
                <ShieldAlert size={16} />
                <span>Pending Action Approvals ({pendingProposals.length})</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Never perform sensitive external actions without confirmation
              </span>
            </div>

            {pendingProposals.map((proposal) => {
              const p = proposal.parameters || {};
              const timeStr = p.start_time && p.end_time 
                ? `${new Date(p.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} – ${new Date(p.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` 
                : '';
              const dateStr = p.start_time 
                ? new Date(p.start_time).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }) 
                : '';

              return (
                <div
                  key={proposal.id}
                  style={{
                    background: 'rgba(18, 24, 38, 0.95)',
                    border: '1px solid rgba(245, 158, 11, 0.35)',
                    borderRadius: '12px',
                    padding: '14px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '16px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
                  }}
                >
                  <div>
                    <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#f59e0b', fontWeight: 700, marginBottom: '2px' }}>
                      NEXUS wants to {proposal.action_type.replace('_', ' ')}:
                    </div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                      {proposal.title}
                    </div>
                    {dateStr && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        <span>📅 {dateStr}</span>
                        {timeStr && <span>⏰ {timeStr}</span>}
                      </div>
                    )}
                    {proposal.description && (
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {proposal.description}
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
                    <button
                      onClick={() => handleApproveProposal(proposal.id)}
                      className="btn btn-primary btn-sm"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                        border: 'none',
                        padding: '6px 14px',
                        fontWeight: 600,
                        fontSize: '0.8rem'
                      }}
                    >
                      <Check size={14} />
                      Approve
                    </button>
                    <button
                      onClick={() => handleRejectProposal(proposal.id)}
                      className="btn btn-secondary btn-sm"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '6px',
                        borderColor: 'rgba(239, 68, 68, 0.4)',
                        color: '#ef4444',
                        padding: '6px 14px',
                        fontSize: '0.8rem'
                      }}
                    >
                      <CloseIcon size={14} />
                      Reject
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Input Bar */}
        <div style={{
          padding: '16px 20px',
          borderTop: '1px solid var(--border-subtle)',
          background: 'rgba(13, 17, 26, 0.95)'
        }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSendMessage();
            }}
            style={{ display: 'flex', gap: '12px', alignItems: 'center' }}
          >
            <input
              type="text"
              className="form-input"
              style={{
                flex: 1,
                padding: '12px 18px',
                borderRadius: 'var(--radius-lg)',
                fontSize: '0.9rem'
              }}
              placeholder={documents.length === 0 ? "Upload a document to ask questions..." : "Ask NEXUS about your documents..."}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={isStreaming}
            />

            <button
              type="submit"
              className="btn btn-primary"
              style={{
                width: '46px',
                height: '46px',
                borderRadius: 'var(--radius-lg)',
                padding: 0
              }}
              disabled={!inputText.trim() || isStreaming}
            >
              {isStreaming ? (
                <Loader2 size={18} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
              ) : (
                <Send size={18} />
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Check, 
  X, 
  FileText, 
  Calendar, 
  Mail, 
  GitBranch, 
  Search, 
  Database, 
  Cpu, 
  Layers, 
  Sparkles,
  AlertTriangle,
  RefreshCw,
  Terminal,
  Lock
} from 'lucide-react';
import { api } from '../services/api';
import type { ToolDefinition, ActionProposal, AuditLogItem } from '../types';

export const Actions: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'proposals' | 'tools' | 'audit'>('proposals');
  const [tools, setTools] = useState<ToolDefinition[]>([]);
  const [proposals, setProposals] = useState<ActionProposal[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [tList, pList, aList] = await Promise.all([
        api.actions.listTools(),
        api.actions.listProposals(),
        api.actions.listAuditLogs(100),
      ]);
      setTools(tList);
      setProposals(pList);
      setAuditLogs(aList);
    } catch (err: any) {
      console.error('Failed to load actions data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (id: string, title: string) => {
    try {
      await api.actions.approveProposal(id);
      setActionMessage(`Approved and executed: "${title}"`);
      await loadData();
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(`Approval error: ${err.message}`);
    }
  };

  const handleReject = async (id: string, title: string) => {
    const reason = prompt(`Enter rejection reason for "${title}":`, 'User rejected action');
    if (reason === null) return;
    try {
      await api.actions.rejectProposal(id, reason);
      setActionMessage(`Rejected: "${title}"`);
      await loadData();
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(`Rejection error: ${err.message}`);
    }
  };

  const handleCreateMockInterviewProposal = async () => {
    try {
      const now = new Date();
      const tomorrow = new Date(now);
      tomorrow.setDate(tomorrow.getDate() + 1);
      tomorrow.setHours(18, 0, 0, 0);
      const tomorrowEnd = new Date(tomorrow);
      tomorrowEnd.setHours(19, 0, 0, 0);

      await api.actions.propose({
        tool_name: 'calendar',
        action_type: 'create_event',
        title: 'Interview Preparation',
        description: 'Tomorrow\n6:00 PM – 7:00 PM',
        parameters: {
          title: 'Interview Preparation',
          start_time: tomorrow.toISOString(),
          end_time: tomorrowEnd.toISOString(),
          event_type: 'prep',
          location: 'Virtual / Home Office'
        }
      });
      await loadData();
      setActionMessage('Proposed new action: "Interview Preparation". Confirmation required.');
      setTimeout(() => setActionMessage(null), 4000);
    } catch (err: any) {
      alert(`Proposal error: ${err.message}`);
    }
  };

  const pendingProposals = proposals.filter((p) => p.status === 'pending');

  const getToolIcon = (name: string) => {
    switch (name.toLowerCase()) {
      case 'calendar': return <Calendar size={18} />;
      case 'email': return <Mail size={18} />;
      case 'github': return <GitBranch size={18} />;
      case 'task': return <Check size={18} />;
      case 'documents': return <FileText size={18} />;
      case 'search': return <Search size={18} />;
      case 'knowledge_graph': return <Database size={18} />;
      case 'memory': return <Cpu size={18} />;
      default: return <Layers size={18} />;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1280px', margin: '0 auto' }}>
      {/* Top Banner & Metrics */}
      <div className="card" style={{ padding: '24px', background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.8))' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
              <div style={{ padding: '8px', borderRadius: '10px', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--primary)' }}>
                <ShieldCheck size={24} />
              </div>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Secure Tool Calling & Action Execution</h1>
            </div>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Controlled multi-agent tool execution with mandatory human confirmation for external and sensitive actions.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="btn btn-secondary"
              onClick={handleCreateMockInterviewProposal}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}
            >
              <Sparkles size={16} style={{ color: 'var(--primary)' }} />
              <span>Simulate Proposal</span>
            </button>
            <button
              className="btn btn-secondary"
              onClick={loadData}
              disabled={loading}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem' }}
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {actionMessage && (
          <div style={{ marginTop: '16px', padding: '10px 16px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.12)', border: '1px solid rgba(16, 185, 129, 0.3)', color: '#10b981', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Check size={16} />
            <span>{actionMessage}</span>
          </div>
        )}

        {/* Quick Stats Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginTop: '20px' }}>
          <div style={{ padding: '16px', borderRadius: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Pending Confirmations</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: pendingProposals.length > 0 ? '#f59e0b' : 'var(--text-primary)', marginTop: '4px' }}>
              {pendingProposals.length}
            </div>
          </div>
          <div style={{ padding: '16px', borderRadius: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Registered Tools</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--primary)', marginTop: '4px' }}>
              {tools.length}
            </div>
          </div>
          <div style={{ padding: '16px', borderRadius: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Audit Logs Recorded</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#10b981', marginTop: '4px' }}>
              {auditLogs.length}
            </div>
          </div>
          <div style={{ padding: '16px', borderRadius: '12px', background: 'rgba(255, 255, 255, 0.03)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Security Level</span>
            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#38bdf8', marginTop: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Lock size={16} /> Strict Human-in-the-Loop
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Header */}
      <div style={{ display: 'flex', gap: '10px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
        <button
          onClick={() => setActiveTab('proposals')}
          style={{
            padding: '8px 18px',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '0.875rem',
            background: activeTab === 'proposals' ? 'var(--primary)' : 'transparent',
            color: activeTab === 'proposals' ? '#fff' : 'var(--text-secondary)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <AlertTriangle size={15} />
          <span>Pending Approvals ({pendingProposals.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('tools')}
          style={{
            padding: '8px 18px',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '0.875rem',
            background: activeTab === 'tools' ? 'var(--primary)' : 'transparent',
            color: activeTab === 'tools' ? '#fff' : 'var(--text-secondary)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Layers size={15} />
          <span>Tools Catalog ({tools.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          style={{
            padding: '8px 18px',
            borderRadius: '8px',
            fontWeight: 600,
            fontSize: '0.875rem',
            background: activeTab === 'audit' ? 'var(--primary)' : 'transparent',
            color: activeTab === 'audit' ? '#fff' : 'var(--text-secondary)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Terminal size={15} />
          <span>Audit Log Trail ({auditLogs.length})</span>
        </button>
      </div>

      {/* TAB 1: PENDING PROPOSALS & ACTION CONFIRMATION */}
      {activeTab === 'proposals' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {pendingProposals.length === 0 ? (
            <div className="card" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <ShieldCheck size={48} style={{ color: '#10b981', margin: '0 auto 16px' }} />
              <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                All Actions Approved & Synchronized
              </h3>
              <p style={{ fontSize: '0.875rem', maxWidth: '480px', margin: '0 auto' }}>
                No pending actions require your confirmation. When the assistant proposes sensitive external actions (e.g. creating calendar events or sending emails), they will appear here.
              </p>
            </div>
          ) : (
            pendingProposals.map((prop) => (
              <div
                key={prop.id}
                className="card"
                style={{
                  padding: '24px',
                  border: '1px solid rgba(245, 158, 11, 0.35)',
                  background: 'rgba(245, 158, 11, 0.04)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ padding: '10px', borderRadius: '10px', background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b' }}>
                      {getToolIcon(prop.tool_name)}
                    </div>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#f59e0b', fontWeight: 700 }}>
                          Action Proposal • {prop.tool_name}
                        </span>
                        <span style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(239, 68, 68, 0.15)', color: '#ef4444', fontWeight: 700 }}>
                          {prop.risk_level.toUpperCase()} RISK
                        </span>
                      </div>
                      <h3 style={{ fontSize: '1.15rem', fontWeight: 700, marginTop: '4px' }}>
                        NEXUS wants to create:
                      </h3>
                      <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--primary)', marginTop: '2px' }}>
                        {prop.title}
                      </div>
                    </div>
                  </div>

                  {/* Approve / Reject Buttons */}
                  <div style={{ display: 'flex', gap: '10px' }}>
                    <button
                      className="btn"
                      onClick={() => handleApprove(prop.id, prop.title)}
                      style={{
                        background: '#10b981',
                        color: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 20px',
                        fontWeight: 700
                      }}
                    >
                      <Check size={16} />
                      <span>Approve</span>
                    </button>
                    <button
                      className="btn"
                      onClick={() => handleReject(prop.id, prop.title)}
                      style={{
                        background: 'rgba(239, 68, 68, 0.15)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        color: '#ef4444',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '8px 16px',
                        fontWeight: 600
                      }}
                    >
                      <X size={16} />
                      <span>Reject</span>
                    </button>
                  </div>
                </div>

                {prop.description && (
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', background: 'rgba(0, 0, 0, 0.2)', padding: '12px 16px', borderRadius: '8px', whiteSpace: 'pre-line' }}>
                    {prop.description}
                  </div>
                )}

                {/* Sanitized Parameters Preview */}
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <div style={{ fontWeight: 600, marginBottom: '6px' }}>Action Parameters:</div>
                  <pre style={{ margin: 0, padding: '10px', borderRadius: '6px', background: 'rgba(0,0,0,0.3)', overflowX: 'auto', fontFamily: 'monospace' }}>
                    {JSON.stringify(prop.parameters, null, 2)}
                  </pre>
                </div>
              </div>
            ))
          )}

          {/* Historical Proposals */}
          {proposals.filter((p) => p.status !== 'pending').length > 0 && (
            <div style={{ marginTop: '24px' }}>
              <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-secondary)' }}>
                Recent Proposal History
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {proposals.filter((p) => p.status !== 'pending').slice(0, 5).map((p) => (
                  <div key={p.id} className="card" style={{ padding: '14px 18px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>[{p.tool_name}]</span>{' '}
                      <strong style={{ fontSize: '0.9rem' }}>{p.title}</strong>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '12px' }}>
                        {new Date(p.created_at).toLocaleString()}
                      </span>
                    </div>
                    <span style={{
                      fontSize: '0.75rem',
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontWeight: 700,
                      background: p.status === 'executed' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                      color: p.status === 'executed' ? '#10b981' : '#ef4444'
                    }}>
                      {p.status.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: TOOLS CATALOG */}
      {activeTab === 'tools' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
          {tools.map((t) => (
            <div key={t.name} className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <div style={{ padding: '8px', borderRadius: '8px', background: 'rgba(99, 102, 241, 0.15)', color: 'var(--primary)' }}>
                    {getToolIcon(t.name)}
                  </div>
                  <div>
                    <h4 style={{ fontSize: '1rem', fontWeight: 700, textTransform: 'capitalize' }}>{t.name} Tool</h4>
                    <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{t.category}</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '6px' }}>
                  <span style={{
                    fontSize: '0.7rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    fontWeight: 700,
                    background: t.requires_confirmation ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                    color: t.requires_confirmation ? '#f59e0b' : '#10b981'
                  }}>
                    {t.requires_confirmation ? 'REQUIRES APPROVAL' : 'AUTO-APPROVED'}
                  </span>
                </div>
              </div>

              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {t.description}
              </p>

              <div style={{ marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {t.permissions.map((p) => (
                  <span key={p} style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)' }}>
                    {p}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 3: IMMUTABLE AUDIT LOG TRAIL */}
      {activeTab === 'audit' && (
        <div className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Cryptographically Tracked Action Audit Trail</h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Showing last {auditLogs.length} events • Sensitive secrets automatically redacted
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px' }}>Timestamp</th>
                  <th style={{ padding: '10px' }}>Action & Tool</th>
                  <th style={{ padding: '10px' }}>Parameters (Sanitized)</th>
                  <th style={{ padding: '10px' }}>Approval</th>
                  <th style={{ padding: '10px' }}>Execution Status</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <td style={{ padding: '12px 10px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {new Date(log.created_at).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: '12px 10px' }}>
                      <div style={{ fontWeight: 600 }}>{log.action}</div>
                      <div style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>{log.tool}</div>
                    </td>
                    <td style={{ padding: '12px 10px', maxWidth: '300px' }}>
                      <pre style={{ margin: 0, fontSize: '0.725rem', background: 'rgba(0,0,0,0.25)', padding: '6px', borderRadius: '4px', overflowX: 'auto' }}>
                        {JSON.stringify(log.parameters)}
                      </pre>
                    </td>
                    <td style={{ padding: '12px 10px' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: 700,
                        background: log.approval_status === 'user_approved' ? 'rgba(16, 185, 129, 0.15)' : (
                          log.approval_status === 'rejected' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(99, 102, 241, 0.15)'
                        ),
                        color: log.approval_status === 'user_approved' ? '#10b981' : (
                          log.approval_status === 'rejected' ? '#ef4444' : 'var(--primary)'
                        )
                      }}>
                        {log.approval_status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '12px 10px' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontWeight: 700,
                        background: log.status === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: log.status === 'success' ? '#10b981' : '#ef4444'
                      }}>
                        {log.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { 
  User as UserIcon, 
  ShieldCheck, 
  Database, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  Copy, 
  Check
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';

export const Settings: React.FC = () => {
  const { user, refreshUser } = useAuth();

  const [fullName, setFullName] = useState('');
  const [bio, setBio] = useState('');
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [theme, setTheme] = useState('dark');

  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.profile?.full_name || user.username || '');
      setBio(user.profile?.bio || '');
      if (user.profile?.preferences) {
        setNotificationsEnabled(user.profile.preferences.notifications_enabled ?? true);
        setTheme(user.profile.preferences.theme || 'dark');
      }
    }
  }, [user]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      setSaving(true);
      await api.users.updateProfile({
        full_name: fullName.trim(),
        bio: bio.trim(),
        preferences: {
          theme,
          notifications_enabled: notificationsEnabled,
        },
      });
      await refreshUser();
      setSuccessMsg('Profile and preferences updated successfully.');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const copyUserId = () => {
    if (user?.id) {
      navigator.clipboard.writeText(user.id);
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    }
  };

  return (
    <div style={{ maxWidth: '800px' }}>
      <div style={{ marginBottom: '28px' }}>
        <h2 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
          Platform & Account Settings
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Manage your identity, personal preferences, and security telemetry
        </p>
      </div>

      {successMsg && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '12px 16px',
          background: 'rgba(16, 185, 129, 0.1)',
          border: '1px solid rgba(16, 185, 129, 0.25)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--accent-emerald)',
          fontSize: '0.875rem',
          marginBottom: '20px'
        }}>
          <CheckCircle size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
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
          marginBottom: '20px'
        }}>
          <AlertCircle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* User Profile Form */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{ color: 'var(--primary)' }}>
            <UserIcon size={20} />
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Personal Profile</h3>
        </div>

        <form onSubmit={handleSaveProfile}>
          <div className="form-group">
            <label className="form-label">Display Name / Full Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Alex Mercer"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Bio / Focus Statement</label>
            <textarea
              className="form-textarea"
              placeholder="e.g. Lead Engineer exploring multi-agent architectures and high-throughput systems."
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
            <div className="form-group">
              <label className="form-label">Theme Mode</label>
              <select
                className="form-select"
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
              >
                <option value="dark">Nexus Dark (Default)</option>
                <option value="cyber">Cyberpunk Midnight</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Notifications</label>
              <select
                className="form-select"
                value={notificationsEnabled ? 'enabled' : 'disabled'}
                onChange={(e) => setNotificationsEnabled(e.target.value === 'enabled')}
              >
                <option value="enabled">Active (In-App + Alerts)</option>
                <option value="disabled">Muted</option>
              </select>
            </div>
          </div>

          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
            <span>Save Profile</span>
          </button>
        </form>
      </div>

      {/* Account & Security Telemetry */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <div style={{ color: 'var(--accent-cyan)' }}>
            <ShieldCheck size={20} />
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Account & Tenant Isolation</h3>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '0.875rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-muted)' }}>Registered Email</span>
            <span style={{ fontWeight: 600 }}>{user?.email || 'N/A'}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-muted)' }}>Tenant UUID</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <code style={{ fontSize: '0.8rem', background: 'rgba(0,0,0,0.3)', padding: '2px 8px', borderRadius: '4px', fontFamily: 'var(--font-mono)' }}>
                {user?.id || 'N/A'}
              </code>
              <button 
                onClick={copyUserId} 
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 8px' }}
                title="Copy ID"
              >
                {copiedId ? <Check size={12} style={{ color: 'var(--accent-emerald)' }} /> : <Copy size={12} />}
              </button>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <span style={{ color: 'var(--text-muted)' }}>Data Isolation Status</span>
            <span className="badge badge-completed">
              Strict User Scoping Active
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0' }}>
            <span style={{ color: 'var(--text-muted)' }}>Member Since</span>
            <span>{user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* System Infrastructure Telemetry */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
          <div style={{ color: 'var(--accent-emerald)' }}>
            <Database size={20} />
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>System Telemetry (Phase 1)</h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px' }}>
          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Core Architecture</div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginTop: '4px' }}>FastAPI + React 19</div>
          </div>

          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Database Engine</div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginTop: '4px' }}>PostgreSQL 16 + AsyncPG</div>
          </div>

          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Schema Versioning</div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginTop: '4px' }}>Alembic Head (001)</div>
          </div>

          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Security Standard</div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', marginTop: '4px' }}>Bcrypt + JWT HS256</div>
          </div>
        </div>
      </div>
    </div>
  );
};

import React from 'react';
import { 
  LayoutDashboard, 
  Bot,
  Brain,
  Share2,
  FolderKanban, 
  CheckSquare, 
  Target, 
  Settings as SettingsIcon, 
  LogOut, 
  Sparkles,
  ShieldCheck,
  Activity,
  X
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface SidebarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentPath,
  onNavigate,
  isOpen,
  onClose
}) => {
  const { user, logout } = useAuth();

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
    { label: 'AI Chat & RAG', path: '/chat', icon: Bot },
    { label: 'AI Memory', path: '/memory', icon: Brain },
    { label: 'Knowledge Graph', path: '/knowledge-graph', icon: Share2 },
    { label: 'Actions & Audit', path: '/actions', icon: ShieldCheck },
    { label: 'Evaluation & MLOps', path: '/evaluation', icon: Activity },
    { label: 'Projects', path: '/projects', icon: FolderKanban },
    { label: 'Tasks', path: '/tasks', icon: CheckSquare },
    { label: 'Goals', path: '/goals', icon: Target },
    { label: 'Settings', path: '/settings', icon: SettingsIcon },
  ];

  const getInitials = (name?: string | null, email?: string) => {
    if (name) {
      return name.substring(0, 2).toUpperCase();
    }
    if (email) {
      return email.substring(0, 2).toUpperCase();
    }
    return 'NX';
  };

  return (
    <>
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="brand-logo-icon">
            <Sparkles size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="brand-name">NEXUS AI</span>
              <span className="brand-tag">v1.0</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Core Intelligence
            </div>
          </div>
          {isOpen && (
            <button 
              onClick={onClose}
              style={{ marginLeft: 'auto', background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
            >
              <X size={18} />
            </button>
          )}
        </div>

        <nav className="nav-section">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPath === item.path;
            return (
              <a
                key={item.path}
                href={item.path}
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={(e) => {
                  e.preventDefault();
                  onNavigate(item.path);
                  if (isOpen) onClose();
                }}
              >
                <Icon size={18} className="nav-icon" />
                <span>{item.label}</span>
              </a>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="user-profile-badge">
            <div className="avatar">
              {getInitials(user?.profile?.full_name || user?.username, user?.email)}
            </div>
            <div className="user-info">
              <span className="user-name">
                {user?.profile?.full_name || user?.username || 'Nexus User'}
              </span>
              <span className="user-email">{user?.email || ''}</span>
            </div>
          </div>
          <button 
            className="btn-icon-logout" 
            title="Log out" 
            onClick={logout}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
    </>
  );
};

import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar } from './components/Sidebar';
import { Header } from './components/Header';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { Projects } from './pages/Projects';
import { Tasks } from './pages/Tasks';
import { Goals } from './pages/Goals';
import { Settings } from './pages/Settings';
import { Chat } from './pages/Chat';
import { Memory } from './pages/Memory';
import { KnowledgeGraph } from './pages/KnowledgeGraph';
import { Actions } from './pages/Actions';
import { Evaluation } from './pages/Evaluation';
import { Sparkles, Loader2 } from 'lucide-react';
import './index.css';

const AppContent: React.FC = () => {
  const { user, isLoading } = useAuth();
  const [currentPath, setCurrentPath] = useState<string>(() => window.location.pathname || '/dashboard');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);

  const navigate = (path: string) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
    window.scrollTo(0, 0);
  };

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Redirect logic
  useEffect(() => {
    if (!isLoading) {
      if (!user) {
        if (currentPath !== '/login' && currentPath !== '/register') {
          navigate('/login');
        }
      } else {
        if (currentPath === '/login' || currentPath === '/register' || currentPath === '/') {
          navigate('/dashboard');
        }
      }
    }
  }, [user, isLoading, currentPath]);

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
        color: 'var(--text-primary)'
      }}>
        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: 'var(--radius-lg)',
          background: 'linear-gradient(135deg, #6366f1, #06b6d4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 30px var(--primary-glow)',
          marginBottom: '20px'
        }}>
          <Sparkles size={28} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          <Loader2 size={18} className="animate-spin" style={{ animation: 'spin 1s linear infinite' }} />
          <span>Initializing NEXUS Intelligence...</span>
        </div>
      </div>
    );
  }

  // Public Unauthenticated Pages
  if (!user) {
    if (currentPath === '/register') {
      return <Register onNavigate={navigate} />;
    }
    return <Login onNavigate={navigate} />;
  }

  // Authenticated Protected Pages
  const getPageTitle = () => {
    switch (currentPath) {
      case '/dashboard':
        return { title: 'Dashboard', subtitle: 'Personal intelligence and performance overview' };
      case '/chat':
        return { title: 'Document Intelligence & Chat', subtitle: 'Ask questions and retrieve semantic citations from your vault' };
      case '/memory':
        return { title: 'Personalized AI Memory', subtitle: 'Cognitive memory across sessions: facts, events, and workflows' };
      case '/knowledge-graph':
        return { title: 'Knowledge Graph Explorer', subtitle: 'Interactive relational intelligence and semantic graph exploration' };
      case '/actions':
        return { title: 'Actions & Audit Log', subtitle: 'Secure tool execution, permission control, and immutable audit trail' };
      case '/evaluation':
        return { title: 'AI Evaluation & Observability', subtitle: 'RAG benchmarks, Agent metrics, distributed tracing, and MLOps registry' };
      case '/projects':
        return { title: 'Projects', subtitle: 'Workspaces and project containers' };
      case '/tasks':
        return { title: 'Tasks', subtitle: 'Actionable items, statuses, and deadlines' };
      case '/goals':
        return { title: 'Goals', subtitle: 'Strategic milestones and progress tracking' };
      case '/settings':
        return { title: 'Settings', subtitle: 'Profile customization and system telemetry' };
      default:
        return { title: 'Dashboard', subtitle: 'Personal intelligence overview' };
    }
  };

  const { title, subtitle } = getPageTitle();

  const renderActivePage = () => {
    switch (currentPath) {
      case '/dashboard':
        return <Dashboard onNavigate={navigate} />;
      case '/chat':
        return <Chat />;
      case '/memory':
        return <Memory />;
      case '/knowledge-graph':
        return <KnowledgeGraph />;
      case '/actions':
        return <Actions />;
      case '/evaluation':
        return <Evaluation />;
      case '/projects':
        return <Projects />;
      case '/tasks':
        return <Tasks />;
      case '/goals':
        return <Goals />;
      case '/settings':
        return <Settings />;
      default:
        return <Dashboard onNavigate={navigate} />;
    }
  };

  return (
    <div className="app-container">
      <Sidebar
        currentPath={currentPath}
        onNavigate={navigate}
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      <div className="main-wrapper">
        <Header
          title={title}
          subtitle={subtitle}
          onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
        />

        <main className="content-body">
          {renderActivePage()}
        </main>
      </div>
    </div>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

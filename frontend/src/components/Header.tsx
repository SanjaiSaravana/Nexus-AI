import React from 'react';
import { Menu } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onOpenMobileMenu: () => void;
  actions?: React.ReactNode;
}

export const Header: React.FC<HeaderProps> = ({
  title,
  subtitle,
  onOpenMobileMenu,
  actions,
}) => {
  return (
    <header className="header">
      <div className="header-left">
        <button
          onClick={onOpenMobileMenu}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-primary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
          className="mobile-menu-trigger"
        >
          <Menu size={22} />
        </button>
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && (
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {subtitle}
            </p>
          )}
        </div>
      </div>

      <div className="header-right">
        <div className="system-status">
          <span className="status-dot"></span>
          <span>Core Online</span>
        </div>
        {actions && <div>{actions}</div>}
      </div>
    </header>
  );
};

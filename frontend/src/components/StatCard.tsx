import React from 'react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  iconColor?: string;
  iconBg?: string;
  subtext?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon: Icon,
  iconColor = '#6366f1',
  iconBg = 'rgba(99, 102, 241, 0.15)',
  subtext,
}) => {
  return (
    <div className="stat-card">
      <div>
        <div className="stat-label">{label}</div>
        <div className="stat-val">{value}</div>
        {subtext && (
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            {subtext}
          </div>
        )}
      </div>
      <div 
        className="stat-icon-wrapper" 
        style={{ 
          background: iconBg, 
          color: iconColor,
          border: `1px solid ${iconColor}33`
        }}
      >
        <Icon size={24} />
      </div>
    </div>
  );
};

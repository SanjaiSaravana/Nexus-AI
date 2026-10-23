import React from 'react';
import { Plus } from 'lucide-react';

interface EmptyStateProps {
  icon: React.ElementType;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div className="empty-state">
      <div className="empty-icon-ring">
        <Icon size={32} />
      </div>
      <h3 className="empty-title">{title}</h3>
      <p className="empty-desc">{description}</p>
      {actionText && onAction && (
        <button className="btn btn-primary" onClick={onAction}>
          <Plus size={16} />
          <span>{actionText}</span>
        </button>
      )}
    </div>
  );
};

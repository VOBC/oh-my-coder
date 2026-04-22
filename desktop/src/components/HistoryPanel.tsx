// src/components/HistoryPanel.tsx — Session history sidebar panel
import React from 'react';
import { ChatSession } from '../hooks/useChatHistory';

interface HistoryPanelProps {
  sessions: ChatSession[];
  activeId: string;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
}

export default function HistoryPanel({ sessions, activeId, onSelect, onDelete, onNew }: HistoryPanelProps) {
  return (
    <div className="history-panel">
      <div className="history-panel__header">
        <span className="history-panel__title">Sessions</span>
        <button className="history-panel__new" onClick={onNew} title="New Chat">
          +
        </button>
      </div>

      <div className="history-panel__list">
        {sessions.length === 0 && (
          <div className="history-panel__empty">No sessions yet</div>
        )}
        {sessions.map(s => (
          <div
            key={s.id}
            className={`history-item ${s.id === activeId ? 'active' : ''}`}
          >
            <button
              className="history-item__btn"
              onClick={() => onSelect(s.id)}
              title={s.title}
            >
              <div className="history-item__title">{s.title}</div>
              <div className="history-item__meta">
                <span>{s.updated}</span>
                {s.model && <span className="history-item__model">{s.model}</span>}
              </div>
            </button>
            <button
              className="history-item__delete"
              onClick={() => onDelete(s.id)}
              title="Delete session"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

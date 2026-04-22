// src/components/HistoryPanel.tsx — Session history sidebar panel
// Uses <history-list> web component for Shadow DOM encapsulation
import React, { useRef, useEffect } from 'react';
import { ChatSession } from '../hooks/useChatHistory';

interface HistoryPanelProps {
  sessions: ChatSession[];
  activeId: string;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
}

// Type augmentation for the custom element
declare global {
  interface HTMLElementTagNameMap {
    'history-list': HTMLElement & {
      sessions: Array<{ id: string; title: string; updated: string; model?: string }>;
      activeId: string;
      onSelect?: (id: string) => void;
      onDelete?: (id: string) => void;
      onNew?: () => void;
    };
  }
}

export default function HistoryPanel({ sessions, activeId, onSelect, onDelete, onNew }: HistoryPanelProps) {
  const historyListRef = useRef<HTMLElementTagNameMap['history-list']>(null);

  // Sync sessions to web component
  useEffect(() => {
    const el = historyListRef.current;
    if (!el) return;

    // Convert sessions to plain objects for the web component
    el.sessions = sessions.map(s => ({
      id: s.id,
      title: s.title,
      updated: s.updated,
      model: s.model,
    }));
  }, [sessions]);

  // Sync activeId to web component
  useEffect(() => {
    const el = historyListRef.current;
    if (!el) return;
    el.activeId = activeId;
  }, [activeId]);

  // Set up event handlers
  useEffect(() => {
    const el = historyListRef.current;
    if (!el) return;

    el.onSelect = onSelect;
    el.onDelete = onDelete;
    el.onNew = onNew;

    // Also listen for custom events (for external listeners)
    const handleSelect = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.id) onSelect(detail.id);
    };

    const handleDelete = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.id) onDelete(detail.id);
    };

    const handleNew = () => onNew();

    el.addEventListener('session-select', handleSelect);
    el.addEventListener('session-delete', handleDelete);
    el.addEventListener('session-new', handleNew);

    return () => {
      el.removeEventListener('session-select', handleSelect);
      el.removeEventListener('session-delete', handleDelete);
      el.removeEventListener('session-new', handleNew);
    };
  }, [onSelect, onDelete, onNew]);

  return (
    <div className="history-panel">
      <history-list ref={historyListRef} />
    </div>
  );
}

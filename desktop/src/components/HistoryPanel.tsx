// src/components/HistoryPanel.tsx — Session history sidebar panel
// P3-3: Enhanced with rename, export, clear all
import { useRef, useEffect } from 'react';
import { ChatSession } from '../hooks/useChatHistory';

interface HistoryPanelProps {
  sessions: ChatSession[];
  activeId: string;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, newTitle: string) => void;
  onExport: (id: string) => void;
  onClearAll: () => void;
}

declare global {
  interface HTMLElementTagNameMap {
    'history-list': HTMLElement & {
      sessions: Array<{ id: string; title: string; updated: string; model?: string }>;
      activeId: string;
      onSelect?: (id: string) => void;
      onDelete?: (id: string) => void;
      onNew?: () => void;
      onRename?: (id: string, newTitle: string) => void;
      onExport?: (id: string) => void;
      onClearAll?: () => void;
    };
  }
}

export default function HistoryPanel({
  sessions,
  activeId,
  onSelect,
  onDelete,
  onNew,
  onRename,
  onExport,
  onClearAll,
}: HistoryPanelProps) {
  const historyListRef = useRef<HTMLElementTagNameMap['history-list']>(null);

  // Sync sessions
  useEffect(() => {
    const el = historyListRef.current;
    if (!el) return;
    el.sessions = sessions.map(s => ({
      id: s.id,
      title: s.title,
      updated: s.updated,
      model: s.model,
    }));
  }, [sessions]);

  // Sync activeId
  useEffect(() => {
    const el = historyListRef.current;
    if (!el) return;
    el.activeId = activeId;
  }, [activeId]);

  // Event handlers
  useEffect(() => {
    const el = historyListRef.current;
    if (!el) return;

    el.onSelect = onSelect;
    el.onDelete = onDelete;
    el.onNew = onNew;
    el.onRename = onRename;
    el.onExport = onExport;
    el.onClearAll = onClearAll;

    const handleSelect = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.id) onSelect(detail.id);
    };

    const handleDelete = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.id) onDelete(detail.id);
    };

    const handleNew = () => onNew();

    const handleRename = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.id && detail?.newTitle) onRename(detail.id, detail.newTitle);
    };

    const handleExport = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.id) onExport(detail.id);
    };

    const handleClearAll = () => onClearAll();

    el.addEventListener('session-select', handleSelect);
    el.addEventListener('session-delete', handleDelete);
    el.addEventListener('session-new', handleNew);
    el.addEventListener('session-rename', handleRename);
    el.addEventListener('session-export', handleExport);
    el.addEventListener('sessions-clear-all', handleClearAll);

    return () => {
      el.removeEventListener('session-select', handleSelect);
      el.removeEventListener('session-delete', handleDelete);
      el.removeEventListener('session-new', handleNew);
      el.removeEventListener('session-rename', handleRename);
      el.removeEventListener('session-export', handleExport);
      el.removeEventListener('sessions-clear-all', handleClearAll);
    };
  }, [onSelect, onDelete, onNew, onRename, onExport, onClearAll]);

  return (
    <div className="history-panel">
      <history-list ref={historyListRef} />
    </div>
  );
}

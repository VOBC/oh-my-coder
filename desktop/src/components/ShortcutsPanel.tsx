// src/components/ShortcutsPanel.tsx — Keyboard shortcuts help panel
// Reference: OpenCode-style categorized shortcuts with search and click-to-execute

import { useEffect, useRef, useState, useMemo } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────
export interface ShortcutItem {
  id: string;
  key: string;
  metaKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  description: string;
  category: 'global' | 'editor' | 'chat';
  action?: () => void;
}

interface ShortcutsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onExecute?: (shortcut: ShortcutItem) => void;
}

// ── Category Labels ───────────────────────────────────────────────────────────
const CATEGORY_LABELS: Record<string, { label: string; icon: string }> = {
  global: { label: '全局', icon: '⌘' },
  editor: { label: '编辑器', icon: '✎' },
  chat: { label: '聊天', icon: '💬' },
};

// ── All Registered Shortcuts ──────────────────────────────────────────────────
const ALL_SHORTCUTS: ShortcutItem[] = [
  // Global
  { id: 'new-chat', key: 'n', metaKey: true, description: '新建会话', category: 'global' },
  { id: 'settings', key: ',', metaKey: true, description: '打开设置', category: 'global' },
  { id: 'shortcuts', key: '/', metaKey: true, description: '显示快捷键', category: 'global' },
  { id: 'escape', key: 'Escape', description: '关闭面板/取消操作', category: 'global' },
  
  // Editor
  { id: 'focus-input', key: 'i', metaKey: true, description: '聚焦输入框', category: 'editor' },
  { id: 'inline-edit', key: 'e', metaKey: true, description: '行内编辑模式', category: 'editor' },
  { id: 'submit', key: 'Enter', description: '发送消息', category: 'editor' },
  { id: 'newline', key: 'Enter', shiftKey: true, description: '换行', category: 'editor' },
  
  // Chat
  { id: 'switch-model', key: 'm', metaKey: true, description: '切换模型', category: 'chat' },
  { id: 'clear-chat', key: 'l', metaKey: true, description: '清空对话', category: 'chat' },
  { id: 'history-prev', key: 'ArrowUp', altKey: true, description: '上一条历史', category: 'chat' },
  { id: 'history-next', key: 'ArrowDown', altKey: true, description: '下一条历史', category: 'chat' },
];

// ── Format Key Combo ──────────────────────────────────────────────────────────
function formatKeyCombo(s: ShortcutItem): string {
  const parts: string[] = [];
  
  if (s.metaKey || s.ctrlKey) parts.push('⌘');
  if (s.ctrlKey && !s.metaKey) parts[0] = 'Ctrl';
  if (s.altKey) parts.push('⌥');
  if (s.shiftKey) parts.push('⇧');
  
  // Format key name
  const keyMap: Record<string, string> = {
    'Escape': 'Esc',
    'ArrowUp': '↑',
    'ArrowDown': '↓',
    'ArrowLeft': '←',
    'ArrowRight': '→',
    'Enter': '↵',
    'Tab': '⇥',
    'Backspace': '⌫',
    'Delete': '⌦',
    ' ': 'Space',
  };
  
  parts.push(keyMap[s.key] || s.key.toUpperCase());
  return parts.join('');
}

// ── Key Combo Component ───────────────────────────────────────────────────────
function KeyCombo({ shortcut, small }: { shortcut: ShortcutItem; small?: boolean }) {
  const keys = [];
  if (shortcut.metaKey || shortcut.ctrlKey) keys.push('⌘');
  if (shortcut.ctrlKey && !shortcut.metaKey) keys[0] = 'Ctrl';
  if (shortcut.altKey) keys.push('⌥');
  if (shortcut.shiftKey) keys.push('⇧');
  
  const keyMap: Record<string, string> = {
    'Escape': 'Esc', 'ArrowUp': '↑', 'ArrowDown': '↓',
    'ArrowLeft': '←', 'ArrowRight': '→', 'Enter': '↵',
    'Tab': '⇥', 'Backspace': '⌫', 'Delete': '⌦', ' ': 'Space',
  };
  keys.push(keyMap[shortcut.key] || shortcut.key.toUpperCase());
  
  return (
    <span className={`key-combo ${small ? 'key-combo--small' : ''}`}>
      {keys.map((k, i) => (
        <kbd key={i} className="key-combo__key">{k}</kbd>
      ))}
    </span>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function ShortcutsPanel({ isOpen, onClose, onExecute }: ShortcutsPanelProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Focus search on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSearch('');
      setSelectedId(null);
    }
  }, [isOpen]);

  // Filter shortcuts
  const filtered = useMemo(() => {
    if (!search.trim()) return ALL_SHORTCUTS;
    const q = search.toLowerCase();
    return ALL_SHORTCUTS.filter(s => 
      s.description.toLowerCase().includes(q) ||
      formatKeyCombo(s).toLowerCase().includes(q) ||
      s.category.toLowerCase().includes(q)
    );
  }, [search]);

  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<string, ShortcutItem[]> = {};
    filtered.forEach(s => {
      if (!groups[s.category]) groups[s.category] = [];
      groups[s.category].push(s);
    });
    return groups;
  }, [filtered]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Close on overlay click
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  };

  // Execute shortcut
  const handleExecute = (s: ShortcutItem) => {
    setSelectedId(s.id);
    onExecute?.(s);
    // Visual feedback
    setTimeout(() => setSelectedId(null), 200);
  };

  if (!isOpen) return null;

  return (
    <div 
      ref={overlayRef}
      className="shortcuts-overlay"
      onClick={handleOverlayClick}
    >
      <div className="shortcuts-panel shortcuts-panel--enhanced">
        {/* Header with search */}
        <div className="shortcuts-header">
          <div className="shortcuts-header__left">
            <span className="shortcuts-title">键盘快捷键</span>
            <span className="shortcuts-count">{filtered.length}</span>
          </div>
          <button className="shortcuts-close" onClick={onClose} aria-label="关闭">✕</button>
        </div>

        {/* Search bar */}
        <div className="shortcuts-search">
          <span className="shortcuts-search__icon">🔍</span>
          <input
            ref={inputRef}
            type="text"
            className="shortcuts-search__input"
            placeholder="搜索快捷键..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button 
              className="shortcuts-search__clear" 
              onClick={() => { setSearch(''); inputRef.current?.focus(); }}
            >
              ✕
            </button>
          )}
          <span className="shortcuts-search__hint">
            <KeyCombo small shortcut={{ key: '/', metaKey: true, description: '', category: 'global' }} />
          </span>
        </div>
        
        {/* Body with categories */}
        <div className="shortcuts-body shortcuts-body--scrollable">
          {Object.keys(grouped).length === 0 ? (
            <div className="shortcuts-empty">
              <span className="shortcuts-empty__icon">🔍</span>
              <span>未找到匹配的快捷键</span>
            </div>
          ) : (
            Object.entries(grouped).map(([category, items]) => (
              <div key={category} className="shortcuts-section">
                <div className="shortcuts-section__header">
                  <span className="shortcuts-section__icon">
                    {CATEGORY_LABELS[category]?.icon || '⌘'}
                  </span>
                  <span className="shortcuts-section__title">
                    {CATEGORY_LABELS[category]?.label || category}
                  </span>
                  <span className="shortcuts-section__count">{items.length}</span>
                </div>
                <div className="shortcuts-list">
                  {items.map(s => (
                    <div 
                      key={s.id}
                      className={`shortcuts-item ${selectedId === s.id ? 'shortcuts-item--active' : ''}`}
                      onClick={() => handleExecute(s)}
                      title="点击执行"
                    >
                      <span className="shortcuts-item__desc">{s.description}</span>
                      <KeyCombo shortcut={s} />
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
        
        {/* Footer */}
        <div className="shortcuts-footer">
          <span className="shortcuts-hint">
            <KeyCombo small shortcut={{ key: 'Enter', description: '', category: 'global' }} />
            执行
          </span>
          <span className="shortcuts-hint">
            <KeyCombo small shortcut={{ key: 'Escape', description: '', category: 'global' }} />
            关闭
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Exports ───────────────────────────────────────────────────────────────────
export { ALL_SHORTCUTS as SHORTCUTS, formatKeyCombo };
export default ShortcutsPanel;


// src/components/ShortcutsPanel.tsx — Keyboard shortcuts help panel
// Shows all registered shortcuts in a modal overlay

import { useEffect, useRef } from 'react';

interface ShortcutItem {
  key: string;
  metaKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  description: string;
}

interface ShortcutsPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// All registered shortcuts
const SHORTCUTS: ShortcutItem[] = [
  { key: 'i', metaKey: true, description: '聚焦输入框' },
  { key: 'e', metaKey: true, description: '行内编辑模式' },
  { key: 'm', metaKey: true, description: '切换模型' },
  { key: 'n', metaKey: true, description: '新建会话' },
  { key: ',', metaKey: true, description: '打开设置' },
  { key: '/', metaKey: true, description: '显示快捷键' },
  { key: 'l', metaKey: true, description: '清空对话' },
  { key: 'Escape', description: '关闭面板/取消操作' },
];

function formatShortcut(s: ShortcutItem): string {
  const parts: string[] = [];
  if (s.metaKey || s.ctrlKey) parts.push('⌘');
  if (s.shiftKey) parts.push('⇧');
  
  // Format key name
  let keyName = s.key.toUpperCase();
  if (s.key === 'Escape') keyName = 'Esc';
  if (s.key === '/') keyName = '/';
  
  parts.push(keyName);
  return parts.join('');
}

export function ShortcutsPanel({ isOpen, onClose }: ShortcutsPanelProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

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
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      ref={overlayRef}
      className="shortcuts-overlay"
      onClick={handleOverlayClick}
    >
      <div className="shortcuts-panel">
        <div className="shortcuts-header">
          <h2 className="shortcuts-title">键盘快捷键</h2>
          <button 
            className="shortcuts-close"
            onClick={onClose}
            aria-label="关闭"
          >
            ✕
          </button>
        </div>
        
        <div className="shortcuts-body">
          <div className="shortcuts-section">
            <h3 className="shortcuts-section__title">通用操作</h3>
            <div className="shortcuts-list">
              {SHORTCUTS.map((s, i) => (
                <div key={i} className="shortcuts-item">
                  <span className="shortcuts-item__keys">
                    <kbd>{formatShortcut(s)}</kbd>
                  </span>
                  <span className="shortcuts-item__desc">{s.description}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <div className="shortcuts-footer">
          <span className="shortcuts-hint">按 <kbd>Esc</kbd> 关闭</span>
        </div>
      </div>
    </div>
  );
}

export { SHORTCUTS, formatShortcut };

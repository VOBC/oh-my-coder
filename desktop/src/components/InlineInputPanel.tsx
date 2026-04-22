// src/components/InlineInputPanel.tsx — Cursor-style inline input (Cmd+K)
// Spotlight-like input overlay for quick prompts

import { useState, useEffect, useRef } from 'react';

// UI strings (not in JSX)
const UI_TEXTS = {
  placeholder: 'Ask anything...',
  hint: 'Press Enter to send',
  escHint: 'Esc',
};

interface InlineInputPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSend: (message: string) => void;
  currentModel: string;
}

export function InlineInputPanel({ isOpen, onClose, onSend, currentModel }: InlineInputPanelProps) {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setInput('');
      // Small delay to ensure animation starts
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, [isOpen]);

  // Handle keyboard
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

  // Send message
  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    
    onSend(trimmed);
    setInput('');
    onClose();
  };

  // Submit on Enter
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Close on overlay click
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="inline-input-overlay" onClick={handleOverlayClick}>
      <div className="inline-input-container">
        <div className="inline-input-box">
          <input
            ref={inputRef}
            type="text"
            className="inline-input-field"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={UI_TEXTS.placeholder}
            autoComplete="off"
            spellCheck={false}
          />
          <button 
            className="inline-input-send" 
            onClick={handleSend}
            disabled={!input.trim()}
          >
            ↑
          </button>
        </div>
        
        <div className="inline-input-footer">
          <span className="inline-input-model">{currentModel}</span>
          <span className="inline-input-hint">
            <kbd>Enter</kbd> {UI_TEXTS.hint}
            <kbd className="inline-input-esc">{UI_TEXTS.escHint}</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}

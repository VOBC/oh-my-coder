// src/components/InlineEditor.tsx — Cmd+K inline editing modal (Cursor-style)
import React, { useState, useRef, useEffect, useCallback } from 'react';

interface InlineEditorProps {
  isOpen: boolean;
  onClose: () => void;
  targetLabel?: string;   // e.g. "claude-3-5-sonnet" row being edited
  onAccept: (diff: string) => void;
  onReject: () => void;
  modelId?: string;
}

export default function InlineEditor({
  isOpen, onClose, targetLabel, onAccept, onReject, modelId,
}: InlineEditorProps) {
  const [intent, setIntent] = useState('');
  const [loading, setLoading] = useState(false);
  const [diff, setDiff] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isOpen) {
      setIntent('');
      setDiff('');
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  const handleSubmit = useCallback(async () => {
    if (!intent.trim()) return;
    setLoading(true);
    try {
      // Ask AI to generate an inline diff based on the user's intent
      const result = await window.omc?.chatSend({
        message: `You are editing model config: ${modelId || targetLabel}\nUser intent: ${intent.trim()}\nGenerate an inline unified diff (--- / +++) showing what changes should be made to the model config. If no file applies, respond with a plain-text summary of the change only. Keep it concise.`,
        model: modelId,
      });
      const output = result?.stdout || result?.stderr || (result?.code === 0 ? 'Done.' : 'No changes needed.');
      setDiff(output);
    } catch (e: any) {
      setDiff(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [intent, modelId, targetLabel]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="inline-editor-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="inline-editor">
        {/* Header */}
        <div className="inline-editor__header">
          <div className="inline-editor__header-left">
            <span className="inline-editor__kbd">⌘K</span>
            <span className="inline-editor__title">Inline Edit</span>
            {targetLabel && (
              <span className="inline-editor__target">{targetLabel}</span>
            )}
          </div>
          <button className="inline-editor__close" onClick={onClose}>✕</button>
        </div>

        {/* Intent input */}
        <div className="inline-editor__intent">
          <textarea
            ref={inputRef}
            className="inline-editor__input"
            value={intent}
            onChange={e => setIntent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what you want to change… (⌘↵ to submit)"
            rows={3}
          />
          <button
            className="inline-editor__submit"
            onClick={handleSubmit}
            disabled={!intent.trim() || loading}
          >
            {loading ? '◐' : '→'}
          </button>
        </div>

        {/* Diff output */}
        {diff && (
          <div className="inline-editor__diff">
            <div className="inline-editor__diff-toolbar">
              <span className="inline-editor__diff-label">Preview</span>
              <div className="inline-editor__diff-actions">
                <button className="inline-editor__btn inline-editor__btn--accept" onClick={() => onAccept(diff)}>
                  ✓ Accept
                </button>
                <button className="inline-editor__btn inline-editor__btn--reject" onClick={() => { setDiff(''); onReject(); }}>
                  ✗ Reject
                </button>
              </div>
            </div>
            <pre className="inline-editor__diff-content">{diff}</pre>
          </div>
        )}

        <div className="inline-editor__hint">
          ⌘↵ to submit · Esc to close · Accept/Reject to apply
        </div>
      </div>
    </div>
  );
}

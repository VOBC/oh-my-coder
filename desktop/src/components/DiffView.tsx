// src/components/DiffView.tsx — Diff visualization with Accept/Reject
// Reference: Cline-style inline diff acceptance

import { useState, useMemo } from 'react';

export interface DiffLine {
  type: 'add' | 'delete' | 'context';
  content: string;
  oldLineNumber?: number;
  newLineNumber?: number;
}

export interface FileDiff {
  path: string;
  hunks: DiffLine[];
  originalContent?: string;
  newContent?: string;
}

interface DiffViewProps {
  diff: FileDiff;
  onAccept?: (path: string) => void;
  onReject?: (path: string) => void;
}

/**
 * Parse unified diff format into structured lines
 */
function parseUnifiedDiff(diffText: string): DiffLine[] {
  const lines = diffText.split('\n');
  const result: DiffLine[] = [];
  let oldLine = 0;
  let newLine = 0;

  for (const line of lines) {
    // Skip diff headers
    if (line.startsWith('---') || line.startsWith('+++') || line.startsWith('@@') || line.startsWith('diff ')) {
      continue;
    }

    if (line.startsWith('+')) {
      newLine++;
      result.push({
        type: 'add',
        content: line.slice(1),
        newLineNumber: newLine,
      });
    } else if (line.startsWith('-')) {
      oldLine++;
      result.push({
        type: 'delete',
        content: line.slice(1),
        oldLineNumber: oldLine,
      });
    } else if (line.startsWith(' ')) {
      oldLine++;
      newLine++;
      result.push({
        type: 'context',
        content: line.slice(1),
        oldLineNumber: oldLine,
        newLineNumber: newLine,
      });
    } else if (line.match(/^\d+/)) {
      // Line number header from unified diff, reset counters
      const match = line.match(/@@ -(\d+).* \+(\d+)/);
      if (match) {
        oldLine = parseInt(match[1], 10) - 1;
        newLine = parseInt(match[2], 10) - 1;
      }
    }
  }

  return result;
}

/**
 * Get file name from path
 */
function getFileName(path: string): string {
  return path.split('/').pop() || path;
}

/**
 * Get file extension for syntax highlighting hint
 */
function getFileExtension(path: string): string {
  const ext = path.split('.').pop() || '';
  return ext.toLowerCase();
}

export default function DiffView({ diff, onAccept, onReject }: DiffViewProps) {
  const [accepted, setAccepted] = useState<'pending' | 'accepted' | 'rejected'>('pending');
  const [isExpanded, setIsExpanded] = useState(true);

  // Parse diff if it's a string, otherwise use structured data
  const lines = useMemo(() => {
    if (typeof diff.hunks === 'string') {
      return parseUnifiedDiff(diff.hunks as unknown as string);
    }
    return diff.hunks;
  }, [diff.hunks]);

  const handleAccept = () => {
    setAccepted('accepted');
    onAccept?.(diff.path);
  };

  const handleReject = () => {
    setAccepted('rejected');
    onReject?.(diff.path);
  };

  // Count changes
  const additions = lines.filter(l => l.type === 'add').length;
  const deletions = lines.filter(l => l.type === 'delete').length;
  const ext = getFileExtension(diff.path);

  return (
    <div className={`diff-view ${accepted !== 'pending' ? `diff-view--${accepted}` : ''}`}>
      {/* Header */}
      <div className="diff-view__header" onClick={() => setIsExpanded(!isExpanded)}>
        <div className="diff-view__file-info">
          <span className="diff-view__file-icon">📝</span>
          <span className="diff-view__file-path">{getFileName(diff.path)}</span>
          <span className="diff-view__file-ext">.{ext}</span>
        </div>
        <div className="diff-view__stats">
          {additions > 0 && (
            <span className="diff-view__stat diff-view__stat--add">+{additions}</span>
          )}
          {deletions > 0 && (
            <span className="diff-view__stat diff-view__stat--del">-{deletions}</span>
          )}
        </div>
        <button className="diff-view__toggle">
          {isExpanded ? '▼' : '▶'}
        </button>
      </div>

      {/* Diff content */}
      {isExpanded && (
        <div className="diff-view__content">
          <div className="diff-view__lines">
            {lines.map((line, idx) => (
              <div key={idx} className={`diff-line diff-line--${line.type}`}>
                <span className="diff-line__gutter">
                  {line.type === 'delete' && line.oldLineNumber}
                  {line.type === 'add' && line.newLineNumber}
                  {line.type === 'context' && (
                    <>
                      <span className="diff-line__old">{line.oldLineNumber}</span>
                      <span className="diff-line__new">{line.newLineNumber}</span>
                    </>
                  )}
                </span>
                <span className="diff-line__marker">
                  {line.type === 'add' && '+'}
                  {line.type === 'delete' && '-'}
                  {line.type === 'context' && ' '}
                </span>
                <span className="diff-line__content">{line.content || '\u00A0'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action buttons */}
      {accepted === 'pending' && (
        <div className="diff-view__actions">
          <button className="diff-btn diff-btn--accept" onClick={handleAccept}>
            ✓ Accept
          </button>
          <button className="diff-btn diff-btn--reject" onClick={handleReject}>
            ✕ Reject
          </button>
        </div>
      )}

      {/* Status indicator */}
      {accepted !== 'pending' && (
        <div className={`diff-view__status diff-view__status--${accepted}`}>
          {accepted === 'accepted' ? '✓ 已接受' : '✕ 已拒绝'}
        </div>
      )}
    </div>
  );
}

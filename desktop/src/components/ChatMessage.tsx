// src/components/ChatMessage.tsx — Bubble tea style message bubbles
// P0-1: Replaced inline ToolCallCard with <tool-card> custom element
// P1-3: Added diff visualization support
// P3-2: Markdown rendering for AI messages
import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChatMessage } from '../hooks/useChatHistory';
import { ToolCardElement, ToolCallData, createToolCard } from './ToolCard';
import DiffView, { FileDiff, DiffLine } from './DiffView';

interface ToolCall {
  tool: string;
  status: 'pending' | 'success' | 'error';
  content: string;
}

interface ChatMessageProps {
  msg: ChatMessage;
  toolCalls?: ToolCall[];
  diff?: FileDiff;
  onDiffAccept?: (path: string) => void;
  onDiffReject?: (path: string) => void;
}

// React wrapper for <tool-card> custom element
interface ToolCardWrapperProps {
  toolCalls: ToolCall[];
}

function ToolCardWrapper({ toolCalls }: ToolCardWrapperProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    
    // Clear existing content
    containerRef.current.innerHTML = '';
    
    // Render tool-cards as custom elements
    toolCalls.forEach(tc => {
      const card = createToolCard({
        tool: tc.tool,
        status: tc.status,
        content: tc.content,
      });
      containerRef.current!.appendChild(card);
    });
  }, [toolCalls]);

  return <div ref={containerRef} className="bubble__toolcalls" />;
}

/**
 * Parse diff content from message if present
 * Supports format: ```diff\n...\n```
 */
function parseDiffFromMessage(content: string): FileDiff | null {
  const diffMatch = content.match(/```diff\n([\s\S]*?)\n```/);
  if (!diffMatch) return null;

  const pathMatch = content.match(/(?:File|文件|修改)[:\s]+`?([^`\n]+)`?/i);
  const path = pathMatch ? pathMatch[1].trim() : 'unknown-file';

  const diffText = diffMatch[1];
  const lines: DiffLine[] = [];
  const diffLines = diffText.split('\n');
  let oldLine = 0;
  let newLine = 0;

  for (const line of diffLines) {
    if (line.startsWith('@@')) {
      const match = line.match(/@@ -?(\d+).* \+?(\d+)/);
      if (match) {
        oldLine = parseInt(match[1], 10);
        newLine = parseInt(match[2], 10);
      }
      continue;
    }
    if (line.startsWith('---') || line.startsWith('+++')) continue;

    if (line.startsWith('+')) {
      newLine++;
      lines.push({ type: 'add', content: line.slice(1), newLineNumber: newLine });
    } else if (line.startsWith('-')) {
      oldLine++;
      lines.push({ type: 'delete', content: line.slice(1), oldLineNumber: oldLine });
    } else {
      oldLine++;
      newLine++;
      lines.push({ type: 'context', content: line.slice(1), oldLineNumber: oldLine, newLineNumber: newLine });
    }
  }

  return { path, hunks: lines };
}

export default function ChatMessageBubble({ msg, toolCalls, diff, onDiffAccept, onDiffReject }: ChatMessageProps) {
  const isUser = msg.role === 'user';
  const [pendingDiff, setPendingDiff] = useState<FileDiff | null>(null);

  // Parse diff from message content if not provided
  useEffect(() => {
    if (diff) {
      setPendingDiff(diff);
    } else if (msg.role === 'assistant') {
      const parsed = parseDiffFromMessage(msg.content);
      if (parsed) setPendingDiff(parsed);
    }
  }, [msg.content, diff]);

  return (
    <div className={`bubble-wrap bubble-wrap--${msg.role}`}>
      <div className={`bubble bubble--${msg.role}`}>
        {/* Avatar */}
        <div className="bubble__avatar">
          {isUser ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="2"/>
              <path d="M4 20c0-4 4-6 8-6s8 2 8 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" strokeWidth="2"/>
              <path d="M8 12h8M12 8v8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          )}
        </div>

        {/* Content */}
        <div className="bubble__body">
          <div className="bubble__content">
            {isUser ? (
              // User message: plain text with line breaks
              msg.content.split('\n').map((line, i, arr) => (
                <React.Fragment key={i}>
                  {line}
                  {i < arr.length - 1 && <br />}
                </React.Fragment>
              ))
            ) : (
              // AI message: Markdown rendering
              <ReactMarkdown
                components={{
                  // Code block
                  code: ({ node, inline, className, children, ...props }: any) => {
                    if (inline) {
                      return <code className="md-inline-code" {...props}>{children}</code>;
                    }
                    return (
                      <div className="md-code-block">
                        <div className="md-code-header">
                          <span className="md-code-lang">{className?.replace('language-', '') || 'code'}</span>
                          <button
                            className="md-code-copy"
                            onClick={() => {
                              navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
                            const btn = document.activeElement as HTMLButtonElement;
                              btn.textContent = 'Copied!';
                              setTimeout(() => btn.textContent = 'Copy', 1500);
                            }}
                          >
                            Copy
                          </button>
                        </div>
                        <code className={className} {...props}>{children}</code>
                      </div>
                    );
                  },
                  // Paragraph
                  p: ({ children }) => <p className="md-paragraph">{children}</p>,
                  // List
                  ul: ({ children }) => <ul className="md-list">{children}</ul>,
                  ol: ({ children }) => <ol className="md-list md-list--ordered">{children}</ol>,
                  li: ({ children }) => <li className="md-list-item">{children}</li>,
                  // Headings
                  h1: ({ children }) => <h1 className="md-heading md-heading--1">{children}</h1>,
                  h2: ({ children }) => <h2 className="md-heading md-heading--2">{children}</h2>,
                  h3: ({ children }) => <h3 className="md-heading md-heading--3">{children}</h3>,
                  // Strong & emphasis
                  strong: ({ children }) => <strong className="md-strong">{children}</strong>,
                  em: ({ children }) => <em className="md-em">{children}</em>,
                  // Blockquote
                  blockquote: ({ children }) => <blockquote className="md-blockquote">{children}</blockquote>,
                  // Link
                  a: ({ href, children }) => (
                    <a href={href} className="md-link" target="_blank" rel="noopener noreferrer">
                      {children}
                    </a>
                  ),
                }}
              >
                {msg.content}
              </ReactMarkdown>
            )}
          </div>
          <div className="bubble__time">
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>

          {/* Diff visualization */}
          {pendingDiff && (
            <DiffView
              diff={pendingDiff}
              onAccept={onDiffAccept}
              onReject={onDiffReject}
            />
          )}

          {/* Tool calls — using <tool-card> custom element */}
          {toolCalls && toolCalls.length > 0 && (
            <ToolCardWrapper toolCalls={toolCalls} />
          )}
        </div>
      </div>
    </div>
  );
}

// Re-export for backward compatibility
export { ToolCardElement, ToolCallData, createToolCard } from './ToolCard';

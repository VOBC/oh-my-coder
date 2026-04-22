// src/components/ChatMessage.tsx — Bubble tea style message bubbles
// P0-1: Replaced inline ToolCallCard with <tool-card> custom element
import React, { useEffect, useRef } from 'react';
import { ChatMessage } from '../hooks/useChatHistory';
import { ToolCardElement, ToolCallData, createToolCard } from './ToolCard';

interface ToolCall {
  tool: string;
  status: 'pending' | 'success' | 'error';
  content: string;
}

interface ChatMessageProps {
  msg: ChatMessage;
  toolCalls?: ToolCall[];
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

export default function ChatMessageBubble({ msg, toolCalls }: ChatMessageProps) {
  const isUser = msg.role === 'user';

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
            {msg.content.split('\n').map((line, i, arr) => (
              <React.Fragment key={i}>
                {line}
                {i < arr.length - 1 && <br />}
              </React.Fragment>
            ))}
          </div>
          <div className="bubble__time">
            {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </div>

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

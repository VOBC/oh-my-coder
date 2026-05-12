import React, { useRef, useEffect } from 'react';

interface LogEntry {
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
  timestamp: number;
}

interface LiveLogProps {
  logs: LogEntry[];
  maxHeight?: number;
}

const LEVEL_ICONS: Record<string, string> = {
  info: 'ℹ',
  warn: '⚠',
  error: '✗',
  success: '✓',
};

const LEVEL_COLORS: Record<string, string> = {
  info: '#94a3b8',
  warn: '#f59e0b',
  error: '#ef4444',
  success: '#4ade80',
};

export function LiveLog({ logs, maxHeight = 200 }: LiveLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  if (logs.length === 0) return null;

  return (
    <div className="live-log">
      <div className="live-log__header">
        <span className="live-log__label">实时日志</span>
        <span className="live-log__count">{logs.length} 条</span>
      </div>
      <div
        ref={scrollRef}
        className="live-log__content"
        style={{ maxHeight }}
      >
        {logs.map((log, idx) => (
          <div key={idx} className={`live-log__entry ${log.level}`}>
            <span
              className="live-log__icon"
              style={{ color: LEVEL_COLORS[log.level] }}
            >
              {LEVEL_ICONS[log.level]}
            </span>
            <span className="live-log__time">
              {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            <span className="live-log__message">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

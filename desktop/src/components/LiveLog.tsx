import React, { useRef, useEffect, useState } from 'react';

interface LogEntry {
  level: 'info' | 'warn' | 'error' | 'success';
  message: string;
  timestamp: number;
  isError?: boolean;
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
  const [dotFrame, setDotFrame] = useState(0);
  const isRunningRef = useRef(false);

  // Carousel dots while active: cycle through 0/1/2 every 800ms
  useEffect(() => {
    if (logs.length === 0) {
      isRunningRef.current = false;
      return;
    }
    // Check if latest log is a running indicator
    const latest = logs[logs.length - 1];
    const isRunning = !latest.message.startsWith('✅') && !latest.message.startsWith('❌') && !latest.message.startsWith('🛑');
    isRunningRef.current = isRunning;

    if (!isRunning) return;

    const id = setInterval(() => {
      setDotFrame(f => (f + 1) % 3);
    }, 800);
    return () => clearInterval(id);
  }, [logs]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  if (logs.length === 0) return null;

  const latest = logs[logs.length - 1];
  const isRunning = !latest.message.startsWith('✅') && !latest.message.startsWith('❌') && !latest.message.startsWith('🛑');
  const dotFrames = ['⠋', '⠙', '⠹'];

  return (
    <div className="live-log">
      <div className="live-log__header">
        <span className="live-log__label">
          {isRunning ? '实时日志' : '执行日志'}
        </span>
        <span className="live-log__count">{logs.length} 条</span>
      </div>
      <div
        ref={scrollRef}
        className="live-log__content"
        style={{ maxHeight }}
      >
        {logs.map((log, idx) => {
          const isLast = idx === logs.length - 1;
          return (
            <div key={idx} className={`live-log__entry ${log.level} ${isLast ? 'live-log__entry--latest' : ''}`}>
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
              {isLast && isRunning && (
                <span className="live-log__carousel">{dotFrames[dotFrame]}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
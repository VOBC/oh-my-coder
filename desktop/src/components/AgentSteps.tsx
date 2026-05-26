import React, { useState } from 'react';

interface Step {
  agent: string;
  action: string;
  detail: string;
  timestamp: number;
  status: 'running' | 'completed' | 'error';
}

interface AgentStepsProps {
  steps: Step[];
}

const AGENT_COLORS: Record<string, string> = {
  Planner: '#60a5fa',
  Coder: '#4ade80',
  Reviewer: '#c084fc',
  Executor: '#f59e0b',
};

export function AgentSteps({ steps }: AgentStepsProps) {
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggleExpand = (idx: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  if (steps.length === 0) return null;

  return (
    <div className="agent-steps">
      <div className="agent-steps__header">
        <span className="agent-steps__label">Agent 执行详情</span>
        <span className="agent-steps__count">{steps.length} 步</span>
      </div>
      <div className="agent-steps__list">
        {steps.map((step, idx) => {
          const isExpanded = expanded.has(idx);
          const isLast = idx === steps.length - 1;
          const color = AGENT_COLORS[step.agent] || '#71717a';
          
          return (
            <div
              key={idx}
              className={`agent-steps__item ${step.status} ${isLast ? 'agent-steps__item--latest' : ''}`}
              onClick={() => toggleExpand(idx)}
            >
              <div className="agent-steps__row">
                <span
                  className="agent-steps__agent"
                  style={{ color }}
                >
                  {step.agent}
                </span>
                <span className="agent-steps__action">{step.action}</span>
                <span className="agent-steps__time">
                  {new Date(step.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </span>
                <span className="agent-steps__arrow">{isExpanded ? '▼' : '▶'}</span>
              </div>
              {isExpanded && (
                <div className="agent-steps__detail">
                  <pre>{step.detail}</pre>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

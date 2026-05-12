import React from 'react';

interface Stage {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'error';
}

interface TaskProgressProps {
  stages: Stage[];
  currentStage: number;
}

const STAGE_ICONS: Record<string, string> = {
  '需求分析': '📋',
  '方案设计': '🏗️',
  '代码编写': '💻',
  '代码审查': '👀',
  '测试执行': '🧪',
};

export function TaskProgress({ stages, currentStage }: TaskProgressProps) {
  return (
    <div className="task-progress">
      <div className="task-progress__header">
        <span className="task-progress__label">任务进度</span>
        <span className="task-progress__count">
          {stages.filter(s => s.status === 'completed').length} / {stages.length}
        </span>
      </div>
      <div className="task-progress__bar">
        {stages.map((stage, idx) => {
          const isActive = idx === currentStage;
          const isCompleted = stage.status === 'completed';
          const isError = stage.status === 'error';
          
          return (
            <div
              key={stage.name}
              className={`task-progress__stage ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isError ? 'error' : ''}`}
            >
              <div className="task-progress__dot">
                {isCompleted ? '✓' : isError ? '✗' : STAGE_ICONS[stage.name] || '○'}
              </div>
              <span className="task-progress__name">{stage.name}</span>
              {isActive && <div className="task-progress__pulse" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}

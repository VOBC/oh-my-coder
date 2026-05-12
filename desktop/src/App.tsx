// src/App.tsx — Oh My Coder Desktop MVP
// Design: Terminal Forge — dark industrial, amber accents, precision UI
import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import { getKeyboardShortcutsController } from './controllers/KeyboardShortcutsController';
import { useChatHistory } from './hooks/useChatHistory';
import HistoryPanel from './components/HistoryPanel';
import DiffView, { FileDiff, DiffLine } from './components/DiffView';
import { ModelSelector } from './components/ModelSelector';
import { ShortcutsPanel } from './components/ShortcutsPanel';
import { InlineInputPanel } from './components/InlineInputPanel';
import SettingsPanel from './components/SettingsPanel';
import { PRODUCTION_MODELS as FALLBACK_MODELS } from './models/productionModels';
import WelcomeScreen from './components/WelcomeScreen';
import { VoiceInput } from './components/VoiceInput';
import { TaskProgress } from './components/TaskProgress';
import { AgentSteps } from './components/AgentSteps';
import { LiveLog } from './components/LiveLog';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Model { id: string; name: string; provider: string; tier: string; context?: number; endpoint?: string; pricing?: Record<string, number>; features?: string[]; }
interface Message { id: string; role: 'user' | 'assistant' | 'system'; content: string; timestamp: number; }

// ── Agent Status Types ────────────────────────────────────────────────────────
type AgentName = 'Planner' | 'Coder' | 'Reviewer' | 'Executor' | 'Idle';
type AgentStatus = '分析中' | '编码中' | '测试中' | '审查中' | '执行中' | '已完成' | '待机中';

interface AgentState {
  name: AgentName;
  status: AgentStatus;
  color: string;
  icon: string;
}

const AGENT_CONFIG: Record<AgentName, { color: string; icon: string; statuses: AgentStatus[] }> = {
  Planner:   { color: '#60a5fa', icon: '📋', statuses: ['分析中', '已完成'] },
  Coder:     { color: '#4ade80', icon: '💻', statuses: ['编码中', '测试中', '已完成'] },
  Reviewer:  { color: '#c084fc', icon: '👀', statuses: ['审查中', '已完成'] },
  Executor:  { color: '#f59e0b', icon: '⚡', statuses: ['执行中', '已完成'] },
  Idle:      { color: '#71717a', icon: '💤', statuses: ['待机中'] },
};

// ── Diff Parsing ──────────────────────────────────────────────────────────────
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

// ── Tier display config ───────────────────────────────────────────────────────
const TIER_ICON: Record<string, string> = { free: '◈', low: '◇', medium: '◆', high: '★' };
const TIER_COLOR: Record<string, string> = { free: '#4ade80', low: '#94a3b8', medium: '#d4a017', high: '#f59e0b' };

// ── API helpers ────────────────────────────────────────────────────────────────
declare global { interface Window { omc: any; } }

/** Get the omc API (from preload contextBridge). Returns null when not available. */
function api(): any {
  return window.omc ?? null;
}

// ── Component: ChatMessage ──────────────────────────────────────────────────────
interface ChatMessageProps {
  msg: Message;
  onDiffAccept?: (path: string) => void;
  onDiffReject?: (path: string) => void;
}

function ChatMessage({ msg, onDiffAccept, onDiffReject }: ChatMessageProps) {
  const isUser = msg.role === 'user';
  const [pendingDiff, setPendingDiff] = useState<FileDiff | null>(null);

  // Parse diff from message content
  useEffect(() => {
    if (msg.role === 'assistant') {
      const diff = parseDiffFromMessage(msg.content);
      if (diff) setPendingDiff(diff);
    }
  }, [msg.content]);

  return (
    <div className={`message message--${msg.role}`}>
      <div className="message__avatar">
        {isUser ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="8" r="4" stroke="#d4a017" strokeWidth="2"/><path d="M4 20c0-4 4-6 8-6s8 2 8 6" stroke="#d4a017" strokeWidth="2" strokeLinecap="round"/></svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="4" stroke="#4ade80" strokeWidth="2"/><path d="M8 12h8M12 8v8" stroke="#4ade80" strokeWidth="2" strokeLinecap="round"/></svg>
        )}
      </div>
      <div className="message__body">
        <div className="message__content">
          {msg.content.split('\n').map((line, i) => (
            <React.Fragment key={i}>{line}{i < msg.content.split('\n').length - 1 && <br/>}</React.Fragment>
          ))}
        </div>
        {/* Diff visualization */}
        {pendingDiff && (
          <DiffView
            diff={pendingDiff}
            onAccept={onDiffAccept}
            onReject={onDiffReject}
          />
        )}
        <div className="message__time">{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
      </div>
    </div>
  );
}

// ── Component: AgentStatusBar ─────────────────────────────────────────────────
function AgentStatusBar({ agent, loading }: { agent: AgentState; loading: boolean }) {
  const config = AGENT_CONFIG[agent.name];
  const isActive = loading && agent.name !== 'Idle';

  return (
    <div className="agent-status-bar">
      <div className="agent-status-bar__label">
        <span className="agent-status-bar__pulse" style={{ background: config.color }} />
        多 Agent 协作
      </div>
      <div className="agent-status-bar__agents">
        {(Object.keys(AGENT_CONFIG) as AgentName[]).filter(n => n !== 'Idle').map(name => {
          const cfg = AGENT_CONFIG[name];
          const isCurrent = agent.name === name;
          return (
            <div
              key={name}
              className={`agent-status-bar__item ${isCurrent ? 'active' : ''} ${isCurrent && isActive ? 'animating' : ''}`}
              style={{ '--agent-color': cfg.color } as React.CSSProperties}
            >
              <span className="agent-status-bar__icon">{cfg.icon}</span>
              <span className="agent-status-bar__name">{name}</span>
              {isCurrent && (
                <span className="agent-status-bar__badge" style={{ background: cfg.color }}>
                  {agent.status}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Component: ConfigPanel ──────────────────────────────────────────────────────
interface ApiKeyEntry { model: string; displayName?: string; apiKey: string; isCustom?: boolean; isFree?: boolean; }

function ConfigPanel({ onClose, models }: { onClose: () => void; models: Model[] }) {
  const [entries, setEntries] = useState<ApiKeyEntry[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [toast, setToast] = useState<{msg: string; type: 'success'|'error'} | null>(null);
  const [confirmClose, setConfirmClose] = useState(false);

  // Initialize from localStorage + omc models
  useEffect(() => {
    const saved = localStorage.getItem('omc-api-keys');
    const savedEntries: ApiKeyEntry[] = saved ? JSON.parse(saved) : [];
    
    // Build entries from omc models (display name, store id)
    const modelEntries: ApiKeyEntry[] = models.map(m => {
      const savedEntry = savedEntries.find(e => e.model === m.id);
      return {
        model: m.id,          // unique key (id)
        displayName: m.name,  // display label (Chinese name)
        apiKey: savedEntry?.apiKey || '',
        isFree: m.tier === 'free'
      };
    });
    
    // Add custom entries not in models
    const customEntries = savedEntries.filter(e => !models.some(m => m.id === e.model));
    
    setEntries([...modelEntries, ...customEntries]);
  }, [models]);

  const updateEntry = (index: number, apiKey: string) => {
    setEntries(prev => prev.map((e, i) => i === index ? { ...e, apiKey } : e));
    setHasUnsavedChanges(true);
  };

  const removeEntry = (index: number) => {
    setEntries(prev => prev.filter((_, i) => i !== index));
    setHasUnsavedChanges(true);
  };

  const addCustomEntry = () => {
    setEntries(prev => [...prev, { model: '', apiKey: '', isCustom: true }]);
    setHasUnsavedChanges(true);
  };

  const updateCustomModel = (index: number, model: string) => {
    setEntries(prev => prev.map((e, i) => i === index ? { ...e, model } : e));
    setHasUnsavedChanges(true);
  };

  const handleSave = () => {
    // Validate: non-empty keys should start with sk-
    const invalid = entries.filter(e => e.apiKey && !e.apiKey.startsWith('sk-'));
    if (invalid.length > 0) {
      setToast({ msg: 'Invalid API Key format (should start with sk-)', type: 'error' });
      setTimeout(() => setToast(null), 3000);
      return;
    }
    
    // Save to localStorage
    localStorage.setItem('omc-api-keys', JSON.stringify(entries));
    setHasUnsavedChanges(false);
    setToast({ msg: 'Configuration saved', type: 'success' });
    setTimeout(() => setToast(null), 2000);
  };

  const handleClose = () => {
    if (hasUnsavedChanges && !confirmClose) {
      setConfirmClose(true);
      return;
    }
    onClose();
  };

  const uiText = {
    settings: 'Settings',
    apiKeys: 'API Keys',
    about: 'About',
    addCustom: '+ Add Custom Model',
    save: 'Save Configuration',
    unsavedTitle: 'Unsaved Changes',
    unsavedMsg: 'You have unsaved changes. Leave without saving?',
    leave: 'Leave',
    cancel: 'Cancel',
    optional: 'optional',
    modelName: 'Model name'
  };

  return (
    <div className="config-panel">
      <div className="config-panel__header">
        <span className="config-panel__title">⚙ {uiText.settings}</span>
        <button className="config-panel__close" onClick={handleClose}>✕</button>
      </div>
      
      <div className="config-panel__body">
        <div className="config-section">
          <div className="config-section__label">{uiText.apiKeys}</div>
          
          {entries.map((entry, idx) => (
            <div className="config-entry" key={`${entry.model}-${idx}`}>
              <div className="config-entry__header">
                {entry.isCustom ? (
                  <input
                    type="text"
                    className="config-entry__model-input"
                    value={entry.model}
                    placeholder={uiText.modelName}
                    onChange={e => updateCustomModel(idx, e.target.value)}
                  />
                ) : (
                  <span className="config-entry__model">
                    {entry.displayName || entry.model}
                    {entry.isFree && <span className="config-entry__free"> (Free)</span>}
                  </span>
                )}
                <button 
                  className="config-entry__remove" 
                  onClick={() => removeEntry(idx)}
                  title="Remove"
                >
                  −
                </button>
              </div>
              <input
                type="password"
                className="config-entry__input"
                value={entry.apiKey}
                placeholder={entry.isFree ? uiText.optional : 'sk-...'}
                onChange={e => updateEntry(idx, e.target.value)}
              />
            </div>
          ))}
          
          <button className="config-add-btn" onClick={addCustomEntry}>
            {uiText.addCustom}
          </button>
        </div>
        
        <div className="config-section">
          <div className="config-section__label">{uiText.about}</div>
          <div className="config-about">
            <div className="config-about__row"><span>Oh My Coder</span><span>v0.1.0</span></div>
            <div className="config-about__row"><span>Platform</span><span>{navigator.platform}</span></div>
            <div className="config-about__row"><span>API</span><span>window.omc (IPC)</span></div>
          </div>
        </div>
        
        <button 
          className={`config-save-btn${hasUnsavedChanges ? ' unsaved' : ''}`}
          onClick={handleSave}
        >
          💾 {uiText.save}
        </button>
      </div>
      
      {toast && (
        <div className={`config-toast ${toast.type}`}>
          {toast.type === 'success' ? '✓' : '✗'} {toast.msg}
        </div>
      )}
      
      {confirmClose && (
        <div className="config-confirm-overlay">
          <div className="config-confirm">
            <div className="config-confirm__title">{uiText.unsavedTitle}</div>
            <div className="config-confirm__msg">{uiText.unsavedMsg}</div>
            <div className="config-confirm__actions">
              <button className="config-confirm__leave" onClick={onClose}>{uiText.leave}</button>
              <button className="config-confirm__cancel" onClick={() => setConfirmClose(false)}>{uiText.cancel}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────────
export default function App() {
  const [models, setModels] = useState<Model[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [serverStatus, setServerStatus] = useState<'stopped' | 'starting' | 'running'>('stopped');
  const [tab, setTab] = useState<'chat' | 'models'>('chat');
  const [agentState, setAgentState] = useState<AgentState>({ name: 'Idle', status: '待机中', color: '#71717a', icon: '💤' });
  
  // Task progress state
  const [taskStages, setTaskStages] = useState([
    { name: '需求分析', status: 'pending' as const },
    { name: '方案设计', status: 'pending' as const },
    { name: '代码编写', status: 'pending' as const },
    { name: '代码审查', status: 'pending' as const },
    { name: '测试执行', status: 'pending' as const },
  ]);
  const [currentStage, setCurrentStage] = useState(0);
  
  // Agent steps state
  const [agentSteps, setAgentSteps] = useState<Array<{
    agent: string;
    action: string;
    detail: string;
    timestamp: number;
    status: 'running' | 'completed' | 'error';
  }>>([]);
  
  // Live log state
  const [liveLogs, setLiveLogs] = useState<Array<{
    level: 'info' | 'warn' | 'error' | 'success';
    message: string;
    timestamp: number;
  }>>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Use chat history hook for persistence
  const {
    sessions,
    activeId,
    activeMessages,
    // activeModel, // unused - model tracked by currentModel state
    createSession,
    switchSession,
    addMessage,
    updateModel,
    deleteSession,
    renameSession,
    exportSession,
    clearAllSessions,
    // clearActive, // unused after removing Cmd+L clear chat
  } = useChatHistory();

  // Track open overlays/popups for Esc to close
  const [modelSelectorOpen, setModelSelectorOpen] = useState(false);
  const [shortcutsPanelOpen, setShortcutsPanelOpen] = useState(false);
  const [inlineInputOpen, setInlineInputOpen] = useState(false);

  // Initialize keyboard shortcuts controller
  useEffect(() => {
    const controller = getKeyboardShortcutsController();

    // Cmd+L: Focus input ("Focus sidebar chat")
    controller.register('focus-input', {
      key: 'l',
      metaKey: true,
      description: '聚焦输入框',
      handler: () => {
        inputRef.current?.focus();
        console.log('[Shortcuts] Input focused');
      },
    });

    // Cmd+K: Inline input (Cursor mode)
    controller.register('inline-edit', {
      key: 'k',
      metaKey: true,
      description: '内联输入',
      handler: () => {
        setInlineInputOpen(v => !v);
        console.log('[Shortcuts] Inline input toggled');
      },
    });

    // Cmd+M: Toggle model selector
    controller.register('model-selector', {
      key: 'm',
      metaKey: true,
      description: '切换模型',
      handler: () => {
        setModelSelectorOpen(v => !v);
        console.log('[Shortcuts] Model selector toggled');
      },
    });

    // Cmd+N: New chat
    controller.register('new-chat', {
      key: 'n',
      metaKey: true,
      description: '新建会话',
      handler: () => {
        createSession(currentModel);
        inputRef.current?.focus();
        console.log('[Shortcuts] New chat started');
      },
    });

    // Cmd+Shift+S: Open Settings
    controller.register('settings-shift', {
      key: 's',
      metaKey: true,
      shiftKey: true,
      description: '打开设置',
      handler: () => {
        setShowConfig(true);
        console.log('[Shortcuts] Settings opened (Cmd+Shift+S)');
      },
    });

    // Cmd+,: Open Settings (VS Code standard)
    controller.register('settings-comma', {
      key: ',',
      metaKey: true,
      description: '打开设置',
      handler: () => {
        setShowConfig(true);
        console.log('[Shortcuts] Settings opened (Cmd+,)');
      },
    });

    // Esc: Close all overlays/popups
    controller.register('escape', {
      key: 'Escape',
      standalone: true,
      description: '关闭所有浮层',
      handler: () => {
        setModelSelectorOpen(false);
        setShowConfig(false);
        setShowHistory(false);
        setShortcutsPanelOpen(false);
        setInlineInputOpen(false);
        console.log('[Shortcuts] All overlays closed');
      },
    });

    // Cmd+/: Show shortcuts panel
    controller.register('shortcuts-panel', {
      key: '/',
      metaKey: true,
      description: '显示快捷键',
      handler: () => {
        setShortcutsPanelOpen(v => !v);
        console.log('[Shortcuts] Shortcuts panel toggled');
      },
    });

    controller.start();

    return () => {
      controller.dispose();
    };
  }, [currentModel, createSession]);

  // Fallback models imported from productionModels.ts (single source of truth)

  // Load
  useEffect(() => {
    const omcApi = api();
    if (!omcApi) {
      // Standalone Vite mode: use fallback models
      console.warn('[App] omc API not available — using fallback model list');
      setModels(FALLBACK_MODELS);
      const fallbackModel = FALLBACK_MODELS[0]?.id ?? '';
      if (!currentModel) setCurrentModel(fallbackModel);
      // Auto-create session if none exists (for standalone Vite demo)
      if (!activeId && fallbackModel) {
        createSession(fallbackModel);
      }
      return;
    }
    omcApi.modelList().then((data: any) => {
      if (data?.models?.length) setModels(data.models);
      else if (Array.isArray(data)) setModels(data);
    }).catch((e: any) => {
      console.error('[App] modelList failed, falling back:', e);
      setModels(FALLBACK_MODELS);
    });
    omcApi.modelCurrent().then((m: any) => {
      if (typeof m === 'string' && m) setCurrentModel(m);
      else if (m?.model) setCurrentModel(m.model);
    }).catch(() => {});
    // omcApi.historyList().then(setHistory).catch(() => {});
    // Note: Using localStorage-based useChatHistory instead
    omcApi.serverStatus().then((s: any) => setServerStatus(s.running ? 'running' : 'stopped')).catch(() => {});
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [activeMessages]);

  // Agent status simulation — cycles through agents when loading
  useEffect(() => {
    if (!loading) {
      setAgentState({ name: 'Idle', status: '待机中', color: '#71717a', icon: '💤' });
      // Reset task progress
      setTaskStages(prev => prev.map((s, i) => ({ ...s, status: i === 0 ? 'pending' : 'pending' })));
      setCurrentStage(0);
      return;
    }

    const agents: AgentName[] = ['Planner', 'Coder', 'Reviewer', 'Executor'];
    let idx = 0;

    // Start with Planner
    const startAgent = agents[0];
    const startCfg = AGENT_CONFIG[startAgent];
    setAgentState({ name: startAgent, status: startCfg.statuses[0], color: startCfg.color, icon: startCfg.icon });
    
    // Update task progress - mark first stage active
    setTaskStages(prev => prev.map((s, i) => ({ ...s, status: i === 0 ? 'active' : 'pending' })));
    setCurrentStage(0);
    
    // Add initial log
    setLiveLogs(prev => [...prev, {
      level: 'info',
      message: '任务开始执行...',
      timestamp: Date.now(),
    }]);

    const interval = setInterval(() => {
      idx = (idx + 1) % agents.length;
      const name = agents[idx];
      const cfg = AGENT_CONFIG[name];
      setAgentState({ name, status: cfg.statuses[0], color: cfg.color, icon: cfg.icon });
      
      // Update task progress
      const stageIdx = Math.min(idx, taskStages.length - 1);
      setTaskStages(prev => prev.map((s, i) => ({
        ...s,
        status: i < stageIdx ? 'completed' : i === stageIdx ? 'active' : 'pending'
      })));
      setCurrentStage(stageIdx);
      
      // Add agent step
      const actions = ['分析需求', '编写代码', '审查代码', '执行测试'];
      setAgentSteps(prev => [...prev, {
        agent: name,
        action: actions[idx % actions.length],
        detail: `${name} 正在${actions[idx % actions.length]}...`,
        timestamp: Date.now(),
        status: 'running',
      }]);
      
      // Add log
      setLiveLogs(prev => [...prev, {
        level: 'info',
        message: `${name} ${actions[idx % actions.length]}`,
        timestamp: Date.now(),
      }]);
    }, 2500);

    return () => clearInterval(interval);
  }, [loading]);

  // Diff acceptance/rejection
  const [diffFiles, setDiffFiles] = useState<Map<string, { old: string; new_: string }>>(new Map());

  const handleDiffAccept = useCallback(async (path: string) => {
    const diffData = diffFiles.get(path);
    if (!diffData) {
      console.warn('[Diff] No diff data for:', path);
      return;
    }
    try {
      // Write the new content to file
      const result = await api().fileWrite(path, diffData.new_);
      if (result.ok) {
        console.log('[Diff] File accepted:', path);
        // Remove from pending diffs
        setDiffFiles(prev => {
          const next = new Map(prev);
          next.delete(path);
          return next;
        });
      } else {
        console.error('[Diff] Write failed:', result.error);
      }
    } catch (e: any) {
      console.error('[Diff] Accept error:', e.message);
    }
  }, [diffFiles]);

  const handleDiffReject = useCallback((path: string) => {
    console.log('[Diff] File rejected:', path);
    setDiffFiles(prev => {
      const next = new Map(prev);
      next.delete(path);
      return next;
    });
  }, []);

  const handleSwitch = async (id: string) => {
    setCurrentModel(id);
    updateModel(id);
    await api().modelSwitch(id);
  };

  const handleSendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text.trim(),
      timestamp: Date.now(),
    };
    if (!activeId) { createSession(currentModel); }
    addMessage(userMsg);
    setLoading(true);

    try {
      const omcApi = api();
      if (!omcApi) {
        addMessage({
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Error: omc API not available. Please run in Electron or check preload.',
          timestamp: Date.now(),
        });
        setLoading(false);
        return;
      }

      // Quick fix: use direct LLM API call instead of `omc run`
      // Get API key + endpoint for current model from SettingsPanel encrypted storage
      let endpoint = '';
      let apiKey = '';
      try {
        const stored = localStorage.getItem('omc-model-configs');
        if (stored) {
          // XOR decrypt (same as SettingsPanel.tsx)
          const decoded = atob(stored);
          let decrypted = '';
          const key = 'omc-v1-key-2024';
          for (let i = 0; i < decoded.length; i++) {
            decrypted += String.fromCharCode(decoded.charCodeAt(i) ^ key.charCodeAt(i % key.length));
          }
          const configs = JSON.parse(decrypted);
          const cfg = configs[currentModel] || {};
          endpoint = cfg.endpoint || '';
          apiKey = cfg.api_key || '';
        }
        if (!apiKey) {
          // Fallback: legacy unencrypted omc-api-keys
          const saved = localStorage.getItem('omc-api-keys');
          if (saved) {
            const entries = JSON.parse(saved);
            const entry = entries.find(e => e.model === currentModel);
            if (entry) apiKey = entry.apiKey;
          }
        }
      } catch (e) { /* silently ignore config read errors */ }

      // Fallback endpoint for common providers
      const DEFAULT_ENDPOINTS: Record<string, string> = {
        'glm': 'https://open.bigmodel.cn/api/paas/v4',
        'deepseek': 'https://api.deepseek.com/v1',
        'kimi': 'https://api.moonshot.cn/v1',
        'doubao': 'https://ark.cn-beijing.volces.com/api/v3',
        'minimax': 'https://api.minimax.chat/v1',
        'baichuan': 'https://api.baichuan-ai.com/v1',
      };
      if (!endpoint) {
        const provider = currentModel?.split('-')[0] || '';
        endpoint = DEFAULT_ENDPOINTS[provider] || '';
      }

      const result = await omcApi.chatDirect({ endpoint, model: currentModel, apiKey, message: text.trim() });

      // Parse SSE stream output to extract plain text content
      let parsedContent = '';
      if (result.stdout) {
        const lines = result.stdout.split('\n');
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed.startsWith(':') || trimmed === '[DONE]') continue;
          if (trimmed.startsWith('data: ')) {
            try {
              const json = JSON.parse(trimmed.slice(6));
              const delta = json.choices?.[0]?.delta?.content;
              if (delta) parsedContent += delta;
            } catch { /* skip malformed JSON */ }
          }
        }
      }

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: parsedContent || result.stderr || (result.code === 0 ? '(empty response)' : `Error: exit code ${result.code}`),
        timestamp: Date.now(),
      };
      addMessage(assistantMsg);
    } catch (e: any) {
      addMessage({
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${e.message}`,
        timestamp: Date.now(),
      });
    } finally {
      setLoading(false);
    }
  }, [loading, currentModel, addMessage]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput('');
    await handleSendMessage(text);
  }, [input, loading, handleSendMessage]);

  const handleExampleClick = useCallback(async (task: string) => {
    if (loading) return;
    await handleSendMessage(task);
  }, [loading, handleSendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleServerToggle = async () => {
    if (serverStatus === 'running') {
      await api().serverStop();
      setServerStatus('stopped');
    } else {
      setServerStatus('starting');
      await api().serverStart();
      setServerStatus('running');
    }
  };

  const handleHistorySelect = (id: string) => {
    switchSession(id);
    setShowHistory(false);
  };

  const handleHistoryDelete = (id: string) => {
    deleteSession(id);
  };

  const handleHistoryNew = () => {
    createSession(currentModel);
    setShowHistory(false);
  };

  const handleHistoryRename = (id: string, newTitle: string) => {
    renameSession(id, newTitle);
  };

  const handleHistoryExport = (id: string) => {
    const json = exportSession(id);
    if (!json) return;
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chat-${id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleHistoryClearAll = () => {
    if (window.confirm('Delete all chat history? This cannot be undone.')) {
      clearAllSessions();
    }
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className={`sidebar ${showHistory ? 'sidebar--open' : ''}`}>
        <div className="sidebar__header">
          <span className="sidebar__logo">⬡ OMC</span>
          <button className="sidebar__btn" onClick={() => setShowHistory(v => !v)} title="History">
            {showHistory ? '◀' : '☰'}
          </button>
        </div>

        {/* History panel */}
        {showHistory ? (
          <HistoryPanel
            sessions={sessions}
            activeId={activeId}
            onSelect={handleHistorySelect}
            onDelete={handleHistoryDelete}
            onNew={handleHistoryNew}
            onRename={handleHistoryRename}
            onExport={handleHistoryExport}
            onClearAll={handleHistoryClearAll}
          />
        ) : (
          <>
            {/* Tab nav */}
            <div className="sidebar__tabs">
              <button className={`sidebar__tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>Chat</button>
              <button className={`sidebar__tab ${tab === 'models' ? 'active' : ''}`} onClick={() => setTab('models')}>Models</button>
            </div>

            {tab === 'models' ? (
              <div className="sidebar__models">
                {models.map(m => (
                  <button
                    key={m.id}
                    className={`sidebar__model ${m.id === currentModel ? 'active' : ''}`}
                    onClick={() => handleSwitch(m.id)}
                  >
                    <span style={{ color: TIER_COLOR[m.tier] }}>{TIER_ICON[m.tier]}</span>
                    <span>{m.name}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="sidebar__models">
                <button className="sidebar__new-chat" onClick={() => createSession(currentModel)}>+ New Chat</button>
              </div>
            )}

            {/* Settings */}
            <div className="sidebar__footer">
              <button className="sidebar__settings" onClick={() => setShowConfig(true)}>
                ⚙ Settings
              </button>
              <button className="sidebar__shortcuts" onClick={() => setShortcutsPanelOpen(true)}>
                ⌨ 快捷键
              </button>
            </div>
          </>
        )}
      </aside>

      {/* Main */}
      <main className="main">
        {/* Top bar */}
        <div className="topbar">
          <ModelSelector
            models={models}
            current={currentModel}
            onSwitch={handleSwitch}
            open={modelSelectorOpen}
            onOpenChange={setModelSelectorOpen}
            trigger={
              <div className="topbar__model-badge topbar__model-badge--clickable">
                <span style={{ color: TIER_COLOR[models.find(m => m.id === currentModel)?.tier || 'free'] }}>
                  {TIER_ICON[models.find(m => m.id === currentModel)?.tier || 'free']}
                </span>
                <span className="topbar__model-name">
                  {models.find(m => m.id === currentModel)?.name || currentModel}
                </span>
                <span className="topbar__model-caret">▼</span>
              </div>
            }
          />
        </div>

        {/* Agent Status Bar */}
        <AgentStatusBar agent={agentState} loading={loading} />

        {/* Task Progress */}
        {loading && <TaskProgress stages={taskStages} currentStage={currentStage} />}

        {/* Agent Steps */}
        {loading && <AgentSteps steps={agentSteps} />}

        {/* Live Log */}
        {loading && <LiveLog logs={liveLogs} />}

        {/* Messages */}
        <div className="messages">
          {activeMessages.length === 0 && (
            <WelcomeScreen onExampleClick={handleExampleClick} />
          )}
          {activeMessages.map(msg => (
            <ChatMessage
              key={msg.id}
              msg={msg}
              onDiffAccept={handleDiffAccept}
              onDiffReject={handleDiffReject}
            />
          ))}
          {loading && (
            <div className="message message--assistant">
              <div className="message__avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="4" stroke="#4ade80" strokeWidth="2"/><path d="M8 12h8M12 8v8" stroke="#4ade80" strokeWidth="2" strokeLinecap="round"/></svg>
              </div>
              <div className="message__body">
                <div className="message__content typing"><span/><span/><span/></div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="input-area">
          <div className="input-area__wrap">
            <textarea
              ref={inputRef}
              className="input-area__input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask omc to do anything..."
              rows={1}
              disabled={loading}
            />
            <VoiceInput
              onResult={(text) => setInput(prev => prev ? prev + ' ' + text : text)}
              disabled={loading}
            />
            <button className="input-area__send" onClick={handleSend} disabled={loading || !input.trim()}>
              {loading ? '◐' : '↑'}
            </button>
          </div>
          <div className="input-area__hint">omc · desktop MVP · {currentModel}</div>
        </div>
      </main>

      {/* Config modal */}
      {showConfig && <SettingsPanel onClose={() => setShowConfig(false)} />}
      
      {/* Shortcuts panel */}
      <ShortcutsPanel 
        isOpen={shortcutsPanelOpen} 
        onClose={() => setShortcutsPanelOpen(false)} 
      />
      
      {/* Inline input (Cursor mode) */}
      <InlineInputPanel
        isOpen={inlineInputOpen}
        onClose={() => setInlineInputOpen(false)}
        onSend={(msg) => {
          setInput('');
          handleSendMessage(msg);
        }}
        currentModel={currentModel}
      />
    </div>
  );
}

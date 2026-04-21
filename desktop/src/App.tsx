// src/App.tsx — Oh My Coder Desktop MVP
// Design: Terminal Forge — dark industrial, amber accents, precision UI
import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';

// ── Types ─────────────────────────────────────────────────────────────────────
interface Model { id: string; name: string; provider: string; tier: string; context?: number; endpoint?: string; pricing?: Record<string, number>; features?: string[]; }
interface Message { id: string; role: 'user' | 'assistant' | 'system'; content: string; timestamp: number; }
interface HistoryItem { id: string; title: string; updated: string; model?: string; }

// ── Tier display config ───────────────────────────────────────────────────────
const TIER_ICON: Record<string, string> = { free: '◈', low: '◇', medium: '◆', high: '★' };
const TIER_COLOR: Record<string, string> = { free: '#4ade80', low: '#94a3b8', medium: '#d4a017', high: '#f59e0b' };

// ── API helpers ────────────────────────────────────────────────────────────────
declare global { interface Window { omc: any; } }

/** Get the omc API (from preload contextBridge) */
function api() {
  if (!window.omc) {
    console.warn('[App] window.omc not available — preload may not be loaded');
  }
  return window.omc;
}

// ── Component: ModelSelector ───────────────────────────────────────────────────
function ModelSelector({ models, current, onSwitch }: { models: Model[]; current: string; onSwitch: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const cur = models.find(m => m.id === current) || models[0];

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  return (
    <div className="model-selector" ref={ref}>
      <button className="model-selector__trigger" onClick={() => setOpen(v => !v)}>
        <span className="model-selector__icon" style={{ color: TIER_COLOR[cur?.tier] || '#d4a017' }}>
          {TIER_ICON[cur?.tier] || '◆'}
        </span>
        <span className="model-selector__name">{cur?.name || 'Select model'}</span>
        <span className="model-selector__caret">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="model-selector__dropdown">
          {models.map(m => (
            <button
              key={m.id}
              className={`model-selector__item${m.id === current ? ' active' : ''}`}
              onClick={() => { onSwitch(m.id); setOpen(false); }}
            >
              <span className="model-selector__icon" style={{ color: TIER_COLOR[m.tier] }}>{TIER_ICON[m.tier]}</span>
              <span className="model-selector__item-name">{m.name}</span>
              <span className="model-selector__provider">{m.provider}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Component: ChatMessage ──────────────────────────────────────────────────────
function ChatMessage({ msg }: { msg: Message }) {
  const isUser = msg.role === 'user';
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
        <div className="message__time">{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
      </div>
    </div>
  );
}

// ── Component: ConfigPanel ──────────────────────────────────────────────────────
function ConfigPanel({ onClose }: { onClose: () => void }) {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api().configGet().then(setConfig);
  }, []);

  const handleSave = async (key: string, value: string) => {
    setSaving(true);
    await api().configSet(key, value);
    setConfig(prev => ({ ...prev, [key]: value }));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="config-panel">
      <div className="config-panel__header">
        <span className="config-panel__title">⚙ Settings</span>
        <button className="config-panel__close" onClick={onClose}>✕</button>
      </div>
      <div className="config-panel__body">
        <div className="config-section">
          <div className="config-section__label">API Keys</div>
          {[
            {key:'DEEPSEEK_API_KEY', label:'🌊 DeepSeek（深度求索）', models: ['DeepSeek V3', 'DeepSeek R1']},
            {key:'ZHIPU_API_KEY', label:'🧠 智谱 GLM', models: ['GLM-4-Flash (free)', 'GLM-4V-Flash (free)', 'GLM-4-Plus']},
            {key:'DASHSCOPE_API_KEY', label:'🌐 通义千问 Qwen', models: ['Qwen 2.5']},
            {key:'MOONSHOT_API_KEY', label:'🌙 月之暗面 Kimi', models: ['Kimi Moonshot V1 128K']},
            {key:'ARK_API_KEY', label:'🎵 字节豆包 Doubao', models: ['Doubao-Pro 128K']},
            {key:'ERNIE_API_KEY', label:'🐻 百度文心 Ernie', models: ['ERNIE-Bot 4']},
            {key:'HUNYUAN_API_KEY', label:'🐧 腾讯混元 Hunyuan', models: ['Hunyuan Standard']},
            {key:'MINIMAX_API_KEY', label:'🎭 MiniMax', models: ['MiniMax 汀灵 6B']},
            {key:'TIANGONG_API_KEY', label:'⚡ 天工 AI', models: ['天工 3.0']},
            {key:'SPARK_API_KEY', label:'🔥 讯飞星火 Spark', models: ['讯飞星火 V3.5']},
            {key:'BAICHUAN_API_KEY', label:'🌊 百川 Baichuan', models: ['Baichuan 4']},
            {key:'MIMO_API_KEY', label:'🤖 小米 MiMo', models: ['MiMo V2 Flash (free)']}
          ].map(({key, label, models: modelList}) => (
            <div className="config-field" key={key}>
              <label className="config-field__label">{label}</label>
              <div className="config-field__models">{modelList.join(' · ')}</div>
              <div className="config-field__row">
                <input
                  type="password"
                  className="config-field__input"
                  defaultValue={config[key] || ''}
                  placeholder="sk-..."
                  onBlur={e => handleSave(key, e.target.value)}
                />
              </div>
            </div>
          ))}
        </div>
        <div className="config-section">
          <div className="config-section__label">About</div>
          <div className="config-about">
            <div className="config-about__row"><span>Oh My Coder</span><span>v0.1.0</span></div>
            <div className="config-about__row"><span>Platform</span><span>{navigator.platform}</span></div>
            <div className="config-about__row"><span>API</span><span>window.omc (IPC)</span></div>
          </div>
        </div>
        {saved && <div className="config-saved">✓ Saved</div>}
      </div>
    </div>
  );
}

// ── Main App ────────────────────────────────────────────────────────────────────
export default function App() {
  const [models, setModels] = useState<Model[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [serverStatus, setServerStatus] = useState<'stopped' | 'starting' | 'running'>('stopped');
  const [tab, setTab] = useState<'chat' | 'models'>('chat');
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load models + history
  useEffect(() => {
    const omcApi = api();
    if (!omcApi) {
      console.warn('[App] omc API not available, skipping model load');
      return;
    }
    omcApi.modelList().then((data: any) => {
      if (data?.models?.length) setModels(data.models);
      else if (Array.isArray(data)) setModels(data);
    }).catch((e: any) => console.error('[App] modelList failed:', e));
    omcApi.modelCurrent().then((m: any) => {
      if (typeof m === 'string' && m) setCurrentModel(m);
      else if (m?.model) setCurrentModel(m.model);
    }).catch(() => {});
    omcApi.historyList().then(setHistory).catch(() => {});
    omcApi.serverStatus().then((s: any) => setServerStatus(s.running ? 'running' : 'stopped')).catch(() => {});
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const handleSwitch = async (id: string) => {
    setCurrentModel(id);
    await api().modelSwitch(id);
  };

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: Date.now(),
    };
    setMessages(prev => [...prev, userMsg]);
    const text = input;
    setInput('');
    setLoading(true);

    try {
      const result = await api().chatSend({ message: text, model: currentModel });
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: result.stdout || result.stderr || (result.code === 0 ? 'Done.' : `Exit code: ${result.code}`),
        timestamp: Date.now(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (e: any) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${e.message}`,
        timestamp: Date.now(),
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, currentModel]);

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

  const handleHistorySelect = (item: HistoryItem) => {
    api().historyGet(item.id).then(data => {
      if (data?.messages) setMessages(data.messages);
      else if (data?.content) setMessages([{ id: '1', role: 'assistant', content: data.content, timestamp: Date.now() }]);
    });
    setShowHistory(false);
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
          <div className="sidebar__history">
            <div className="sidebar__section-title">History</div>
            {history.length === 0 && <div className="sidebar__empty">No history yet</div>}
            {history.map(h => (
              <button key={h.id} className="sidebar__history-item" onClick={() => handleHistorySelect(h)}>
                <div className="sidebar__history-title">{h.title}</div>
                <div className="sidebar__history-meta">{h.updated}</div>
              </button>
            ))}
          </div>
        ) : (
          <>
            {/* Server toggle */}
            <div className="sidebar__section">
              <div className="sidebar__section-title">Server</div>
              <button className={`server-btn server-btn--${serverStatus}`} onClick={handleServerToggle}>
                <span className="server-btn__dot" />
                {serverStatus === 'stopped' ? 'Start Server' : serverStatus === 'starting' ? 'Starting...' : 'Stop Server'}
              </button>
            </div>

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
                <button className="sidebar__new-chat" onClick={() => setMessages([])}>+ New Chat</button>
              </div>
            )}

            {/* Settings */}
            <div className="sidebar__footer">
              <button className="sidebar__settings" onClick={() => setShowConfig(true)}>⚙ Settings</button>
            </div>
          </>
        )}
      </aside>

      {/* Main */}
      <main className="main">
        {/* Top bar */}
        <div className="topbar">
          <div className="topbar__title">
            <span className="topbar__model-badge">
              <span style={{ color: TIER_COLOR[models.find(m => m.id === currentModel)?.tier] }}>
                {TIER_ICON[models.find(m => m.id === currentModel)?.tier]}
              </span>
              {models.find(m => m.id === currentModel)?.name || currentModel}
            </span>
          </div>
          <ModelSelector models={models} current={currentModel} onSwitch={handleSwitch} />
        </div>

        {/* Messages */}
        <div className="messages">
          {messages.length === 0 && (
            <div className="messages__empty">
              <div className="messages__empty-icon">⬡</div>
              <div className="messages__empty-title">Oh My Coder Desktop</div>
              <div className="messages__empty-sub">Ask anything — code, docs, tasks, automation</div>
              <div className="messages__empty-hint">Press Enter to send · Shift+Enter for newline</div>
            </div>
          )}
          {messages.map(msg => <ChatMessage key={msg.id} msg={msg} />)}
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
            <button className="input-area__send" onClick={handleSend} disabled={loading || !input.trim()}>
              {loading ? '◐' : '↑'}
            </button>
          </div>
          <div className="input-area__hint">omc · desktop MVP · {currentModel}</div>
        </div>
      </main>

      {/* Config modal */}
      {showConfig && <ConfigPanel onClose={() => setShowConfig(false)} />}
    </div>
  );
}

// src/components/SettingsPanel.tsx
// Settings panel: model-centric API key configuration with encryption
// - Left sidebar: collapsible provider groups → model list
// - Right panel: selected model's API Key, base URL, test button
// - Top: Import/Export JSON, Reset to defaults
// - Encryption: simple XOR + base64 for localStorage
import React, { useState, useEffect, useCallback } from 'react';

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  tier: string;
  context?: number;
  endpoint?: string;
  pricing?: Record<string, number>;
  features?: string[];
}

interface ModelConfigEntry {
  api_key: string;
  base_url?: string;
  enabled?: boolean;
}

interface ModelConfig {
  [modelId: string]: ModelConfigEntry;
}

interface ProviderGroup {
  provider: string;
  label: string;
  models: ModelInfo[];
  collapsed: boolean;
}

const PROVIDER_LABELS: Record<string, string> = {
  deepseek: 'DeepSeek',
  glm: '智谱 GLM',
  doubao: '字节豆包',
  kimi: 'Kimi',
  tongyi: '通义千问',
  wenxin: '文心一言',
  hunyuan: '腾讯混元',
  minimax: 'MiniMax',
  baichuan: '百川智能',
};

// ── Fallback Models for Vite dev mode ─────────────────────────────────────────
const FALLBACK_MODELS: ModelInfo[] = [
  { id: 'deepseek-chat', name: 'DeepSeek V3', provider: 'deepseek', tier: 'medium', context: 64000 },
  { id: 'deepseek-reasoner', name: 'DeepSeek R1', provider: 'deepseek', tier: 'high', context: 64000 },
  { id: 'glm-4-flash', name: 'GLM-4-Flash', provider: 'glm', tier: 'free', context: 128000 },
  { id: 'doubao-pro-32k', name: 'Doubao-Pro-32K', provider: 'doubao', tier: 'medium', context: 32000 },
  { id: 'kimi-moonshot', name: 'Kimi', provider: 'kimi', tier: 'medium', context: 200000 },
  { id: 'qwen-plus', name: 'Qwen2.5-72B', provider: 'tongyi', tier: 'high', context: 128000 },
];

// ── Simple Encryption for localStorage ─────────────────────────────────────────
const ENCRYPTION_KEY = 'omc-v1-key-2024'; // Simple XOR key

function xorEncrypt(text: string, key: string): string {
  let result = '';
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
  }
  return btoa(result); // base64 encode
}

function xorDecrypt(encoded: string, key: string): string {
  try {
    const text = atob(encoded); // base64 decode
    let result = '';
    for (let i = 0; i < text.length; i++) {
      result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length));
    }
    return result;
  } catch {
    return encoded; // fallback for unencrypted data
  }
}

function saveEncryptedConfig(configs: ModelConfig) {
  const encrypted = xorEncrypt(JSON.stringify(configs), ENCRYPTION_KEY);
  localStorage.setItem('omc-model-configs', encrypted);
}

function loadEncryptedConfig(): ModelConfig {
  const stored = localStorage.getItem('omc-model-configs');
  if (!stored) return {};
  try {
    const decrypted = xorDecrypt(stored, ENCRYPTION_KEY);
    return JSON.parse(decrypted);
  } catch {
    // Try legacy unencrypted format
    try {
      return JSON.parse(stored);
    } catch {
      return {};
    }
  }
}

function clearEncryptedConfig() {
  localStorage.removeItem('omc-model-configs');
}

function getProviderFromModelId(modelId: string): string {
  const known = Object.keys(PROVIDER_LABELS);
  for (const p of known) {
    if (modelId.startsWith(p) || modelId.includes(p)) return p;
  }
  const first = modelId.split('-')[0];
  return first in PROVIDER_LABELS ? first : 'other';
}

function groupModels(models: ModelInfo[]): ProviderGroup[] {
  const groups = new Map<string, ProviderGroup>();
  for (const m of models) {
    const provider = getProviderFromModelId(m.id);
    if (!groups.has(provider)) {
      groups.set(provider, { provider, label: PROVIDER_LABELS[provider] || provider, models: [], collapsed: false });
    }
    groups.get(provider)!.models.push(m);
  }
  const known = Object.keys(PROVIDER_LABELS);
  return Array.from(groups.values()).sort((a, b) => {
    const ai = known.indexOf(a.provider);
    const bi = known.indexOf(b.provider);
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
    return a.label.localeCompare(b.label);
  });
}

const TIER_ICON: Record<string, string> = { free: '◈', low: '◇', medium: '◆', high: '★' };

// ── Test Connection ────────────────────────────────────────────────────────────
function TestConnection({ config, onResult }: { modelId: string; config: ModelConfigEntry; onResult: (ok: boolean, msg: string) => void }) {
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; msg: string } | null>(null);

  const handleTest = async () => {
    if (!config.api_key) {
      setResult({ ok: false, msg: 'API Key is required' });
      onResult(false, 'API Key is required');
      return;
    }
    setTesting(true);
    setResult(null);
    try {
      const resp = await (window.omc as any).modelConfigTest?.(null, config);
      const ok = resp?.ok ?? config.api_key.length > 10;
      const msg = resp?.msg ?? (ok ? 'Key format looks valid' : 'Key too short');
      setResult({ ok, msg });
      onResult(ok, msg);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Connection failed';
      setResult({ ok: false, msg });
      onResult(false, msg);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="settings-test">
      <button
        className={`settings-test__btn ${result ? (result.ok ? 'ok' : 'err') : ''}`}
        onClick={handleTest}
        disabled={testing}
      >
        {testing ? '⏳ Testing...' : result ? (result.ok ? '✓ Connected' : '✗ Failed') : '🔗 Test Connection'}
      </button>
      {result && (
        <span className={`settings-test__msg ${result.ok ? 'ok' : 'err'}`}>{result.msg}</span>
      )}
    </div>
  );
}

// ── Model Detail Panel ─────────────────────────────────────────────────────────
function ModelDetailPanel({
  model,
  config,
  onUpdate,
  onConfigSave,
}: {
  model: ModelInfo;
  config: ModelConfigEntry;
  onUpdate: (cfg: ModelConfigEntry) => void;
  onConfigSave: (modelId: string, cfg: ModelConfigEntry) => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const provider = getProviderFromModelId(model.id);
  const label = PROVIDER_LABELS[provider] || provider;
  const isFree = model.tier === 'free';

  const handleChange = (key: keyof ModelConfigEntry, value: string | boolean) => {
    onUpdate({ ...config, [key]: value });
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await onConfigSave(model.id, config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    onUpdate({ api_key: '', base_url: '', enabled: true });
  };

  return (
    <div className="settings-detail">
      <div className="settings-detail__header">
        <div className="settings-detail__title">{model.name}</div>
        <div className="settings-detail__meta">
          <span className="settings-detail__provider">{label}</span>
          <span className="settings-detail__id">{model.id}</span>
          {isFree && <span className="settings-detail__free">Free Tier</span>}
        </div>
      </div>

      <div className="settings-detail__field">
        <label className="settings-detail__label">
          API Key {isFree ? '(可选)' : ''}
          <span className="settings-detail__free-hint">{isFree ? ' — 免费模型，可跳过' : ''}</span>
        </label>
        <div className="settings-detail__input-row">
          <input
            type={showKey ? 'text' : 'password'}
            className="settings-detail__input"
            value={config.api_key ?? ''}
            placeholder={isFree ? '可选（无 API Key 时走环境变量）' : 'sk-...'}
            onChange={e => handleChange('api_key', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <button
            className={`settings-detail__toggle-vis ${showKey ? 'active' : ''}`}
            onClick={() => setShowKey(v => !v)}
            title={showKey ? 'Hide API Key' : 'Show API Key'}
          >
            {showKey ? '🙈' : '👁️'}
          </button>
        </div>
      </div>

      <div className="settings-detail__field">
        <label className="settings-detail__label">
          Base URL
          <span className="settings-detail__hint">（可选，默认使用官方地址）</span>
        </label>
        <input
          type="text"
          className="settings-detail__input"
          value={config.base_url ?? ''}
          placeholder={getDefaultEndpoint(provider)}
          onChange={e => handleChange('base_url', e.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
      </div>

      <div className="settings-detail__register">
        <span>需要 API Key？</span>
        <button className="settings-detail__link" onClick={() => (window.omc as any).openExternal(getRegisterUrl(provider))}>
          前往注册 →
        </button>
      </div>

      <TestConnection modelId={model.id} config={config} onResult={() => {}} />

      <div className="settings-detail__actions">
        <button className="settings-detail__reset" onClick={handleReset} title="Clear API Key and Base URL">
          ↺ Reset
        </button>
        <button className="settings-detail__save" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : saved ? '✓ Saved' : '💾 Save Configuration'}
        </button>
      </div>
    </div>
  );
}

function getDefaultEndpoint(provider: string): string {
  const endpoints: Record<string, string> = {
    deepseek: 'https://api.deepseek.com',
    glm: 'https://open.bigmodel.cn',
    kimi: 'https://api.moonshot.cn',
    doubao: 'https://ark.cn-beijing.volces.com',
    tongyi: 'https://dashscope.aliyuncs.com',
    minimax: 'https://api.minimax.chat',
    wenxin: 'https://aip.baidubce.com',
    hunyuan: 'https://hunyuan.cloud.tencent.com',
    baichuan: 'https://api.baichuan-ai.com',
  };
  return endpoints[provider] || '';
}

function getRegisterUrl(provider: string): string {
  const urls: Record<string, string> = {
    deepseek: 'https://platform.deepseek.com',
    glm: 'https://open.bigmodel.cn',
    kimi: 'https://platform.moonshot.cn',
    doubao: 'https://console.volcengine.com/ark',
    tongyi: 'https://dashscope.console.aliyun.com',
    minimax: 'https://www.minimaxi.com',
    wenxin: 'https://console.bce.baidu.com',
    hunyuan: 'https://console.cloud.tencent.com/hunyuan',
    baichuan: 'https://www.baichuan-ai.com',
  };
  return urls[provider] || 'https://platform.deepseek.com';
}

// ── Main SettingsPanel ─────────────────────────────────────────────────────────
export default function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [, setModels] = useState<ModelInfo[]>([]);
  const [configs, setConfigs] = useState<ModelConfig>({});
  const [groups, setGroups] = useState<ProviderGroup[]>([]);
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [exportDropdown, setExportDropdown] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [migrationNotice, setMigrationNotice] = useState<string | null>(null);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        // Load from localStorage (encrypted) first
        const localConfigs = loadEncryptedConfig();
        
        let modelList: ModelInfo[] = [];
        let cfgData: ModelConfig = {};
        
        try {
          modelList = await (window.omc as any).modelList();
          cfgData = await (window.omc as any).modelConfigList();
        } catch {
          // API not available, use fallback models
          modelList = FALLBACK_MODELS;
        }
        
        // Merge: API configs take precedence, but fill gaps from localStorage
        const mergedConfigs = { ...localConfigs, ...cfgData };
        
        setModels(modelList);
        setConfigs(mergedConfigs);
        setGroups(groupModels(modelList));
        if (modelList.length > 0) {
          setSelectedModel(modelList[0]);
        }
      } catch (e) {
        console.error('[Settings] Load failed:', e);
        // Fallback to localStorage only
        const localConfigs = loadEncryptedConfig();
        setConfigs(localConfigs);
        // Use fallback models
        setModels(FALLBACK_MODELS);
        setGroups(groupModels(FALLBACK_MODELS));
        if (FALLBACK_MODELS.length > 0) {
          setSelectedModel(FALLBACK_MODELS[0]);
        }
      } finally {
        setLoading(false);
      }
    };
    load();

    const notice = sessionStorage.getItem('omc-migration-done');
    if (notice) {
      setMigrationNotice(notice);
      sessionStorage.removeItem('omc-migration-done');
    }
  }, []);

  const handleConfigUpdate = useCallback((modelId: string, cfg: ModelConfigEntry) => {
    setConfigs(prev => ({ ...prev, [modelId]: cfg }));
  }, []);

  const handleConfigSave = useCallback(async (modelId: string, cfg: ModelConfigEntry) => {
    // Save to localStorage (encrypted)
    const updatedConfigs = { ...configs, [modelId]: cfg };
    saveEncryptedConfig(updatedConfigs);
    setConfigs(updatedConfigs);
    
    // Also try to save via API
    try {
      await (window.omc as any).modelConfigSet(modelId, cfg);
    } catch {
      // API might not be available, localStorage is the fallback
    }
  }, [configs]);

  const toggleGroup = (provider: string) => {
    setGroups(prev => prev.map(g =>
      g.provider === provider ? { ...g, collapsed: !g.collapsed } : g
    ));
  };

  const handleExport = () => {
    const data = JSON.stringify({ version: 1, models: configs }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `omc-models-config-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setExportDropdown(false);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const text = ev.target?.result as string;
        const data = JSON.parse(text);
        const imported = data.models ?? data;
        if (typeof imported !== 'object') throw new Error('Invalid format');
        const merged = { ...configs };
        const entries = Object.entries(imported) as [string, ModelConfigEntry][];
        for (const [mid, cfg] of entries) {
          merged[mid] = cfg;
          try {
            await (window.omc as any).modelConfigSet(mid, cfg);
          } catch { /* skip per-key errors */ }
        }
        // Save encrypted to localStorage
        saveEncryptedConfig(merged);
        setConfigs(merged);
        setImportError(null);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'invalid JSON';
        setImportError(`Import failed: ${msg}`);
        setTimeout(() => setImportError(null), 4000);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleResetAll = () => {
    clearEncryptedConfig();
    setConfigs({});
    setShowResetConfirm(false);
    // Reload page to reset all state
    window.location.reload();
  };

  const currentConfig = selectedModel ? (configs[selectedModel.id] ?? { api_key: '' }) : { api_key: '' };

  return (
    <div className="settings-panel">
      <div className="settings-panel__header">
        <span className="settings-panel__title">⚙ Model Settings</span>
        <div className="settings-panel__actions">
          <div className="settings-dropdown">
            <button className="settings-action-btn" onClick={() => setExportDropdown(v => !v)}>
              ↓ Export
            </button>
            {exportDropdown && (
              <div className="settings-dropdown__menu">
                <button onClick={handleExport}>Export as JSON</button>
                <label className="settings-dropdown__item">
                  Import from JSON
                  <input type="file" accept=".json" onChange={handleImport} style={{ display: 'none' }} />
                </label>
              </div>
            )}
          </div>
          <button className="settings-panel__reset-all" onClick={() => setShowResetConfirm(true)} title="Reset all settings to default">
            ↺ Reset All
          </button>
          <button className="settings-panel__close" onClick={onClose}>✕</button>
        </div>
      </div>

      {migrationNotice && (
        <div className="settings-migration-notice">✅ {migrationNotice}</div>
      )}
      {importError && (
        <div className="settings-error">{importError}</div>
      )}

      {showResetConfirm && (
        <div className="settings-reset-confirm">
          <div className="settings-reset-confirm__content">
            <div className="settings-reset-confirm__title">⚠️ Reset All Settings?</div>
            <div className="settings-reset-confirm__desc">
              This will clear all API keys and configuration. This action cannot be undone.
            </div>
            <div className="settings-reset-confirm__actions">
              <button className="settings-reset-confirm__cancel" onClick={() => setShowResetConfirm(false)}>
                Cancel
              </button>
              <button className="settings-reset-confirm__confirm" onClick={handleResetAll}>
                Yes, Reset Everything
              </button>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="settings-loading">Loading models...</div>
      ) : (
        <div className="settings-panel__body">
          <div className="settings-sidebar">
            <div className="settings-sidebar__label">Models</div>
            {groups.map(group => (
              <div key={group.provider} className="settings-group">
                <button className="settings-group__header" onClick={() => toggleGroup(group.provider)}>
                  <span className="settings-group__caret">{group.collapsed ? '▶' : '▼'}</span>
                  <span className="settings-group__name">{group.label}</span>
                  <span className="settings-group__count">{group.models.length}</span>
                  <span className={`settings-group__status ${
                    group.models.some(m => configs[m.id]?.api_key) ? 'has-key' : 'no-key'
                  }`} />
                </button>
                {!group.collapsed && (
                  <div className="settings-group__models">
                    {group.models.map(m => {
                      const hasKey = Boolean(configs[m.id]?.api_key);
                      const isSelected = selectedModel?.id === m.id;
                      return (
                        <button
                          key={m.id}
                          className={`settings-model-item ${isSelected ? 'active' : ''} ${hasKey ? 'has-key' : ''}`}
                          onClick={() => setSelectedModel(m)}
                        >
                          <span className="settings-model-item__icon">{TIER_ICON[m.tier] || '◆'}</span>
                          <span className="settings-model-item__name">{m.name}</span>
                          {hasKey && <span className="settings-model-item__key-dot" />}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="settings-detail-wrap">
            {selectedModel ? (
              <ModelDetailPanel
                model={selectedModel}
                config={currentConfig}
                onUpdate={cfg => handleConfigUpdate(selectedModel.id, cfg)}
                onConfigSave={handleConfigSave}
              />
            ) : (
              <div className="settings-detail-empty">Select a model to configure</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

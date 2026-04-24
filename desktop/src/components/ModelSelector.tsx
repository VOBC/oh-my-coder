// src/components/ModelSelector.tsx
import React, { useState, useEffect, useRef, useMemo } from 'react';
import modelMetadata from '../models/model_metadata.json';

// ── Types ──────────────────────────────────────────────────────────────────────
interface Model {
  id: string;
  name: string;
  provider: string;
  tier?: string;
  context?: number;
}

interface MetadataEntry {
  id: string;
  provider: string;
  name: string;
}

type Status = 'production' | 'beta' | 'deprecated';

// ── Status icons ──────────────────────────────────────────────────────────────
const STATUS_ICON: Record<string, string> = {
  beta: '🔶',
  deprecated: '⛔',
};
const TIER_ICON: Record<string, string> = { free: '◈', low: '◇', medium: '◆', high: '★' };
const TIER_COLOR: Record<string, string> = {
  free: '#4ade80',
  low: '#94a3b8',
  medium: '#d4a017',
  high: '#f59e0b',
};

// ── Metadata helpers ───────────────────────────────────────────────────────────
const META = modelMetadata as Record<Status, MetadataEntry[]>;

function getModelStatus(modelId: string): Status {
  for (const status of ['production', 'beta', 'deprecated'] as Status[]) {
    if (META[status].some(m => m.id === modelId)) return status;
  }
  return 'beta'; // unknown → treat as beta
}

// ── Component ─────────────────────────────────────────────────────────────────
interface ModelSelectorProps {
  models: Model[];
  current: string;
  onSwitch: (id: string) => void;
  trigger?: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export function ModelSelector({
  models,
  current,
  onSwitch,
  trigger,
  open: controlledOpen,
  onOpenChange,
}: ModelSelectorProps) {
  const [internalOpen, setInternalOpen] = useState(false);
  const [showBeta, setShowBeta] = useState(false);
  const [search, setSearch] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  const open = controlledOpen !== undefined ? controlledOpen : internalOpen;
  const setOpen = (v: boolean) => {
    if (onOpenChange) onOpenChange(v);
    if (controlledOpen === undefined) setInternalOpen(v);
  };

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [setOpen]);

  // Enrich models with status
  const enrichedModels = useMemo(
    () => models.map(m => ({ ...m, status: getModelStatus(m.id) })),
    [models],
  );

  // Filtered list
  const filteredModels = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (q) {
      return enrichedModels.filter(
        m =>
          m.id.toLowerCase().includes(q) ||
          m.name.toLowerCase().includes(q) ||
          m.provider.toLowerCase().includes(q),
      );
    }
    return enrichedModels.filter(m => showBeta || m.status === 'production');
  }, [enrichedModels, showBeta, search]);

  // Count of non-production models
  const nonProdCount = useMemo(
    () => enrichedModels.filter(m => m.status !== 'production').length,
    [enrichedModels],
  );

  const cur = enrichedModels.find(m => m.id === current) || enrichedModels[0];

  return (
    <div className="model-selector" ref={ref}>
      {trigger ? (
        <div onClick={() => setOpen(!open)}>{trigger}</div>
      ) : (
        <button className="model-selector__trigger" onClick={() => setOpen(!open)}>
          <span
            className="model-selector__icon"
            style={{ color: TIER_COLOR[cur?.tier ?? 'medium'] || '#d4a017' }}
          >
            {TIER_ICON[cur?.tier ?? 'medium'] || '◆'}
          </span>
          <span className="model-selector__name">{cur?.name || 'Select model'}</span>
          <span className="model-selector__caret">{open ? '▲' : '▼'}</span>
        </button>
      )}

      {open && (
        <div className="model-selector__dropdown">
          <div className="model-selector__shortcut-hint">
            <kbd>⌘</kbd>
            <kbd>M</kbd> 快速切换
          </div>

          {/* Search — no filter restrictions while searching */}
          <div className="model-selector__search-wrap">
            <input
              type="text"
              className="model-selector__search"
              placeholder="搜索模型..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              autoFocus
            />
          </div>

          {/* Model list */}
          {filteredModels.map(m => (
            <button
              key={m.id}
              className={`model-selector__item${m.id === current ? ' active' : ''}`}
              onClick={() => {
                onSwitch(m.id);
                setOpen(false);
              }}
            >
              <span
                className="model-selector__icon"
                style={{ color: TIER_COLOR[m.tier ?? 'medium'] }}
              >
                {TIER_ICON[m.tier ?? 'medium'] || '◆'}
              </span>
              <span className="model-selector__item-name">{m.name}</span>
              {m.status !== 'production' && (
                <span className="model-selector__status-badge">
                  {STATUS_ICON[m.status]}
                </span>
              )}
              <span className="model-selector__provider">{m.provider}</span>
            </button>
          ))}

          {/* Collapse toggle — hidden while searching */}
          {!search && nonProdCount > 0 && (
            <button
              className="model-selector__toggle-beta"
              onClick={() => setShowBeta(v => !v)}
            >
              {showBeta
                ? `▲ 隐藏 Beta 模型`
                : `▼ 其他模型 (${nonProdCount})`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default ModelSelector;

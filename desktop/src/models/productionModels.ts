// productionModels.ts — Unified model definitions for Oh My Coder Desktop
// This file is the single source of truth for fallback models in both App.tsx and SettingsPanel.tsx

export interface Model {
  id: string;
  name: string;
  provider: string;
  tier: string;
  context?: number;
  endpoint?: string;
  pricing?: Record<string, number>;
  features?: string[];
}

export const PRODUCTION_MODELS: Model[] = [
  { id: 'deepseek-chat', name: 'DeepSeek V4', provider: 'deepseek', tier: 'low', context: 64000 },

  { id: 'glm-4-flash', name: 'GLM-4.7-Flash', provider: 'glm', tier: 'free', context: 128000 },
  { id: 'MiniMax-Text-01', name: 'MiMo Flash', provider: 'xiaomi', tier: 'free', context: 200000 },
  { id: 'moonshot-v1-128k', name: 'Kimi 128K', provider: 'kimi', tier: 'low', context: 128000 },
  { id: 'doubao-pro-32k', name: 'Doubao-Pro-32K', provider: 'doubao', tier: 'low', context: 32000 },
  { id: 'tiangong-3', name: '天工 3.0', provider: 'doubao', tier: 'low', context: 128000 },
  { id: 'Baichuan4', name: '百川 4', provider: 'baichuan', tier: 'low', context: 128000 },
];

export default PRODUCTION_MODELS;

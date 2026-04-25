"use client";
import { useState } from "react";
import { useChatStore } from "@/lib/chat-store";

const CONFIGS = [
  { label: "智谱 AI", envKey: "ZHIPU_API_KEY", placeholder: "sk-xxxxxxxx", url: "https://open.bigmodel.cn/" },
  { label: "DeepSeek", envKey: "DEEPSEEK_API_KEY", placeholder: "sk-xxxxxxxx", url: "https://platform.deepseek.com/" },
  { label: "OpenAI", envKey: "OPENAI_API_KEY", placeholder: "sk-xxxxxxxx", url: "https://platform.openai.com/" },
  { label: "Anthropic", envKey: "ANTHROPIC_API_KEY", placeholder: "sk-ant-xxxxxxxx", url: "https://console.anthropic.com/" },
  { label: "Google Gemini", envKey: "GOOGLE_API_KEY", placeholder: "AIzaxxxxxxxx", url: "https://aistudio.google.com/app/apikey" },
];

export default function SettingsPanel({ onClose }: { onClose: () => void }) {
  const { apiKeys, setApiKey } = useChatStore();
  const [localKeys, setLocalKeys] = useState<Record<string, string>>(Object.fromEntries(CONFIGS.map((c) => [c.envKey, apiKeys[c.envKey] || ""])));
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    CONFIGS.forEach((c) => { const k = localKeys[c.envKey]?.trim(); if (k) setApiKey(c.envKey, k); });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div><h2 className="text-lg font-bold text-gray-900">API Key 配置</h2><p className="text-xs text-gray-500 mt-0.5">Keys 仅存储在浏览器本地，不会上传</p></div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-2xl leading-none">×</button>
        </div>
        <div className="px-6 py-4 space-y-4">
          {CONFIGS.map((c) => (
            <div key={c.envKey}>
              <div className="flex items-center justify-between mb-1">
                <label className="text-sm font-medium text-gray-700">{c.label}</label>
                <a href={c.url} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">获取 Key →</a>
              </div>
              <input type="password" value={localKeys[c.envKey] || ""} onChange={(e) => setLocalKeys((p) => ({ ...p, [c.envKey]: e.target.value }))} placeholder={c.placeholder}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          ))}
        </div>
        <div className="mx-6 mb-4 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <p className="text-xs text-blue-700"><span className="font-bold">安全说明：</span>API Key 仅存储在浏览器本地（Zustand persist → IndexedDB），请勿在公共设备上保存。</p>
        </div>
        <div className="px-6 pb-6 flex gap-3">
          <button onClick={onClose} className="flex-1 border border-gray-300 text-gray-700 rounded-lg px-4 py-2.5 text-sm font-medium hover:bg-gray-50">取消</button>
          <button onClick={handleSave} className="flex-1 bg-blue-500 hover:bg-blue-600 text-white rounded-lg px-4 py-2.5 text-sm font-medium">{saved ? "✓ 已保存" : "保存配置"}</button>
        </div>
      </div>
    </div>
  );
}

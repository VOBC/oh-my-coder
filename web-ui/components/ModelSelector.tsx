"use client";
import { useChatStore } from "@/lib/chat-store";
import { getModelGroups } from "@/lib/models";
import { useState, useEffect } from "react";

export default function ModelSelector() {
  const { selectedModel, setSelectedModel, apiKeys } = useChatStore();
  const [groups, setGroups] = useState<Array<{ provider: string; display_name: string; models: Array<{ name: string; display_name: string; provider: string }> }>>([]);
  const [hovered, setHovered] = useState(false);

  useEffect(() => { getModelGroups().then(setGroups); }, []);

  const apiKeyMap: Record<string, string> = { zhipu: "ZHIPU_API_KEY", openai: "OPENAI_API_KEY", anthropic: "ANTHROPIC_API_KEY", deepseek: "DEEPSEEK_API_KEY", google: "GOOGLE_API_KEY" };

  let curProvider = "zhipu";
  for (const g of groups) {
    for (const m of g.models) {
      if (m.name === selectedModel) { curProvider = g.provider; break; }
    }
  }
  const hasKey = !!apiKeys[apiKeyMap[curProvider] || "ZHIPU_API_KEY"];

  return (
    <div className="relative" onMouseEnter={() => setHovered(true)} onMouseLeave={() => setHovered(false)}>
      <select
        value={selectedModel}
        onChange={(e) => setSelectedModel(e.target.value)}
        className="appearance-none bg-white border border-gray-300 rounded-lg px-3 py-1.5 pr-7 text-sm font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
      >
        {groups.map((g) => (
          <optgroup key={g.provider} label={g.display_name}>
            {g.models.map((m) => (
              <option key={m.name} value={m.name}>{m.display_name}</option>
            ))}
          </optgroup>
        ))}
      </select>
      <div className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400 text-xs">▼</div>
      {hovered && !hasKey && (
        <div className="absolute top-full left-0 mt-1 bg-amber-50 border border-amber-200 text-amber-700 text-xs px-2 py-1 rounded whitespace-nowrap z-10">
          请先配置 API Key ⚠
        </div>
      )}
    </div>
  );
}

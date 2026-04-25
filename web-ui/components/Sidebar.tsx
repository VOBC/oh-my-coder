"use client";
import { useState } from "react";
import { useChatStore } from "@/lib/chat-store";
import { Settings } from "lucide-react";
import SettingsPanel from "./SettingsPanel";

export default function Sidebar() {
  const { sessions, currentSessionId, addSession, deleteSession, switchSession } = useChatStore();
  const [showSettings, setShowSettings] = useState(false);

  return (
    <>
      <div className="w-64 bg-gray-900 text-white flex flex-col h-full">
        <div className="px-4 py-4 border-b border-gray-700">
          <h1 className="font-bold text-base flex items-center gap-2"><span className="text-xl">🐾</span> oh-my-coder</h1>
          <p className="text-xs text-gray-400 mt-0.5">AI Coding Assistant</p>
        </div>
        <div className="px-3 py-3">
          <button onClick={addSession}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg px-3 py-2 text-sm font-medium flex items-center gap-2 transition-colors">
            <span>+</span> 新对话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {sessions.map((s) => (
            <div key={s.id}
              className={`group flex items-center gap-1 rounded-lg px-2 py-2 cursor-pointer transition-colors ${s.id === currentSessionId ? "bg-indigo-600 text-white" : "hover:bg-gray-800 text-gray-300"}`}
              onClick={() => switchSession(s.id)}>
              <span className="text-xs flex-shrink-0">{s.id === currentSessionId ? "▶" : "○"}</span>
              <span className="text-xs flex-1 truncate">{s.name}</span>
              <span className="text-xs text-gray-500">{s.messages.length}</span>
              <button onClick={(e) => { e.stopPropagation(); if (confirm("删除此对话？")) deleteSession(s.id); }}
                className="opacity-0 group-hover:opacity-100 text-xs hover:text-red-400 px-1">×</button>
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-gray-700">
          <button onClick={() => setShowSettings(true)}
            className="w-full flex items-center gap-2 text-gray-400 hover:text-white px-3 py-2 rounded-lg text-sm hover:bg-gray-800 transition-colors">
            <Settings size={16} /> 设置
          </button>
        </div>
      </div>
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </>
  );
}

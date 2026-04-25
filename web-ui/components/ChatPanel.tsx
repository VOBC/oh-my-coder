"use client";
import { useRef, useEffect, useState, type FormEvent } from "react";
import { useChatStore } from "@/lib/chat-store";
import { sendChatMessage } from "@/lib/sse-client";
import MessageItem from "./MessageItem";
import ModelSelector from "./ModelSelector";

const API_KEY_MAP: Record<string, string> = {
  "glm-4-flash": "ZHIPU_API_KEY", "glm-4": "ZHIPU_API_KEY",
  "deepseek-chat": "DEEPSEEK_API_KEY", "deepseek-coder": "DEEPSEEK_API_KEY",
  "gpt-4o-mini": "OPENAI_API_KEY", "gpt-4o": "OPENAI_API_KEY",
  "claude-3-haiku": "ANTHROPIC_API_KEY", "claude-3-sonnet": "ANTHROPIC_API_KEY",
};

export default function ChatPanel() {
  const { inputText, setInputText, addMessage, appendToLastMessage, setLoading, isLoading, getCurrentSession, apiKeys } = useChatStore();
  const [streaming, setStreaming] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const session = getCurrentSession();
  const messages = session?.messages || [];

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, streaming]);

  const handleSubmit = async (e?: FormEvent) => {
    e?.preventDefault();
    const text = inputText.trim();
    if (!text || isLoading) return;
    setInputText("");
    setLoading(true);
    addMessage({ role: "user", content: text });

    const model = session?.model || "glm-4-flash";
    const envKey = API_KEY_MAP[model] || "ZHIPU_API_KEY";
    const apiKey = apiKeys[envKey] || "";
    addMessage({ role: "assistant", content: "" });
    setStreaming(true);

    await sendChatMessage(
      { message: text, model, apiKey, sessionHistory: messages.slice(-20).map((m) => ({ role: m.role, content: m.content })) },
      (chunk) => appendToLastMessage(chunk),
      () => { setLoading(false); setStreaming(false); },
      (err) => { setLoading(false); setStreaming(false); appendToLastMessage(`\n\n[错误] ${err.message}\n请检查 API Key 或网络连接。`); }
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-gray-200 bg-white px-4 py-2 flex items-center gap-3">
        <span className="text-xs text-gray-500 font-medium">模型:</span>
        <ModelSelector />
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-2">
            <div className="text-4xl">🤖</div><p className="text-sm">输入消息开始对话</p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} isStreaming={streaming && msg === messages[messages.length - 1] && msg.role === "assistant"} />
        ))}
        {isLoading && !streaming && messages[messages.length - 1]?.role === "user" && (
          <div className="flex gap-3 message-enter">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-sm font-bold text-white">AI</div>
            <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <div className="border-t border-gray-200 bg-white p-4">
        <form onSubmit={handleSubmit} className="flex gap-2 items-end">
          <textarea value={inputText} onChange={(e) => setInputText(e.target.value)} onKeyDown={handleKeyDown}
            placeholder="输入消息，Enter 发送，Shift+Enter 换行..." rows={1}
            className="flex-1 resize-none border border-gray-300 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" style={{ maxHeight: "120px" }} />
          <button type="submit" disabled={!inputText.trim() || isLoading}
            className="bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white rounded-xl px-5 py-3 text-sm font-medium transition-colors flex-shrink-0">发送</button>
        </form>
        <p className="text-xs text-gray-400 mt-2 text-center">API Key 仅本地存储，不会发送到服务器</p>
      </div>
    </div>
  );
}

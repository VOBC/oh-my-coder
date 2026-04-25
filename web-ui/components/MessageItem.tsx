"use client";
import MarkdownRenderer from "./MarkdownRenderer";
import type { Message } from "@/lib/chat-store";

export default function MessageItem({ message, isStreaming }: { message: Message; isStreaming?: boolean }) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center my-2">
        <div className="bg-amber-50 border border-amber-200 text-amber-700 text-xs px-3 py-1.5 rounded-full">{message.content}</div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 message-enter ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${isUser ? "bg-blue-500 text-white" : "bg-gradient-to-br from-purple-500 to-indigo-600 text-white"}`}>
        {isUser ? "U" : "AI"}
      </div>
      <div className={`max-w-[75%] rounded-2xl px-4 py-3 ${isUser ? "bg-blue-500 text-white" : "bg-white border border-gray-200 text-gray-800"}`}>
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="text-sm">
            <MarkdownRenderer content={message.content} />
            {isStreaming && <span className="inline-block w-2 h-4 bg-indigo-500 ml-1 animate-pulse" />}
          </div>
        )}
        <div className={`text-xs mt-1 ${isUser ? "text-blue-100" : "text-gray-400"}`}>
          {new Date(message.timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  );
}

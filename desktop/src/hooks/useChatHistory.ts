// src/hooks/useChatHistory.ts — localStorage chat history persistence
import { useState, useEffect, useCallback, useRef } from 'react';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface ChatSession {
  id: string;
  title: string;        // first user message, truncated
  updated: string;      // ISO timestamp string for display
  model?: string;
  messages: ChatMessage[];
  updatedAt: number;    // ms timestamp for sorting
}

const STORAGE_KEY = 'omc-chat-history';
const MAX_SESSIONS = 10;

function makeTitle(messages: ChatMessage[]): string {
  const first = messages.find(m => m.role === 'user');
  if (!first) return 'New Chat';
  const raw = first.content.trim().slice(0, 40);
  return raw.length < first.content.trim().length ? raw + '…' : raw;
}

function now(): string {
  return new Date().toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  });
}

export function useChatHistory() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string>('');
  const [activeMessages, setActiveMessages] = useState<ChatMessage[]>([]);
  const [activeModel, setActiveModel] = useState<string>('');
  const isLoading = useRef(false);

  // ── Load from localStorage on mount ─────────────────────────────────────
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed: ChatSession[] = JSON.parse(raw);
        setSessions(parsed);
        // Restore last active session
        if (parsed.length > 0) {
          const last = parsed[0];
          setActiveId(last.id);
          setActiveMessages(last.messages);
          setActiveModel(last.model || '');
        }
      }
    } catch (e) {
      console.warn('[useChatHistory] load failed:', e);
    }
  }, []);

  // ── Persist whenever sessions change ─────────────────────────────────────
  const persist = useCallback((next: ChatSession[]) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch (e) {
      console.warn('[useChatHistory] persist failed:', e);
    }
  }, []);

  // ── Create or switch session ─────────────────────────────────────────────
  const createSession = useCallback((model?: string): string => {
    const id = Date.now().toString();
    const session: ChatSession = {
      id,
      title: 'New Chat',
      updated: now(),
      model: model || '',
      messages: [],
      updatedAt: Date.now(),
    };
    setSessions(prev => {
      const next = [session, ...prev].slice(0, MAX_SESSIONS);
      persist(next);
      return next;
    });
    setActiveId(id);
    setActiveMessages([]);
    setActiveModel(model || '');
    return id;
  }, [persist]);

  const switchSession = useCallback((id: string) => {
    setSessions(prev => {
      const found = prev.find(s => s.id === id);
      if (found) {
        setActiveId(id);
        setActiveMessages([...found.messages]);
        setActiveModel(found.model || '');
      }
      return prev;
    });
  }, []);

  // ── Append a message to the active session ───────────────────────────────
  const addMessage = useCallback((msg: ChatMessage) => {
    setActiveMessages(prev => [...prev, msg]);
    setSessions(prev => {
      const next = prev.map(s => {
        if (s.id !== activeId) return s;
        const msgs = [...s.messages, msg];
        return {
          ...s,
          messages: msgs,
          title: makeTitle(msgs),
          updated: now(),
          updatedAt: Date.now(),
          model: activeModel || s.model,
        };
      });
      persist(next);
      return next;
    });
  }, [activeId, activeModel, persist]);

  // ── Update active model ───────────────────────────────────────────────────
  const updateModel = useCallback((modelId: string) => {
    setActiveModel(modelId);
    setSessions(prev => {
      const next = prev.map(s => s.id === activeId ? { ...s, model: modelId } : s);
      persist(next);
      return next;
    });
  }, [activeId, persist]);

  // ── Delete a session ───────────────────────────────────────────────────────
  const deleteSession = useCallback((id: string) => {
    setSessions(prev => {
      const next = prev.filter(s => s.id !== id);
      persist(next);
      if (id === activeId && next.length > 0) {
        setActiveId(next[0].id);
        setActiveMessages([...next[0].messages]);
        setActiveModel(next[0].model || '');
      } else if (id === activeId) {
        setActiveId('');
        setActiveMessages([]);
        setActiveModel('');
      }
      return next;
    });
  }, [activeId, persist]);

  // ── Clear active session ──────────────────────────────────────────────────
  const clearActive = useCallback(() => {
    setActiveMessages([]);
    setSessions(prev => {
      const next = prev.map(s => {
        if (s.id !== activeId) return s;
        return { ...s, messages: [], title: 'New Chat', updated: now(), updatedAt: Date.now() };
      });
      persist(next);
      return next;
    });
  }, [activeId, persist]);

  return {
    sessions,
    activeId,
    activeMessages,
    activeModel,
    createSession,
    switchSession,
    addMessage,
    updateModel,
    deleteSession,
    clearActive,
  };
}

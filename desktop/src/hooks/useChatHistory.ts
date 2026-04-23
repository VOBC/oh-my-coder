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
  const [activeModel, setActiveModel] = useState<string>('');
  const isLoading = useRef(false);
  
  // Derive activeMessages from sessions to ensure single source of truth
  const activeMessages = sessions.find(s => s.id === activeId)?.messages || [];

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
    setActiveModel(model || '');
    return id;
  }, [persist]);

  const switchSession = useCallback((id: string) => {
    const found = sessions.find(s => s.id === id);
    if (found) {
      setActiveId(id);
      setActiveModel(found.model || '');
    }
  }, [sessions]);

  // ── Append a message to the active session ───────────────────────────────
  const addMessage = useCallback((msg: ChatMessage) => {
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
        setActiveModel(next[0].model || '');
      } else if (id === activeId) {
        setActiveId('');
        setActiveModel('');
      }
      return next;
    });
  }, [activeId, persist]);

  // ── Clear active session ──────────────────────────────────────────────────
  const clearActive = useCallback(() => {
    setSessions(prev => {
      const next = prev.map(s => {
        if (s.id !== activeId) return s;
        return { ...s, messages: [], title: 'New Chat', updated: now(), updatedAt: Date.now() };
      });
      persist(next);
      return next;
    });
  }, [activeId, persist]);

  // ── Rename session ──────────────────────────────────────────────────────────
  const renameSession = useCallback((id: string, newTitle: string) => {
    setSessions(prev => {
      const next = prev.map(s => {
        if (s.id !== id) return s;
        return { ...s, title: newTitle.slice(0, 50), updated: now(), updatedAt: Date.now() };
      });
      persist(next);
      return next;
    });
  }, [persist]);

  // ── Export session as JSON ──────────────────────────────────────────────────
  const exportSession = useCallback((id: string): string | null => {
    const session = sessions.find(s => s.id === id);
    if (!session) return null;
    return JSON.stringify(session, null, 2);
  }, [sessions]);

  // ── Clear all sessions ─────────────────────────────────────────────────────
  const clearAllSessions = useCallback(() => {
    setSessions([]);
    setActiveId('');
    setActiveModel('');
    persist([]);
  }, [persist]);

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
    renameSession,
    exportSession,
    clearAllSessions,
  };
}

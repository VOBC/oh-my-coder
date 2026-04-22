// src/hooks/useGlobalKeymap.ts — global Cmd+L / Cmd+K shortcuts
import { useEffect, useCallback } from 'react';

interface Keymap {
  onCmdL?: () => void;
  onCmdK?: () => void;
}

export function useGlobalKeymap({ onCmdL, onCmdK }: Keymap) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;

      if (e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        onCmdK?.();
      } else if (e.key === 'l' || e.key === 'L') {
        e.preventDefault();
        onCmdL?.();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onCmdK, onCmdL]);
}

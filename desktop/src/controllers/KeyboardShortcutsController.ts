// src/controllers/KeyboardShortcutsController.ts
// Keyboard shortcuts management for Oh My Coder Desktop
// Supports Cmd/Ctrl combinations, Shift modifiers, and standalone keys (Esc)

export type ShortcutHandler = () => void;

export interface ShortcutConfig {
  key: string;
  metaKey?: boolean;  // Cmd on Mac, Ctrl on Windows
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  description: string;
  handler: ShortcutHandler;
  /** If true, this shortcut works without meta/ctrl (e.g., Esc) */
  standalone?: boolean;
}

export class KeyboardShortcutsController {
  private shortcuts: Map<string, ShortcutConfig> = new Map();
  private isActive: boolean = false;
  private boundHandler: (e: KeyboardEvent) => void;

  constructor() {
    this.boundHandler = this.handleKeyDown.bind(this);
  }

  /**
   * Register a keyboard shortcut
   * @param id Unique identifier for the shortcut
   * @param config Shortcut configuration
   */
  register(id: string, config: ShortcutConfig): void {
    this.shortcuts.set(id, config);
  }

  /**
   * Unregister a keyboard shortcut
   * @param id Shortcut identifier
   */
  unregister(id: string): void {
    this.shortcuts.delete(id);
  }

  /**
   * Start listening for keyboard events
   */
  start(): void {
    if (this.isActive) return;
    document.addEventListener('keydown', this.boundHandler);
    this.isActive = true;
    console.log('[KeyboardShortcuts] Started listening');
  }

  /**
   * Stop listening for keyboard events
   */
  stop(): void {
    if (!this.isActive) return;
    document.removeEventListener('keydown', this.boundHandler);
    this.isActive = false;
    console.log('[KeyboardShortcuts] Stopped listening');
  }

  /**
   * Check if controller is active
   */
  get active(): boolean {
    return this.isActive;
  }

  /**
   * Get all registered shortcuts (for display)
   */
  getShortcuts(): ShortcutConfig[] {
    return Array.from(this.shortcuts.values());
  }

  /**
   * Get shortcuts as formatted list (for UI)
   */
  getShortcutsList(): Array<{ id: string; keys: string; description: string }> {
    return Array.from(this.shortcuts.entries()).map(([id, config]) => {
      const parts: string[] = [];
      if (config.metaKey) parts.push('⌘');
      if (config.ctrlKey) parts.push('Ctrl');
      if (config.shiftKey) parts.push('⇧');
      if (config.altKey) parts.push('⌥');
      parts.push(config.key.toUpperCase());
      return { id, keys: parts.join('+'), description: config.description };
    });
  }

  private handleKeyDown(e: KeyboardEvent): void {
    // Find matching shortcut
    for (const [id, config] of this.shortcuts) {
      if (this.matchesShortcut(e, config)) {
        e.preventDefault();
        e.stopPropagation();
        console.log(`[KeyboardShortcuts] Triggered: ${id} (${config.description})`);
        config.handler();
        return;
      }
    }
  }

  private matchesShortcut(e: KeyboardEvent, config: ShortcutConfig): boolean {
    const key = e.key.toLowerCase();
    const configKey = config.key.toLowerCase();

    // Key must match
    if (key !== configKey) return false;

    // For standalone shortcuts (like Esc), no modifiers required
    if (config.standalone) {
      return !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey;
    }

    // Check modifier keys (default false for optional)
    const metaMatch = (config.metaKey ?? false) === e.metaKey;
    const ctrlMatch = (config.ctrlKey ?? false) === e.ctrlKey;
    const shiftMatch = (config.shiftKey ?? false) === e.shiftKey;
    const altMatch = (config.altKey ?? false) === e.altKey;

    return metaMatch && ctrlMatch && shiftMatch && altMatch;
  }

  /**
   * Dispose the controller
   */
  dispose(): void {
    this.stop();
    this.shortcuts.clear();
  }
}

// Singleton instance for app-wide use
let globalController: KeyboardShortcutsController | null = null;

export function getKeyboardShortcutsController(): KeyboardShortcutsController {
  if (!globalController) {
    globalController = new KeyboardShortcutsController();
  }
  return globalController;
}

export function disposeKeyboardShortcutsController(): void {
  if (globalController) {
    globalController.dispose();
    globalController = null;
  }
}

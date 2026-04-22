// src/controllers/KeyboardShortcutsController.ts
// Keyboard shortcuts management for Oh My Coder Desktop
// Handles Cmd+L (Clear chat), Cmd+M (Focus model selector), Cmd+N (New chat)

export type ShortcutHandler = () => void;

export interface ShortcutConfig {
  key: string;
  metaKey: boolean;
  ctrlKey: boolean;
  description: string;
  handler: ShortcutHandler;
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
   * Get all registered shortcuts
   */
  getShortcuts(): ShortcutConfig[] {
    return Array.from(this.shortcuts.values());
  }

  private handleKeyDown(e: KeyboardEvent): void {
    // Only process if meta (Cmd on Mac) or ctrl is pressed
    if (!e.metaKey && !e.ctrlKey) return;

    const key = e.key.toLowerCase();
    const isMeta = e.metaKey;
    const isCtrl = e.ctrlKey;

    for (const [id, config] of this.shortcuts) {
      if (
        config.key.toLowerCase() === key &&
        config.metaKey === isMeta &&
        config.ctrlKey === isCtrl
      ) {
        e.preventDefault();
        e.stopPropagation();
        console.log(`[KeyboardShortcuts] Triggered: ${id} (${config.description})`);
        config.handler();
        return;
      }
    }
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

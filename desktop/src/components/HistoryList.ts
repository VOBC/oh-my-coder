// src/components/HistoryList.ts — <history-list> web component
// P3-3: Enhanced with right-click menu, rename, export, clear all

export interface HistorySession {
  id: string;
  title: string;
  updated: string;
  model?: string;
}

interface HistoryListState {
  sessions: HistorySession[];
  activeId: string;
  contextMenuId: string | null;
  renameDialogId: string | null;
  renameValue: string;
}

class HistoryList extends HTMLElement {
  private _state: HistoryListState = {
    sessions: [],
    activeId: '',
    contextMenuId: null,
    renameDialogId: null,
    renameValue: '',
  };
  private _shadow: ShadowRoot;
  private _onSelect?: (id: string) => void;
  private _onDelete?: (id: string) => void;
  private _onNew?: () => void;
  private _onRename?: (id: string, newTitle: string) => void;
  private _onExport?: (id: string) => void;
  private _onClearAll?: () => void;

  static get observedAttributes() {
    return ['active-id'];
  }

  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: 'open' });
    this.render();
    // Close context menu on outside click
    document.addEventListener('click', this._handleOutsideClick.bind(this));
  }

  disconnectedCallback() {
    document.removeEventListener('click', this._handleOutsideClick.bind(this));
  }

  private _handleOutsideClick(e: MouseEvent) {
    const path = e.composedPath();
    if (!path.includes(this._shadow.host)) {
      this._state.contextMenuId = null;
      this._state.renameDialogId = null;
      this.render();
    }
  }

  attributeChangedCallback(name: string, oldVal: string, newVal: string) {
    if (name === 'active-id' && oldVal !== newVal) {
      this._state.activeId = newVal || '';
      this.render();
    }
  }

  // Public API
  set sessions(data: HistorySession[]) {
    this._state.sessions = data;
    this.render();
  }

  get sessions(): HistorySession[] {
    return [...this._state.sessions];
  }

  set activeId(id: string) {
    this._state.activeId = id;
    this.setAttribute('active-id', id);
    this.render();
  }

  get activeId(): string {
    return this._state.activeId;
  }

  // Event handlers
  set onSelect(handler: (id: string) => void) { this._onSelect = handler; }
  set onDelete(handler: (id: string) => void) { this._onDelete = handler; }
  set onNew(handler: () => void) { this._onNew = handler; }
  set onRename(handler: (id: string, newTitle: string) => void) { this._onRename = handler; }
  set onExport(handler: (id: string) => void) { this._onExport = handler; }
  set onClearAll(handler: () => void) { this._onClearAll = handler; }

  private handleSelect(id: string) {
    this._state.activeId = id;
    this._state.contextMenuId = null;
    this.render();
    this._onSelect?.(id);
    this.dispatchEvent(new CustomEvent('session-select', { detail: { id }, bubbles: true, composed: true }));
  }

  private handleDelete(id: string, e: Event) {
    e.stopPropagation();
    this._state.contextMenuId = null;
    this._onDelete?.(id);
    this.dispatchEvent(new CustomEvent('session-delete', { detail: { id }, bubbles: true, composed: true }));
  }

  private handleNew() {
    this._onNew?.();
    this.dispatchEvent(new CustomEvent('session-new', { bubbles: true, composed: true }));
  }

  private handleRename(id: string, newTitle: string) {
    this._state.renameDialogId = null;
    this._onRename?.(id, newTitle);
    this.dispatchEvent(new CustomEvent('session-rename', { detail: { id, newTitle }, bubbles: true, composed: true }));
  }

  private handleExport(id: string) {
    this._state.contextMenuId = null;
    this._onExport?.(id);
    this.dispatchEvent(new CustomEvent('session-export', { detail: { id }, bubbles: true, composed: true }));
  }

  private handleClearAll() {
    this._state.contextMenuId = null;
    this._onClearAll?.();
    this.dispatchEvent(new CustomEvent('sessions-clear-all', { bubbles: true, composed: true }));
  }

  private showContextMenu(id: string, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    this._state.contextMenuId = id;
    this.render();
  }

  private showRenameDialog(id: string, currentTitle: string) {
    this._state.contextMenuId = null;
    this._state.renameDialogId = id;
    this._state.renameValue = currentTitle;
    this.render();
  }

  private render() {
    const { sessions, activeId, contextMenuId, renameDialogId, renameValue } = this._state;

    this._shadow.innerHTML = `
      <style>
        :host {
          display: flex;
          flex-direction: column;
          height: 100%;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: #1a1a1a;
          color: #e5e5e5;
        }

        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 16px;
          border-bottom: 1px solid #333;
          background: #1a1a1a;
        }

        .title {
          font-size: 13px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: #888;
        }

        .new-btn {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 6px;
          background: #d4a017;
          color: #1a1a1a;
          font-size: 18px;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.15s ease;
        }

        .new-btn:hover { background: #e5b028; }

        .list {
          flex: 1;
          overflow-y: auto;
          padding: 8px;
        }

        .empty {
          padding: 24px 16px;
          text-align: center;
          color: #666;
          font-size: 13px;
        }

        .session {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          margin-bottom: 4px;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.15s ease;
          position: relative;
          user-select: none;
        }

        .session:hover { background: #2a2a2a; }

        .session.active {
          background: #d4a01720;
          border: 1px solid #d4a01740;
        }

        .session-content {
          flex: 1;
          min-width: 0;
          text-align: left;
          background: none;
          border: none;
          color: inherit;
          cursor: pointer;
          padding: 0;
        }

        .session-title {
          font-size: 13px;
          font-weight: 500;
          color: #e5e5e5;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          margin-bottom: 4px;
        }

        .session-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 11px;
          color: #666;
        }

        .session-model {
          color: #d4a017;
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.3px;
          font-weight: 500;
        }

        .delete-btn {
          width: 22px;
          height: 22px;
          border: none;
          border-radius: 4px;
          background: transparent;
          color: #666;
          font-size: 12px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
          transition: all 0.15s ease;
        }

        .session:hover .delete-btn { opacity: 1; }
        .delete-btn:hover { background: #ff444420; color: #ff6666; }

        /* Context Menu */
        .context-menu {
          position: fixed;
          background: #2a2a2a;
          border: 1px solid #444;
          border-radius: 8px;
          padding: 4px;
          min-width: 140px;
          z-index: 1000;
          box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        }

        .menu-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 12px;
          font-size: 13px;
          color: #ccc;
          cursor: pointer;
          border-radius: 4px;
          transition: background 0.15s ease;
        }

        .menu-item:hover { background: #3a3a3a; }
        .menu-item.danger:hover { background: #ff444420; color: #ff6666; }

        .menu-icon { width: 14px; text-align: center; }

        /* Rename Dialog */
        .dialog-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.6);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1001;
        }

        .dialog {
          background: #2a2a2a;
          border: 1px solid #444;
          border-radius: 12px;
          padding: 20px;
          min-width: 320px;
        }

        .dialog-title {
          font-size: 14px;
          font-weight: 600;
          color: #e5e5e5;
          margin-bottom: 12px;
        }

        .dialog-input {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #444;
          border-radius: 6px;
          background: #1a1a1a;
          color: #e5e5e5;
          font-size: 13px;
          outline: none;
          box-sizing: border-box;
        }

        .dialog-input:focus { border-color: #d4a017; }

        .dialog-actions {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 16px;
        }

        .dialog-btn {
          padding: 8px 16px;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .dialog-btn--cancel {
          background: transparent;
          border: 1px solid #444;
          color: #888;
        }

        .dialog-btn--cancel:hover { border-color: #666; color: #aaa; }

        .dialog-btn--save {
          background: #d4a017;
          border: none;
          color: #1a1a1a;
        }

        .dialog-btn--save:hover { background: #e5b028; }

        /* Footer */
        .footer {
          padding: 12px 16px;
          border-top: 1px solid #333;
        }

        .clear-all-btn {
          width: 100%;
          padding: 10px;
          border: 1px solid #444;
          border-radius: 6px;
          background: transparent;
          color: #666;
          font-size: 12px;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .clear-all-btn:hover {
          border-color: #ff4444;
          color: #ff6666;
          background: #ff444410;
        }

        /* Scrollbar */
        .list::-webkit-scrollbar { width: 6px; }
        .list::-webkit-scrollbar-track { background: transparent; }
        .list::-webkit-scrollbar-thumb { background: #444; border-radius: 3px; }
        .list::-webkit-scrollbar-thumb:hover { background: #555; }
      </style>

      <div class="header">
        <span class="title">Sessions</span>
        <button class="new-btn" title="New Chat">+</button>
      </div>

      <div class="list">
        ${sessions.length === 0
          ? '<div class="empty">No sessions yet</div>'
          : sessions.map(s => `
            <div class="session ${s.id === activeId ? 'active' : ''}" data-id="${s.id}">
              <button class="session-content">
                <div class="session-title">${this.escapeHtml(s.title)}</div>
                <div class="session-meta">
                  <span>${s.updated}</span>
                  ${s.model ? `<span class="session-model">${this.escapeHtml(s.model)}</span>` : ''}
                </div>
              </button>
              <button class="delete-btn" title="Delete">✕</button>
            </div>
          `).join('')}
      </div>

      ${sessions.length > 0 ? `
        <div class="footer">
          <button class="clear-all-btn">Clear All History</button>
        </div>
      ` : ''}

      ${contextMenuId ? `
        <div class="context-menu" id="ctx-menu">
          <div class="menu-item" data-action="rename">
            <span class="menu-icon">✏️</span>
            <span>Rename</span>
          </div>
          <div class="menu-item" data-action="export">
            <span class="menu-icon">📤</span>
            <span>Export</span>
          </div>
          <div class="menu-item danger" data-action="delete">
            <span class="menu-icon">🗑️</span>
            <span>Delete</span>
          </div>
        </div>
      ` : ''}

      ${renameDialogId ? `
        <div class="dialog-overlay" id="rename-overlay">
          <div class="dialog">
            <div class="dialog-title">Rename Session</div>
            <input type="text" class="dialog-input" id="rename-input" value="${this.escapeHtml(renameValue)}" />
            <div class="dialog-actions">
              <button class="dialog-btn dialog-btn--cancel" id="rename-cancel">Cancel</button>
              <button class="dialog-btn dialog-btn--save" id="rename-save">Save</button>
            </div>
          </div>
        </div>
      ` : ''}
    `;

    this.attachListeners();
  }

  private attachListeners() {
    // New button
    const newBtn = this._shadow.querySelector('.new-btn');
    newBtn?.addEventListener('click', () => this.handleNew());

    // Clear all button
    const clearAllBtn = this._shadow.querySelector('.clear-all-btn');
    clearAllBtn?.addEventListener('click', () => this.handleClearAll());

    // Session items
    const sessions = this._shadow.querySelectorAll('.session');
    sessions.forEach(el => {
      const id = el.getAttribute('data-id');
      if (!id) return;

      const contentBtn = el.querySelector('.session-content');
      const deleteBtn = el.querySelector('.delete-btn');

      contentBtn?.addEventListener('click', () => this.handleSelect(id));
      deleteBtn?.addEventListener('click', (e) => this.handleDelete(id, e as MouseEvent));
      el.addEventListener('contextmenu', (e) => this.showContextMenu(id, e as MouseEvent));
    });

    // Context menu
    const ctxMenu = this._shadow.querySelector('#ctx-menu');
    if (ctxMenu) {
      const session = this._state.sessions.find(s => s.id === this._state.contextMenuId);
      ctxMenu.querySelectorAll('.menu-item').forEach(item => {
        const action = item.getAttribute('data-action');
        item.addEventListener('click', (e) => {
          e.stopPropagation();
          if (!this._state.contextMenuId) return;
          if (action === 'rename') {
            this.showRenameDialog(this._state.contextMenuId, session?.title || '');
          } else if (action === 'export') {
            this.handleExport(this._state.contextMenuId);
          } else if (action === 'delete') {
            this.handleDelete(this._state.contextMenuId, e as MouseEvent);
          }
        });
      });

      // Position context menu
      const rect = this.getBoundingClientRect();
      (ctxMenu as HTMLElement).style.left = `${Math.min(rect.right - 150, rect.left + 20)}px`;
      (ctxMenu as HTMLElement).style.top = `${Math.min(rect.bottom - 120, rect.top + 100)}px`;
    }

    // Rename dialog
    const renameOverlay = this._shadow.querySelector('#rename-overlay');
    if (renameOverlay) {
      const input = this._shadow.querySelector('#rename-input') as HTMLInputElement;
      const cancelBtn = this._shadow.querySelector('#rename-cancel');
      const saveBtn = this._shadow.querySelector('#rename-save');

      input?.focus();
      input?.select();

      cancelBtn?.addEventListener('click', () => {
        this._state.renameDialogId = null;
        this.render();
      });

      saveBtn?.addEventListener('click', () => {
        if (this._state.renameDialogId && input?.value.trim()) {
          this.handleRename(this._state.renameDialogId, input.value.trim());
        }
      });

      input?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && input.value.trim() && this._state.renameDialogId) {
          this.handleRename(this._state.renameDialogId, input.value.trim());
        } else if (e.key === 'Escape') {
          this._state.renameDialogId = null;
          this.render();
        }
      });

      // Click overlay to close
      renameOverlay.addEventListener('click', (e) => {
        if (e.target === renameOverlay) {
          this._state.renameDialogId = null;
          this.render();
        }
      });
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

customElements.define('history-list', HistoryList);

export default HistoryList;

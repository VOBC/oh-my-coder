// src/components/HistoryList.ts — <history-list> web component
// P1-3: Enhanced with search/filter, relative time, right-click menu, empty state

export interface HistorySession {
  id: string;
  title: string;
  updated: string; // ISO timestamp
  model?: string;
}

interface HistoryListState {
  sessions: HistorySession[];
  filteredSessions: HistorySession[];
  activeId: string;
  searchQuery: string;
  contextMenuId: string | null;
  contextMenuPos: { x: number; y: number };
  renameDialogId: string | null;
  renameValue: string;
}

// ── Relative Time Formatter ───────────────────────────────────────────────────
function formatRelativeTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return '刚刚';
  if (diffMin < 60) return `${diffMin}分钟前`;
  if (diffHour < 24) return `${diffHour}小时前`;
  if (diffDay === 1) return '昨天';
  if (diffDay < 7) return `${diffDay}天前`;
  if (diffDay < 30) return `${Math.floor(diffDay / 7)}周前`;
  
  // Older: show date
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

class HistoryList extends HTMLElement {
  private _state: HistoryListState = {
    sessions: [],
    filteredSessions: [],
    activeId: '',
    searchQuery: '',
    contextMenuId: null,
    contextMenuPos: { x: 0, y: 0 },
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
    document.addEventListener('click', this._handleOutsideClick.bind(this));
    document.addEventListener('keydown', this._handleKeyDown.bind(this));
  }

  disconnectedCallback() {
    document.removeEventListener('click', this._handleOutsideClick.bind(this));
    document.removeEventListener('keydown', this._handleKeyDown.bind(this));
  }

  private _handleOutsideClick(e: MouseEvent) {
    const path = e.composedPath();
    if (!path.includes(this._shadow.host)) {
      this._state.contextMenuId = null;
      this._state.renameDialogId = null;
      this.render();
    }
  }

  private _handleKeyDown(e: KeyboardEvent) {
    // Close context menu on Escape
    if (e.key === 'Escape' && this._state.contextMenuId) {
      this._state.contextMenuId = null;
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
    this._filterSessions();
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

  private _filterSessions() {
    const query = this._state.searchQuery.toLowerCase().trim();
    if (!query) {
      this._state.filteredSessions = [...this._state.sessions];
    } else {
      this._state.filteredSessions = this._state.sessions.filter(s =>
        s.title.toLowerCase().includes(query) ||
        (s.model && s.model.toLowerCase().includes(query))
      );
    }
  }

  private handleSelect(id: string) {
    this._state.activeId = id;
    this._state.contextMenuId = null;
    this.render();
    this._onSelect?.(id);
    this.dispatchEvent(new CustomEvent('session-select', { detail: { id }, bubbles: true, composed: true }));
  }

  private handleDelete(id: string, e?: Event) {
    e?.stopPropagation();
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

  private handleSearch(query: string) {
    this._state.searchQuery = query;
    this._filterSessions();
    this.render();
  }

  private showContextMenu(id: string, e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    this._state.contextMenuId = id;
    this._state.contextMenuPos = { x: e.clientX, y: e.clientY };
    this.render();
  }

  private showRenameDialog(id: string, currentTitle: string) {
    this._state.contextMenuId = null;
    this._state.renameDialogId = id;
    this._state.renameValue = currentTitle;
    this.render();
  }

  private render() {
    const { filteredSessions, activeId, searchQuery, contextMenuId, contextMenuPos, renameDialogId, renameValue, sessions } = this._state;
    const hasSessions = sessions.length > 0;

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

        /* Search */
        .search-box {
          padding: 12px 16px;
          border-bottom: 1px solid #333;
        }

        .search-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .search-icon {
          position: absolute;
          left: 10px;
          font-size: 12px;
          opacity: 0.5;
        }

        .search-input {
          width: 100%;
          padding: 8px 10px 8px 28px;
          border: 1px solid #333;
          border-radius: 6px;
          background: #0f0f0f;
          color: #e5e5e5;
          font-size: 13px;
          outline: none;
          transition: border-color 0.15s ease;
        }

        .search-input:focus { border-color: #d4a017; }

        .search-input::placeholder { color: #666; }

        .search-clear {
          position: absolute;
          right: 8px;
          width: 16px;
          height: 16px;
          border: none;
          border-radius: 50%;
          background: #444;
          color: #888;
          font-size: 10px;
          cursor: pointer;
          display: ${searchQuery ? 'flex' : 'none'};
          align-items: center;
          justify-content: center;
        }

        .search-clear:hover { background: #555; color: #aaa; }

        .search-stats {
          font-size: 11px;
          color: #666;
          margin-top: 6px;
          padding-left: 4px;
        }

        .list {
          flex: 1;
          overflow-y: auto;
          padding: 8px;
        }

        /* Empty State */
        .empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 20px;
          text-align: center;
        }

        .empty-icon {
          font-size: 48px;
          margin-bottom: 16px;
          opacity: 0.3;
        }

        .empty-title {
          font-size: 14px;
          font-weight: 500;
          color: #888;
          margin-bottom: 8px;
        }

        .empty-desc {
          font-size: 12px;
          color: #666;
          line-height: 1.5;
        }

        .empty-new-btn {
          margin-top: 16px;
          padding: 8px 16px;
          border: 1px solid #d4a017;
          border-radius: 6px;
          background: transparent;
          color: #d4a017;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .empty-new-btn:hover {
          background: #d4a01720;
        }

        /* No Search Results */
        .no-results {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 40px 20px;
          text-align: center;
          color: #666;
        }

        .no-results-icon {
          font-size: 32px;
          margin-bottom: 12px;
          opacity: 0.5;
        }

        /* Session Item */
        .session {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          margin-bottom: 4px;
          border-radius: 8px;
          cursor: pointer;
          transition: all 0.15s ease;
          position: relative;
          user-select: none;
          border: 1px solid transparent;
        }

        .session:hover { background: #2a2a2a; }

        .session.active {
          background: #d4a01715;
          border-color: #d4a01740;
        }

        .session.active .session-title { color: #d4a017; }

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
        }

        .session-time {
          color: #666;
        }

        .session.active .session-time {
          color: #888;
        }

        .session-model {
          color: #d4a017;
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.3px;
          font-weight: 500;
          background: #d4a01715;
          padding: 2px 6px;
          border-radius: 3px;
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
          min-width: 160px;
          z-index: 10000;
          box-shadow: 0 8px 24px rgba(0,0,0,0.5);
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
          transition: all 0.15s ease;
        }

        .menu-item:hover { background: #3a3a3a; color: #fff; }
        .menu-item.danger { color: #ff8888; }
        .menu-item.danger:hover { background: #ff444420; color: #ff6666; }

        .menu-icon { width: 16px; text-align: center; font-size: 14px; }
        .menu-shortcut { margin-left: auto; font-size: 11px; color: #666; }

        /* Rename Dialog */
        .dialog-overlay {
          position: fixed;
          top: 0; left: 0; right: 0; bottom: 0;
          background: rgba(0,0,0,0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10001;
          backdrop-filter: blur(4px);
        }

        .dialog {
          background: #2a2a2a;
          border: 1px solid #444;
          border-radius: 12px;
          padding: 20px;
          min-width: 320px;
          box-shadow: 0 20px 60px rgba(0,0,0,0.5);
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
          transition: border-color 0.15s ease;
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

        .footer-stats {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 11px;
          color: #666;
          margin-bottom: 8px;
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
        <button class="new-btn" title="New Chat (⌘N)">+</button>
      </div>

      ${hasSessions ? `
        <div class="search-box">
          <div class="search-input-wrapper">
            <span class="search-icon">🔍</span>
            <input 
              type="text" 
              class="search-input" 
              placeholder="搜索会话..."
              value="${this.escapeHtml(searchQuery)}"
              id="search-input"
            />
            <button class="search-clear" id="search-clear">✕</button>
          </div>
          ${searchQuery ? `<div class="search-stats">找到 ${filteredSessions.length} 个结果</div>` : ''}
        </div>
      ` : ''}

      <div class="list">
        ${!hasSessions ? `
          <div class="empty">
            <div class="empty-icon">💬</div>
            <div class="empty-title">暂无会话</div>
            <div class="empty-desc">开始新对话，让 AI 帮你写代码、<br/>解答问题或处理任务</div>
            <button class="empty-new-btn" id="empty-new-btn">开始新对话</button>
          </div>
        ` : filteredSessions.length === 0 ? `
          <div class="no-results">
            <div class="no-results-icon">🔍</div>
            <div>未找到匹配的会话</div>
          </div>
        ` : filteredSessions.map(s => `
          <div class="session ${s.id === activeId ? 'active' : ''}" data-id="${s.id}">
            <button class="session-content">
              <div class="session-title">${this.escapeHtml(s.title)}</div>
              <div class="session-meta">
                <span class="session-time">${formatRelativeTime(s.updated)}</span>
                ${s.model ? `<span class="session-model">${this.escapeHtml(s.model)}</span>` : ''}
              </div>
            </button>
            <button class="delete-btn" title="Delete">✕</button>
          </div>
        `).join('')}
      </div>

      ${hasSessions && filteredSessions.length > 0 ? `
        <div class="footer">
          <div class="footer-stats">
            <span>${filteredSessions.length} 个会话</span>
            <span>${sessions.length > filteredSessions.length ? `(共 ${sessions.length})` : ''}</span>
          </div>
          <button class="clear-all-btn">清空所有历史</button>
        </div>
      ` : ''}

      ${contextMenuId ? `
        <div class="context-menu" id="ctx-menu" style="left: ${contextMenuPos.x}px; top: ${contextMenuPos.y}px;">
          <div class="menu-item" data-action="rename">
            <span class="menu-icon">✏️</span>
            <span>重命名</span>
            <span class="menu-shortcut">↵</span>
          </div>
          <div class="menu-item" data-action="export">
            <span class="menu-icon">📤</span>
            <span>导出</span>
          </div>
          <div class="menu-item danger" data-action="delete">
            <span class="menu-icon">🗑️</span>
            <span>删除</span>
            <span class="menu-shortcut">⌫</span>
          </div>
        </div>
      ` : ''}

      ${renameDialogId ? `
        <div class="dialog-overlay" id="rename-overlay">
          <div class="dialog">
            <div class="dialog-title">重命名会话</div>
            <input type="text" class="dialog-input" id="rename-input" value="${this.escapeHtml(renameValue)}" placeholder="输入新名称..." />
            <div class="dialog-actions">
              <button class="dialog-btn dialog-btn--cancel" id="rename-cancel">取消</button>
              <button class="dialog-btn dialog-btn--save" id="rename-save">保存</button>
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

    // Empty state new button
    const emptyNewBtn = this._shadow.querySelector('#empty-new-btn');
    emptyNewBtn?.addEventListener('click', () => this.handleNew());

    // Search input
    const searchInput = this._shadow.querySelector('#search-input') as HTMLInputElement;
    searchInput?.addEventListener('input', (e) => {
      this.handleSearch((e.target as HTMLInputElement).value);
    });

    // Search clear
    const searchClear = this._shadow.querySelector('#search-clear');
    searchClear?.addEventListener('click', () => {
      this.handleSearch('');
      searchInput?.focus();
    });

    // Clear all button
    const clearAllBtn = this._shadow.querySelector('.clear-all-btn');
    clearAllBtn?.addEventListener('click', () => this.handleClearAll());

    // Session items
    const sessionEls = this._shadow.querySelectorAll('.session');
    sessionEls.forEach(el => {
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

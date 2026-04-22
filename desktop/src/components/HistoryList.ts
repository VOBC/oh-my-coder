// src/components/HistoryList.ts — <history-list> web component
// Shadow DOM encapsulated history list with session persistence

export interface HistorySession {
  id: string;
  title: string;
  updated: string;
  model?: string;
}

interface HistoryListState {
  sessions: HistorySession[];
  activeId: string;
}

class HistoryList extends HTMLElement {
  private _state: HistoryListState = { sessions: [], activeId: '' };
  private _shadow: ShadowRoot;
  private _onSelect?: (id: string) => void;
  private _onDelete?: (id: string) => void;
  private _onNew?: () => void;

  static get observedAttributes() {
    return ['active-id'];
  }

  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: 'open' });
    this.render();
  }

  attributeChangedCallback(name: string, oldVal: string, newVal: string) {
    if (name === 'active-id' && oldVal !== newVal) {
      this._state.activeId = newVal || '';
      this.render();
    }
  }

  // Public API: Set session data
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
  set onSelect(handler: (id: string) => void) {
    this._onSelect = handler;
  }

  set onDelete(handler: (id: string) => void) {
    this._onDelete = handler;
  }

  set onNew(handler: () => void) {
    this._onNew = handler;
  }

  private handleSelect(id: string) {
    this._state.activeId = id;
    this.render();
    this._onSelect?.(id);
    this.dispatchEvent(new CustomEvent('session-select', {
      detail: { id },
      bubbles: true,
      composed: true,
    }));
  }

  private handleDelete(id: string, e: Event) {
    e.stopPropagation();
    this._onDelete?.(id);
    this.dispatchEvent(new CustomEvent('session-delete', {
      detail: { id },
      bubbles: true,
      composed: true,
    }));
  }

  private handleNew() {
    this._onNew?.();
    this.dispatchEvent(new CustomEvent('session-new', {
      bubbles: true,
      composed: true,
    }));
  }

  private render() {
    const { sessions, activeId } = this._state;

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

        .new-btn:hover {
          background: #e5b028;
        }

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
        }

        .session:hover {
          background: #2a2a2a;
        }

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
          margin-bottom: 2px;
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

        .session:hover .delete-btn {
          opacity: 1;
        }

        .delete-btn:hover {
          background: #ff444420;
          color: #ff6666;
        }

        /* Scrollbar styling */
        .list::-webkit-scrollbar {
          width: 6px;
        }

        .list::-webkit-scrollbar-track {
          background: transparent;
        }

        .list::-webkit-scrollbar-thumb {
          background: #444;
          border-radius: 3px;
        }

        .list::-webkit-scrollbar-thumb:hover {
          background: #555;
        }
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
              <button class="delete-btn" title="Delete session">✕</button>
            </div>
          `).join('')}
      </div>
    `;

    this.attachListeners();
  }

  private attachListeners() {
    const newBtn = this._shadow.querySelector('.new-btn');
    newBtn?.addEventListener('click', () => this.handleNew());

    const sessions = this._shadow.querySelectorAll('.session');
    sessions.forEach(el => {
      const id = el.getAttribute('data-id');
      if (!id) return;

      const contentBtn = el.querySelector('.session-content');
      const deleteBtn = el.querySelector('.delete-btn');

      contentBtn?.addEventListener('click', () => this.handleSelect(id));
      deleteBtn?.addEventListener('click', (e) => this.handleDelete(id, e));
    });
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Register the custom element
customElements.define('history-list', HistoryList);

export default HistoryList;

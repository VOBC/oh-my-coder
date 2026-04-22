// src/components/ToolCard.ts — <tool-card> web component
// Replaces inline ToolCallCard rendering with a reusable custom element

export interface ToolCallData {
  tool: string;
  status: 'pending' | 'success' | 'error';
  content?: string;
}

const STATUS_ICON: Record<string, string> = {
  pending: '⏳',
  success: '✓',
  error: '✗',
};

const STATUS_COLOR: Record<string, string> = {
  pending: 'var(--amber, #f59e0b)',
  success: 'var(--green, #4ade80)',
  error: 'var(--red, #ef4444)',
};

export class ToolCardElement extends HTMLElement {
  private _tool: string = '';
  private _status: ToolCallData['status'] = 'pending';
  private _content: string = '';

  static get observedAttributes() {
    return ['tool', 'status', 'content'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.render();
  }

  attributeChangedCallback(name: string, oldValue: string | null, newValue: string | null) {
    if (oldValue === newValue) return;
    switch (name) {
      case 'tool':
        this._tool = newValue || '';
        break;
      case 'status':
        this._status = (newValue as ToolCallData['status']) || 'pending';
        break;
      case 'content':
        this._content = newValue || '';
        break;
    }
    this.render();
  }

  get tool() { return this._tool; }
  set tool(value: string) {
    this._tool = value;
    this.setAttribute('tool', value);
    this.render();
  }

  get status() { return this._status; }
  set status(value: ToolCallData['status']) {
    this._status = value;
    this.setAttribute('status', value);
    this.render();
  }

  get content() { return this._content; }
  set content(value: string) {
    this._content = value;
    this.setAttribute('content', value);
    this.render();
  }

  private render() {
    const icon = STATUS_ICON[this._status] || '⏳';
    const color = STATUS_COLOR[this._status] || STATUS_COLOR.pending;

    this.shadowRoot!.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }
        .tool-card {
          background: rgba(0, 0, 0, 0.3);
          border: 1px solid rgba(212, 160, 23, 0.2);
          border-radius: 6px;
          padding: 8px 12px;
          margin: 4px 0;
        }
        .tool-card--pending {
          border-left: 3px solid ${STATUS_COLOR.pending};
        }
        .tool-card--success {
          border-left: 3px solid ${STATUS_COLOR.success};
        }
        .tool-card--error {
          border-left: 3px solid ${STATUS_COLOR.error};
        }
        .tool-card__header {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
        }
        .tool-card__icon {
          font-size: 14px;
        }
        .tool-card__name {
          font-weight: 600;
          color: #d4a017;
          flex: 1;
        }
        .tool-card__status {
          text-transform: uppercase;
          font-size: 10px;
          letter-spacing: 0.5px;
        }
        .tool-card__content {
          margin-top: 6px;
          padding: 6px 8px;
          background: rgba(0, 0, 0, 0.4);
          border-radius: 4px;
          font-size: 11px;
          color: #a0a0a0;
          white-space: pre-wrap;
          word-break: break-word;
          max-height: 200px;
          overflow-y: auto;
        }
        .tool-card__content:empty {
          display: none;
        }
      </style>
      <div class="tool-card tool-card--${this._status}">
        <div class="tool-card__header">
          <span class="tool-card__icon">${icon}</span>
          <span class="tool-card__name">${this.escapeHtml(this._tool)}</span>
          <span class="tool-card__status" style="color: ${color}">${this._status}</span>
        </div>
        ${this._content ? `<pre class="tool-card__content">${this.escapeHtml(this._content)}</pre>` : ''}
      </div>
    `;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// Register the custom element
customElements.define('tool-card', ToolCardElement);

// Helper function to create a tool-card element from data
export function createToolCard(data: ToolCallData): ToolCardElement {
  const card = document.createElement('tool-card') as ToolCardElement;
  card.tool = data.tool;
  card.status = data.status;
  if (data.content) card.content = data.content;
  return card;
}

// src/ui/diff/diff-viewer.ts — Side-by-side diff visualization component
// Uses diff-match-patch for precise character-level diff

import DiffMatchPatch from 'diff-match-patch';

const TAG_NAME = 'diff-viewer';

/**
 * DiffViewer Web Component
 * 
 * Renders a side-by-side diff view with:
 * - Left panel: original content (red for deletions)
 * - Right panel: new content (green for additions)
 * - Line numbers on both sides
 * 
 * Attributes:
 * - original: string — original content
 * - modified: string — modified content
 * 
 * Usage:
 * ```html
 * <diff-viewer original="old text" modified="new text"></diff-viewer>
 * ```
 */
export class DiffViewerElement extends HTMLElement {
  private _original: string = '';
  private _modified: string = '';
  private _onAccept: (() => void) | null = null;
  private _onReject: (() => void) | null = null;
  private shadow: ShadowRoot;

  static get observedAttributes() {
    return ['original', 'modified'];
  }

  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: 'open' });
  }

  get original(): string {
    return this._original;
  }

  set original(value: string) {
    this._original = value;
    this.render();
  }

  get modified(): string {
    return this._modified;
  }

  set modified(value: string) {
    this._modified = value;
    this.render();
  }

  get onAccept(): (() => void) | null {
    return this._onAccept;
  }

  set onAccept(handler: (() => void) | null) {
    this._onAccept = handler;
  }

  get onReject(): (() => void) | null {
    return this._onReject;
  }

  set onReject(handler: (() => void) | null) {
    this._onReject = handler;
  }

  attributeChangedCallback(name: string, oldValue: string, newValue: string) {
    if (name === 'original' && oldValue !== newValue) {
      this._original = newValue;
      this.render();
    }
    if (name === 'modified' && oldValue !== newValue) {
      this._modified = newValue;
      this.render();
    }
  }

  connectedCallback() {
    this.render();
  }

  /**
   * Compute diff using diff-match-patch
   * Returns array of { type: 'add'|'del'|'eq', text: string }
   */
  private computeDiff(original: string, modified: string): DiffPart[] {
    const dmp = new DiffMatchPatch();
    const diffs = dmp.diff_main(original, modified);
    dmp.diff_cleanupSemantic(diffs);
    return diffs.map(([op, text]) => {
      if (op === DiffMatchPatch.DIFF_DELETE) return { type: 'del', text };
      if (op === DiffMatchPatch.DIFF_INSERT) return { type: 'add', text };
      return { type: 'eq', text };
    });
  }

  /**
   * Convert diff parts to line-based diff lines
   * Each line has a type, content, and line numbers
   */
  private diffToLines(diffParts: DiffPart[]): DiffLine[] {
    const lines: DiffLine[] = [];
    let leftLine = 0;
    let rightLine = 0;

    for (const part of diffParts) {
      const partLines = part.text.split('\n');
      
      // Handle each line in the part
      for (let i = 0; i < partLines.length; i++) {
        const lineContent = partLines[i];
        const isLastLine = i === partLines.length - 1;
        
        // Skip empty line at end if it's just trailing newline
        if (isLastLine && lineContent === '' && partLines.length > 1) continue;
        
        if (part.type === 'del') {
          leftLine++;
          lines.push({
            type: 'del',
            content: lineContent,
            leftLine,
            rightLine: null,
          });
        } else if (part.type === 'add') {
          rightLine++;
          lines.push({
            type: 'add',
            content: lineContent,
            leftLine: null,
            rightLine,
          });
        } else {
          leftLine++;
          rightLine++;
          lines.push({
            type: 'eq',
            content: lineContent,
            leftLine,
            rightLine,
          });
        }
      }
    }

    return lines;
  }

  private render() {
    if (!this._original && !this._modified) {
      this.shadow.innerHTML = '<div class="diff-empty">No content to compare</div>';
      return;
    }

    const diffParts = this.computeDiff(this._original, this._modified);
    const lines = this.diffToLines(diffParts);

    // Build line-by-line side-by-side view
    const leftLines: string[] = [];
    const rightLines: string[] = [];

    for (const line of lines) {
      if (line.type === 'del') {
        // Deletion: show in left panel (red), right panel empty
        leftLines.push(this.renderLine(line, 'left'));
        rightLines.push(this.renderEmptyLine(line.leftLine));
      } else if (line.type === 'add') {
        // Addition: show in right panel (green), left panel empty
        leftLines.push(this.renderEmptyLine(line.rightLine));
        rightLines.push(this.renderLine(line, 'right'));
      } else {
        // Equal: show in both panels
        leftLines.push(this.renderLine(line, 'left'));
        rightLines.push(this.renderLine(line, 'right'));
      }
    }

    this.shadow.innerHTML = `
      <style>${this.getStyles()}</style>
      <div class="diff-container">
        <div class="diff-header">
          <div class="diff-header__side diff-header__side--left">
            <span class="diff-header__label">Original</span>
            <span class="diff-header__stats diff-header__stats--del">${lines.filter(l => l.type === 'del').length} deleted</span>
          </div>
          <div class="diff-header__side diff-header__side--right">
            <span class="diff-header__label">Modified</span>
            <span class="diff-header__stats diff-header__stats--add">${lines.filter(l => l.type === 'add').length} added</span>
          </div>
        </div>
        <div class="diff-body">
          <div class="diff-panel diff-panel--left">
            ${leftLines.join('')}
          </div>
          <div class="diff-panel diff-panel--right">
            ${rightLines.join('')}
          </div>
        </div>
        <div class="diff-actions">
          <button class="diff-btn diff-btn--accept" id="btn-accept">
            <span class="diff-btn__icon">✓</span>
            <span class="diff-btn__text">Accept</span>
          </button>
          <button class="diff-btn diff-btn--reject" id="btn-reject">
            <span class="diff-btn__icon">✕</span>
            <span class="diff-btn__text">Reject</span>
          </button>
        </div>
      </div>
    `;
    
    // Bind button events after rendering
    this.bindEvents();
  }

  private renderLine(line: DiffLine, side: 'left' | 'right'): string {
    const lineNum = side === 'left' ? line.leftLine : line.rightLine;
    const typeClass = line.type === 'del' ? 'diff-line--del' : 
                      line.type === 'add' ? 'diff-line--add' : '';
    
    return `
      <div class="diff-line ${typeClass}">
        <span class="diff-line__num">${lineNum ?? ''}</span>
        <span class="diff-line__marker">${line.type === 'del' ? '−' : line.type === 'add' ? '+' : ' '}</span>
        <span class="diff-line__content">${this.escapeHtml(line.content) || '&nbsp;'}</span>
      </div>
    `;
  }

  private renderEmptyLine(lineNum: number | null): string {
    return `
      <div class="diff-line diff-line--empty">
        <span class="diff-line__num">${lineNum ?? ''}</span>
        <span class="diff-line__marker"></span>
        <span class="diff-line__content"></span>
      </div>
    `;
  }

  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  /**
   * Bind button click events after rendering
   */
  private bindEvents(): void {
    const acceptBtn = this.shadow.querySelector('#btn-accept');
    const rejectBtn = this.shadow.querySelector('#btn-reject');
    
    if (acceptBtn) {
      acceptBtn.addEventListener('click', () => {
        if (this._onAccept) {
          this._onAccept();
        }
        // Dispatch custom event for external listeners
        this.dispatchEvent(new CustomEvent('accept', { 
          bubbles: true,
          detail: { original: this._original, modified: this._modified }
        }));
      });
    }
    
    if (rejectBtn) {
      rejectBtn.addEventListener('click', () => {
        if (this._onReject) {
          this._onReject();
        }
        // Dispatch custom event for external listeners
        this.dispatchEvent(new CustomEvent('reject', {
          bubbles: true,
          detail: { original: this._original, modified: this._modified }
        }));
      });
    }
  }

  private getStyles(): string {
    return `
      :host {
        display: block;
        font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
        font-size: 12px;
        line-height: 1.5;
        background: #1a1b26;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #3b3f5c;
      }

      .diff-container {
        display: flex;
        flex-direction: column;
        height: 100%;
        max-height: 500px;
      }

      .diff-header {
        display: flex;
        background: #24283b;
        border-bottom: 1px solid #3b3f5c;
      }

      .diff-header__side {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 12px;
      }

      .diff-header__side--left {
        border-right: 1px solid #3b3f5c;
      }

      .diff-header__label {
        font-weight: 600;
        color: #a9b1d6;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      .diff-header__stats {
        font-size: 10px;
        font-weight: 500;
        padding: 2px 6px;
        border-radius: 4px;
      }

      .diff-header__stats--del {
        background: rgba(248, 113, 113, 0.2);
        color: #f87171;
      }

      .diff-header__stats--add {
        background: rgba(74, 222, 128, 0.2);
        color: #4ade80;
      }

      .diff-body {
        display: flex;
        flex: 1;
        overflow: auto;
      }

      .diff-panel {
        flex: 1;
        overflow-x: auto;
        overflow-y: hidden;
      }

      .diff-panel--left {
        border-right: 1px solid #3b3f5c;
      }

      .diff-line {
        display: flex;
        align-items: stretch;
        min-height: 18px;
      }

      .diff-line--del {
        background: rgba(248, 113, 113, 0.15);
      }

      .diff-line--add {
        background: rgba(74, 222, 128, 0.15);
      }

      .diff-line--empty {
        background: transparent;
      }

      .diff-line__num {
        min-width: 40px;
        padding: 0 8px;
        background: #24283b;
        color: #565f89;
        text-align: right;
        user-select: none;
        border-right: 1px solid #3b3f5c;
      }

      .diff-line__marker {
        min-width: 16px;
        text-align: center;
        color: #565f89;
        user-select: none;
      }

      .diff-line--del .diff-line__marker {
        color: #f87171;
      }

      .diff-line--add .diff-line__marker {
        color: #4ade80;
      }

      .diff-line__content {
        flex: 1;
        padding: 0 8px;
        white-space: pre;
        color: #c0caf5;
        min-width: 0;
      }

      .diff-line--del .diff-line__content {
        text-decoration: line-through;
        color: #f87171;
      }

      .diff-line--add .diff-line__content {
        color: #4ade80;
      }

      .diff-empty {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100px;
        color: #565f89;
        font-style: italic;
      }

      /* Scrollbar styling */
      .diff-body::-webkit-scrollbar,
      .diff-panel::-webkit-scrollbar {
        width: 8px;
        height: 8px;
      }

      .diff-body::-webkit-scrollbar-track,
      .diff-panel::-webkit-scrollbar-track {
        background: #1a1b26;
      }

      .diff-body::-webkit-scrollbar-thumb,
      .diff-panel::-webkit-scrollbar-thumb {
        background: #3b3f5c;
        border-radius: 4px;
      }

      .diff-body::-webkit-scrollbar-thumb:hover,
      .diff-panel::-webkit-scrollbar-thumb:hover {
        background: #565f89;
      }

      /* Action buttons */
      .diff-actions {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
        padding: 12px 16px;
        background: #24283b;
        border-top: 1px solid #3b3f5c;
      }

      .diff-btn {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 16px;
        border: none;
        border-radius: 6px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.15s ease;
      }

      .diff-btn__icon {
        font-size: 14px;
      }

      .diff-btn--accept {
        background: #4ade80;
        color: #052e16;
      }

      .diff-btn--accept:hover {
        background: #22c55e;
        box-shadow: 0 2px 8px rgba(74, 222, 128, 0.3);
      }

      .diff-btn--reject {
        background: #f87171;
        color: #450a0a;
      }

      .diff-btn--reject:hover {
        background: #ef4444;
        box-shadow: 0 2px 8px rgba(248, 113, 113, 0.3);
      }
    `;
  }
}

// Types
interface DiffPart {
  type: 'add' | 'del' | 'eq';
  text: string;
}

interface DiffLine {
  type: 'add' | 'del' | 'eq';
  content: string;
  leftLine: number | null;
  rightLine: number | null;
}

// Register custom element
if (!customElements.get(TAG_NAME)) {
  customElements.define(TAG_NAME, DiffViewerElement);
}

// Export for programmatic use
export function createDiffViewer(
  original: string, 
  modified: string,
  callbacks?: { onAccept?: () => void; onReject?: () => void }
): DiffViewerElement {
  const el = document.createElement(TAG_NAME) as DiffViewerElement;
  el.original = original;
  el.modified = modified;
  if (callbacks?.onAccept) el.onAccept = callbacks.onAccept;
  if (callbacks?.onReject) el.onReject = callbacks.onReject;
  return el;
}

export { TAG_NAME };

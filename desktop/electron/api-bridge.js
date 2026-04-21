// electron/api-bridge.js — Bridge between Electron main process and omc CLI
const { execSync, exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// ── Resolve omc binary ───────────────────────────────────────────────────────
function resolveOmcBin() {
  const OMC_ROOT = path.join(__dirname, '..');
  // In packaged app: OMC_ROOT is asar root; try system PATH first
  // In dev: try local .venv/bin/omc or bin/omc
  const candidates = [
    'omc',  // system PATH (most reliable in production)
    path.join(OMC_ROOT, '.venv', 'bin', 'omc'),
    path.join(OMC_ROOT, 'bin', 'omc'),
    path.join(OMC_ROOT, '..', '.venv', 'bin', 'omc'), // desktop/../.venv
  ];
  for (const c of candidates) {
    try {
      if (c === 'omc') {
        execSync('omc --version', { stdio: 'pipe', timeout: 5000 });
      } else if (fs.existsSync(c)) {
        execSync(c + ' --version', { stdio: 'pipe', timeout: 5000 });
      }
      return c;
    } catch {}
  }
  return null;
}

let _cachedOmcBin = null;

function getOmcBin() {
  if (_cachedOmcBin) return _cachedOmcBin;
  _cachedOmcBin = resolveOmcBin();
  return _cachedOmcBin;
}

// ── Helper: run omc CLI and parse JSON output ────────────────────────────────

/**
 * Execute omc command and return parsed result.
 * @param {string[]} args - CLI arguments
 * @param {object} opts - extra options for execSync
 * @returns {{ok: boolean, data?: any, error?: string}}
 */
function runOmc(args, opts = {}) {
  const bin = getOmcBin();
  if (!bin) {
    return { ok: false, error: 'omc CLI not found. Install oh-my-coder: pip install oh-my-coder' };
  }

  const cwd = opts.cwd || process.cwd();
  const timeout = opts.timeout || 15000;

  try {
    const stdout = execSync(
      `${typeof bin === 'string' && bin.includes(' ') ? `"${bin}"` : bin} ${args.map(a => a.includes(' ') ? `"${a}"` : a).join(' ')} --json`,
      { encoding: 'utf-8', cwd, timeout, stdio: ['pipe', 'pipe', 'pipe'] }
    );
    const data = JSON.parse(stdout.trim());
    return { ok: true, data };
  } catch (e) {
    // Some commands may output non-JSON on stderr but still have useful stdout
    let rawError = '';
    if (e.stderr) rawError = e.stderr.toString().trim();
    if (e.stdout) {
      try {
        const data = JSON.parse(e.stdout.toString().trim());
        return { ok: true, data };
      } catch {}
    }
    return { ok: false, error: rawError || e.message || String(e) };
  }
}

// ── Public API ────────────────────────────────────────────────────────────────

const ApiBridge = {
  /**
   * Get model list from `omc model list --json`
   * Returns normalized array: [{id, name, provider, tier, context, endpoint, pricing}]
   */
  getModelList() {
    const result = runOmc(['model', 'list']);
    if (!result.ok || !Array.isArray(result.data)) {
      console.error('[api-bridge] model list failed:', result.error);
      return [];
    }
    // Normalize: map omc's format to frontend Model type
    return result.data.map(m => ({
      id: m.model || m.name?.toLowerCase().replace(/[^a-z0-9]/g, '-'),
      name: m.name,
      provider: m.provider,
      tier: m.tier || 'medium',
      context: m.context || null,
      endpoint: m.endpoint || '',
      pricing: m.pricing || {},
      features: m.features || [],
    }));
  },

  /**
   * Get current active model
   */
  getCurrentModel() {
    const result = runOmc(['model', 'current']);
    if (!result.ok) return null;
    // Could be string or object
    if (typeof result.data === 'string') return result.data;
    if (result.data && result.data.model) return result.data.model;
    return result.data;
  },

  /**
   * Switch model
   */
  switchModel(modelId) {
    const bin = getOmcBin();
    if (!bin) return { ok: false, error: 'omc not found' };
    try {
      const stdout = execSync(`${bin} model switch "${modelId}"`, {
        encoding: 'utf-8', timeout: 10000,
      });
      return { ok: true, output: stdout.trim() };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  },

  /**
   * Send chat message to omc
   * Returns Promise<{code, stdout, stderr}>
   */
  chatSend(event, { message, model }) {
    return new Promise((resolve) => {
      const bin = getOmcBin();
      if (!bin) {
        resolve({ code: 1, stdout: '', stderr: 'omc CLI not found' });
        return;
      }

      const args = ['run', '--no-interactive', '--json', message];
      if (model) args.push('--model', model);

      const child = spawn(bin, args, {
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let stdout = '', stderr = '';
      child.stdout.on('data', (d) => {
        stdout += d.toString();
        if (event && event.sender) {
          event.sender.send('omc:chat:chunk', d.toString());
        }
      });
      child.stderr.on('data', (d) => {
        stderr += d.toString();
        if (event && event.sender) {
          event.sender.send('omc:chat:error', d.toString());
        }
      });
      child.on('close', (code) => resolve({ code, stdout, stderr }));
      child.on('error', (e) => resolve({ code: 1, stdout: '', stderr: e.message }));
    });
  },
};

module.exports = { ApiBridge, getOmcBin, runOmc };

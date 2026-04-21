// electron/api-bridge.js — Bridge between Electron main process and omc CLI
const { execSync, exec } = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');

// ── Resolve omc binary ───────────────────────────────────────────────────────
function resolveOmcBin() {
  const OMC_ROOT = path.resolve(path.join(__dirname, '..'));
  // Candidates ordered by priority:
  //   1. Absolute paths to known omc locations (most reliable)
  //   2. Project-local paths (dev mode)
  //   3. System PATH (production, if omc is in PATH)
  const absCandidates = [
    // macOS pip install (most common on macOS)
    path.join(os.homedir(), 'Library', 'Python', '3.9', 'bin', 'omc'),
    path.join(os.homedir(), 'Library', 'Python', '3.10', 'bin', 'omc'),
    path.join(os.homedir(), 'Library', 'Python', '3.11', 'bin', 'omc'),
    path.join(os.homedir(), 'Library', 'Python', '3.12', 'bin', 'omc'),
    path.join(os.homedir(), '.local', 'bin', 'omc'),
    // Linux
    path.join(os.homedir(), '.local', 'bin', 'omc'),
    // Windows
    path.join(process.env.APPDATA || '', 'Python', 'Scripts', 'omc.exe'),
    // Project-local (dev mode)
    path.join(OMC_ROOT, '.venv', 'bin', 'omc'),
    path.join(OMC_ROOT, 'bin', 'omc'),
    path.join(OMC_ROOT, '..', '.venv', 'bin', 'omc'),
  ];
  const allCandidates = [...absCandidates, 'omc'];  // PATH last resort

  for (const c of allCandidates) {
    try {
      if (c === 'omc') {
        execSync('omc --version', { stdio: 'pipe', timeout: 5000 });
        console.log('[api-bridge] Found omc via PATH');
      } else if (fs.existsSync(c)) {
        execSync(c + ' --version', { stdio: 'pipe', timeout: 5000 });
        console.log('[api-bridge] Found omc at:', c);
      } else {
        continue;
      }
      return c;
    } catch (e) {
      // Silently skip unavailable candidates
    }
  }
  console.warn('[api-bridge] omc CLI not found in any location');
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
    const { execFileSync } = require('child_process');
    const stdout = execFileSync(bin, [...args, '--json'], {
      encoding: 'utf-8', cwd, timeout, stdio: ['pipe', 'pipe', 'pipe'],
    });
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

const CHINESE_PROVIDERS = [
  'deepseek', 'glm', 'mimo', 'wenxin', 'tongyi', 'kimi', 'doubao',
  'hunyuan', 'minimax', 'tiangong', 'spark', 'baichuan', 'zhipu'
];

// Production-ready models (7 core providers)
// Only these models are shown in Settings and Models list
const PRODUCTION_PROVIDERS = [
  'deepseek',   // DeepSeek V3
  'glm',        // GLM-4-Flash
  'mimo',       // MiMo V2 Flash
  'kimi',       // Kimi 128K
  'doubao',     // Doubao-Pro
  'tiangong',   // TianGong 3.0
  'baichuan',   // Baichuan 4
];

const ApiBridge = {
  /**
   * Get model list from `omc model list --json`
   * Returns normalized array: [{id, name, provider, tier, context, endpoint, pricing}]
   * Only includes Chinese production models with valid endpoints.
   */
  getModelList() {
    const result = runOmc(['model', 'list']);
    if (!result.ok || !Array.isArray(result.data)) {
      console.error('[api-bridge] model list failed:', result.error);
      return [];
    }

    // Filter: only Chinese providers with valid endpoints
    let filtered = result.data.filter(m => {
      if (!CHINESE_PROVIDERS.includes(m.provider)) return false;
      if (!m.endpoint || !m.endpoint.startsWith('http')) return false;
      // Only show production-ready models (7 core providers)
      if (!PRODUCTION_PROVIDERS.includes(m.provider)) return false;
      return true;
    });

    // Deduplicate: keep one default model per provider
    // Priority: free > low > medium > high (prefer free/low as defaults)
    const seen = new Set();
    const deduped = [];
    for (const m of filtered) {
      if (!seen.has(m.provider)) {
        seen.add(m.provider);
        deduped.push(m);
      }
    }

    // Sort by PRODUCTION_PROVIDERS order
    const providerOrder = Object.fromEntries(PRODUCTION_PROVIDERS.map((p, i) => [p, i]));
    deduped.sort((a, b) => (providerOrder[a.provider] ?? 99) - (providerOrder[b.provider] ?? 99));

    return deduped.map(m => ({
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
      const { execFileSync } = require('child_process');
      const stdout = execFileSync(bin, ['model', 'switch', modelId], {
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

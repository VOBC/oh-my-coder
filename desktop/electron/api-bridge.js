// electron/api-bridge.js — Bridge between Electron main process and omc CLI
const { execFileSync, spawn } = require('child_process');
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
  // ── Model Config ───────────────────────────────────────────────────────────
  /**
   * Get all model configs from ~/.omc/config/models.json
   * @returns {Record<string, {api_key: string, base_url?: string, enabled?: boolean}>}
   */
  getModelConfigList() {
    const cfgPath = getModelConfigPath();
    try {
      if (!fs.existsSync(cfgPath)) return {};
      const raw = fs.readFileSync(cfgPath, 'utf-8');
      return JSON.parse(raw);
    } catch (e) {
      console.error('[api-bridge] getModelConfigList failed:', e.message);
      return {};
    }
  },

  /**
   * Get config for a single model
   */
  getModelConfig(modelId) {
    const all = this.getModelConfigList();
    return all[modelId] ?? null;
  },

  /**
   * Set config for a single model (partial update)
   */
  setModelConfig(modelId, cfg) {
    const cfgPath = getModelConfigPath();
    try {
      // Ensure directory exists
      const dir = path.dirname(cfgPath);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

      // Load existing
      let all = {};
      if (fs.existsSync(cfgPath)) {
        try { all = JSON.parse(fs.readFileSync(cfgPath, 'utf-8')); } catch {}
      }

      // Merge (replace only provided fields)
      all[modelId] = {
        ...(all[modelId] || {}),
        ...cfg,
        api_key: cfg.api_key ?? '',
        base_url: cfg.base_url ?? all[modelId]?.base_url ?? '',
      };

      fs.writeFileSync(cfgPath, JSON.stringify(all, null, 2), 'utf-8');
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  },

  /**
   * Delete config for a model
   */
  deleteModelConfig(modelId) {
    const cfgPath = getModelConfigPath();
    try {
      if (!fs.existsSync(cfgPath)) return { ok: true };
      const all = JSON.parse(fs.readFileSync(cfgPath, 'utf-8'));
      delete all[modelId];
      fs.writeFileSync(cfgPath, JSON.stringify(all, null, 2), 'utf-8');
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  },

  /**
   * Migrate old providers.json to new models.json
   */
  migrateProvidersConfig() {
    const providersPath = getProvidersConfigPath();
    const modelsPath = getModelConfigPath();
    try {
      if (!fs.existsSync(providersPath)) return { ok: true, migrated: 0 };
      if (fs.existsSync(modelsPath)) return { ok: true, migrated: 0 }; // already migrated

      const providers = JSON.parse(fs.readFileSync(providersPath, 'utf-8'));
      const models: Record<string, any> = {};

      // Old format: { provider: { api_key, models: [...] } }
      // New format: { "model-id": { api_key, provider } }
      for (const [provider, pcfg] of Object.entries(providers)) {
        const pc = pcfg as any;
        if (!pc.api_key) continue;
        for (const m of (pc.models || [])) {
          const modelId = typeof m === 'string' ? m : (m.id || m.model || m.name);
          if (modelId) {
            models[modelId] = { api_key: pc.api_key, base_url: pc.base_url || '', provider };
          }
        }
      }

      if (Object.keys(models).length === 0) return { ok: true, migrated: 0 };

      // Ensure directory
      const dir = path.dirname(modelsPath);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

      fs.writeFileSync(modelsPath, JSON.stringify(models, null, 2), 'utf-8');
      return { ok: true, migrated: Object.keys(models).length };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  },

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

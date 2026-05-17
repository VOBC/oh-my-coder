// electron/main.js — Oh My Coder Desktop MVP
const { app, BrowserWindow, ipcMain, Menu, shell, dialog, nativeTheme } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const { ApiBridge } = require('./api-bridge');
const { transcribeAudio } = require('./voice');

// ── Paths ────────────────────────────────────────────────────────────────────
const isDev = !app.isPackaged;
const OMC_ROOT = path.join(__dirname, '..');
const CONFIG_PATH = path.join(OMC_ROOT, '.omc');

// ── State ────────────────────────────────────────────────────────────────────
let mainWindow = null;
let omcProcess = null; // omc server child process
let omcReady = false;

// ── Helpers ───────────────────────────────────────────────────────────────────
function log(...args) {

// ── Process-level error protection ────────────────────────────────────────
process.on("uncaughtException", (err) => {
  log("UNCAUGHT EXCEPTION:", err.message, err.stack?.slice(0, 200));
});
process.on("unhandledRejection", (reason) => {
  log("UNHANDLED REJECTION:", reason);
});
  const ts = new Date().toISOString().slice(11, 23);
  console.log(`[omc:electron:${ts}]`, ...args);
}

function resolveOmcBinary() {
  // Try local omc first, then system
  const candidates = [
    path.join(OMC_ROOT, 'bin', 'omc'),
    path.join(OMC_ROOT, '.venv', 'bin', 'omc'),
    'omc',
  ];
  for (const c of candidates) {
    try {
      if (c === 'omc') {
        execSync(c + ' --version', { stdio: 'pipe' });
      } else if (fs.existsSync(c)) {
        execSync(c + ' --version', { stdio: 'pipe' });
      }
      return c;
    } catch {}
  }
  return 'omc'; // fallback to PATH
}

function ensureConfigDir() {
  try { fs.mkdirSync(CONFIG_PATH, { recursive: true }); } catch {}
  const envPath = path.join(CONFIG_PATH, '.env');
  if (!fs.existsSync(envPath)) {
    fs.writeFileSync(envPath, '# OMC Desktop Config\n# Add your API keys here:\n# OPENAI_API_KEY=sk-...\n');
  }
  return CONFIG_PATH;
}

// ── omc Server lifecycle ──────────────────────────────────────────────────────
function startOmcServer() {
  return new Promise((resolve) => {
    const omcBin = resolveOmcBinary();
    const configDir = ensureConfigDir();
    const env = { ...process.env, OMC_CONFIG_DIR: configDir };

    log('Starting omc server:', omcBin);
    omcProcess = spawn(omcBin, ['server', '--port', '7890'], {
      cwd: OMC_ROOT,
      env,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let startupBuf = '';
    omcProcess.stdout.on('data', (d) => {
      startupBuf += d.toString();
      process.stdout.write(d); // echo to terminal in dev
      if (!omcReady && startupBuf.includes('ready') || startupBuf.includes('running') || startupBuf.includes('Uvicorn running')) {
        omcReady = true;
        log('omc server ready');
        resolve();
      }
    });
    omcProcess.stderr.on('data', (d) => process.stderr.write(d));
    omcProcess.on('exit', (code) => {
      log('omc server exited with code', code);
      omcReady = false;
    });

    // Timeout fallback
    setTimeout(() => { if (!omcReady) { omcReady = true; resolve(); } }, 5000);
  });
}

function stopOmcServer() {
  if (omcProcess) {
    omcProcess.kill('SIGTERM');
    omcProcess = null;
    omcReady = false;
  }
}

// ── IPC Handlers ─────────────────────────────────────────────────────────────
function setupIpc() {
  // Get current model config
  ipcMain.handle('omc:model:list', async () => {
    const models = ApiBridge.getModelList();
    return { models };
  });

  ipcMain.handle('omc:model:current', async () => {
    return ApiBridge.getCurrentModel() || 'glm-4-flash';
  });

  ipcMain.handle('omc:model:switch', async (_, modelId) => {
    return ApiBridge.switchModel(modelId);
  });

  // Chat — send task to omc and stream response
  ipcMain.handle('omc:chat:send', async (event, opts) => {
    return ApiBridge.chatSend(event, opts);
  });

  // Task — execute actual omc CLI command (explore / run)
  // Payload: { command, args, projectPath }
  // Returns: { code, stdout, stderr, outputFile }
  ipcMain.handle('omc:task:execute', async (event, { command, args, projectPath }) => {
    log('[task:execute] command=', command, 'args=', args, 'project=', projectPath);
    try {
      const omcBin = resolveOmcBinary();
      const taskDir = path.join(CONFIG_PATH, 'tasks');
      fs.mkdirSync(taskDir, { recursive: true });

      let actualPath = projectPath || OMC_ROOT;

      // If projectPath is a GitHub URL, clone it first
      if (actualPath.match(/^https?:\/\/github\.com\/[\w.-]+\/[\w.-]+/)) {
        const repoUrl = actualPath;
        const repoName = repoUrl.split('/').pop().replace(/\.git$/, '') || 'repo';
        actualPath = path.join(os.tmpdir(), `omc-task-${Date.now()}-${repoName}`);
        log('[task:execute] cloning', repoUrl, 'to', actualPath);
        await new Promise((resolve, reject) => {
          const clone = spawn('git', ['clone', '--depth', '1', repoUrl, actualPath], { stdio: ['ignore', 'pipe', 'pipe'] });
          let stderr = '';
          clone.stderr.on('data', d => stderr += d.toString());
          clone.on('close', code => code === 0 ? resolve() : reject(new Error(`git clone failed (${code}): ${stderr}`)));
        });
        log('[task:execute] cloned successfully');
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      const outputFile = path.join(taskDir, `task_${timestamp}.md`);

      const cmdArgs = [command, ...args];
      cmdArgs.push(actualPath);

      log('[task:execute] running:', omcBin, cmdArgs.join(' '));
      const child = spawn(omcBin, cmdArgs, {
        cwd: actualPath,
        stdio: ['ignore', 'pipe', 'pipe'],
        env: {
          ...process.env,
          PYTHONIOENCODING: 'utf-8',
          // Inject API keys from config.json so omc CLI can use them
          DEEPSEEK_API_KEY: (() => {
            try {
              const cfg = JSON.parse(fs.readFileSync(path.join(CONFIG_PATH, 'config.json'), 'utf-8'));
              return cfg.models?.deepseek?.api_key || '';
            } catch { return ''; }
          })(),
          OPENAI_API_KEY: (() => {
            try {
              const cfg = JSON.parse(fs.readFileSync(path.join(CONFIG_PATH, 'config.json'), 'utf-8'));
              return cfg.models?.deepseek?.api_key || '';
            } catch { return ''; }
          })(),
        },
        shell: false,
      });

      let stdout = '';
      let stderr = '';

      // Stream output to renderer
      child.stdout.on('data', (chunk) => {
        const text = chunk.toString();
        stdout += text;
        if (event && event.sender && !event.sender.isDestroyed()) {
          event.sender.send('omc:task:chunk', text);
        }
      });

      child.stderr.on('data', (chunk) => {
        const text = chunk.toString();
        stderr += text;
        if (event && event.sender && !event.sender.isDestroyed()) {
          event.sender.send('omc:task:error', text);
        }
      });

      return new Promise((resolve) => {
        child.on('close', (code) => {
          // Save result to MD file
          const header = `# Task Report\n\n- **Command**: \`omc ${cmdArgs.join(' ')}\`\n- **Time**: ${new Date().toLocaleString('zh-CN')}\n- **Status**: ${code === 0 ? '✅ Success' : '❌ Failed (exit ' + code + ')'}\n- **Project**: ${projectPath || './'}\n\n---\n\n`;
          let mdContent = header + '## Output\n\n' + stdout;
          if (stderr) {
            mdContent += '\n\n## Errors\n\n```\n' + stderr + '\n```';
          }
          fs.writeFileSync(outputFile, mdContent, 'utf-8');
          log('[task:execute] done, saved to', outputFile);
          resolve({ code, stdout, stderr, outputFile });
        });

        child.on('error', (e) => {
          log('[task:execute] error:', e.message);
          resolve({ code: 1, stdout: '', stderr: e.message, outputFile: '' });
        });

        // Timeout after 5 minutes
        setTimeout(() => {
          child.kill('SIGTERM');
          resolve({ code: 124, stdout, stderr: 'Task timed out (5 min)', outputFile: '' });
        }, 300000);
      });
    } catch (e) {
      log('[task:execute] exception:', e.message);
      return { code: 1, stdout: '', stderr: e.message, outputFile: '' };
    }
  });

  // Task — list saved task results
  ipcMain.handle('omc:task:list', async () => {
    const taskDir = path.join(CONFIG_PATH, 'tasks');
    if (!fs.existsSync(taskDir)) return [];
    const files = fs.readdirSync(taskDir)
      .filter(f => f.endsWith('.md'))
      .sort((a, b) => b.localeCompare(a))
      .slice(0, 50);
    return files.map(f => ({
      name: f,
      path: path.join(taskDir, f),
      mtime: fs.statSync(path.join(taskDir, f)).mtimeMs,
      size: fs.statSync(path.join(taskDir, f)).size,
    }));
  });

  // Task — read a saved task result
  ipcMain.handle('omc:task:read', async (_, { filePath }) => {
    try {
      if (!fs.existsSync(filePath)) return { error: 'File not found' };
      return { content: fs.readFileSync(filePath, 'utf-8') };
    } catch (e) {
      return { error: e.message };
    }
  });

  // Chat — route through omc server to support tools (web_fetch, browser, etc.)
  // Payload: { endpoint, model, apiKey, message }
  ipcMain.handle('omc:chat:direct', async (event, { endpoint, model, apiKey, message }) => {
    console.log('[chatDirect] model=', model, 'hasKey=', !!apiKey);
    try {
      const { spawn } = require('child_process');

      // Ensure omc server is running
      if (!omcReady) {
        console.log('[chatDirect] omc server not ready, starting...');
        await startOmcServer();
      }

      // Route through omc server's /api/chat/completions endpoint (has tool support)
      const serverUrl = 'http://localhost:7890/api/chat/completions';
      const payload = {
        messages: [{ role: 'user', content: message }],
        model: model,
        stream: true,
      };

      console.log('[chatDirect] calling omc server:', serverUrl);
      const child = spawn('curl', [
        '-s', '-N',
        '-X', 'POST', serverUrl,
        '-H', 'Content-Type: application/json',
        '-d', JSON.stringify(payload),
      ], {
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: false,
      });

      let buffer = '';
      let fullResponse = '';

      child.stdout.on('data', (chunk) => {
        buffer += chunk.toString();
        // Parse SSE: each line is "data: {...}"
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';  // Keep incomplete line
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (dataStr === '[DONE]') continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.content) {
                fullResponse += data.content;
                if (event && event.sender && !event.sender.isDestroyed()) {
                  event.sender.send('omc:chat:chunk', data.content);
                }
              }
            } catch (e) {
              // Ignore parse errors for malformed SSE
            }
          }
        }
      });

      child.stderr.on('data', (d) => {
        if (event && event.sender && !event.sender.isDestroyed()) {
          event.sender.send('omc:chat:error', d.toString());
        }
      });

      return new Promise((resolve) => {
        child.on('close', (code) => {
          console.log('[chatDirect] done, code=', code, 'responseLen=', fullResponse.length);
          resolve({ code, stdout: fullResponse, stderr: '' });
        });
        child.on('error', (e) => {
          console.error('[chatDirect] error:', e.message);
          resolve({ code: 1, stdout: '', stderr: e.message });
        });
        // Timeout after 60s
        setTimeout(() => {
          child.kill('SIGTERM');
          resolve({ code: 124, stdout: fullResponse, stderr: 'timeout' });
        }, 60000);
      });
    } catch (e) {
      console.error('[chatDirect] exception:', e.message);
      return { code: 1, stdout: '', stderr: e.message };
    }
  });

  // Config
  ipcMain.handle('omc:config:get', async () => {
    const envPath = path.join(CONFIG_PATH, '.env');
    if (!fs.existsSync(envPath)) return {};
    const content = fs.readFileSync(envPath, 'utf-8');
    const result = {};
    for (const line of content.split('\n')) {
      const m = line.match(/^([A-Z_]+)=(.*)$/);
      if (m) result[m[1]] = m[2];
    }
    return result;
  });

  ipcMain.handle('omc:config:set', async (_, { key, value }) => {
    const envPath = path.join(CONFIG_PATH, '.env');
    ensureConfigDir();
    let content = '';
    if (fs.existsSync(envPath)) content = fs.readFileSync(envPath, 'utf-8');
    const lines = content.split('\n').filter(l => !l.startsWith(`${key}=`));
    lines.push(`${key}=${value}`);
    fs.writeFileSync(envPath, lines.join('\n') + '\n');
    return { ok: true };
  });

  // Server status
  ipcMain.handle('omc:server:status', () => ({ running: omcReady }));
  ipcMain.handle('omc:server:start', async () => {
    await startOmcServer();
    return { running: omcReady };
  });
  ipcMain.handle('omc:server:stop', () => {
    stopOmcServer();
    return { running: false };
  });

  // History
  ipcMain.handle('omc:history:list', async () => {
    try {
      const out = execSync('omc history list --json 2>/dev/null || echo "[]"', {
        cwd: OMC_ROOT,
        encoding: 'utf-8',
        timeout: 10000,
      });
      return JSON.parse(out);
    } catch { return []; }
  });

  ipcMain.handle('omc:history:get', async (_, id) => {
    try {
      const out = execSync(`omc history get ${id} --json 2>/dev/null || echo "{}"`, {
        cwd: OMC_ROOT,
        encoding: 'utf-8',
        timeout: 10000,
      });
      return JSON.parse(out);
    } catch { return {}; }
  });

  // Open folder / file
  ipcMain.handle('shell:openExternal', async (_, url) => {
    shell.openExternal(url);
    return { ok: true };
  });
  ipcMain.handle('shell:openPath', async (_, p) => {
    shell.openPath(p);
    return { ok: true };
  });

  // App info
  ipcMain.handle('app:info', () => ({
    version: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    isDev,
    omcRoot: OMC_ROOT,
    configPath: CONFIG_PATH,
  }));

  // File operations (for diff acceptance)
  ipcMain.handle('omc:file:read', async (_, filePath) => {
    try {
      // Security: only allow reading files within project
      const resolved = path.resolve(OMC_ROOT, filePath);
      if (!resolved.startsWith(OMC_ROOT)) {
        return { ok: false, error: 'Access denied: path outside project' };
      }
      if (!fs.existsSync(resolved)) {
        return { ok: false, error: 'File not found' };
      }
      const content = fs.readFileSync(resolved, 'utf-8');
      return { ok: true, content };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  ipcMain.handle('omc:file:write', async (_, { path: filePath, content }) => {
    try {
      // Security: only allow writing files within project
      const resolved = path.resolve(OMC_ROOT, filePath);
      if (!resolved.startsWith(OMC_ROOT)) {
        return { ok: false, error: 'Access denied: path outside project' };
      }
      // Ensure parent directory exists
      const dir = path.dirname(resolved);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(resolved, content, 'utf-8');
      log('File written:', resolved);
      return { ok: true, path: resolved };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  ipcMain.handle('omc:file:exists', async (_, filePath) => {
    try {
      const resolved = path.resolve(OMC_ROOT, filePath);
      if (!resolved.startsWith(OMC_ROOT)) {
        return { ok: false, exists: false };
      }
      return { ok: true, exists: fs.existsSync(resolved) };
    } catch (e) {
      return { ok: false, exists: false };
    }
  });

  // Model Config Persistence (read/write ~/.omc/config.json)
  ipcMain.handle('omc:model:config:list', async () => {
    try {
      const configPath = path.join(os.homedir(), '.omc', 'config.json');
      if (!fs.existsSync(configPath)) return {};
      const content = fs.readFileSync(configPath, 'utf-8');
      const config = JSON.parse(content);
      return config.models || {};
    } catch (e) {
      log('Failed to read model configs:', e.message);
      return {};
    }
  });

  ipcMain.handle('omc:model:config:set', async (_, { modelId, config }) => {
    try {
      const omcDir = path.join(os.homedir(), '.omc');
      const configPath = path.join(omcDir, 'config.json');
      
      // Ensure directory exists
      if (!fs.existsSync(omcDir)) {
        fs.mkdirSync(omcDir, { recursive: true });
      }
      
      // Read existing config or create new
      let fullConfig = { models: {}, defaults: {} };
      if (fs.existsSync(configPath)) {
        const content = fs.readFileSync(configPath, 'utf-8');
        fullConfig = JSON.parse(content);
      }
      
      // Update model config
      if (!fullConfig.models) fullConfig.models = {};
      fullConfig.models[modelId] = {
        ...(fullConfig.models[modelId] || {}),
        ...config,
        updated_at: new Date().toISOString(),
      };
      
      // Write back
      fs.writeFileSync(configPath, JSON.stringify(fullConfig, null, 4), 'utf-8');
      log('Model config saved:', modelId);
      return { ok: true };
    } catch (e) {
      log('Failed to save model config:', e.message);
      return { ok: false, error: e.message };
    }
  });

  ipcMain.handle('omc:model:config:delete', async (_, modelId) => {
    try {
      const configPath = path.join(os.homedir(), '.omc', 'config.json');
      if (!fs.existsSync(configPath)) return { ok: true };
      
      const content = fs.readFileSync(configPath, 'utf-8');
      const fullConfig = JSON.parse(content);
      
      if (fullConfig.models && fullConfig.models[modelId]) {
        delete fullConfig.models[modelId];
        fs.writeFileSync(configPath, JSON.stringify(fullConfig, null, 4), 'utf-8');
        log('Model config deleted:', modelId);
      }
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  // Model Config Test
  ipcMain.handle('omc:model:config:test', async (_, { modelId, config }) => {
    try {
      // Simple validation: check if API key looks valid
      const { api_key, base_url } = config || {};
      if (!api_key || api_key.length < 10) {
        return { ok: false, msg: 'API Key is too short or missing' };
      }
      // TODO: Actually test the connection by making a request to the provider
      // For now, just validate key format
      return { ok: true, msg: 'Key format looks valid (live test not implemented)' };
    } catch (e) {
      return { ok: false, msg: e.message || 'Test failed' };
    }
  });

  // Whisper voice transcription
  ipcMain.handle('omc:whisper:transcribe', async (_, audioBytes) => {
    try {
      // audioBytes is Uint8Array (WAV bytes) from renderer
      const text = await transcribeAudio(audioBytes);
      return { ok: true, text };
    } catch (e) {
      log('Whisper transcribe error:', e.message);
      return { ok: false, error: e.message };
    }
  });
}

// ── Window ───────────────────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    backgroundColor: '#0a0a0a',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 12, y: 12 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    show: false,
  });

  // Build menu
  const tmpl = [
    {
      label: 'File',
      submenu: [
        { label: 'Open Project…', accelerator: 'CmdOrCtrl+O', click: () => dialog.showOpenDialog({ properties: ['openDirectory'] }) },
        { type: 'separator' },
        { label: 'Settings', accelerator: 'CmdOrCtrl+,', click: () => mainWindow.webContents.send('navigate', '/settings') },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' }, { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' }, { role: 'copy' }, { role: 'paste' },
        { role: 'selectAll' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' }, { role: 'forceReload' }, { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        { label: 'Documentation', click: () => shell.openExternal('https://github.com/VOBC/oh-my-coder') },
        { label: 'Report Issue', click: () => shell.openExternal('https://github.com/VOBC/oh-my-coder/issues') },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(tmpl));

  if (isDev) {
    mainWindow.loadURL('http://localhost:1420');
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  // Show window when ready, with a 5s fallback in case ready-to-show never fires
  let shown = false;
  const forceShow = () => {
    if (!shown && mainWindow && !mainWindow.isDestroyed()) {
      shown = true;
      mainWindow.show();
      mainWindow.focus();
    }
  };
  mainWindow.once('ready-to-show', forceShow);
  setTimeout(forceShow, 5000);
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {

  // Auto-retry when Vite dev server is temporarily unreachable
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDesc, validatedURL, isMainFrame) => {
    if (!isMainFrame) return;
    log('Failed to load:', errorDesc, '— retrying in 2s...');
    setTimeout(() => {      if (mainWindow && !mainWindow.isDestroyed()) {
        log('Retrying load...');
        mainWindow.loadURL('http://localhost:1420');
      }
    }, 2000);
  });

    const levels = ['verbose','info','warning','error'];
    console.log(`[renderer:${levels[level] || level}] ${message} (${sourceId}:${line})`);
  });
  mainWindow.on('closed', () => { mainWindow = null; });
}

// ── Bootstrap ─────────────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  setupIpc();
  createWindow();
  // Don't auto-start server — let user decide
  log('App ready, omcRoot:', OMC_ROOT);
});

app.on('window-all-closed', () => {
  // On macOS, keep app running even when all windows are closed
  if (process.platform !== 'darwin') {
    stopOmcServer();
    app.quit();
  }
});

// On macOS, re-create window when clicking dock icon
app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => stopOmcServer());

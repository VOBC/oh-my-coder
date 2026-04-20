// electron/main.js — Oh My Coder Desktop MVP
const { app, BrowserWindow, ipcMain, Menu, shell, dialog, nativeTheme } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const fs = require('fs');
const os = require('os');

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
    try {
      const out = execSync('omc model list --json 2>/dev/null || omc model list 2>/dev/null', {
        cwd: OMC_ROOT,
        encoding: 'utf-8',
        timeout: 10000,
      });
      // Try JSON parse, fallback to raw
      try { return JSON.parse(out); } catch { return { raw: out, models: [] }; }
    } catch (e) {
      return { error: e.message, models: [] };
    }
  });

  ipcMain.handle('omc:model:current', async () => {
    try {
      const out = execSync('omc model current --json 2>/dev/null || echo "{}"', {
        cwd: OMC_ROOT,
        encoding: 'utf-8',
        timeout: 10000,
      });
      return JSON.parse(out);
    } catch { return {}; }
  });

  ipcMain.handle('omc:model:switch', async (_, modelId) => {
    try {
      const out = execSync(`omc model switch ${modelId}`, {
        cwd: OMC_ROOT,
        encoding: 'utf-8',
        timeout: 10000,
      });
      return { ok: true, output: out };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });

  // Chat — send task to omc and stream response
  ipcMain.handle('omc:chat:send', async (event, { message, model }) => {
    return new Promise((resolve) => {
      try {
        const args = ['run', '--no-interactive', '--json', message];
        if (model) args.push('--model', model);
        const child = spawn('omc', args, { cwd: OMC_ROOT, stdio: ['pipe', 'pipe', 'pipe'] });

        let stdout = '', stderr = '';
        child.stdout.on('data', (d) => { stdout += d.toString(); event.sender.send('omc:chat:chunk', stdout); });
        child.stderr.on('data', (d) => { stderr += d.toString(); event.sender.send('omc:chat:error', stderr); });
        child.on('close', (code) => resolve({ code, stdout, stderr }));
      } catch (e) {
        resolve({ code: 1, stdout: '', stderr: e.message });
      }
    });
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
    trafficLightPosition: { x: 14, y: 14 },
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
    mainWindow.loadFile(path.join(OMC_ROOT, 'desktop', 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => mainWindow.show());
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
  stopOmcServer();
  app.quit();
});

app.on('before-quit', () => stopOmcServer());

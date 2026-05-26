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
// OMC_ROOT: 项目根目录（desktop 的父目录）
const OMC_ROOT = path.join(__dirname, '..', '..');
const CONFIG_PATH = path.join(OMC_ROOT, '.omc');

// ── State ────────────────────────────────────────────────────────────────────
let mainWindow = null;
let omcProcess = null; // omc server child process
let omcReady = false;
let taskChild = null; // current task child process (for kill support)

// ── Helpers ───────────────────────────────────────────────────────────────────
function log(...args) {
  const ts = new Date().toISOString().slice(11, 23);
  console.log(`[omc:electron:${ts}]`, ...args);
}

// ── Process-level error protection ────────────────────────────────────────
process.on("uncaughtException", (err) => {
  log("UNCAUGHT EXCEPTION:", err.message, err.stack?.slice(0, 200));
});
process.on("unhandledRejection", (reason) => {
  log("UNHANDLED REJECTION:", reason);
});

// ── IPC Input Validation ─────────────────────────────────────────────────────
/**
 * Validate IPC arguments against a schema
 * @param {Object} args - The arguments to validate
 * @param {Object} schema - Validation schema { key: { type, required, pattern, enum } }
 * @returns {{ valid: boolean, error?: string }}
 */
function validateIpcArgs(args, schema) {
  if (!args || typeof args !== 'object') {
    return { valid: false, error: 'Arguments must be an object' };
  }

  for (const [key, rules] of Object.entries(schema)) {
    const value = args[key];

    // Check required
    if (rules.required && (value === undefined || value === null)) {
      return { valid: false, error: `Missing required field: ${key}` };
    }

    // Skip further validation if value is not provided and not required
    if (value === undefined || value === null) {
      continue;
    }

    // Check type
    if (rules.type && typeof value !== rules.type) {
      return { valid: false, error: `Field '${key}' must be of type ${rules.type}, got ${typeof value}` };
    }

    // Check pattern (regex)
    if (rules.pattern && typeof value === 'string' && !rules.pattern.test(value)) {
      return { valid: false, error: `Field '${key}' does not match required pattern` };
    }

    // Check enum
    if (rules.enum && !rules.enum.includes(value)) {
      return { valid: false, error: `Field '${key}' must be one of: ${rules.enum.join(', ')}` };
    }

    // Check array type
    if (rules.isArray && !Array.isArray(value)) {
      return { valid: false, error: `Field '${key}' must be an array` };
    }
  }

  return { valid: true };
}

/**
 * Sanitize a path to prevent path traversal attacks
 * @param {string} inputPath - The path to sanitize
 * @param {string} basePath - The allowed base path
 * @returns {{ valid: boolean, path?: string, error?: string }}
 */
function sanitizePath(inputPath, basePath) {
  if (!inputPath || typeof inputPath !== 'string') {
    return { valid: false, error: 'Path must be a non-empty string' };
  }

  // Resolve to absolute path
  const resolved = path.resolve(basePath, inputPath);
  
  // Check if path is within base path
  if (!resolved.startsWith(basePath)) {
    return { valid: false, error: 'Path traversal detected' };
  }

  return { valid: true, path: resolved };
}

/**
 * Validate URL to prevent SSRF attacks
 * @param {string} url - The URL to validate
 * @returns {{ valid: boolean, error?: string }}
 */
function validateUrl(url) {
  if (!url || typeof url !== 'string') {
    return { valid: false, error: 'URL must be a non-empty string' };
  }

  try {
    const parsed = new URL(url);
    // Only allow http and https protocols
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return { valid: false, error: 'Only HTTP and HTTPS protocols are allowed' };
    }
    // Block private IPs (basic check)
    const hostname = parsed.hostname;
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.') || hostname.startsWith('10.') || hostname.startsWith('172.')) {
      return { valid: false, error: 'Private IP addresses are not allowed' };
    }
    return { valid: true };
  } catch (e) {
    return { valid: false, error: 'Invalid URL format' };
  }
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
    // Validate: modelId must be a non-empty string
    if (!modelId || typeof modelId !== 'string' || modelId.trim().length === 0) {
      return { ok: false, error: 'modelId must be a non-empty string' };
    }
    // Sanitize: only allow alphanumeric, hyphens, underscores, dots
    if (!/^[\w\.-]+$/.test(modelId)) {
      return { ok: false, error: 'Invalid modelId format' };
    }
    return ApiBridge.switchModel(modelId);
  });

  // Chat — send task to omc and stream response
  ipcMain.handle('omc:chat:send', async (event, opts) => {
    // Validate opts
    const validation = validateIpcArgs(opts, {
      message: { type: 'string', required: true },
      model: { type: 'string', required: false },
      stream: { type: 'boolean', required: false },
    });
    if (!validation.valid) {
      return { ok: false, error: validation.error };
    }
    // Sanitize message length
    if (opts.message.length > 100000) {
      return { ok: false, error: 'Message too long (max 100000 characters)' };
    }
    return ApiBridge.chatSend(event, opts);
  });

  // Task — execute actual omc CLI command (explore / run)
  // Payload: { command, args, projectPath }
  // Returns: { code, stdout, stderr, outputFile }
  ipcMain.handle('omc:task:execute', async (event, { command, args, projectPath }) => {
    // === Input Validation ===
    // Validate command
    const validation = validateIpcArgs({ command, args, projectPath }, {
      command: { type: 'string', required: true, pattern: /^[a-zA-Z0-9_:-]+$/ },
      args: { isArray: true, required: false },
      projectPath: { type: 'string', required: false },
    });
    if (!validation.valid) {
      return { code: 1, stdout: '', stderr: `Invalid input: ${validation.error}`, outputFile: '' };
    }

    // Validate command whitelist (security: only allow specific commands)
    const allowedCommands = ['explore', 'run', 'test', 'lint', 'format', 'typecheck', 'build', 'init'];
    if (!allowedCommands.includes(command)) {
      return { code: 1, stdout: '', stderr: `Command not allowed: ${command}`, outputFile: '' };
    }

    // Validate args (no shell metacharacters)
    if (args) {
      for (const arg of args) {
        if (typeof arg !== 'string') {
          return { code: 1, stdout: '', stderr: 'All args must be strings', outputFile: '' };
        }
        // Block shell metacharacters
        if (/[;|&$`\n\r]/.test(arg)) {
          return { code: 1, stdout: '', stderr: 'Invalid argument: shell metacharacters not allowed', outputFile: '' };
        }
      }
    }

    // Validate projectPath
    let actualPath = projectPath || OMC_ROOT;
    if (projectPath) {
      // Only allow GitHub URLs or paths within OMC_ROOT
      const isGitHubUrl = projectPath.match(/^https?:\/\/github\.com\/[\w.-]+\/[\w.-]+/);
      const isWithinRoot = path.resolve(projectPath).startsWith(OMC_ROOT);
      if (!isGitHubUrl && !isWithinRoot) {
        return { code: 1, stdout: '', stderr: 'projectPath must be a GitHub URL or a path within the project', outputFile: '' };
      }
    }

    log('[task:execute] command=', command, 'args=', args, 'project=', actualPath);
    try {
      const omcBin = resolveOmcBinary();
      const taskDir = path.join(CONFIG_PATH, 'tasks');
      fs.mkdirSync(taskDir, { recursive: true });

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
      // Note: actualPath is used as cwd, NOT appended as an argument
      // (omc run/explore etc. don't accept a path argument)

      log('[task:execute] running:', omcBin, cmdArgs.join(' '), 'in', actualPath);
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
      taskChild = child; // store reference so it can be killed

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
          taskChild = null;
          // Save result to MD file
          const header = `# Task Report\n\n- **Command**: \`omc ${cmdArgs.join(' ')}\`\n- **Time**: ${new Date().toLocaleString('zh-CN')}\n- **Status**: ${code === 0 ? '✅ Success' : '❌ Failed (exit ' + code + ')'}\n- **Project**: ${projectPath || './'}\n\n---\n\n`;
          let mdContent = header + '## Output\n\n' + stdout;
          // Filter out noisy retry logs (e.g. 429 rate-limit retries)
          const errorLines = stderr.split('\n').filter(l => !l.match(/请求失败.*attempt=\d+\/\d+\)/));
          const cleanErrors = errorLines.filter(l => l.trim()).join('\n');
          if (cleanErrors) {
            mdContent += '\n\n## Errors\n\n```\n' + cleanErrors + '\n```';
          }
          fs.writeFileSync(outputFile, mdContent, 'utf-8');
          log('[task:execute] done, saved to', outputFile);

          // Also save a copy to Desktop for easy access
          const desktopPath = path.join(require('os').homedir(), 'Desktop');
          let desktopFile = null;
          try {
            if (fs.existsSync(desktopPath)) {
              // Use task description from args for filename
              const taskLabel = (args && args.length > 0) ? args[0].slice(0, 30).replace(/[^\w\u4e00-\u9fff-]/g, '_') : 'task';
              const ts = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 10); // just date
              desktopFile = path.join(desktopPath, `omc_${ts}_${taskLabel}.md`);
              fs.writeFileSync(desktopFile, mdContent, 'utf-8');
              log('[task:execute] also saved to Desktop:', desktopFile);
            }
          } catch (e) {
            log('[task:execute] warning: could not save to Desktop:', e.message);
          }

          resolve({ code, stdout, stderr, outputFile, desktopFile: desktopFile || '' });
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
    // Validate filePath
    const validation = validateIpcArgs({ filePath }, {
      filePath: { type: 'string', required: true },
    });
    if (!validation.valid) {
      return { error: `Invalid input: ${validation.error}` };
    }

    // Sanitize path (only allow reading from task directory)
    const taskDir = path.join(CONFIG_PATH, 'tasks');
    const resolved = path.resolve(filePath);
    if (!resolved.startsWith(taskDir)) {
      return { error: 'Access denied: can only read from tasks directory' };
    }

    try {
      if (!fs.existsSync(resolved)) return { error: 'File not found' };
      return { content: fs.readFileSync(resolved, 'utf-8') };
    } catch (e) {
      return { error: e.message };
    }
  });

  // Task — kill running task
  ipcMain.handle('omc:task:kill', async () => {
    if (taskChild && taskChild.pid) {
      log('[task:kill] killing task process', taskChild.pid);
      taskChild.kill('SIGTERM');
      // Give it a moment then SIGKILL
      setTimeout(() => {
        if (taskChild && taskChild.pid) {
          try { taskChild.kill('SIGKILL'); } catch {}
        }
      }, 2000);
      return { killed: true };
    }
    return { killed: false, reason: 'No task running' };
  });

  // Chat — direct connection to model API endpoint (OpenAI-compatible)
  // Payload: { endpoint, model, apiKey, message }
  ipcMain.handle('omc:chat:direct', async (event, { endpoint, model, apiKey, message }) => {
    // Validate inputs
    const validation = validateIpcArgs({ endpoint, model, apiKey, message }, {
      endpoint: { type: 'string', required: true },
      model: { type: 'string', required: true },
      apiKey: { type: 'string', required: false },
      message: { type: 'string', required: true },
    });
    if (!validation.valid) {
      return { code: 1, stdout: '', stderr: `Invalid input: ${validation.error}` };
    }

    // Validate endpoint URL (prevent SSRF)
    const urlValidation = validateUrl(endpoint);
    if (!urlValidation.valid) {
      return { code: 1, stdout: '', stderr: `Invalid endpoint: ${urlValidation.error}` };
    }

    // Validate message length
    if (message.length > 100000) {
      return { code: 1, stdout: '', stderr: 'Message too long (max 100000 characters)' };
    }

    // Validate model name format
    if (!/^[\w\.-]+$/.test(model)) {
      return { code: 1, stdout: '', stderr: 'Invalid model name format' };
    }

    console.log('[chatDirect] endpoint=', endpoint, 'model=', model, 'hasKey=', !!apiKey);
    try {
      const { spawn } = require('child_process');

      // Ensure endpoint ends with /chat/completions (OpenAI-compatible)
      if (endpoint && !endpoint.endsWith('/chat/completions')) {
        endpoint = endpoint.replace(/\/$/, '') + '/chat/completions';
      }

      // Define tools for web_fetch
      const tools = [
        {
          type: 'function',
          function: {
            name: 'web_fetch',
            description: 'Fetch the content of a URL and return the text content',
            parameters: {
              type: 'object',
              properties: {
                url: { type: 'string', description: 'The URL to fetch' },
              },
              required: ['url'],
            },
          },
        },
        {
          type: 'function',
          function: {
            name: 'file_read',
            description: 'Read the contents of a local file. Returns the first 2000 characters.',
            parameters: {
              type: 'object',
              properties: {
                path: { type: 'string', description: 'Absolute path to the file' },
              },
              required: ['path'],
            },
          },
        },
      ];

      // Step 1: Non-streaming call to check for tool calls
      const initialPayload = {
        model,
        messages: [{ role: 'user', content: message }],
        tools,
        stream: false,
      };

      const initialResponse = await curlPost(endpoint, apiKey, initialPayload);
      let responseData;
      try {
        responseData = JSON.parse(initialResponse);
      } catch (e) {
        // If not JSON, just return the response as-is
        if (event && event.sender && !event.sender.isDestroyed()) {
          event.sender.send('omc:chat:chunk', initialResponse);
        }
        return { code: 0, stdout: initialResponse, stderr: '' };
      }

      // Check for tool calls
      const toolCalls = responseData.choices?.[0]?.message?.tool_calls || [];
      console.log('[DEBUG] initial response:', JSON.stringify(responseData, null, 2));

      if (toolCalls.length > 0) {
        // Execute tool calls
        const messages = [
          { role: 'user', content: message },
          responseData.choices[0].message,
        ];

        for (const toolCall of toolCalls) {
          if (toolCall.function.name === 'web_fetch') {
            const args = JSON.parse(toolCall.function.arguments);
            const content = await webFetch(args.url);
            messages.push({
              role: 'tool',
              tool_call_id: toolCall.id,
              content: content,
            });
          } else if (toolCall.function.name === 'file_read') {
            const args = JSON.parse(toolCall.function.arguments);
            
            // Path traversal security check
            if (args.path.includes('..')) {
              messages.push({
                role: 'tool',
                tool_call_id: toolCall.id,
                content: 'Error reading file: Path traversal detected (contains \'..\'). Access denied for security reasons.',
              });
              continue;
            }
            
            try {
              const fs = require('fs');
              const content = fs.readFileSync(args.path, 'utf-8');
              messages.push({
                role: 'tool',
                tool_call_id: toolCall.id,
                content: content.slice(0, 2000),
              });
            } catch (e) {
              messages.push({
                role: 'tool',
                tool_call_id: toolCall.id,
                content: `Error reading file: ${e.message}`,
              });
            }
          }
        }

        // Step 2: Non-streaming call with tool results
        // NOTE: streaming + function_calling conflict on DeepSeek & some providers,
        // so we use non-streaming here, then simulate SSE chunks for the UI
        const finalPayload = {
          model,
          messages,
          stream: false,
        };

        // Execute non-streaming call
        const finalResponse = await curlPost(endpoint, apiKey, finalPayload);
        let finalData;
        try {
          finalData = JSON.parse(finalResponse);
        } catch (e) {
          return { code: 0, stdout: finalResponse, stderr: '' };
        }
        // DEBUG: log full response to diagnose empty response issue
        console.log('[DEBUG] finalData:', JSON.stringify(finalData, null, 2));
        const content = finalData.choices?.[0]?.message?.content || '';
        // Simulate SSE streaming: send content in 3 chunks
        if (content) {
          const third = Math.max(1, Math.floor(content.length / 3));
          const chunks = [
            content.slice(0, third),
            content.slice(third, third * 2),
            content.slice(third * 2),
          ];
          for (let i = 0; i < chunks.length; i++) {
            const isLast = i === chunks.length - 1;
            const doneData = JSON.stringify({
              choices: [{ delta: { content: chunks[i] } }],
            });
            if (event && event.sender && !event.sender.isDestroyed()) {
              event.sender.send('omc:chat:chunk', 'data: ' + doneData + '\n\n');
            }
            await new Promise(r => setTimeout(r, 30));
          }
        }
        // Send [DONE] to signal end of stream
        if (event && event.sender && !event.sender.isDestroyed()) {
          event.sender.send('omc:chat:chunk', 'data: [DONE]\n\n');
        }
        return { code: 0, stdout: finalResponse, stderr: '' };
      } else {
        // No tool calls, stream the response
        const payload = {
          model,
          messages: [{ role: 'user', content: message }],
          stream: true,
        };
        return await streamCurl(event, endpoint, apiKey, payload);
      }
    } catch (e) {
      console.error('[chatDirect] error:', e.message);
      return { code: 1, stdout: '', stderr: e.message };
    }
  });

  // Helper: POST request using curl (non-streaming)
  async function curlPost(url, apiKey, payload) {
    return new Promise((resolve, reject) => {
      const curlCmd = [
        'curl', '-s',
        '-X', 'POST', url,
        '-H', 'Content-Type: application/json',
        '-H', `Authorization: Bearer ${apiKey}`,
        '-d', JSON.stringify(payload),
      ];
      const child = spawn(curlCmd[0], curlCmd.slice(1), {
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: false,
      });
      let stdout = '';
      let stderr = '';
      child.stdout.on('data', (d) => { stdout += d.toString(); });
      child.stderr.on('data', (d) => { stderr += d.toString(); });
      child.on('close', (code) => {
        if (code === 0) resolve(stdout);
        else reject(new Error(stderr || `curl exited with ${code}`));
      });
      child.on('error', reject);
    });
  }

  // Helper: Streaming request using curl
  async function streamCurl(event, url, apiKey, payload) {
    return new Promise((resolve) => {
      const curlCmd = [
        'curl', '-s', '-N',
        '-X', 'POST', url,
        '-H', 'Content-Type: application/json',
        '-H', `Authorization: Bearer ${apiKey}`,
        '-d', JSON.stringify(payload),
      ];
      const child = spawn(curlCmd[0], curlCmd.slice(1), {
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: false,
      });
      let fullResponse = '';
      child.stdout.on('data', (chunk) => {
        const text = chunk.toString();
        fullResponse += text;
        if (event && event.sender && !event.sender.isDestroyed()) {
          event.sender.send('omc:chat:chunk', text);
        }
      });
      child.stderr.on('data', (d) => {
        if (event && event.sender && !event.sender.isDestroyed()) {
          event.sender.send('omc:chat:error', d.toString());
        }
      });
      child.on('close', (code) => {
        resolve({ code, stdout: fullResponse, stderr: '' });
      });
      child.on('error', (e) => {
        resolve({ code: 1, stdout: '', stderr: e.message });
      });
      setTimeout(() => {
        child.kill('SIGTERM');
        resolve({ code: 124, stdout: fullResponse, stderr: 'timeout' });
      }, 60000);
    });
  }

  // Helper: Fetch URL content (web_fetch implementation)
  async function webFetch(url) {
    return new Promise((resolve) => {
      const curlCmd = [
        'curl', '-s', '-L', '--max-time', '30',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        url,
      ];
      const child = spawn(curlCmd[0], curlCmd.slice(1), {
        stdio: ['ignore', 'pipe', 'pipe'],
        shell: false,
      });
      let content = '';
      child.stdout.on('data', (d) => { content += d.toString(); });
      child.stderr.on('data', () => {});
      child.on('close', () => {
        // Strip HTML tags and truncate
        let text = content.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
        text = text.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '');
        text = text.replace(/<[^>]+>/g, ' ');
        text = text.replace(/\s+/g, ' ').trim();
        if (text.length > 8000) {
          text = text.slice(0, 8000) + '\n\n... (content truncated)';
        }
        resolve(text);
      });
      child.on('error', () => resolve('Error fetching URL'));
      setTimeout(() => {
        child.kill('SIGTERM');
        resolve('Timeout fetching URL');
      }, 35000);
    });
  }

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
    // Validate inputs
    const validation = validateIpcArgs({ key, value }, {
      key: { type: 'string', required: true, pattern: /^[A-Z_][A-Z0-9_]*$/ },
      value: { type: 'string', required: true },
    });
    if (!validation.valid) {
      return { ok: false, error: `Invalid input: ${validation.error}` };
    }

    // Validate value length (prevent buffer overflow)
    if (value.length > 10000) {
      return { ok: false, error: 'Value too long (max 10000 characters)' };
    }

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
    // Validate id (prevent command injection)
    if (!id || typeof id !== 'string') {
      return {};
    }
    // Only allow alphanumeric, hyphens, underscores
    if (!/^[\w-]+$/.test(id)) {
      return {};
    }
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
    // Validate URL (prevent SSRF)
    if (!url || typeof url !== 'string') {
      return { ok: false, error: 'URL must be a non-empty string' };
    }
    
    const urlValidation = validateUrl(url);
    if (!urlValidation.valid) {
      return { ok: false, error: `Invalid URL: ${urlValidation.error}` };
    }

    shell.openExternal(url);
    return { ok: true };
  });

  ipcMain.handle('shell:openPath', async (_, p) => {
    // Validate path
    if (!p || typeof p !== 'string') {
      return { ok: false, error: 'Path must be a non-empty string' };
    }

    // Only allow opening paths within OMC_ROOT or common system paths
    const resolved = path.resolve(p);
    const allowedPrefixes = [
      OMC_ROOT,
      path.join(os.homedir(), 'Downloads'),
      path.join(os.homedir(), 'Documents'),
    ];
    
    const isAllowed = allowedPrefixes.some(prefix => resolved.startsWith(prefix));
    if (!isAllowed) {
      return { ok: false, error: 'Access denied: path not allowed' };
    }

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

#!/usr/bin/env node
/**
 * start.js — oh-my-coder Desktop 一键启动脚本
 *
 * 直接用 Node.js API 启动 Vite + Electron，绕过 npx/vite CLI stdout 问题。
 * 用法：node start.js
 */
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

// ── ANSI Colors ────────────────────────────────────────────────────────────────
const c = {
  green: (s) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s) => `\x1b[33m${s}\x1b[0m`,
  cyan: (s) => `\x1b[36m${s}\x1b[0m`,
  red: (s) => `\x1b[31m${s}\x1b[0m`,
  dim: (s) => `\x1b[2m${s}\x1b[0m`,
};

// ── Wait for a URL to be ready ─────────────────────────────────────────────────
function waitForUrl(url, timeout = 30000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`⏰ 等待 ${url} 超时（${timeout}ms）`)), timeout);
    const check = () => {
      http.get(url, (res) => {
        if (res.statusCode >= 200 && res.statusCode < 400) {
          clearTimeout(timer);
          resolve();
        } else {
          setTimeout(check, 500);
        }
      }).on('error', () => setTimeout(check, 500));
    };
    check();
  });
}

// ── Log with timestamp ─────────────────────────────────────────────────────────
function log(label, msg, color) {
  color = color || c.dim;
  const ts = new Date().toISOString().slice(11, 23);
  console.log(`${c.dim(`[${ts}]`)} ${color(label)} ${msg}`);
}

// ── Open URL in browser ────────────────────────────────────────────────────────
function openBrowser(url) {
  try {
    require('child_process').execSync(`open "${url}"`, { stdio: 'ignore' });
  } catch (e) {
    // ignore
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  console.log(`\n${c.cyan('🐾')} ${c.green('oh-my-coder Desktop')} 启动中...\n`);

  const rootDir = __dirname;

  // 1. Check node_modules exist
  const viteBin = path.join(rootDir, 'node_modules/vite/bin/vite.js');
  const electronBin = path.join(rootDir, 'node_modules/electron/dist/Electron.app/Contents/MacOS/Electron');

  if (!fs.existsSync(viteBin)) {
    console.error(`${c.red('❌')} 未找到 vite，请先运行：npm install`);
    process.exit(1);
  }
  if (!fs.existsSync(electronBin)) {
    console.error(`${c.red('❌')} 未找到 electron，请先运行：npm install`);
    process.exit(1);
  }

  // 2. Use QClaw's bundled node if available, otherwise system node
  const qclawNode = '/Applications/QClaw.app/Contents/Resources/node/node';
  const nodePath = fs.existsSync(qclawNode) ? qclawNode : process.execPath;

  // 3. Start Vite directly via node (bypass npx/vite CLI wrapper)
  log('⚡', '启动 Vite 前端服务...', c.yellow);
  const viteProcess = spawn(nodePath, [viteBin], {
    cwd: rootDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env },
  });

  viteProcess.stdout.on('data', (d) => process.stdout.write(d));
  viteProcess.stderr.on('data', (d) => process.stderr.write(d));
  viteProcess.on('error', (e) => {
    console.error(`${c.red('❌')} Vite 启动失败:`, e.message);
    process.exit(1);
  });

  // 4. Wait for Vite
  log('⏳', '等待 Vite 启动...', c.yellow);
  try {
    await waitForUrl('http://localhost:1420', 30000);
    log('✅', 'Vite 已就绪 http://localhost:1420', c.green);
  } catch (e) {
    console.error(`${c.red('❌')} ${e.message}`);
    process.exit(1);
  }

  // 5. Start Electron
  log('🪟', '启动 Electron 窗口...', c.yellow);
  const electronProcess = spawn(electronBin, ['.'], {
    cwd: rootDir,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, ELECTRON_DISABLE_GPU: '1' },
  });

  electronProcess.stdout.on('data', (d) => process.stdout.write(d));
  electronProcess.stderr.on('data', (d) => process.stderr.write(d));
  electronProcess.on('error', (e) => {
    console.error(`${c.red('❌')} Electron 启动失败:`, e.message);
    process.exit(1);
  });

  log('🎉', `Desktop 已启动！Electron PID: ${electronProcess.pid}`, c.green);
  console.log(`${c.dim('   按 Ctrl+C 停止\n')}`);

  // Cleanup
  process.on('SIGINT', () => {
    log('🛑', '正在停止...', c.yellow);
    electronProcess.kill();
    viteProcess.kill();
    process.exit(0);
  });
}

main().catch((e) => {
  console.error(`${c.red('❌')} 启动失败:`, e.message);
  process.exit(1);
});

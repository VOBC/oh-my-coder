// electron/preload.js — contextBridge API for renderer
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('omc', {
  // Model
  modelList: () => ipcRenderer.invoke('omc:model:list'),
  modelCurrent: () => ipcRenderer.invoke('omc:model:current'),
  modelSwitch: (id) => ipcRenderer.invoke('omc:model:switch', id),

  // Chat
  chatSend: (opts) => ipcRenderer.invoke('omc:chat:send', opts),
  onChatChunk: (cb) => {
    const h = (_, data) => cb(data);
    ipcRenderer.on('omc:chat:chunk', h);
    return () => ipcRenderer.removeListener('omc:chat:chunk', h);
  },
  onChatError: (cb) => {
    const h = (_, data) => cb(data);
    ipcRenderer.on('omc:chat:error', h);
    return () => ipcRenderer.removeListener('omc:chat:error', h);
  },

  // Config
  configGet: () => ipcRenderer.invoke('omc:config:get'),
  configSet: (key, value) => ipcRenderer.invoke('omc:config:set', { key, value }),

  // Server
  serverStatus: () => ipcRenderer.invoke('omc:server:status'),
  serverStart: () => ipcRenderer.invoke('omc:server:start'),
  serverStop: () => ipcRenderer.invoke('omc:server:stop'),

  // History
  historyList: () => ipcRenderer.invoke('omc:history:list'),
  historyGet: (id) => ipcRenderer.invoke('omc:history:get', id),

  // File operations (for diff acceptance)
  fileRead: (path) => ipcRenderer.invoke('omc:file:read', path),
  fileWrite: (path, content) => ipcRenderer.invoke('omc:file:write', { path, content }),
  fileExists: (path) => ipcRenderer.invoke('omc:file:exists', path),

  // Shell
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
  openPath: (p) => ipcRenderer.invoke('shell:openPath', p),

  // App
  appInfo: () => ipcRenderer.invoke('app:info'),
  onNavigate: (cb) => {
    const h = (_, path) => cb(path);
    ipcRenderer.on('navigate', h);
    return () => ipcRenderer.removeListener('navigate', h);
  },
});

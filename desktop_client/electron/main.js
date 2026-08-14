const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const http = require('http');
const { spawn } = require('child_process');

let mainWindow;
let apiProcess = null;

// Automatically probe port 8000 and spawn FastAPI server if not running
function ensureBackendRunning() {
  const req = http.get('http://127.0.0.1:8000/health', (res) => {
    console.log('[MAK Core] FastAPI backend is already running on http://127.0.0.1:8000');
  });

  req.on('error', () => {
    console.log('[MAK Core] Starting headless FastAPI backend server (server.py)...');
    const rootDir = path.resolve(__dirname, '../../');
    const venvPython = path.join(rootDir, '.venv', 'Scripts', 'python.exe');
    const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python';

    apiProcess = spawn(pythonCmd, ['server.py'], {
      cwd: rootDir,
      shell: true,
      stdio: 'inherit'
    });

    apiProcess.on('error', (err) => {
      console.error('[MAK Core] Failed to spawn FastAPI process:', err);
    });
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: 'MAK // Autonomous Cognitive Core',
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#06080d',
      symbolColor: '#94a3b8',
      height: 38
    },
    backgroundColor: '#06080d',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false
    },
    icon: path.join(__dirname, '../public/vite.svg'),
    show: false
  });

  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

  if (isDev) {
    // In dev mode, load the Vite dev server
    const devUrl = process.env.VITE_DEV_SERVER_URL || 'http://localhost:5173';
    mainWindow.loadURL(devUrl);
  } else {
    // In production, load the built HTML bundle
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Graceful show once ready to prevent white flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Open all external links in the default OS browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) {
      shell.openExternal(url);
    }
    return { action: 'deny' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (url.startsWith('http') && !url.includes('localhost:5173')) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// App lifecycle
app.whenReady().then(() => {
  ensureBackendRunning();
  createWindow();

  ipcMain.handle('ping', () => 'pong');

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('will-quit', () => {
  if (apiProcess && apiProcess.pid) {
    try {
      console.log('[MAK Core] Terminating spawned FastAPI backend process...');
      if (process.platform === 'win32') {
        spawn('taskkill', ['/pid', apiProcess.pid, '/f', '/t']);
      } else {
        apiProcess.kill();
      }
    } catch (e) {
      console.error('[MAK Core] Error terminating backend process:', e);
    }
  }
});

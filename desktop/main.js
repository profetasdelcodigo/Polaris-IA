const { app, BrowserWindow, Tray, Menu, Notification, nativeImage, ipcMain, shell } = require('electron');
const path = require('path');

let mainWindow = null;
let tray = null;
let isQuitting = false;

// ── Crear la ventana principal ─────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    frame: false,          // Sin barra de título nativa — usamos la nuestra
    transparent: false,
    backgroundColor: '#04080F',
    icon: path.join(__dirname, 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    titleBarStyle: 'hidden',
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));

  // Mostrar ventana cuando esté lista (evita flash blanco)
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Minimizar a bandeja en vez de cerrar
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
      showTrayNotification('Polaris IA sigue aprendiendo', 'El cerebro continúa activo en segundo plano.');
    }
  });
}

// ── Bandeja del sistema (System Tray) ────────────────────────────────────
function createTray() {
  const icon = nativeImage.createFromPath(path.join(__dirname, 'assets', 'icon.png'));
  tray = new Tray(icon.resize({ width: 16, height: 16 }));

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '🧠 Abrir Monitor Neural',
      click: () => { mainWindow.show(); mainWindow.focus(); }
    },
    {
      label: '⚡ Forzar ciclo de aprendizaje',
      click: () => {
        mainWindow.webContents.send('trigger-cycle');
      }
    },
    { type: 'separator' },
    {
      label: '🌐 Ver en navegador',
      click: () => shell.openExternal('https://pdlc-polaris-ia.hf.space')
    },
    {
      label: '📊 Ver estado JSON',
      click: () => shell.openExternal('https://pdlc-polaris-ia.hf.space/status')
    },
    { type: 'separator' },
    {
      label: '❌ Salir de Polaris IA',
      click: () => { isQuitting = true; app.quit(); }
    },
  ]);

  tray.setToolTip('Polaris IA — Monitor Neural');
  tray.setContextMenu(contextMenu);
  tray.on('double-click', () => { mainWindow.show(); mainWindow.focus(); });
}

// ── Notificaciones nativas ────────────────────────────────────────────────
function showTrayNotification(title, body) {
  if (Notification.isSupported()) {
    new Notification({ title, body, icon: path.join(__dirname, 'assets', 'icon.png') }).show();
  }
}

// ── IPC: comunicación renderer → main ─────────────────────────────────────
ipcMain.on('window-minimize', () => mainWindow.minimize());
ipcMain.on('window-maximize', () => {
  mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize();
});
ipcMain.on('window-close',   () => mainWindow.hide());
ipcMain.on('window-quit',    () => { isQuitting = true; app.quit(); });
ipcMain.on('notify-growth',  (_, data) => {
  showTrayNotification('🧠 ¡Polaris IA creció!', `La red neuronal ahora tiene ${data.neurons} neuronas.`);
});

// ── App lifecycle ─────────────────────────────────────────────────────────
app.whenReady().then(() => {
  createWindow();
  createTray();
});

app.on('before-quit', () => { isQuitting = true; });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });

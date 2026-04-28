const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('polarisApp', {
  minimize:      () => ipcRenderer.send('window-minimize'),
  maximize:      () => ipcRenderer.send('window-maximize'),
  close:         () => ipcRenderer.send('window-close'),
  quit:          () => ipcRenderer.send('window-quit'),
  notifyGrowth:  (data) => ipcRenderer.send('notify-growth', data),
  triggerCycle:  () => ipcRenderer.on('trigger-cycle', () => {
    fetch('https://pdlc-polaris-ia.hf.space/trigger-cycle').catch(() => {});
  }),
});

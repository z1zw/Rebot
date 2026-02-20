const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('rebot', {
  chooseDirectory: () => ipcRenderer.invoke('choose-directory')
});

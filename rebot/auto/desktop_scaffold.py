"""Electron desktop scaffold for workbench UI."""

from __future__ import annotations

from pathlib import Path


def build_electron_app(path: Path, product: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "package.json").write_text(_pkg(product), encoding="utf-8")
    (path / "main.js").write_text(_main_js(), encoding="utf-8")
    (path / "preload.js").write_text(_preload_js(), encoding="utf-8")
    (path / "README.md").write_text(_readme(), encoding="utf-8")


def _pkg(product: str) -> str:
    name = product.lower().replace(" ", "-")
    return (
        "{\n"
        f"  \"name\": \"{name}-desktop\",\n"
        "  \"version\": \"0.1.0\",\n"
        "  \"main\": \"main.js\",\n"
        "  \"scripts\": {\n"
        "    \"dev\": \"electron .\",\n"
        "    \"start\": \"electron .\"\n"
        "  },\n"
        "  \"devDependencies\": {\n"
        "    \"electron\": \"^29.4.1\"\n"
        "  }\n"
        "}\n"
    )


def _main_js() -> str:
    return (
        "const { app, BrowserWindow, dialog, ipcMain } = require('electron');\n"
        "const path = require('path');\n"
        "const createWindow = () => {\n"
        "  const win = new BrowserWindow({\n"
        "    width: 1400,\n"
        "    height: 900,\n"
        "    webPreferences: {\n"
        "      preload: path.join(__dirname, 'preload.js')\n"
        "    }\n"
        "  });\n"
        "  const devUrl = process.env.REBOT_DEV_URL;\n"
        "  if (devUrl) {\n"
        "    win.loadURL(devUrl);\n"
        "  } else {\n"
        "    win.loadFile(path.join(__dirname, '../frontend/dist/index.html'));\n"
        "  }\n"
        "};\n"
        "app.whenReady().then(() => {\n"
        "  ipcMain.handle('choose-directory', async () => {\n"
        "    const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });\n"
        "    if (result.canceled) return null;\n"
        "    return result.filePaths[0];\n"
        "  });\n"
        "  createWindow();\n"
        "});\n"
    )


def _preload_js() -> str:
    return (
        "const { contextBridge, ipcRenderer } = require('electron');\n"
        "contextBridge.exposeInMainWorld('rebot', {\n"
        "  chooseDirectory: () => ipcRenderer.invoke('choose-directory')\n"
        "});\n"
    )


def _readme() -> str:
    return (
        "# Desktop App\n\n"
        "Run with:\n"
        "- `set REBOT_DEV_URL=http://localhost:5173`\n"
        "- `npm install`\n"
        "- `npm run dev`\n"
    )

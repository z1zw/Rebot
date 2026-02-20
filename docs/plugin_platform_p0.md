# Plugin Platform P0

This document describes the first plugin platform baseline:

- Permission-gated plugin execution sandbox (file/network/command).
- Plugin SDK scaffold + signature verification.
- Install/upgrade/rollback/toggle lifecycle.

## 1. Manifest

Each plugin package must include `plugin.json`:

```json
{
  "id": "my.plugin.id",
  "name": "My Plugin",
  "version": "0.1.0",
  "description": "Plugin description",
  "permissions": ["fs.read", "fs.write"],
  "entry": "main.py",
  "signature_alg": "hmac-sha256",
  "signature": ""
}
```

Allowed permissions:

- `fs.read`
- `fs.write`
- `git.read`
- `git.write`
- `net.http`
- `exec.command`

## 2. Signature Model

Signature algorithm: `hmac-sha256`.

Digest scope:

- Includes all files in plugin package recursively.
- Excludes `plugin.json` and `plugin.sig`.

Payload:

`{plugin_id}\n{version}\n{digest_hex}`

Verification key:

- Environment variable: `REBOT_PLUGIN_SIGNING_KEY`.
- If `signature` is present but key missing, install/upgrade fails.
- If `signature` missing, plugin is accepted as `unsigned`.

## 3. Lifecycle APIs

- `GET /api/plugins/installed`
- `POST /api/plugins/install`
- `POST /api/plugins/upgrade`
- `POST /api/plugins/rollback`
- `POST /api/plugins/toggle`

## 4. Sandbox Execution API

`POST /api/plugins/execute`

Request shape:

```json
{
  "plugin_id": "my.plugin.id",
  "operation": "fs.read",
  "workspace": "C:/workspace/demo",
  "args": {
    "path": "README.md"
  }
}
```

Supported operations:

- `fs.read`
- `fs.write`
- `net.http_get`
- `exec.command`

Each operation is hard-blocked if plugin permission is missing.

## 5. SDK APIs

- `GET /api/plugins/sdk/template`
- `POST /api/plugins/sdk/init`

`sdk/init` creates:

- `plugin.json`
- `main.py`
- `sign_plugin.ps1`
- `README.md`


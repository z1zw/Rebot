Place Monaco offline package here.

Required runtime path:

- assets/monaco/min/vs/loader.js
- assets/monaco/min/vs/editor/editor.main.js
- and the full Monaco `min/vs` directory tree

Recommended source:

- npm package `monaco-editor` version `0.52.2`
- copy from `node_modules/monaco-editor/min/vs` into:
  `assets/monaco/min/vs`

This app now loads Monaco from local `flutter_assets` only (no CDN).

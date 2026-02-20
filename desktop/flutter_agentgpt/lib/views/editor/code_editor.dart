import "dart:convert";
import "dart:async";
import "dart:io";
import "package:flutter/material.dart";
import "package:webview_windows/webview_windows.dart";
import "package:rebot_agentgpt/theme/app_tokens.dart";

class EditorModeToggle extends StatelessWidget {
  const EditorModeToggle({
    super.key,
    required this.monacoEnabled,
    required this.onChanged,
  });

  final bool monacoEnabled;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 28,
      decoration: BoxDecoration(
        color: AppTokens.surface,
        borderRadius: BorderRadius.circular(AppTokens.radiusSm),
        border: Border.all(color: AppTokens.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ToggleItem(
            label: "Native",
            selected: !monacoEnabled,
            onTap: () => onChanged(false),
          ),
          _ToggleItem(
            label: "Monaco",
            selected: monacoEnabled,
            onTap: () => onChanged(true),
          ),
        ],
      ),
    );
  }
}

class _ToggleItem extends StatelessWidget {
  const _ToggleItem({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(AppTokens.radiusSm),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? AppTokens.primary.withOpacity(0.18) : Colors.transparent,
          borderRadius: BorderRadius.circular(AppTokens.radiusSm),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: selected ? AppTokens.primary : AppTokens.textSecondary,
            fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
          ),
        ),
      ),
    );
  }
}

class MonacoPreview extends StatefulWidget {
  const MonacoPreview({
    super.key,
    required this.content,
    required this.language,
    required this.onChanged,
    this.readOnly = false,
    this.onUnavailable,
  });

  final String content;
  final String language;
  final ValueChanged<String> onChanged;
  final bool readOnly;
  final VoidCallback? onUnavailable;

  @override
  State<MonacoPreview> createState() => _MonacoPreviewState();
}

class _MonacoPreviewState extends State<MonacoPreview> {
  final WebviewController _controller = WebviewController();
  bool _ready = false;
  String _lastPayload = "";
  String _lastContent = "";
  bool _monacoReady = false;
  Timer? _readyTimer;
  StreamSubscription<dynamic>? _messageSub;

  @override
  void initState() {
    super.initState();
    _lastContent = widget.content;
    _init();
  }

  @override
  void didUpdateWidget(covariant MonacoPreview oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_ready) return;
    if (oldWidget.content == widget.content &&
        oldWidget.language == widget.language &&
        oldWidget.readOnly == widget.readOnly) {
      return;
    }
    if (oldWidget.content != widget.content && widget.content != _lastContent) {
      _lastContent = widget.content;
      _syncContentToEditor(widget.content);
      return;
    }
    if (oldWidget.language != widget.language || oldWidget.readOnly != widget.readOnly) {
      _load();
    }
  }

  Future<void> _init() async {
    try {
      await _controller.initialize();
      _messageSub = _controller.webMessage.listen(_onWebMessage);
      if (!mounted) return;
      setState(() => _ready = true);
      await _load();
    } catch (_) {}
  }

  Future<void> _load() async {
    final encoded = base64Encode(utf8.encode(_html(widget.content, widget.language, widget.readOnly)));
    if (encoded == _lastPayload) return;
    _lastPayload = encoded;
    _lastContent = widget.content;
    _monacoReady = false;
    _readyTimer?.cancel();
    _readyTimer = Timer(const Duration(seconds: 6), () {
      if (!_monacoReady) widget.onUnavailable?.call();
    });
    await _controller.loadUrl("data:text/html;base64,$encoded");
  }

  Future<void> _syncContentToEditor(String content) async {
    final safeCode = jsonEncode(content);
    await _controller.executeScript("""
      if (window.__editor) {
        const incoming = $safeCode;
        const current = window.__editor.getValue();
        if (incoming !== current) {
          window.__skipNextPost = true;
          window.__editor.setValue(incoming);
        }
      }
    """);
  }

  void _onWebMessage(dynamic message) {
    Map<String, dynamic>? data;
    if (message is Map) {
      data = message.map((key, value) => MapEntry("$key", value));
    } else if (message is String) {
      try {
        final parsed = jsonDecode(message);
        if (parsed is Map) {
          data = parsed.map((key, value) => MapEntry("$key", value));
        }
      } catch (_) {}
    }
    if (data == null) return;
    final type = (data["type"] ?? "").toString();
    if (type == "ready") {
      _monacoReady = true;
      _readyTimer?.cancel();
      return;
    }
    if (type == "error") {
      widget.onUnavailable?.call();
      return;
    }
    if (type != "change") return;
    final value = (data["value"] ?? "").toString();
    if (value == _lastContent) return;
    _lastContent = value;
    widget.onChanged(value);
  }

  @override
  Widget build(BuildContext context) {
    if (!_ready) {
      return const Center(
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }
    return Webview(_controller);
  }

  @override
  void dispose() {
    _readyTimer?.cancel();
    _messageSub?.cancel();
    unawaited(_controller.dispose());
    super.dispose();
  }

  String _html(String content, String language, bool readOnly) {
    final safeCode = jsonEncode(content);
    final safeLang = jsonEncode(language);
    final safeReadOnly = readOnly ? "true" : "false";
    final vsPath = _localMonacoVsUri();
    final safeVsPath = jsonEncode(vsPath);
    final safeLoaderSrc = jsonEncode("$vsPath/loader.js");
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>
    html, body, #app { margin: 0; width: 100%; height: 100%; overflow: hidden; background: #1e1e1e; }
  </style>
  <script>
    (function() {
      var s = document.createElement("script");
      s.src = $safeLoaderSrc;
      s.onerror = function() {
        if (window.chrome && window.chrome.webview) {
          window.chrome.webview.postMessage(JSON.stringify({ type: "error", reason: "monaco_loader_missing" }));
        }
      };
      document.head.appendChild(s);
    })();
  </script>
</head>
<body>
  <div id="app"></div>
  <script>
    const code = $safeCode;
    const language = $safeLang;
    const vsPath = $safeVsPath;
    function boot() {
      if (typeof require === "undefined") {
        setTimeout(boot, 50);
        return;
      }
      require.config({ paths: { vs: vsPath } });
      require(["vs/editor/editor.main"], function () {
      window.__skipNextPost = false;
      window.__editor = monaco.editor.create(document.getElementById("app"), {
        value: code,
        language: language,
        readOnly: $safeReadOnly,
        automaticLayout: true,
        minimap: { enabled: false },
        theme: "vs-dark",
        fontSize: 13,
        fontFamily: "JetBrains Mono, Consolas, monospace",
        lineHeight: 21
      });
      window.__editor.onDidChangeModelContent(function () {
        if (window.__skipNextPost) {
          window.__skipNextPost = false;
          return;
        }
        if (window.chrome && window.chrome.webview) {
          window.chrome.webview.postMessage(JSON.stringify({
            type: "change",
            value: window.__editor.getValue()
          }));
        }
      });
      if (window.chrome && window.chrome.webview) {
        window.chrome.webview.postMessage(JSON.stringify({ type: "ready" }));
      }
      }, function() {
        if (window.chrome && window.chrome.webview) {
          window.chrome.webview.postMessage(JSON.stringify({ type: "error", reason: "monaco_boot_failed" }));
        }
      });
    }
    boot();
  </script>
</body>
</html>
""";
  }

  String _localMonacoVsUri() {
    final exe = File(Platform.resolvedExecutable).parent;
    final flutterAssets = exe.path.endsWith("data")
        ? Directory("${exe.path}${Platform.pathSeparator}flutter_assets")
        : Directory("${exe.path}${Platform.pathSeparator}data${Platform.pathSeparator}flutter_assets");
    final vsDir = Directory(
      "${flutterAssets.path}${Platform.pathSeparator}assets${Platform.pathSeparator}monaco${Platform.pathSeparator}min${Platform.pathSeparator}vs",
    );
    return Uri.file(vsDir.path).toString();
  }
}

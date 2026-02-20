import "dart:async";
import "dart:io";
import "dart:ui" as ui;
import "package:flutter/material.dart";
import "package:flutter/rendering.dart";
import "package:flutter/services.dart";
import "package:provider/provider.dart";
import "package:webview_windows/webview_windows.dart";
import "package:http/http.dart" as http;
import "../app_state.dart";
import "preview/device_profiles.dart";

/// Connected device info
class ConnectedDevice {
  final String id;
  final String model;
  final String type; // "device" | "emulator"
  final String status; // "online" | "offline"

  ConnectedDevice({
    required this.id,
    required this.model,
    this.type = "device",
    this.status = "online",
  });

  factory ConnectedDevice.fromJson(Map<String, dynamic> json) {
    return ConnectedDevice(
      id: json["id"]?.toString() ?? "",
      model: json["model"]?.toString() ?? json["id"]?.toString() ?? "Unknown",
      type: json["type"]?.toString() ?? "device",
      status: json["status"]?.toString() ?? "online",
    );
  }

  bool get isOnline => status == "online";
  bool get isEmulator =>
      type == "emulator" ||
      id.contains("emulator") ||
      id.startsWith("192.168.");
}

class RightPanel extends StatefulWidget {
  const RightPanel({
    super.key,
    required this.selectedDevice,
    this.onDeviceChanged,
    this.activeTab = "preview",
    this.onActiveTabChanged,
  });

  final String selectedDevice;
  final ValueChanged<String>? onDeviceChanged;
  final String activeTab;
  final ValueChanged<String>? onActiveTabChanged;

  @override
  State<RightPanel> createState() => _RightPanelState();
}

class _RightPanelState extends State<RightPanel> {
  static const Color _xBlue = Color(0xFF0A84FF);
  static const Color _xStroke = Color(0xFF3A3F48);
  static const Color _xPanel = Color(0xFF252830);
  static const Color _xPanel2 = Color(0xFF2D3138);
  static const MethodChannel _embedChannel =
      MethodChannel("rebot.emulator.embed");
  final WebviewController _controller = WebviewController();
  final TextEditingController _urlController = TextEditingController();
  final GlobalKey _previewKey = GlobalKey();
  final GlobalKey _captureKey = GlobalKey();

  bool _initialized = false;
  String? _lastPreviewUrl;
  String _device = "iPhone 15 Pro";
  bool _running = false;
  bool _runActionInFlight = false;
  bool _reachable = false;
  bool _emuRunning = false;
  String _emuDevice = "None";
  bool _mirrorRunning = false;
  bool _embedded = false;
  Timer? _statusTimer;
  String _activeTab = "preview";
  int _lastReloadSignal = 0;
  int _lastCaptureSignal = 0;

  // 閳光偓閳光偓閳光偓 Device Panel State 閳光偓閳光偓閳光偓
  bool _showDevicePanel = false;
  List<ConnectedDevice> _connectedDevices = [];
  bool _loadingDevices = false;
  String? _selectedDeviceId;
  bool _adbAvailable = false;
  bool _scrcpyAvailable = false;
  bool _connectingMirror = false;

  static const _devices = {
    // iPhone
    "iPhone 15 Pro": Size(393, 852),
    "iPhone 15 Pro Max": Size(430, 932),
    "iPhone 15": Size(390, 844),
    "iPhone 14": Size(390, 844),
    "iPhone SE": Size(375, 667),
    "iPhone 13 mini": Size(375, 812),
    // Android
    "Pixel 8": Size(412, 915),
    "Pixel 7": Size(412, 915),
    "Pixel 6a": Size(412, 892),
    "Samsung S24": Size(360, 780),
    "Samsung S23": Size(360, 780),
    // iPad
    "iPad Pro 12.9": Size(1024, 1366),
    "iPad Pro 11": Size(834, 1194),
    "iPad Air": Size(820, 1180),
    "iPad mini": Size(744, 1133),
    // Desktop
    "Desktop 1920": Size(1920, 1080),
    "Desktop 1440": Size(1440, 900),
    "Desktop 1280": Size(1280, 720),
    // Custom
    "Custom": Size(400, 800),
  };

  static const _platforms = {
    "iPhone 15 Pro": "ios",
    "iPhone 15 Pro Max": "ios",
    "iPhone 15": "ios",
    "iPhone 14": "ios",
    "iPhone SE": "ios",
    "iPhone 13 mini": "ios",
    "Pixel 8": "android",
    "Pixel 7": "android",
    "Pixel 6a": "android",
    "Samsung S24": "android",
    "Samsung S23": "android",
    "iPad Pro 12.9": "ios",
    "iPad Pro 11": "ios",
    "iPad Air": "ios",
    "iPad mini": "ios",
    "Desktop 1920": "desktop",
    "Desktop 1440": "desktop",
    "Desktop 1280": "desktop",
    "Custom": "desktop",
  };

  // Xcode-style zoom levels
  double _zoom = 1.0;
  bool _landscape = false;
  final Size _customSize = const Size(400, 800);

  @override
  void initState() {
    super.initState();
    _device = widget.selectedDevice;
    _activeTab = widget.activeTab;
    // Don't init webview immediately - wait for user to view preview tab
    if (_activeTab == "preview") {
      Future.delayed(const Duration(milliseconds: 1000), () {
        if (mounted && !_initialized) _initWebview();
      });
    }
    // Delay status polling significantly
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted) _startStatusPolling();
    });
    _checkToolsAvailability();
  }

  @override
  void didUpdateWidget(covariant RightPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.selectedDevice != oldWidget.selectedDevice &&
        widget.selectedDevice != _device) {
      setState(() => _device = widget.selectedDevice);
    }
    if (widget.activeTab != oldWidget.activeTab &&
        widget.activeTab != _activeTab) {
      setState(() => _activeTab = widget.activeTab);
      // Init webview only when preview tab is first viewed
      if (_activeTab == "preview" && !_initialized) {
        Future.delayed(const Duration(milliseconds: 500), () {
          if (mounted && !_initialized) _initWebview();
        });
      }
    }
  }

  @override
  void dispose() {
    _urlController.dispose();
    _statusTimer?.cancel();
    super.dispose();
  }

  Future<void> _checkToolsAvailability() async {
    final state = context.read<AppState>();
    final adb = await state.isAdbAvailable();
    final scrcpy = await state.isScrcpyAvailable();
    if (mounted) {
      setState(() {
        _adbAvailable = adb;
        _scrcpyAvailable = scrcpy;
      });
    }
  }

  Future<void> _refreshDevices() async {
    if (_loadingDevices) return;
    setState(() => _loadingDevices = true);
    try {
      final state = context.read<AppState>();
      final devices = await state.getConnectedDevices();
      if (mounted) {
        setState(() {
          _connectedDevices =
              devices.map((d) => ConnectedDevice.fromJson(d)).toList();
          _loadingDevices = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loadingDevices = false);
    }
  }

  Future<void> _connectToDevice(String deviceId) async {
    if (_connectingMirror) return;
    setState(() {
      _connectingMirror = true;
      _selectedDeviceId = deviceId;
    });
    try {
      final state = context.read<AppState>();
      final success = await state.startMirrorForDevice(deviceId);
      if (mounted) {
        setState(() {
          _connectingMirror = false;
          if (success) {
            _mirrorRunning = true;
            _emuDevice = _connectedDevices
                .firstWhere((d) => d.id == deviceId,
                    orElse: () =>
                        ConnectedDevice(id: deviceId, model: deviceId))
                .model;
          }
        });
        if (success) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text("Mirror started for $_emuDevice"),
              backgroundColor: const Color(0xFF1F2D3D),
            ),
          );
        }
      }
    } catch (_) {
      if (mounted) setState(() => _connectingMirror = false);
    }
  }

  Future<void> _initWebview() async {
    try {
      await _controller.initialize();
      if (mounted) setState(() => _initialized = true);
    } catch (e) {
      debugPrint("Webview init failed: $e");
      // Continue without webview - preview won't work but app won't crash
    }
  }

  void _syncControllersFromValues(String previewUrl) {
    if (previewUrl != _lastPreviewUrl) {
      _lastPreviewUrl = previewUrl;
      _urlController.text = previewUrl;
      if (_initialized) {
        try {
          _controller.loadUrl(previewUrl);
        } catch (e) {
          debugPrint("Webview loadUrl failed: $e");
        }
      }
    }
  }

  void _startStatusPolling() {
    _statusTimer?.cancel();
    _statusTimer = Timer.periodic(const Duration(seconds: 8), (_) async {
      if (!mounted) return;
      try {
        final state = context.read<AppState>();
        if (state.activeProject == null) return;

        final status = await state.getFrameworkStatus(state.selectedFramework);
        final running = status["running"] == true;
        if (mounted && running != _running) setState(() => _running = running);

        if (_activeTab == "preview") {
          final emu = await state.getEmulatorStatus();
          final emuRunning = emu["running"] == true;
          final emuDevice = (emu["device"] ?? "None").toString();
          final mirrorRunning = emu["mirror_running"] == true;
          if (mounted &&
              (emuRunning != _emuRunning || emuDevice != _emuDevice)) {
            setState(() {
              _emuRunning = emuRunning;
              _emuDevice = emuDevice;
            });
          }
          if (mounted && mirrorRunning != _mirrorRunning) {
            setState(() => _mirrorRunning = mirrorRunning);
          }
          if (emuRunning && !mirrorRunning) await state.startEmulatorMirror();
          if (mirrorRunning && !_embedded) await _tryEmbedExisting();
          if (running) {
            final reachable = await _pingPreview(state.previewUrl);
            if (mounted && reachable != _reachable) {
              setState(() => _reachable = reachable);
            }
          } else if (mounted && _reachable) {
            setState(() => _reachable = false);
          }
        }
      } catch (e) {
        debugPrint("Status polling error: $e");
      }
    });
  }

  Future<bool> _pingPreview(String url) async {
    try {
      final r =
          await http.get(Uri.parse(url)).timeout(const Duration(seconds: 1));
      return r.statusCode < 500;
    } catch (_) {
      return false;
    }
  }

  Future<void> _capturePreviewSnapshot() async {
    try {
      final boundary = _captureKey.currentContext?.findRenderObject()
          as RenderRepaintBoundary?;
      if (boundary == null) {
        throw Exception("preview_not_ready");
      }
      final ui.Image image = await boundary.toImage(pixelRatio: 1.5);
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      if (byteData == null) {
        throw Exception("snapshot_failed");
      }
      final bytes = byteData.buffer.asUint8List();
      final home = Platform.environment["USERPROFILE"] ??
          Platform.environment["HOME"] ??
          "";
      Directory dir;
      if (home.isNotEmpty) {
        final downloads = Directory("$home\\Downloads\\RebotShots");
        dir = downloads;
      } else {
        dir = Directory("${Directory.systemTemp.path}\\rebot");
      }
      if (!await dir.exists()) {
        await dir.create(recursive: true);
      }
      final stamp = DateTime.now().millisecondsSinceEpoch;
      final file = File("${dir.path}\\preview_$stamp.png");
      await file.writeAsBytes(bytes, flush: true);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Preview snapshot saved: ${file.path}")),
      );
    } catch (_) {
      await Clipboard.setData(ClipboardData(text: _urlController.text.trim()));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text("Snapshot unavailable now. Preview URL copied.")),
      );
    }
  }

  Future<void> _showDevserverLogsDialog(String logs) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E222A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFF343A46)),
        ),
        title: const Text("Devserver Logs"),
        content: SizedBox(
          width: 860,
          height: 520,
          child: SingleChildScrollView(
            child: SelectableText(
              logs.trim().isEmpty ? "No logs available." : logs,
              style: const TextStyle(
                fontFamily: "JetBrains Mono",
                fontSize: 12,
                color: Color(0xFFDCE4F2),
                height: 1.35,
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text("Close")),
        ],
      ),
    );
  }

  Future<void> _tryEmbedExisting() async {
    final rect = _getPreviewRect();
    if (rect == null) return;
    try {
      await _embedChannel.invokeMethod("embedWindow", {
        "title": "Rebot Android Mirror",
        "process": "scrcpy.exe",
        "x": rect.left.round(),
        "y": rect.top.round(),
        "width": rect.width.round(),
        "height": rect.height.round(),
      });
      setState(() => _embedded = true);
    } catch (_) {}
  }

  Rect? _getPreviewRect() {
    final ctx = _previewKey.currentContext;
    if (ctx == null) return null;
    final box = ctx.findRenderObject() as RenderBox?;
    if (box == null) return null;
    return box.localToGlobal(Offset.zero) & box.size;
  }

  @override
  Widget build(BuildContext context) {
    // Only watch specific properties to avoid unnecessary rebuilds
    final previewUrl = context.select<AppState, String>((s) => s.previewUrl);
    final captureSignal =
        context.select<AppState, int>((s) => s.previewCaptureSignal);
    final reloadSignal =
        context.select<AppState, int>((s) => s.previewReloadSignal);

    _syncControllersFromValues(previewUrl);
    if (_lastCaptureSignal != captureSignal) {
      _lastCaptureSignal = captureSignal;
      unawaited(_capturePreviewSnapshot());
    }
    if (_lastReloadSignal != reloadSignal) {
      _lastReloadSignal = reloadSignal;
      if (_initialized) {
        _controller.reload();
      }
    }
    final rawSize = _device == "Custom"
        ? _customSize
        : (_devices[_device] ?? const Size(393, 852));
    final deviceSize =
        _landscape ? Size(rawSize.height, rawSize.width) : rawSize;
    final showPreviewTools = _activeTab == "preview";

    return Column(
      children: [
        _buildXcodeToolbar(),
        Expanded(
          child: _activeTab == "preview"
              ? _buildPreview(deviceSize)
              : (_activeTab == "network"
                  ? _buildNetworkPanel()
                  : _buildConsolePanel()),
        ),
        if (showPreviewTools) _buildPreviewControls(context.read<AppState>()),
      ],
    );
  }

  // Real Xcode-style toolbar: left=tabs | center=device+orientation | right=zoom+run
  Widget _buildXcodeToolbar() {
    final platform = _platforms[_device] ?? "ios";
    final rawSize = _device == "Custom"
        ? _customSize
        : (_devices[_device] ?? const Size(393, 852));
    final deviceSize =
        _landscape ? Size(rawSize.height, rawSize.width) : rawSize;
    Future<void> onRunTap() async {
      if (_runActionInFlight) return;
      final state = context.read<AppState>();
      final messenger = ScaffoldMessenger.of(context);
      setState(() => _runActionInFlight = true);
      if (_running) {
        await state.stopFrameworkServer(framework: state.selectedFramework);
        if (mounted) {
          setState(() {
            _running = false;
            _reachable = false;
            _runActionInFlight = false;
          });
        }
      } else {
        setState(() => _running = true);
        final result = await state.runPreviewWithSelfHeal(
            framework: state.selectedFramework);
        if (!mounted) return;
        if (result["running"] == true) {
          setState(() {
            _running = true;
            _runActionInFlight = false;
          });
          if (_initialized) _controller.loadUrl(state.previewUrl);
          if (state.isWebPreviewFramework(state.selectedFramework)) {
            await state.openPreviewInExternalBrowser(url: state.previewUrl);
          }
        } else {
          setState(() {
            _running = false;
            _runActionInFlight = false;
          });
          final reason = state.previewFailureMessage(result);
          final logs = (result["devserver_logs"] ?? "").toString();
          messenger.showSnackBar(
            SnackBar(
              content: Text("Failed to start dev server: $reason"),
              backgroundColor: const Color(0xFFCC3333),
              duration: const Duration(seconds: 4),
              action: logs.trim().isEmpty
                  ? null
                  : SnackBarAction(
                      label: "View Logs",
                      onPressed: () => _showDevserverLogsDialog(logs),
                    ),
            ),
          );
        }
      }
      if (mounted && _runActionInFlight) {
        setState(() => _runActionInFlight = false);
      }
    }

    Widget leftControls() {
      return Row(
        children: [
          _XcodeTabBar(
            selected: _activeTab,
            onChanged: (v) => setState(() {
              _activeTab = v;
              widget.onActiveTabChanged?.call(v);
              if (v == "preview" && !_initialized) {
                Future.delayed(const Duration(milliseconds: 300), () {
                  if (mounted && !_initialized) _initWebview();
                });
              }
            }),
          ),
          const _XcodeToolbarDivider(),
          _XcodeDeviceButton(
            device: _device,
            platform: platform,
            devices: _devices.keys.toList(),
            onChanged: (v) {
              setState(() => _device = v);
              widget.onDeviceChanged?.call(v);
            },
          ),
          const SizedBox(width: 4),
          _XcodeOrientationButton(
            landscape: _landscape,
            onTap: () => setState(() => _landscape = !_landscape),
          ),
        ],
      );
    }

    Widget rightControls() {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _XcodeZoomControl(
            zoom: _zoom,
            onZoomIn: () =>
                setState(() => _zoom = (_zoom + 0.25).clamp(0.25, 3.0)),
            onZoomOut: () =>
                setState(() => _zoom = (_zoom - 0.25).clamp(0.25, 3.0)),
            onZoomReset: () => setState(() => _zoom = 1.0),
            onZoomSet: (v) => setState(() => _zoom = v.clamp(0.25, 3.0)),
            size: deviceSize,
          ),
          const SizedBox(width: 6),
          _XcodeRunBtn(
            running: _running || _runActionInFlight,
            onTap: () => onRunTap(),
          ),
        ],
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 980;
        return Container(
          height: compact ? 56 : 48,
          decoration: const BoxDecoration(
            color: _xPanel2,
            border: Border(bottom: BorderSide(color: _xStroke, width: 1)),
          ),
          child: compact
              ? ScrollConfiguration(
                  behavior: ScrollConfiguration.of(context)
                      .copyWith(scrollbars: false),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    child: Row(
                      children: [
                        leftControls(),
                        const SizedBox(width: 12),
                        rightControls(),
                      ],
                    ),
                  ),
                )
              : Row(
                  children: [
                    Expanded(
                      child: ScrollConfiguration(
                        behavior: ScrollConfiguration.of(context)
                            .copyWith(scrollbars: false),
                        child: SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                          child: leftControls(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    rightControls(),
                    const SizedBox(width: 8),
                  ],
                ),
        );
      },
    );
  }

  // Preview Panel
  Widget _buildPreview(Size deviceSize) {
    return Stack(
      children: [
        CustomPaint(
          painter: _DotPatternPainter(),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final maxW = constraints.maxWidth;
                final maxH = constraints.maxHeight;
                // Apply zoom to base scale calculation
                final baseScale = [
                  (maxW - 32) / deviceSize.width,
                  (maxH - 32) / deviceSize.height,
                  1.0,
                ].reduce((a, b) => a < b ? a : b);
                final scale = baseScale * _zoom;
                final frameW = deviceSize.width * scale;
                final frameH = deviceSize.height * scale;
                final platform = _platforms[_device] ?? "ios";

                // Only resize mirror once on initial embed, not on every build
                // _resizeMirror is already called elsewhere when needed

                return Center(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: SingleChildScrollView(
                      scrollDirection: Axis.vertical,
                      child: RepaintBoundary(
                        key: _captureKey,
                        child: _XcodeDeviceFrame(
                          key: _previewKey,
                          width: frameW,
                          height: frameH,
                          platform: platform,
                          deviceName: _device,
                          landscape: _landscape,
                          child: _initialized
                              ? Stack(
                                  children: [
                                    Webview(_controller),
                                    if (!_running || !_reachable)
                                      Container(
                                        color: Colors.white,
                                        child: Center(
                                          child: !_running
                                              ? _XcodeEmptyPreview(
                                                  deviceName: _device)
                                              : const _PreviewLoadingSkeleton(),
                                        ),
                                      ),
                                  ],
                                )
                              : Center(
                                  child:
                                      _XcodeEmptyPreview(deviceName: _device)),
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ),
        // Device Panel Overlay
        if (_showDevicePanel)
          Positioned(
            left: 12,
            top: 12,
            child: _DeviceConnectionPanel(
              devices: _connectedDevices,
              loading: _loadingDevices,
              connecting: _connectingMirror,
              selectedDeviceId: _selectedDeviceId,
              adbAvailable: _adbAvailable,
              scrcpyAvailable: _scrcpyAvailable,
              onRefresh: _refreshDevices,
              onConnect: _connectToDevice,
              onClose: () => setState(() => _showDevicePanel = false),
            ),
          ),
      ],
    );
  }

  Widget _buildNetworkPanel() {
    final state = context.read<AppState>();
    final hasAstDeps = state.astDepAddedLinks > 0 || state.astDepTotalEdges > 0;
    return Container(
      margin: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _xPanel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _xStroke),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: _xPanel2,
              borderRadius: BorderRadius.vertical(top: Radius.circular(10)),
              border: Border(bottom: BorderSide(color: _xStroke)),
            ),
            child: Row(
              children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    color: _xBlue.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(5),
                  ),
                  child:
                      const Icon(Icons.network_check, size: 12, color: _xBlue),
                ),
                const SizedBox(width: 8),
                Text(
                  "Network / Event Logs",
                  style: const TextStyle(
                      fontFamily: "Consolas",
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFF8E8E8E)),
                ),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1F2228),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: _xStroke),
                  ),
                  child: Text(
                    "${state.consoleLogs.length}",
                    style:
                        const TextStyle(fontSize: 10, color: Color(0xFF6E6E6E)),
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Column(
              children: [
                if (hasAstDeps) _buildAstGraphCard(state),
                Expanded(
                  child: state.consoleLogs.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.wifi_off_outlined,
                                  size: 32, color: const Color(0xFF4A4A4A)),
                              const SizedBox(height: 10),
                              const Text("No network activity",
                                  style: TextStyle(
                                      fontSize: 12, color: Color(0xFF6E6E6E))),
                            ],
                          ),
                        )
                      : ListView.builder(
                          padding: const EdgeInsets.all(14),
                          itemCount: state.consoleLogs.length,
                          itemBuilder: (context, index) {
                            final log = state.consoleLogs[index];
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Text(
                                log.text,
                                style: const TextStyle(
                                    fontFamily: "Consolas",
                                    fontSize: 11,
                                    color: Color(0xFFA9B7C6)),
                              ),
                            );
                          },
                        ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAstGraphCard(AppState state) {
    final edges = state.astDepAddedEdges;
    final nodes = _collectAstNodes(edges);
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF1C2624),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF2E4A43)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "AST Dependency Graph",
            style: const TextStyle(
              fontFamily: "Consolas",
              fontSize: 11,
              color: Color(0xFF81D4C0),
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            "attempt ${state.astDepAttempt + 1}  |  +${state.astDepAddedLinks} links  |  files ${state.astDepTouchedFiles}  |  edges ${state.astDepTotalEdges}",
            style: const TextStyle(
              fontFamily: "Consolas",
              fontSize: 10,
              color: Color(0xFFA9B7C6),
            ),
          ),
          if (nodes.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text(
              "Nodes",
              style: TextStyle(
                fontFamily: "Consolas",
                fontSize: 10,
                color: Color(0xFF93B5AE),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: nodes.take(14).map((n) {
                return InkWell(
                  onTap: () => _openAstNode(n),
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF21302D),
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(color: const Color(0xFF385C54)),
                    ),
                    child: Text(
                      n,
                      style: const TextStyle(
                        fontFamily: "Consolas",
                        fontSize: 10,
                        color: Color(0xFFC7E8DF),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
          if (edges.isNotEmpty) ...[
            const SizedBox(height: 8),
            const Text(
              "Edges",
              style: TextStyle(
                fontFamily: "Consolas",
                fontSize: 10,
                color: Color(0xFF93B5AE),
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            ...edges.take(10).map(
                  (e) => Padding(
                    padding: const EdgeInsets.only(bottom: 2),
                    child: Text(
                      "- $e",
                      style: const TextStyle(
                        fontFamily: "Consolas",
                        fontSize: 10,
                        color: Color(0xFF93B5AE),
                      ),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }

  List<String> _collectAstNodes(List<String> edges) {
    final out = <String>[];
    final seen = <String>{};
    for (final edge in edges) {
      final parts = edge.split("->");
      if (parts.length != 2) continue;
      final from = parts[0].trim();
      final to = parts[1].trim();
      if (from.isNotEmpty && !seen.contains(from)) {
        seen.add(from);
        out.add(from);
      }
      if (to.isNotEmpty && !seen.contains(to)) {
        seen.add(to);
        out.add(to);
      }
    }
    return out;
  }

  void _openAstNode(String path) {
    final clean = path.trim();
    if (clean.isEmpty) return;
    unawaited(context.read<AppState>().readFile(clean));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text("Opened $clean"),
        duration: const Duration(milliseconds: 900),
      ),
    );
  }

  Widget _buildConsolePanel() {
    final state = context.read<AppState>();
    return Container(
      margin: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _xPanel,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _xStroke),
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: _xPanel2,
              borderRadius: BorderRadius.vertical(top: Radius.circular(10)),
              border: Border(bottom: BorderSide(color: _xStroke)),
            ),
            child: Row(
              children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: BoxDecoration(
                    color: _xBlue.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(5),
                  ),
                  child: const Icon(Icons.terminal, size: 12, color: _xBlue),
                ),
                const SizedBox(width: 8),
                const Text("Terminal",
                    style: TextStyle(
                        fontSize: 11,
                        color: Color(0xFF8E8E8E),
                        fontWeight: FontWeight.w600)),
                const Spacer(),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1F2228),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: _xStroke),
                  ),
                  child: Text(
                    "${state.consoleLogs.length} lines",
                    style:
                        const TextStyle(fontSize: 10, color: Color(0xFF6E6E6E)),
                  ),
                ),
                const SizedBox(width: 8),
                _IdeaMiniBtn(
                  icon: Icons.delete_outline,
                  onTap: state.clearConsoleLogs,
                  tooltip: "Clear",
                ),
              ],
            ),
          ),
          Expanded(
            child: Stack(
              children: [
                ListView.builder(
                  padding: const EdgeInsets.all(14),
                  itemCount: state.consoleLogs.length,
                  itemBuilder: (context, index) {
                    final log = state.consoleLogs[index];
                    Color color;
                    switch (log.level) {
                      case "info":
                        color = const Color(0xFF0A84FF);
                        break;
                      case "success":
                        color = const Color(0xFF64D2FF);
                        break;
                      case "warning":
                        color = const Color(0xFFFFCC00);
                        break;
                      case "error":
                        color = const Color(0xFFFF6B6B);
                        break;
                      default:
                        color = const Color(0xFFA9B7C6);
                    }
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 3),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SizedBox(
                            width: 28,
                            child: Text(
                              "${index + 1}",
                              style: const TextStyle(
                                  fontFamily: "Consolas",
                                  fontSize: 10,
                                  color: Color(0xFF4A4A4A)),
                            ),
                          ),
                          Expanded(
                            child: Text(
                              log.text,
                              style: TextStyle(
                                  fontFamily: "Consolas",
                                  fontSize: 11,
                                  color: color,
                                  height: 1.6),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  height: 24,
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          const Color(0xFF171717).withValues(alpha: 0),
                          const Color(0xFF171717)
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPreviewControls(AppState state) {
    return Container(
      height: 44,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.bottomCenter,
          end: Alignment.topCenter,
          colors: [Color(0xFF252525), Color(0xFF212121)],
        ),
        border: const Border(top: BorderSide(color: Color(0xFF171717))),
      ),
      child: Row(
        children: [
          _MiniButton(
            icon: Icons.info_outline_rounded,
            onTap: () {
              showDialog<void>(
                context: context,
                builder: (ctx) => Dialog(
                  backgroundColor: Colors.transparent,
                  child: Container(
                    width: 420,
                    decoration: BoxDecoration(
                      color: const Color(0xFF212121),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF2A2A2A)),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 14),
                          decoration: const BoxDecoration(
                            color: Color(0xFF2A2A2A),
                            borderRadius:
                                BorderRadius.vertical(top: Radius.circular(10)),
                          ),
                          child: const Row(
                            children: [
                              Icon(Icons.info_outline_rounded,
                                  size: 18, color: Color(0xFFD1D5DB)),
                              SizedBox(width: 10),
                              Text("Execution Status",
                                  style: TextStyle(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w600,
                                      color: Color(0xFFD1D5DB))),
                            ],
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: const Color(0xFF171717),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              "status: ${state.executionStatus}\nmetrics: ${state.lastRunMetrics}",
                              style: const TextStyle(
                                  fontFamily: "JetBrains Mono",
                                  fontSize: 12,
                                  color: Color(0xFFA9B7C6)),
                            ),
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 12),
                          decoration: const BoxDecoration(
                              border: Border(
                                  top: BorderSide(color: Color(0xFF2A2A2A)))),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              MouseRegion(
                                cursor: SystemMouseCursors.click,
                                child: GestureDetector(
                                  onTap: () => Navigator.of(ctx).pop(),
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 16, vertical: 8),
                                    decoration: BoxDecoration(
                                        color: const Color(0xFF0A84FF),
                                        borderRadius: BorderRadius.circular(6)),
                                    child: const Text("Close",
                                        style: TextStyle(
                                            fontSize: 12,
                                            fontWeight: FontWeight.w500,
                                            color: Colors.white)),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            },
          ),
          const SizedBox(width: 6),
          _MiniButton(
            icon: _running
                ? Icons.stop_circle_outlined
                : Icons.play_circle_outline_rounded,
            onTap: () async {
              if (_running) {
                await state.stopFrameworkServer(
                    framework: state.selectedFramework);
                if (mounted) {
                  setState(() {
                    _running = false;
                    _reachable = false;
                  });
                }
              } else {
                final result = await state.runPreviewWithSelfHeal(
                    framework: state.selectedFramework);
                final running = result["running"] == true;
                if (mounted && running) {
                  setState(() => _running = true);
                  if (state.isWebPreviewFramework(state.selectedFramework)) {
                    await state.openPreviewInExternalBrowser(
                        url: state.previewUrl);
                  }
                }
                if (mounted && !running) {
                  final reason = state.previewFailureMessage(result);
                  final logs = (result["devserver_logs"] ?? "").toString();
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text("Failed to start dev server: $reason"),
                      backgroundColor: const Color(0xFFCC3333),
                      duration: const Duration(seconds: 4),
                      action: logs.trim().isEmpty
                          ? null
                          : SnackBarAction(
                              label: "View Logs",
                              onPressed: () => _showDevserverLogsDialog(logs),
                            ),
                    ),
                  );
                }
                if (mounted && _initialized) {
                  _controller.loadUrl(state.previewUrl);
                }
              }
            },
          ),
          const SizedBox(width: 6),
          _MiniButton(
              icon: Icons.refresh,
              onTap: () {
                if (_initialized) _controller.reload();
              }),
          const SizedBox(width: 6),
          _MiniButton(
            icon: Icons.open_in_full_rounded,
            onTap: () async {
              final target = _urlController.text.trim().isEmpty
                  ? state.previewUrl
                  : _urlController.text.trim();
              final opened =
                  await state.openPreviewInExternalBrowser(url: target);
              if (!opened && _initialized) {
                _controller.loadUrl(target);
              }
            },
          ),
          const Spacer(),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: _running
                  ? (_reachable
                      ? const Color(0xFF2A3D55)
                      : const Color(0xFF2A2A2A))
                  : const Color(0xFF2A2A2A),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                  color: _running && _reachable
                      ? const Color(0xFF3B7B50)
                      : const Color(0xFF4A4D50)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: _running
                        ? (_reachable
                            ? const Color(0xFF64D2FF)
                            : const Color(0xFFFFCC00))
                        : const Color(0xFF8E8E8E),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  _running
                      ? (_reachable ? "Running" : "Connecting...")
                      : "Idle",
                  style: TextStyle(
                    fontSize: 10,
                    color: _running
                        ? (_reachable
                            ? const Color(0xFF64D2FF)
                            : const Color(0xFFFFCC00))
                        : const Color(0xFF8E8E8E),
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (_emuRunning)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFF1F2D3D),
                borderRadius: BorderRadius.circular(5),
                border: Border.all(color: const Color(0xFF0A84FF)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.phone_android,
                      size: 10, color: Color(0xFF0A84FF)),
                  const SizedBox(width: 4),
                  Text(
                    _emuDevice,
                    style:
                        const TextStyle(fontSize: 10, color: Color(0xFF0A84FF)),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _DotPatternPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final bg = Paint()..color = const Color(0xFF171717);
    canvas.drawRect(Offset.zero & size, bg);
    final dot = Paint()..color = const Color(0xFF212121);
    const step = 18.0;
    for (double x = 0; x < size.width; x += step) {
      for (double y = 0; y < size.height; y += step) {
        canvas.drawCircle(Offset(x, y), 1.2, dot);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _PreviewMini extends StatefulWidget {
  const _PreviewMini({required this.running, required this.url});

  final bool running;
  final String url;

  @override
  State<_PreviewMini> createState() => _PreviewMiniState();
}

class _PreviewMiniState extends State<_PreviewMini> {
  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    super.dispose();
  }

  String _shortUrl(String url) {
    final u = Uri.tryParse(url);
    if (u == null) return "localhost";
    final host = u.host.isEmpty ? "localhost" : u.host;
    return u.hasPort ? "$host:${u.port}" : host;
  }

  @override
  Widget build(BuildContext context) {
    final live = widget.running;
    final urlText = _shortUrl(widget.url);
    return Container(
      width: 112,
      height: 72,
      decoration: BoxDecoration(
        color: const Color(0xFF212121),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF2A2A2A)),
      ),
      child: Column(
        children: [
          Container(
            height: 18,
            padding: const EdgeInsets.symmetric(horizontal: 6),
            decoration: const BoxDecoration(
              color: Color(0xFF2A2A2A),
              borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
              border: Border(bottom: BorderSide(color: Color(0xFF171717))),
            ),
            child: Row(
              children: [
                const Icon(Icons.visibility_outlined,
                    size: 10, color: Color(0xFF8E8E8E)),
                const SizedBox(width: 4),
                const Text("Mini Preview",
                    style: TextStyle(fontSize: 9, color: Color(0xFF8E8E8E))),
                const Spacer(),
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: live
                        ? const Color(0xFF22C55E)
                        : const Color(0xFF6B6B6B),
                    shape: BoxShape.circle,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    live ? "Live" : "N/A",
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: live
                          ? const Color(0xFF64D2FF)
                          : const Color(0xFF6B6B6B),
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    urlText,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 9,
                      color: Color(0xFF8E8E8E),
                      fontFamily: "JetBrains Mono",
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// PANEL TAB
class _PanelTab extends StatefulWidget {
  const _PanelTab(
      {required this.icon,
      required this.label,
      required this.active,
      required this.onTap});

  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  State<_PanelTab> createState() => _PanelTabState();
}

class _PanelTabState extends State<_PanelTab> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 2),
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: InkWell(
          onTap: widget.onTap,
          borderRadius: BorderRadius.circular(6),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: widget.active
                  ? const Color(0xFFEFF6FF)
                  : _hovered
                      ? const Color(0xFFF8FAFC)
                      : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              border: widget.active
                  ? Border.all(color: const Color(0xFFBFDBFE))
                  : _hovered
                      ? Border.all(color: const Color(0xFFE2E8F0))
                      : null,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(widget.icon,
                    size: 14,
                    color: widget.active
                        ? const Color(0xFF0A84FF)
                        : const Color(0xFF8E8E8E)),
                const SizedBox(width: 5),
                Text(
                  widget.label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight:
                        widget.active ? FontWeight.w600 : FontWeight.w400,
                    color: widget.active
                        ? const Color(0xFF0A84FF)
                        : const Color(0xFF8E8E8E),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PreviewLoadingSkeleton extends StatefulWidget {
  const _PreviewLoadingSkeleton();

  @override
  State<_PreviewLoadingSkeleton> createState() =>
      _PreviewLoadingSkeletonState();
}

class _PreviewLoadingSkeletonState extends State<_PreviewLoadingSkeleton> {
  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: const Color(0xFF2A2A2A),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFF4A4D50)),
          ),
          child: const Icon(Icons.hourglass_top_rounded,
              color: Color(0xFF8E8E8E), size: 26),
        ),
        const SizedBox(height: 12),
        Container(
          width: 120,
          height: 10,
          decoration: BoxDecoration(
            color: const Color(0xFF2A2A2A),
            borderRadius: BorderRadius.circular(99),
          ),
        ),
        const SizedBox(height: 8),
        Container(
          width: 96,
          height: 8,
          decoration: BoxDecoration(
            color: const Color(0xFF2A2A2A),
            borderRadius: BorderRadius.circular(99),
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          "Connecting to dev server...",
          style: TextStyle(fontSize: 11, color: Color(0xFF8E8E8E)),
        ),
      ],
    );
  }
}

class _MiniButton extends StatefulWidget {
  const _MiniButton({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  State<_MiniButton> createState() => _MiniButtonState();
}

class _MiniButtonState extends State<_MiniButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 28,
          height: 28,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF2A2A2A) : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: const Color(0xFF2A2A2A)),
          ),
          child: Icon(widget.icon,
              size: 14,
              color:
                  _hovered ? const Color(0xFFD1D5DB) : const Color(0xFF8E8E8E)),
        ),
      ),
    );
  }
}

/// IDEA妞嬪孩鐗告潻铚傜稑閹稿鎸抽敍鍫㈡暏娴滃海绮撶粩顖ょ礆
class _IdeaMiniBtn extends StatefulWidget {
  const _IdeaMiniBtn({required this.icon, required this.onTap, this.tooltip});
  final IconData icon;
  final VoidCallback onTap;
  final String? tooltip;

  @override
  State<_IdeaMiniBtn> createState() => _IdeaMiniBtnState();
}

class _IdeaMiniBtnState extends State<_IdeaMiniBtn> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final btn = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF4D5052) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Icon(
            widget.icon,
            size: 14,
            color: _hovered ? const Color(0xFFD1D5DB) : const Color(0xFF6E6E6E),
          ),
        ),
      ),
    );
    if (widget.tooltip != null) {
      return Tooltip(
          message: widget.tooltip!,
          waitDuration: const Duration(milliseconds: 500),
          child: btn);
    }
    return btn;
  }
}

// 閳光偓閳光偓閳光偓 Mirror Status Badge 閳光偓閳光偓閳光偓
class _MirrorStatusBadge extends StatefulWidget {
  const _MirrorStatusBadge({
    required this.device,
    required this.onDisconnect,
  });

  final String device;
  final VoidCallback onDisconnect;

  @override
  State<_MirrorStatusBadge> createState() => _MirrorStatusBadgeState();
}

class _MirrorStatusBadgeState extends State<_MirrorStatusBadge> {
  bool _hovered = false;

  @override
  void initState() {
    super.initState();
  }

  @override
  void dispose() {
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onDisconnect,
        child: Tooltip(
          message: "Click to disconnect",
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF1F2D3D),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: const Color(0xFF0A84FF)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    color: Color(0xFF64D2FF),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                const Icon(Icons.phone_android,
                    size: 12, color: Color(0xFF0A84FF)),
                const SizedBox(width: 4),
                Text(
                  widget.device,
                  style: const TextStyle(
                      fontSize: 11,
                      color: Color(0xFF0A84FF),
                      fontWeight: FontWeight.w500),
                ),
                if (_hovered) ...[
                  const SizedBox(width: 6),
                  const Icon(Icons.close, size: 12, color: Color(0xFFFF6B6B)),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// 閳光偓閳光偓閳光偓 Device Connection Panel 閳光偓閳光偓閳光偓
class _DeviceConnectionPanel extends StatelessWidget {
  const _DeviceConnectionPanel({
    required this.devices,
    required this.loading,
    required this.connecting,
    required this.selectedDeviceId,
    required this.adbAvailable,
    required this.scrcpyAvailable,
    required this.onRefresh,
    required this.onConnect,
    required this.onClose,
  });

  final List<ConnectedDevice> devices;
  final bool loading;
  final bool connecting;
  final String? selectedDeviceId;
  final bool adbAvailable;
  final bool scrcpyAvailable;
  final VoidCallback onRefresh;
  final void Function(String deviceId) onConnect;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 320,
      constraints: const BoxConstraints(maxHeight: 400),
      decoration: BoxDecoration(
        color: const Color(0xFF212121),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF2A2A2A)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: const BoxDecoration(
              color: Color(0xFF2A2A2A),
              borderRadius: BorderRadius.vertical(top: Radius.circular(10)),
            ),
            child: Row(
              children: [
                const Icon(Icons.phone_android,
                    size: 16, color: Color(0xFF0A84FF)),
                const SizedBox(width: 8),
                const Text(
                  "Android Devices",
                  style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: Color(0xFFD1D5DB)),
                ),
                const Spacer(),
                _PanelIconBtn(
                  icon: Icons.refresh,
                  loading: loading,
                  onTap: onRefresh,
                  tooltip: "Refresh",
                ),
                const SizedBox(width: 4),
                _PanelIconBtn(
                  icon: Icons.close,
                  onTap: onClose,
                  tooltip: "Close",
                ),
              ],
            ),
          ),
          // Tool Status
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFF2A2A2A))),
            ),
            child: Row(
              children: [
                _ToolStatus(label: "ADB", available: adbAvailable),
                const SizedBox(width: 12),
                _ToolStatus(label: "Scrcpy", available: scrcpyAvailable),
                const Spacer(),
                if (!adbAvailable || !scrcpyAvailable)
                  Tooltip(
                    message:
                        "Install required tools:\n- ADB: Android SDK platform-tools\n- Scrcpy: https://github.com/Genymobile/scrcpy",
                    child: Icon(Icons.info_outline,
                        size: 14, color: Colors.amber.shade400),
                  ),
              ],
            ),
          ),
          // Device List
          if (devices.isEmpty && !loading)
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Icon(Icons.devices_other,
                      size: 40, color: Colors.grey.shade600),
                  const SizedBox(height: 12),
                  const Text(
                    "No devices found",
                    style: TextStyle(fontSize: 13, color: Color(0xFF8E8E8E)),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    "Connect an Android device via USB\nor start an emulator",
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 11, color: Color(0xFF6E6E6E)),
                  ),
                ],
              ),
            )
          else
            Flexible(
              child: ListView.builder(
                shrinkWrap: true,
                padding: const EdgeInsets.symmetric(vertical: 6),
                itemCount: devices.length,
                itemBuilder: (context, index) {
                  final device = devices[index];
                  final isSelected = device.id == selectedDeviceId;
                  final isConnecting = connecting && isSelected;
                  return _DeviceListItem(
                    device: device,
                    isSelected: isSelected,
                    isConnecting: isConnecting,
                    onConnect: () => onConnect(device.id),
                  );
                },
              ),
            ),
          // Footer hint
          Container(
            padding: const EdgeInsets.all(10),
            decoration: const BoxDecoration(
              color: Color(0xFF171717),
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(10)),
            ),
            child: Row(
              children: [
                Icon(Icons.lightbulb_outline,
                    size: 12, color: Colors.amber.shade600),
                const SizedBox(width: 6),
                const Expanded(
                  child: Text(
                    "USB debugging must be enabled on device",
                    style: TextStyle(fontSize: 10, color: Color(0xFF8E8E8E)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ToolStatus extends StatelessWidget {
  const _ToolStatus({required this.label, required this.available});

  final String label;
  final bool available;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(
            color:
                available ? const Color(0xFF64D2FF) : const Color(0xFFFF6B6B),
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            color:
                available ? const Color(0xFF64D2FF) : const Color(0xFFFF6B6B),
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}

class _DeviceListItem extends StatefulWidget {
  const _DeviceListItem({
    required this.device,
    required this.isSelected,
    required this.isConnecting,
    required this.onConnect,
  });

  final ConnectedDevice device;
  final bool isSelected;
  final bool isConnecting;
  final VoidCallback onConnect;

  @override
  State<_DeviceListItem> createState() => _DeviceListItemState();
}

class _DeviceListItemState extends State<_DeviceListItem> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final d = widget.device;
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: d.isOnline && !widget.isConnecting ? widget.onConnect : null,
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: widget.isSelected
                ? const Color(0xFF1F2D3D)
                : _hovered
                    ? const Color(0xFF2A2A2A)
                    : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: widget.isSelected
                ? Border.all(color: const Color(0xFF0A84FF))
                : _hovered
                    ? Border.all(color: const Color(0xFF4A4D50))
                    : null,
          ),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: d.isEmulator
                      ? const Color(0xFF1F2D3D)
                      : const Color(0xFF2A3D55),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(
                  d.isEmulator ? Icons.computer : Icons.phone_android,
                  size: 18,
                  color: d.isEmulator
                      ? const Color(0xFF0A84FF)
                      : const Color(0xFF64D2FF),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      d.model,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: d.isOnline
                            ? const Color(0xFFD1D5DB)
                            : const Color(0xFF6E6E6E),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Container(
                          width: 5,
                          height: 5,
                          decoration: BoxDecoration(
                            color: d.isOnline
                                ? const Color(0xFF64D2FF)
                                : const Color(0xFF8E8E8E),
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          d.isOnline ? "Online" : "Offline",
                          style: TextStyle(
                            fontSize: 10,
                            color: d.isOnline
                                ? const Color(0xFF64D2FF)
                                : const Color(0xFF8E8E8E),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          d.id,
                          style: const TextStyle(
                            fontSize: 9,
                            color: Color(0xFF6E6E6E),
                            fontFamily: "JetBrains Mono",
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (widget.isConnecting)
                const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Color(0xFF0A84FF)),
                )
              else if (d.isOnline && _hovered)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0A84FF),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    "Connect",
                    style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: Colors.white),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PanelIconBtn extends StatefulWidget {
  const _PanelIconBtn({
    required this.icon,
    required this.onTap,
    this.tooltip,
    this.loading = false,
  });

  final IconData icon;
  final VoidCallback onTap;
  final String? tooltip;
  final bool loading;

  @override
  State<_PanelIconBtn> createState() => _PanelIconBtnState();
}

class _PanelIconBtnState extends State<_PanelIconBtn> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final btn = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.loading ? null : widget.onTap,
        child: Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF4D5052) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
          ),
          child: widget.loading
              ? const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                      strokeWidth: 1.5, color: Color(0xFF8E8E8E)),
                )
              : Icon(
                  widget.icon,
                  size: 14,
                  color: _hovered
                      ? const Color(0xFFD1D5DB)
                      : const Color(0xFF8E8E8E),
                ),
        ),
      ),
    );
    if (widget.tooltip != null) {
      return Tooltip(message: widget.tooltip!, child: btn);
    }
    return btn;
  }
}

// 閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查敓?
// Xcode-style UI Components
// 閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查敓?
// New Xcode-accurate toolbar components
// 閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查敓?

/// Divider matching Xcode's subtle toolbar separators
class _XcodeToolbarDivider extends StatelessWidget {
  const _XcodeToolbarDivider();
  @override
  Widget build(BuildContext context) => Container(
      width: 1,
      height: 20,
      margin: const EdgeInsets.symmetric(horizontal: 8),
      color: const Color(0xFF3C3C3C));
}

/// Xcode-style tab bar (Canvas / Console / Network) 閿?looks like Xcode's top editor tabs
class _XcodeTabBar extends StatelessWidget {
  const _XcodeTabBar({required this.selected, required this.onChanged});
  final String selected;
  final ValueChanged<String> onChanged;

  static const _tabs = [
    ("preview", "Canvas", Icons.phone_iphone_rounded),
    ("console", "Console", Icons.terminal_rounded),
    ("network", "Network", Icons.wifi_rounded),
  ];

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 44,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: _tabs.map((t) {
          final isActive = selected == t.$1;
          return _XcodeTabItem(
            label: t.$2,
            icon: t.$3,
            active: isActive,
            onTap: () => onChanged(t.$1),
          );
        }).toList(),
      ),
    );
  }
}

class _XcodeTabItem extends StatefulWidget {
  const _XcodeTabItem({
    required this.label,
    required this.icon,
    required this.active,
    required this.onTap,
  });
  final String label;
  final IconData icon;
  final bool active;
  final VoidCallback onTap;
  @override
  State<_XcodeTabItem> createState() => _XcodeTabItemState();
}

class _XcodeTabItemState extends State<_XcodeTabItem> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: widget.active
                    ? const Color(0xFF007AFF)
                    : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                widget.icon,
                size: 13,
                color: widget.active
                    ? const Color(0xFF007AFF)
                    : _hovered
                        ? const Color(0xFFCCCCCC)
                        : const Color(0xFF888888),
              ),
              const SizedBox(width: 5),
              Text(
                widget.label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: widget.active ? FontWeight.w600 : FontWeight.w400,
                  color: widget.active
                      ? const Color(0xFFDDDDDD)
                      : _hovered
                          ? const Color(0xFFBBBBBB)
                          : const Color(0xFF888888),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Real Xcode device button 閿?shows device icon + name, popup on click
class _XcodeDeviceButton extends StatefulWidget {
  const _XcodeDeviceButton({
    required this.device,
    required this.platform,
    required this.devices,
    required this.onChanged,
  });

  final String device;
  final String platform;
  final List<String> devices;
  final ValueChanged<String> onChanged;

  @override
  State<_XcodeDeviceButton> createState() => _XcodeDeviceButtonState();
}

class _XcodeDeviceButtonState extends State<_XcodeDeviceButton> {
  bool _hovered = false;

  IconData _platformIcon(String device) {
    if (device.startsWith("iPhone") || device.startsWith("iPad")) {
      return Icons.phone_iphone_rounded;
    }
    if (device.startsWith("Pixel") || device.startsWith("Samsung")) {
      return Icons.phone_android_rounded;
    }
    return Icons.desktop_windows_rounded;
  }

  Color _platformColor(String platform) {
    switch (platform) {
      case "ios":
      case "android":
        return const Color(0xFF0A84FF);
      default:
        return const Color(0xFF8E94A3);
    }
  }

  String _groupOf(String name) {
    if (name.startsWith("iPad")) return "Tablet";
    if (name.startsWith("iPhone") ||
        name.startsWith("Pixel") ||
        name.startsWith("Samsung")) {
      return "Mobile";
    }
    if (name.startsWith("Desktop")) return "Desktop";
    return "Other";
  }

  @override
  Widget build(BuildContext context) {
    final accentColor = _platformColor(widget.platform);
    final selectedSize = DeviceProfiles.byName(widget.device).size;
    final selectedSizeText =
        "${selectedSize.width.round()} x ${selectedSize.height.round()}";
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: PopupMenuButton<String>(
        onSelected: widget.onChanged,
        offset: const Offset(0, 40),
        color: const Color(0xFF252830),
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: Color(0xFF3A3F48)),
        ),
        itemBuilder: (context) {
          final groups = <String, List<String>>{};
          for (final d in widget.devices) {
            final group = _groupOf(d);
            groups.putIfAbsent(group, () => <String>[]).add(d);
          }
          const sortOrder = <String, int>{
            "Mobile": 0,
            "Tablet": 1,
            "Desktop": 2,
            "Other": 3,
          };
          final ordered = groups.entries.toList()
            ..sort((a, b) =>
                (sortOrder[a.key] ?? 99).compareTo(sortOrder[b.key] ?? 99));

          final items = <PopupMenuEntry<String>>[];
          items.add(
            PopupMenuItem<String>(
              enabled: false,
              height: 38,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Row(
                children: [
                  const Icon(Icons.aspect_ratio_rounded,
                      size: 14, color: Color(0xFFB8C1D1)),
                  const SizedBox(width: 8),
                  const Text(
                    "Current screen size",
                    style: TextStyle(
                      fontSize: 12,
                      color: Color(0xFFD7DDEA),
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    selectedSizeText,
                    style:
                        const TextStyle(fontSize: 11, color: Color(0xFF8E94A3)),
                  ),
                ],
              ),
            ),
          );
          for (final entry in ordered) {
            items.add(const PopupMenuDivider(height: 6));
            items.add(
              PopupMenuItem<String>(
                enabled: false,
                height: 24,
                padding: const EdgeInsets.symmetric(horizontal: 14),
                child: Text(
                  entry.key.toUpperCase(),
                  style: const TextStyle(
                    fontSize: 10,
                    color: Color(0xFF666666),
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.8,
                  ),
                ),
              ),
            );
            for (final d in entry.value) {
              final isSelected = d == widget.device;
              final size = DeviceProfiles.byName(d).size;
              final sizeText = "${size.width.round()} x ${size.height.round()}";
              items.add(
                PopupMenuItem<String>(
                  value: d,
                  height: 38,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  child: Row(
                    children: [
                      Icon(
                        _platformIcon(d),
                        size: 15,
                        color:
                            isSelected ? accentColor : const Color(0xFF999999),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              d,
                              style: TextStyle(
                                fontSize: 13,
                                color: isSelected
                                    ? const Color(0xFFFFFFFF)
                                    : const Color(0xFFCCCCCC),
                                fontWeight: isSelected
                                    ? FontWeight.w600
                                    : FontWeight.w400,
                              ),
                            ),
                            Text(
                              sizeText,
                              style: const TextStyle(
                                  fontSize: 10, color: Color(0xFF8E94A3)),
                            ),
                          ],
                        ),
                      ),
                      if (isSelected)
                        Icon(Icons.check_rounded, size: 15, color: accentColor),
                    ],
                  ),
                ),
              );
            }
          }
          return items;
        },
        child: Container(
          height: 28,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF31343A) : const Color(0xFF252830),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
                color: _hovered
                    ? const Color(0xFF4A5362)
                    : const Color(0xFF3A3F48)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(_platformIcon(widget.device), size: 14, color: accentColor),
              const SizedBox(width: 7),
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 120),
                child: Text(
                  widget.device,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFFDDDDDD),
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const SizedBox(width: 5),
              const Icon(Icons.expand_more_rounded,
                  size: 14, color: Color(0xFF8E94A3)),
            ],
          ),
        ),
      ),
    );
  }
}

/// Xcode orientation toggle button
class _XcodeOrientationButton extends StatefulWidget {
  const _XcodeOrientationButton({required this.landscape, required this.onTap});
  final bool landscape;
  final VoidCallback onTap;
  @override
  State<_XcodeOrientationButton> createState() =>
      _XcodeOrientationButtonState();
}

class _XcodeOrientationButtonState extends State<_XcodeOrientationButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: widget.landscape ? "Switch to Portrait" : "Switch to Landscape",
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          child: Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: widget.landscape
                  ? const Color(0x330A84FF)
                  : (_hovered
                      ? const Color(0xFF31343A)
                      : const Color(0xFF252830)),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: widget.landscape
                    ? const Color(0xFF0A84FF)
                    : const Color(0xFF3A3F48),
              ),
            ),
            child: Icon(
              widget.landscape
                  ? Icons.stay_current_landscape_rounded
                  : Icons.stay_current_portrait_rounded,
              size: 15,
              color: widget.landscape
                  ? const Color(0xFF0A84FF)
                  : (_hovered
                      ? const Color(0xFFE2E6EF)
                      : const Color(0xFF8E94A3)),
            ),
          ),
        ),
      ),
    );
  }
}

/// Xcode-style zoom control 閿?"-  100%  +" with dropdown for custom
class _XcodeZoomControl extends StatefulWidget {
  const _XcodeZoomControl({
    required this.zoom,
    required this.onZoomIn,
    required this.onZoomOut,
    required this.onZoomReset,
    this.onZoomSet,
    required this.size,
  });
  final double zoom;
  final VoidCallback onZoomIn;
  final VoidCallback onZoomOut;
  final VoidCallback onZoomReset;
  final ValueChanged<double>? onZoomSet;
  final Size size;
  @override
  State<_XcodeZoomControl> createState() => _XcodeZoomControlState();
}

class _XcodeZoomControlState extends State<_XcodeZoomControl> {
  bool _hoverMinus = false;
  bool _hoverPlus = false;
  bool _hoverPct = false;

  @override
  Widget build(BuildContext context) {
    final pct = "${(widget.zoom * 100).round()}%";
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Minus button
        _ZoomBtn(
          icon: Icons.remove_rounded,
          hovered: _hoverMinus,
          onEnter: () => setState(() => _hoverMinus = true),
          onExit: () => setState(() => _hoverMinus = false),
          onTap: widget.onZoomOut,
        ),
        // Percentage display
        PopupMenuButton<double>(
          onSelected: (v) {
            if (widget.onZoomSet != null) {
              widget.onZoomSet!(v);
              return;
            }
            if ((v - 1.0).abs() <= 0.001) {
              widget.onZoomReset();
            } else if (v > widget.zoom) {
              widget.onZoomIn();
            } else if (v < widget.zoom) {
              widget.onZoomOut();
            }
          },
          offset: const Offset(0, 30),
          color: const Color(0xFF252830),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
            side: const BorderSide(color: Color(0xFF3A3F48)),
          ),
          tooltip: "Zoom to fit",
          itemBuilder: (ctx) => [
            const PopupMenuItem(
                enabled: false,
                height: 28,
                child: Text("Zoom",
                    style: TextStyle(
                        fontSize: 11,
                        color: Color(0xFF777777),
                        fontWeight: FontWeight.w600))),
            const PopupMenuDivider(height: 4),
            ...{
              0.25: "25%",
              0.5: "50%",
              0.75: "75%",
              1.0: "100%",
              1.5: "150%",
              2.0: "200%"
            }.entries.map(
                  (e) => PopupMenuItem<double>(
                    value: e.key,
                    height: 32,
                    child: Text(e.value,
                        style: const TextStyle(
                            fontSize: 13, color: Color(0xFFCCCCCC))),
                  ),
                ),
          ],
          child: MouseRegion(
            cursor: SystemMouseCursors.click,
            onEnter: (_) => setState(() => _hoverPct = true),
            onExit: (_) => setState(() => _hoverPct = false),
            child: GestureDetector(
              onTap: widget.onZoomReset,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color:
                      _hoverPct ? const Color(0xFF31343A) : Colors.transparent,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  pct,
                  style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFFBBBBBB),
                    fontWeight: FontWeight.w500,
                    fontFeatures: [FontFeature.tabularFigures()],
                  ),
                ),
              ),
            ),
          ),
        ),
        // Plus button
        _ZoomBtn(
          icon: Icons.add_rounded,
          hovered: _hoverPlus,
          onEnter: () => setState(() => _hoverPlus = true),
          onExit: () => setState(() => _hoverPlus = false),
          onTap: widget.onZoomIn,
        ),
      ],
    );
  }
}

class _ZoomBtn extends StatelessWidget {
  const _ZoomBtn({
    required this.icon,
    required this.hovered,
    required this.onEnter,
    required this.onExit,
    required this.onTap,
  });
  final IconData icon;
  final bool hovered;
  final VoidCallback onEnter;
  final VoidCallback onExit;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => onEnter(),
      onExit: (_) => onExit(),
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          width: 22,
          height: 22,
          decoration: BoxDecoration(
            color: hovered ? const Color(0xFF31343A) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Icon(icon,
              size: 13,
              color:
                  hovered ? const Color(0xFFE2E6EF) : const Color(0xFF8E94A3)),
        ),
      ),
    );
  }
}

/// Xcode-style run/stop button (green triangle = run, red square = stop)
class _XcodeRunBtn extends StatefulWidget {
  const _XcodeRunBtn({required this.running, required this.onTap});
  final bool running;
  final VoidCallback onTap;
  @override
  State<_XcodeRunBtn> createState() => _XcodeRunBtnState();
}

class _XcodeRunBtnState extends State<_XcodeRunBtn> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final isRun = !widget.running;
    return Tooltip(
      message: isRun ? "Run Preview" : "Stop",
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          child: Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: isRun
                  ? (_hovered
                      ? const Color(0xFF0B8CF9)
                      : const Color(0xFF0A84FF))
                  : (_hovered
                      ? const Color(0xFFCC3333)
                      : const Color(0xFFAA2222)),
              borderRadius: BorderRadius.circular(7),
              border: Border.all(color: const Color(0x44FFFFFF)),
            ),
            child: Icon(
              isRun ? Icons.play_arrow_rounded : Icons.stop_rounded,
              size: 17,
              color: Colors.white,
            ),
          ),
        ),
      ),
    );
  }
}

// 閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查敓?
// Legacy Xcode-style UI Components (keep for compatibility)
// 閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查埡鎰ㄦ櫜閳烘劏鏅查敓?

class _XcodeDeviceSelector extends StatefulWidget {
  const _XcodeDeviceSelector({
    required this.device,
    required this.platform,
    required this.devices,
    required this.onChanged,
  });

  final String device;
  final String platform;
  final List<String> devices;
  final ValueChanged<String> onChanged;

  @override
  State<_XcodeDeviceSelector> createState() => _XcodeDeviceSelectorState();
}

class _XcodeDeviceSelectorState extends State<_XcodeDeviceSelector> {
  bool _hovering = false;

  IconData _platformIcon(String platform) {
    switch (platform) {
      case "ios":
        return Icons.phone_iphone_rounded;
      case "android":
        return Icons.phone_android_rounded;
      default:
        return Icons.desktop_mac_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovering = true),
      onExit: (_) => setState(() => _hovering = false),
      child: PopupMenuButton<String>(
        onSelected: widget.onChanged,
        offset: const Offset(0, 36),
        color: const Color(0xFF2A2A2A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: Color(0xFF3A3A3A)),
        ),
        itemBuilder: (context) {
          final groups = <String, List<String>>{};
          for (final d in widget.devices) {
            final group = d.startsWith("iPhone") || d.startsWith("iPad")
                ? "Apple"
                : d.startsWith("Pixel") || d.startsWith("Samsung")
                    ? "Android"
                    : d.startsWith("Desktop")
                        ? "Desktop"
                        : "Other";
            groups.putIfAbsent(group, () => []).add(d);
          }
          final items = <PopupMenuEntry<String>>[];
          for (final entry in groups.entries) {
            items.add(PopupMenuItem<String>(
              enabled: false,
              height: 28,
              child: Text(
                entry.key,
                style: const TextStyle(
                    fontSize: 10,
                    color: Color(0xFF888888),
                    fontWeight: FontWeight.w600),
              ),
            ));
            for (final d in entry.value) {
              items.add(PopupMenuItem<String>(
                value: d,
                height: 32,
                child: Row(
                  children: [
                    Icon(
                        _platformIcon(d.startsWith("iPhone") ||
                                d.startsWith("iPad")
                            ? "ios"
                            : d.startsWith("Pixel") || d.startsWith("Samsung")
                                ? "android"
                                : "desktop"),
                        size: 14,
                        color: const Color(0xFFAAAAAA)),
                    const SizedBox(width: 10),
                    Text(d,
                        style: TextStyle(
                          fontSize: 12,
                          color: d == widget.device
                              ? const Color(0xFF0A84FF)
                              : const Color(0xFFD1D5DB),
                          fontWeight: d == widget.device
                              ? FontWeight.w600
                              : FontWeight.w400,
                        )),
                    if (d == widget.device) ...[
                      const Spacer(),
                      const Icon(Icons.check_rounded,
                          size: 14, color: Color(0xFF0A84FF)),
                    ],
                  ],
                ),
              ));
            }
          }
          return items;
        },
        child: Container(
          height: 28,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color:
                _hovering ? const Color(0xFF3A3A3A) : const Color(0xFF1E1E1E),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: const Color(0xFF3A3A3A)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(_platformIcon(widget.platform),
                  size: 14, color: const Color(0xFF0A84FF)),
              const SizedBox(width: 8),
              Text(
                widget.device,
                style: const TextStyle(
                    fontSize: 11,
                    color: Color(0xFFD1D5DB),
                    fontWeight: FontWeight.w500),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.unfold_more_rounded,
                  size: 14, color: Color(0xFF888888)),
            ],
          ),
        ),
      ),
    );
  }
}

// Xcode-style device frame with realistic bezels
class _XcodeDeviceFrame extends StatelessWidget {
  const _XcodeDeviceFrame({
    super.key,
    required this.width,
    required this.height,
    required this.platform,
    required this.deviceName,
    required this.landscape,
    required this.child,
  });

  final double width;
  final double height;
  final String platform;
  final String deviceName;
  final bool landscape;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final isIphone = platform == "ios" && !deviceName.contains("iPad");
    final isIpad = deviceName.contains("iPad");
    final isAndroid = platform == "android";
    final isDesktop = platform == "desktop";

    // Calculate bezel size based on device type
    final bezelWidth = isDesktop ? 4.0 : (isIpad ? 16.0 : 12.0);
    final cornerRadius = isDesktop ? 8.0 : (isIpad ? 24.0 : 40.0);
    final notchHeight = isIphone ? 34.0 : 0.0;

    return Container(
      width: width + bezelWidth * 2,
      height: height + bezelWidth * 2 + (isIphone ? 8 : 0),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A1A),
        borderRadius: BorderRadius.circular(cornerRadius + 4),
        border: Border.all(color: const Color(0xFF2A2A2A), width: 2),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(cornerRadius),
        child: Container(
          margin: EdgeInsets.all(bezelWidth),
          child: Stack(
            children: [
              // Main content
              ClipRRect(
                borderRadius: BorderRadius.circular(cornerRadius - bezelWidth),
                child: child,
              ),
              // iPhone notch
              if (isIphone && !landscape)
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: Container(
                      width: width * 0.35,
                      height: notchHeight,
                      decoration: const BoxDecoration(
                        color: Color(0xFF1A1A1A),
                        borderRadius: BorderRadius.only(
                          bottomLeft: Radius.circular(20),
                          bottomRight: Radius.circular(20),
                        ),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            margin: const EdgeInsets.only(right: 8),
                            decoration: BoxDecoration(
                              color: const Color(0xFF2A2A2A),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                          Container(
                            width: 50,
                            height: 6,
                            decoration: BoxDecoration(
                              color: const Color(0xFF2A2A2A),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              // Home indicator for iPhone
              if (isIphone && !landscape)
                Positioned(
                  bottom: 6,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: Container(
                      width: width * 0.35,
                      height: 5,
                      decoration: BoxDecoration(
                        color: const Color(0xFF4A4A4A),
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                  ),
                ),
              // Android status bar
              if (isAndroid && !landscape)
                Positioned(
                  top: 0,
                  left: 0,
                  right: 0,
                  child: Container(
                    height: 24,
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.black.withValues(alpha: 0.3),
                          Colors.transparent
                        ],
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text("12:00",
                            style:
                                TextStyle(fontSize: 10, color: Colors.white70)),
                        Row(
                          children: [
                            const Icon(Icons.signal_cellular_4_bar,
                                size: 10, color: Colors.white70),
                            const SizedBox(width: 4),
                            const Icon(Icons.wifi,
                                size: 10, color: Colors.white70),
                            const SizedBox(width: 4),
                            Container(
                              width: 18,
                              height: 9,
                              decoration: BoxDecoration(
                                border:
                                    Border.all(color: Colors.white70, width: 1),
                                borderRadius: BorderRadius.circular(2),
                              ),
                              child: Align(
                                alignment: Alignment.centerLeft,
                                child: Container(
                                  width: 12,
                                  margin: const EdgeInsets.all(1),
                                  decoration: BoxDecoration(
                                    color: Colors.white70,
                                    borderRadius: BorderRadius.circular(1),
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _XcodeEmptyPreview extends StatelessWidget {
  const _XcodeEmptyPreview({required this.deviceName});
  final String deviceName;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: const Color(0xFFF3F4F6),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: const Color(0xFFE5E7EB)),
          ),
          child: const Icon(Icons.play_circle_outline_rounded,
              size: 28, color: Color(0xFF9CA3AF)),
        ),
        const SizedBox(height: 16),
        Text(
          deviceName,
          style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF6B7280),
              fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 4),
        const Text(
          "Press Run to start preview",
          style: TextStyle(fontSize: 11, color: Color(0xFF9CA3AF)),
        ),
      ],
    );
  }
}

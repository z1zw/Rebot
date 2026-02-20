import "dart:async";
import "dart:collection";
import "package:flutter/widgets.dart";

class PerformanceMonitor {
  PerformanceMonitor._();
  static final instance = PerformanceMonitor._();

  final _errors = Queue<ErrorRecord>();
  final _metrics = <String, List<int>>{};
  final _navTimings = <String, int>{};
  static const _maxErrors = 200;
  static const _maxMetricSamples = 100;

  DateTime? _sessionStart;
  DateTime get sessionStart => _sessionStart ??= DateTime.now();

  void init() {
    _sessionStart = DateTime.now();
  }

  void recordError(Object error, StackTrace? stackTrace, {String context = ""}) {
    _errors.addLast(ErrorRecord(
      error: error.toString(),
      stackTrace: stackTrace?.toString().split("\n").take(10).join("\n") ?? "",
      context: context,
      timestamp: DateTime.now(),
    ));
    while (_errors.length > _maxErrors) {
      _errors.removeFirst();
    }
  }

  void recordMetric(String name, int valueMs) {
    _metrics.putIfAbsent(name, () => []);
    final samples = _metrics[name]!;
    samples.add(valueMs);
    while (samples.length > _maxMetricSamples) {
      samples.removeAt(0);
    }
  }

  void startNavTiming(String routeName) {
    _navTimings[routeName] = DateTime.now().millisecondsSinceEpoch;
  }

  void endNavTiming(String routeName) {
    final start = _navTimings.remove(routeName);
    if (start != null) {
      recordMetric("nav_$routeName", DateTime.now().millisecondsSinceEpoch - start);
    }
  }

  Stopwatch trackApiCall(String endpoint) {
    final sw = Stopwatch()..start();
    return sw;
  }

  void endApiCall(String endpoint, Stopwatch sw, {bool success = true}) {
    sw.stop();
    recordMetric(
      success ? "api_${endpoint}_ok" : "api_${endpoint}_err",
      sw.elapsedMilliseconds,
    );
  }

  Map<String, dynamic> getReport() {
    final avgMetrics = <String, double>{};
    for (final entry in _metrics.entries) {
      if (entry.value.isEmpty) continue;
      avgMetrics[entry.key] =
          entry.value.reduce((a, b) => a + b) / entry.value.length;
    }
    return {
      "session_start": sessionStart.toIso8601String(),
      "uptime_seconds": DateTime.now().difference(sessionStart).inSeconds,
      "error_count": _errors.length,
      "recent_errors": _errors.toList().reversed.take(5).map((e) => e.toMap()).toList(),
      "avg_metrics_ms": avgMetrics,
    };
  }

  List<ErrorRecord> get recentErrors => _errors.toList().reversed.take(20).toList();
  int get errorCount => _errors.length;

  void clear() {
    _errors.clear();
    _metrics.clear();
  }
}

class ErrorRecord {
  final String error;
  final String stackTrace;
  final String context;
  final DateTime timestamp;

  ErrorRecord({
    required this.error,
    required this.stackTrace,
    required this.context,
    required this.timestamp,
  });

  Map<String, dynamic> toMap() => {
        "error": error,
        "context": context,
        "timestamp": timestamp.toIso8601String(),
        "stack_preview": stackTrace.length > 200
            ? "${stackTrace.substring(0, 200)}..."
            : stackTrace,
      };
}

class PerformanceOverlay extends StatelessWidget {
  const PerformanceOverlay({super.key, required this.child, this.enabled = false});

  final Widget child;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    if (!enabled) return child;
    return Stack(
      children: [
        child,
        Positioned(
          right: 8,
          bottom: 8,
          child: _PerfBadge(),
        ),
      ],
    );
  }
}

class _PerfBadge extends StatefulWidget {
  @override
  State<_PerfBadge> createState() => _PerfBadgeState();
}

class _PerfBadgeState extends State<_PerfBadge> {
  Timer? _timer;
  Map<String, dynamic> _report = {};

  @override
  void initState() {
    super.initState();
    _timer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (mounted) {
        setState(() => _report = PerformanceMonitor.instance.getReport());
      }
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final errCount = _report["error_count"] ?? 0;
    final uptime = _report["uptime_seconds"] ?? 0;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xDD212121),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF2A2A2A)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: errCount > 0 ? const Color(0xFFEF4444) : const Color(0xFF10A37F),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            "Err: $errCount | Up: ${uptime}s",
            style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 10, color: Color(0xFF8E8E8E)),
          ),
        ],
      ),
    );
  }
}

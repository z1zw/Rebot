import "package:flutter_test/flutter_test.dart";
import "package:rebot_agentgpt/core/performance_monitor.dart";

void main() {
  late PerformanceMonitor monitor;

  setUp(() {
    monitor = PerformanceMonitor.instance;
    monitor.clear();
    monitor.init();
  });

  group("PerformanceMonitor", () {
    test("init sets session start", () {
      expect(monitor.sessionStart, isNotNull);
      expect(monitor.sessionStart.isBefore(DateTime.now().add(const Duration(seconds: 1))), true);
    });

    test("recordError adds to recent errors", () {
      expect(monitor.errorCount, 0);
      monitor.recordError(Exception("test error"), StackTrace.current, context: "unit_test");
      expect(monitor.errorCount, 1);
      expect(monitor.recentErrors.first.error, contains("test error"));
      expect(monitor.recentErrors.first.context, "unit_test");
    });

    test("recordError respects max limit", () {
      for (int i = 0; i < 250; i++) {
        monitor.recordError("error_$i", null);
      }
      expect(monitor.errorCount, 200);
    });

    test("recordMetric stores values", () {
      monitor.recordMetric("test_metric", 100);
      monitor.recordMetric("test_metric", 200);
      final report = monitor.getReport();
      final avgMetrics = report["avg_metrics_ms"] as Map<String, double>;
      expect(avgMetrics["test_metric"], 150.0);
    });

    test("getReport returns structured data", () {
      monitor.recordError("test", null);
      monitor.recordMetric("api_call", 50);
      final report = monitor.getReport();
      expect(report["session_start"], isA<String>());
      expect(report["uptime_seconds"], isA<int>());
      expect(report["error_count"], 1);
      expect(report["recent_errors"], isA<List>());
      expect(report["avg_metrics_ms"], isA<Map>());
    });

    test("clear resets everything", () {
      monitor.recordError("test", null);
      monitor.recordMetric("m", 100);
      monitor.clear();
      expect(monitor.errorCount, 0);
      expect(monitor.getReport()["avg_metrics_ms"], isEmpty);
    });

    test("trackApiCall creates stopwatch", () {
      final sw = monitor.trackApiCall("test_endpoint");
      expect(sw.isRunning, true);
      monitor.endApiCall("test_endpoint", sw);
      expect(sw.isRunning, false);
    });
  });

  group("ErrorRecord", () {
    test("toMap serializes correctly", () {
      final record = ErrorRecord(
        error: "RuntimeError",
        stackTrace: "line 1\nline 2",
        context: "test",
        timestamp: DateTime(2026, 1, 1),
      );
      final map = record.toMap();
      expect(map["error"], "RuntimeError");
      expect(map["context"], "test");
      expect(map["timestamp"], contains("2026"));
    });
  });
}

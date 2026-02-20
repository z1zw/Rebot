import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:rebot_agentgpt/core/error_boundary.dart";
import "package:rebot_agentgpt/core/performance_monitor.dart";

void main() {
  setUp(() {
    PerformanceMonitor.instance.init();
    PerformanceMonitor.instance.clear();
  });

  group("ErrorBoundary", () {
    testWidgets("renders child when no error", (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: ErrorBoundary(
          child: Scaffold(body: Text("Hello World")),
        ),
      ));
      expect(find.text("Hello World"), findsOneWidget);
    });

    testWidgets("shows fallback UI structure", (tester) async {
      await tester.pumpWidget(const MaterialApp(
        home: ErrorBoundary(
          child: Scaffold(body: Text("Content")),
        ),
      ));
      expect(find.text("Content"), findsOneWidget);
      expect(find.text("Something went wrong"), findsNothing);
    });
  });
}

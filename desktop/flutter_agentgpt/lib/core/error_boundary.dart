import "package:flutter/material.dart";
import "performance_monitor.dart";

/// Call this once in main() before runApp() to set up global error handling.
/// This avoids conflicts with Flutter test framework.
void setupGlobalErrorHandling() {
  final originalHandler = FlutterError.onError;
  FlutterError.onError = (FlutterErrorDetails details) {
    PerformanceMonitor.instance.recordError(
      details.exception,
      details.stack,
      context: details.context?.toDescription() ?? "flutter_error",
    );
    originalHandler?.call(details);
  };
}

/// A simple error boundary widget. Does not override FlutterError.onError
/// (that should be done once in main.dart via setupGlobalErrorHandling).
class ErrorBoundary extends StatelessWidget {
  const ErrorBoundary({super.key, required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return child;
  }
}

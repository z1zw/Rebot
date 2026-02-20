import "package:flutter/material.dart";
import "package:flutter/foundation.dart";
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

class _ErrorFallback extends StatelessWidget {
  const _ErrorFallback({
    required this.error,
    required this.onRetry,
  });

  final Object error;
  final StackTrace? stackTrace;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: const Color(0xFF1E1E1E),
      child: Center(
        child: Container(
          width: 420,
          padding: const EdgeInsets.all(28),
          decoration: BoxDecoration(
            color: const Color(0xFF212121),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFF2A2A2A)),
            boxShadow: const [
              BoxShadow(color: Color(0x60000000), blurRadius: 32, offset: Offset(0, 12)),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: const Color(0xFFEF4444).withOpacity(0.12),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(Icons.error_outline, size: 28, color: Color(0xFFEF4444)),
              ),
              const SizedBox(height: 18),
              const Text(
                "Something went wrong",
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: Color(0xFFFFFFFF),
                ),
              ),
              const SizedBox(height: 8),
              Text(
                error.toString().length > 200
                    ? "${error.toString().substring(0, 200)}..."
                    : error.toString(),
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 12, color: Color(0xFF8E8E8E), height: 1.5),
              ),
              const SizedBox(height: 24),
              MouseRegion(
                cursor: SystemMouseCursors.click,
                child: GestureDetector(
                  onTap: onRetry,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF10A37F),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Text(
                      "Try Again",
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
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

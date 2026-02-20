import "package:flutter/material.dart";

class DevServerState extends ChangeNotifier {
  bool _running = false;
  String _framework = "general";
  int _port = 0;
  String _lastError = "";
  final List<String> _logs = <String>[];

  bool get running => _running;
  String get framework => _framework;
  int get port => _port;
  String get lastError => _lastError;
  List<String> get logs => List.unmodifiable(_logs);

  void updateStatus({
    required bool running,
    String? framework,
    int? port,
    String? error,
  }) {
    _running = running;
    if (framework != null && framework.trim().isNotEmpty) {
      _framework = framework.trim();
    }
    if (port != null) {
      _port = port;
    }
    if (error != null) {
      _lastError = error.trim();
    }
    notifyListeners();
  }

  void pushLog(String line) {
    final text = line.trimRight();
    if (text.isEmpty) return;
    _logs.add(text);
    if (_logs.length > 1000) {
      _logs.removeRange(0, _logs.length - 1000);
    }
    notifyListeners();
  }

  void clearLogs() {
    _logs.clear();
    notifyListeners();
  }
}

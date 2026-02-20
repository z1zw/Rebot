import "package:flutter/material.dart";

class PreviewState extends ChangeNotifier {
  String _url = "";
  bool _running = false;
  bool _healthy = false;
  String _healthReason = "idle";
  int _reloadSignal = 0;

  String get url => _url;
  bool get running => _running;
  bool get healthy => _healthy;
  String get healthReason => _healthReason;
  int get reloadSignal => _reloadSignal;

  void setUrl(String value) {
    final next = value.trim();
    if (_url == next) return;
    _url = next;
    notifyListeners();
  }

  void setRunning(bool value) {
    if (_running == value) return;
    _running = value;
    notifyListeners();
  }

  void setHealth({required bool healthy, String reason = "ok"}) {
    final nextReason = reason.trim().isEmpty ? "unknown" : reason.trim();
    if (_healthy == healthy && _healthReason == nextReason) return;
    _healthy = healthy;
    _healthReason = nextReason;
    notifyListeners();
  }

  void triggerReload() {
    _reloadSignal += 1;
    notifyListeners();
  }
}

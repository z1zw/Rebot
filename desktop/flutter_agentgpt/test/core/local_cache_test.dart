import "package:flutter_test/flutter_test.dart";
import "package:rebot_agentgpt/core/local_cache.dart";

void main() {
  group("ConnectivityMonitor", () {
    late ConnectivityMonitor monitor;

    setUp(() {
      monitor = ConnectivityMonitor.instance;
      monitor.updateStatus(true);
    });

    test("initial state is online", () {
      expect(monitor.isOnline, true);
    });

    test("updateStatus changes state", () {
      monitor.updateStatus(false);
      expect(monitor.isOnline, false);
      monitor.updateStatus(true);
      expect(monitor.isOnline, true);
    });

    test("listeners are notified on change", () {
      bool? received;
      void listener(bool online) => received = online;
      monitor.addListener(listener);
      monitor.updateStatus(false);
      expect(received, false);
      monitor.updateStatus(true);
      expect(received, true);
      monitor.removeListener(listener);
    });

    test("no notification when status unchanged", () {
      int callCount = 0;
      void listener(bool online) => callCount++;
      monitor.addListener(listener);
      monitor.updateStatus(true);
      expect(callCount, 0);
      monitor.removeListener(listener);
    });

    test("lastSyncedText returns readable string", () {
      monitor.updateStatus(false);
      monitor.updateStatus(true);
      expect(monitor.lastSyncedText, isNotEmpty);
    });
  });
}

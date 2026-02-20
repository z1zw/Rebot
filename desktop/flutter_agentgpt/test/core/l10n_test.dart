import "package:flutter_test/flutter_test.dart";
import "package:rebot_agentgpt/core/l10n.dart";

void main() {
  group("S (Localization)", () {
    test("static strings are not empty", () {
      expect(S.appName.isNotEmpty, true);
      expect(S.explorer.isNotEmpty, true);
      expect(S.settings.isNotEmpty, true);
      expect(S.cancel.isNotEmpty, true);
      expect(S.create.isNotEmpty, true);
      expect(S.save.isNotEmpty, true);
      expect(S.refresh.isNotEmpty, true);
      expect(S.retry.isNotEmpty, true);
      expect(S.running.isNotEmpty, true);
      expect(S.idle.isNotEmpty, true);
      expect(S.somethingWentWrong.isNotEmpty, true);
      expect(S.networkError.isNotEmpty, true);
      expect(S.send.isNotEmpty, true);
      expect(S.typeMessage.isNotEmpty, true);
    });

    test("parameterized strings work correctly", () {
      expect(S.nOf(3, 10), "3/10");
      expect(S.nActive(5, 8), "5/8 active");
      expect(S.nFiles(1), "1 file");
      expect(S.nFiles(3), "3 files");
      expect(S.nLines(42), "42 lines");
      expect(S.nItems(7), "7");
    });

    test("all view labels accessible", () {
      expect(S.explorer, "EXPLORER");
      expect(S.skills, "SKILL REGISTRY");
      expect(S.history, "HISTORY");
      expect(S.agents, "AGENTS");
      expect(S.console, "Console");
      expect(S.terminal, "Terminal");
      expect(S.devServer, "DEV SERVER");
    });

    test("action labels accessible", () {
      expect(S.createFile, "Create File");
      expect(S.createFolder, "Create Folder");
      expect(S.copyPath, "Copy Path");
      expect(S.screenshot, "Screenshot");
      expect(S.disconnect, "Disconnect");
    });

    test("status labels accessible", () {
      expect(S.active, "Active");
      expect(S.inactive, "Inactive");
      expect(S.online, "Online");
      expect(S.offline, "Offline");
      expect(S.connecting, "Connecting...");
    });
  });
}

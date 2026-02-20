import "package:flutter/material.dart";

import "console_panel.dart";
import "device_simulator.dart";

class PreviewPanel extends StatelessWidget {
  const PreviewPanel({
    super.key,
    this.title = "Preview",
    this.url = "",
    this.logs = const <String>[],
    this.showConsole = false,
  });

  final String title;
  final String url;
  final List<String> logs;
  final bool showConsole;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(color: Color(0xFF17181C)),
      child: Column(
        children: [
          Container(
            height: 40,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: const BoxDecoration(
              color: Color(0xFF202329),
              border: Border(bottom: BorderSide(color: Color(0xFF343A46))),
            ),
            child: Row(
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Color(0xFFDCE4F2),
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const Spacer(),
                if (url.trim().isNotEmpty)
                  Text(
                    url,
                    style: const TextStyle(color: Color(0xFF8FA0BB), fontSize: 11),
                  ),
              ],
            ),
          ),
          Expanded(
            child: showConsole
                ? ConsolePanel(logs: logs)
                : DeviceSimulator(label: url.trim().isEmpty ? "Run preview" : url),
          ),
        ],
      ),
    );
  }
}

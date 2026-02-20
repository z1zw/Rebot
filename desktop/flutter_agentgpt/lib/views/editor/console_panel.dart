import "package:flutter/material.dart";

class ConsolePanel extends StatelessWidget {
  const ConsolePanel({
    super.key,
    this.logs = const <String>[],
  });

  final List<String> logs;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF141821),
      child: logs.isEmpty
          ? const Center(
              child: Text(
                "No terminal output yet.",
                style: TextStyle(
                  color: Color(0xFF7A859A),
                  fontSize: 12,
                  fontFamily: "JetBrains Mono",
                ),
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(10),
              itemCount: logs.length,
              itemBuilder: (context, index) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: SelectableText(
                  logs[index],
                  style: const TextStyle(
                    fontFamily: "JetBrains Mono",
                    fontSize: 11,
                    color: Color(0xFFC9D3E5),
                    height: 1.4,
                  ),
                ),
              ),
            ),
    );
  }
}

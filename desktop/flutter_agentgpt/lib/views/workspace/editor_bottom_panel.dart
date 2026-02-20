import "package:flutter/material.dart";
import "package:rebot_agentgpt/app_state.dart";

class EditorBottomPanel extends StatelessWidget {
  static const Color _xSurface = Color(0xFF1D1E22);
  static const Color _xPanel = Color(0xFF252830);
  static const Color _xPanel2 = Color(0xFF2A2D34);
  static const Color _xStroke = Color(0xFF343944);
  static const Color _xBlue = Color(0xFF0A84FF);

  const EditorBottomPanel({
    super.key,
    required this.open,
    required this.tab,
    required this.onTabChange,
    required this.onToggleOpen,
    required this.terminalLogs,
    required this.warningCount,
    required this.executionProgress,
  });

  final bool open;
  final String tab;
  final ValueChanged<String> onTabChange;
  final VoidCallback onToggleOpen;
  final List<ConsoleLog> terminalLogs;
  final int warningCount;
  final String executionProgress;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: open ? 180 : 32,
      decoration: const BoxDecoration(
        color: _xSurface,
        border: Border(top: BorderSide(color: _xStroke)),
      ),
      child: Column(
        children: [
          Container(
            height: 32,
            padding: const EdgeInsets.symmetric(horizontal: 8),
            decoration: const BoxDecoration(
              color: _xPanel2,
              border: Border(bottom: BorderSide(color: _xStroke)),
            ),
            child: Row(
              children: [
                _TabChip(label: "Terminal", active: tab == "terminal" && open, count: terminalLogs.length, onTap: () => onTabChange("terminal")),
                _TabChip(label: "Problems", active: tab == "problems" && open, count: warningCount, onTap: () => onTabChange("problems")),
                _TabChip(label: "Output", active: tab == "output" && open, onTap: () => onTabChange("output")),
                const Spacer(),
                InkWell(
                  onTap: onToggleOpen,
                  borderRadius: BorderRadius.circular(6),
                  child: Padding(
                    padding: const EdgeInsets.all(4),
                    child: Icon(open ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_up, size: 16, color: const Color(0xFFA0A8B8)),
                  ),
                ),
              ],
            ),
          ),
          if (open)
            Expanded(
              child: _BottomContent(
                tab: tab,
                terminalLogs: terminalLogs,
                warningCount: warningCount,
                executionProgress: executionProgress,
              ),
            ),
        ],
      ),
    );
  }
}

class _BottomContent extends StatelessWidget {
  const _BottomContent({
    required this.tab,
    required this.terminalLogs,
    required this.warningCount,
    required this.executionProgress,
  });

  final String tab;
  final List<ConsoleLog> terminalLogs;
  final int warningCount;
  final String executionProgress;

  @override
  Widget build(BuildContext context) {
      if (tab == "terminal") {
        if (terminalLogs.isEmpty) {
          return const Center(
            child: Text("No terminal output yet.", style: TextStyle(fontSize: 12, color: Color(0xFF7A8294), fontFamily: "JetBrains Mono")),
          );
        }
        return ListView.builder(
        padding: const EdgeInsets.all(10),
        itemCount: terminalLogs.length,
        itemBuilder: (_, i) {
          final log = terminalLogs[i];
          return Padding(
            padding: const EdgeInsets.only(bottom: 1),
            child: Text(
              log.text,
              style: TextStyle(fontFamily: "JetBrains Mono", fontSize: 12, height: 1.5, color: _color(log.level)),
            ),
          );
        },
      );
    }
    if (tab == "problems") {
      return Center(
        child: Text(
          warningCount > 0 ? "$warningCount warning(s) / error(s)" : "No problems detected.",
          style: const TextStyle(fontSize: 12, color: Color(0xFFA0A8B8), fontFamily: "JetBrains Mono"),
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.all(10),
      child: SelectableText(
        executionProgress.isEmpty ? "No output." : executionProgress,
        style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 12, height: 1.5, color: Color(0xFFCDD5E4)),
      ),
    );
  }

  Color _color(String level) {
    switch (level) {
      case "error":
        return const Color(0xFFFF7B72);
      case "warning":
        return const Color(0xFFFFC857);
      case "success":
        return const Color(0xFF34C759);
      case "info":
        return const Color(0xFF64D2FF);
      default:
        return const Color(0xFFCDD5E4);
    }
  }
}

class _TabChip extends StatelessWidget {
  const _TabChip({
    required this.label,
    required this.active,
    required this.onTap,
    this.count,
  });

  final String label;
  final bool active;
  final int? count;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
        decoration: BoxDecoration(
          color: active ? EditorBottomPanel._xPanel : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: active ? EditorBottomPanel._xStroke : Colors.transparent),
        ),
        child: Row(
          children: [
            Text(label, style: TextStyle(fontSize: 12, color: active ? const Color(0xFFE6E8EE) : const Color(0xFFA0A8B8), fontWeight: active ? FontWeight.w600 : FontWeight.w500)),
            if (count != null) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                decoration: BoxDecoration(
                  color: active ? EditorBottomPanel._xBlue : const Color(0xFF3A3F48),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text("$count", style: const TextStyle(fontSize: 10, color: Colors.white, fontWeight: FontWeight.w600)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

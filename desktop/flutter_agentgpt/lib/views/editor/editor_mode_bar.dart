import "package:flutter/material.dart";
import "package:rebot_agentgpt/views/editor/code_editor.dart";

class EditorModeBar extends StatelessWidget {
  const EditorModeBar({
    super.key,
    required this.useMonaco,
    required this.showAiDiff,
    required this.onMonacoChanged,
    required this.onShowCode,
    required this.onShowDiff,
  });

  final bool useMonaco;
  final bool showAiDiff;
  final ValueChanged<bool> onMonacoChanged;
  final VoidCallback onShowCode;
  final VoidCallback onShowDiff;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 36,
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: const BoxDecoration(
        color: Color(0xFF2B2D30),
        border: Border(bottom: BorderSide(color: Color(0xFF1E1F22))),
      ),
      child: Row(
        children: [
          EditorModeToggle(
            monacoEnabled: useMonaco,
            onChanged: onMonacoChanged,
          ),
          const SizedBox(width: 8),
          _DiffToggleChip(
            label: "Code",
            selected: !showAiDiff,
            onTap: onShowCode,
          ),
          const SizedBox(width: 6),
          _DiffToggleChip(
            label: "AI Diff",
            selected: showAiDiff,
            onTap: onShowDiff,
          ),
          const Spacer(),
          if (useMonaco && !showAiDiff)
            const Text(
              "Monaco Live",
              style: TextStyle(fontSize: 11, color: Color(0xFF8E8E8E)),
            ),
        ],
      ),
    );
  }
}

class _DiffToggleChip extends StatelessWidget {
  const _DiffToggleChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: selected ? const Color(0xFF10A37F).withValues(alpha: 0.16) : const Color(0xFF2B2D30),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: selected ? const Color(0xFF10A37F) : const Color(0xFF3C3F41),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: selected ? const Color(0xFF10A37F) : const Color(0xFF8E8E8E),
          ),
        ),
      ),
    );
  }
}


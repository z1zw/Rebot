import "package:flutter/material.dart";
import "package:rebot_agentgpt/theme/app_tokens.dart";

class EditorBreadcrumbs extends StatelessWidget {
  const EditorBreadcrumbs({
    super.key,
    required this.path,
    required this.onRootTap,
    required this.onSegmentTap,
  });

  final String path;
  final VoidCallback onRootTap;
  final ValueChanged<int> onSegmentTap;

  @override
  Widget build(BuildContext context) {
    final parts = path.trim().replaceAll("\\", "/").split("/").where((e) => e.isNotEmpty).toList();
    return Row(
      children: [
        InkWell(
          onTap: onRootTap,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.folder_outlined, size: 14, color: AppTokens.textTertiary),
              const SizedBox(width: 4),
              Text("Project", style: AppTokens.text(size: 12, color: AppTokens.textTertiary)),
            ],
          ),
        ),
        ...parts.asMap().entries.map((entry) {
          final idx = entry.key;
          final segment = entry.value;
          final isLast = idx == parts.length - 1;
          return Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.chevron_right, size: 14, color: AppTokens.textDisabled),
              InkWell(
                onTap: () => onSegmentTap(idx),
                child: Text(
                  segment,
                  style: AppTokens.text(
                    size: 12,
                    color: isLast ? AppTokens.textPrimary : AppTokens.textTertiary,
                    weight: isLast ? FontWeight.w600 : FontWeight.w500,
                  ),
                ),
              ),
            ],
          );
        }),
      ],
    );
  }
}

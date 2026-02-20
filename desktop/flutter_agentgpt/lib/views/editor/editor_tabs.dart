import "package:flutter/material.dart";
import "package:rebot_agentgpt/theme/app_tokens.dart";

class EditorTabs extends StatelessWidget {
  const EditorTabs({
    super.key,
    required this.tabs,
    required this.activePath,
    required this.isDirty,
    required this.onTap,
    required this.onClose,
  });

  final List<String> tabs;
  final String activePath;
  final bool isDirty;
  final ValueChanged<String> onTap;
  final ValueChanged<String> onClose;

  @override
  Widget build(BuildContext context) {
    if (tabs.isEmpty) {
      return const SizedBox.shrink();
    }
    return SizedBox(
      height: 36,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: tabs.length,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        separatorBuilder: (_, __) => const SizedBox(width: 4),
        itemBuilder: (_, i) {
          final path = tabs[i];
          final active = path == activePath;
          return _EditorTabChip(
            title: path.split("/").last,
            active: active,
            dirty: active && isDirty,
            onTap: () => onTap(path),
            onClose: () => onClose(path),
          );
        },
      ),
    );
  }
}

class _EditorTabChip extends StatelessWidget {
  const _EditorTabChip({
    required this.title,
    required this.active,
    required this.dirty,
    required this.onTap,
    required this.onClose,
  });

  final String title;
  final bool active;
  final bool dirty;
  final VoidCallback onTap;
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: active ? AppTokens.tabActiveBg : AppTokens.tabBg,
      borderRadius: BorderRadius.circular(AppTokens.radiusSm),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppTokens.radiusSm),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppTokens.radiusSm),
            border: Border.all(color: active ? AppTokens.tabBorder : AppTokens.borderSubtle),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                dirty ? "$title *" : title,
                style: AppTokens.text(
                  size: 12,
                  color: active ? AppTokens.textPrimary : AppTokens.textSecondary,
                  weight: active ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
              const SizedBox(width: 6),
              InkWell(
                onTap: onClose,
                child: const Icon(Icons.close, size: 14, color: AppTokens.textTertiary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

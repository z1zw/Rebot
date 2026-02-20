import "package:flutter/material.dart";

class WorkspaceNavRail extends StatelessWidget {
  const WorkspaceNavRail({
    super.key,
    required this.leftPanel,
    required this.activeView,
    required this.settingsOpen,
    required this.onChat,
    required this.onCode,
    required this.onSettings,
    required this.onViewChange,
  });

  final String leftPanel;
  final String activeView;
  final bool settingsOpen;
  final VoidCallback onChat;
  final VoidCallback onCode;
  final VoidCallback onSettings;
  final ValueChanged<String> onViewChange;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      decoration: const BoxDecoration(
        color: Color(0xFF1D1E22),
        border: Border(right: BorderSide(color: Color(0xFF343944))),
      ),
      child: Column(
        children: [
          const SizedBox(height: 8),
          _RailIcon(
            icon: Icons.chat_bubble_outline_rounded,
            label: "Assistant",
            active: leftPanel == "chat" && activeView == "workspace",
            onTap: onChat,
          ),
          _RailIcon(
            icon: Icons.code_rounded,
            label: "Explorer",
            active: leftPanel == "code" && activeView == "workspace",
            onTap: onCode,
          ),
          const SizedBox(height: 10),
          _RailIcon(
            icon: Icons.dashboard_outlined,
            label: "Workspace",
            active: activeView == "workspace",
            onTap: () => onViewChange("workspace"),
          ),
          _RailIcon(
            icon: Icons.dns_outlined,
            label: "Dev Server",
            active: activeView == "devserver",
            onTap: () => onViewChange("devserver"),
          ),
          _RailIcon(
            icon: Icons.history_rounded,
            label: "History",
            active: activeView == "history",
            onTap: () => onViewChange("history"),
          ),
          _RailIcon(
            icon: Icons.groups_outlined,
            label: "Agents",
            active: activeView == "agents",
            onTap: () => onViewChange("agents"),
          ),
          _RailIcon(
            icon: Icons.extension_rounded,
            label: "Plugins",
            active: activeView == "plugins",
            onTap: () => onViewChange("plugins"),
          ),
          _RailIcon(
            icon: Icons.storefront_outlined,
            label: "Templates",
            active: activeView == "templates",
            onTap: () => onViewChange("templates"),
          ),
          _RailIcon(
            icon: Icons.source_rounded,
            label: "Git",
            active: activeView == "git",
            onTap: () => onViewChange("git"),
          ),
          const Spacer(),
          _RailIcon(
            icon: Icons.settings_outlined,
            label: "Settings",
            active: settingsOpen,
            onTap: onSettings,
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }
}

class _RailIcon extends StatefulWidget {
  const _RailIcon({
    required this.icon,
    required this.label,
    required this.active,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  State<_RailIcon> createState() => _RailIconState();
}

class _RailIconState extends State<_RailIcon> {
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    final bg = widget.active
        ? const Color(0x220A84FF)
        : (_hover ? const Color(0xFF2C3037) : const Color(0xFF252830));
    final border = widget.active
        ? const Color(0x660A84FF)
        : (_hover ? const Color(0xFF4A5362) : const Color(0xFF3A3F48));
    final fg = widget.active ? const Color(0xFF0A84FF) : (_hover ? const Color(0xFFE2E6EF) : const Color(0xFFA5ACB9));

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Tooltip(
        message: widget.label,
        waitDuration: const Duration(milliseconds: 250),
        child: MouseRegion(
          onEnter: (_) => setState(() => _hover = true),
          onExit: (_) => setState(() => _hover = false),
          cursor: SystemMouseCursors.click,
          child: GestureDetector(
            onTap: widget.onTap,
            child: Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: bg,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: border),
              ),
              child: Icon(widget.icon, size: 19, color: fg),
            ),
          ),
        ),
      ),
    );
  }
}

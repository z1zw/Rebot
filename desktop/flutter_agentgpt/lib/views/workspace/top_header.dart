import "package:bitsdojo_window/bitsdojo_window.dart";
import "package:flutter/material.dart";
import "package:rebot_agentgpt/theme/app_tokens.dart";

class WorkspaceTopHeader extends StatelessWidget {
  const WorkspaceTopHeader({
    super.key,
    required this.projectName,
    required this.buildStatus,
    required this.running,
    required this.cloneStatus,
    required this.onBack,
    required this.onNewConversation,
    required this.onToggleSidebar,
    required this.onRun,
    required this.onRefresh,
    required this.onGitClone,
    required this.onOpenGit,
    required this.onRetryClone,
    required this.onConsole,
    required this.onNetwork,
    required this.rightPanelTab,
  });

  final String projectName;
  final String buildStatus;
  final String cloneStatus;
  final bool running;
  final String rightPanelTab;
  final VoidCallback onBack;
  final VoidCallback onNewConversation;
  final VoidCallback onToggleSidebar;
  final VoidCallback onRun;
  final VoidCallback onRefresh;
  final VoidCallback onGitClone;
  final VoidCallback onOpenGit;
  final VoidCallback onRetryClone;
  final VoidCallback onConsole;
  final VoidCallback onNetwork;

  @override
  Widget build(BuildContext context) {
    return WindowTitleBarBox(
      child: Container(
        height: 48,
        decoration: const BoxDecoration(
          color: AppTokens.bg,
          border: Border(bottom: BorderSide(color: AppTokens.border)),
        ),
        padding: const EdgeInsets.symmetric(horizontal: AppTokens.space10),
        child: Row(
          children: [
            _HeaderIconBtn(icon: Icons.menu_rounded, onTap: onToggleSidebar),
            const SizedBox(width: 4),
            _HeaderIconBtn(icon: Icons.arrow_back_rounded, onTap: onBack),
            const SizedBox(width: 4),
            _HeaderIconBtn(
              icon: Icons.add_rounded,
              onTap: onNewConversation,
              tooltip: "New conversation",
            ),
            const SizedBox(width: AppTokens.space10),
            Expanded(
              child: MoveWindow(
                child: Text(
                  projectName,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTokens.text(size: AppTokens.textMd, weight: FontWeight.w600, color: AppTokens.textPrimary),
                ),
              ),
            ),
            _HeaderIconBtn(
              icon: Icons.refresh_rounded,
              onTap: onRefresh,
              tooltip: "Refresh",
            ),
            const SizedBox(width: 4),
            _HeaderIconBtn(
              icon: Icons.download_rounded,
              onTap: onGitClone,
              tooltip: "Git clone",
            ),
            const SizedBox(width: 4),
            _HeaderIconBtn(
              icon: Icons.source_rounded,
              onTap: onOpenGit,
              tooltip: "Open Git",
            ),
            const SizedBox(width: 4),
            _HeaderIconBtn(
              icon: Icons.replay_rounded,
              onTap: onRetryClone,
              tooltip: "Retry clone",
            ),
            const SizedBox(width: 4),
            _HeaderIconBtn(
              icon: Icons.terminal_rounded,
              onTap: onConsole,
              active: rightPanelTab == "console",
              tooltip: "Console (Ctrl+`)",
            ),
            const SizedBox(width: 4),
            _HeaderIconBtn(
              icon: Icons.wifi_rounded,
              onTap: onNetwork,
              active: rightPanelTab == "network",
              tooltip: "Network (Ctrl+Shift+N)",
            ),
            const SizedBox(width: AppTokens.space8),
            _RunButton(running: running, onTap: onRun),
            const SizedBox(width: AppTokens.space10),
            _BadgeText(text: buildStatus),
            const SizedBox(width: AppTokens.space8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 190),
              child: _BadgeText(text: cloneStatus),
            ),
            const SizedBox(width: AppTokens.space6),
            const _WindowButtons(),
          ],
        ),
      ),
    );
  }
}

class _BadgeText extends StatelessWidget {
  const _BadgeText({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: AppTokens.space8, vertical: AppTokens.space4),
      decoration: BoxDecoration(
        color: AppTokens.surface,
        borderRadius: BorderRadius.circular(AppTokens.radiusPill),
        border: Border.all(color: AppTokens.border),
      ),
      child: Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: AppTokens.captionStyle(),
      ),
    );
  }
}

class _RunButton extends StatefulWidget {
  const _RunButton({required this.running, required this.onTap});
  final bool running;
  final VoidCallback onTap;

  @override
  State<_RunButton> createState() => _RunButtonState();
}

class _RunButtonState extends State<_RunButton> {
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    final bg = widget.running
        ? (_hover ? const Color(0xFFD14545) : const Color(0xFFC93C3C))
        : (_hover ? const Color(0xFF0B8CF9) : const Color(0xFF0A84FF));
    return MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          height: 30,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(AppTokens.radiusPill),
            border: Border.all(color: const Color(0x44FFFFFF)),
          ),
          alignment: Alignment.center,
          child: Text(
            widget.running ? "Stop" : "Run",
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ),
      ),
    );
  }
}

class _HeaderIconBtn extends StatefulWidget {
  const _HeaderIconBtn({
    required this.icon,
    required this.onTap,
    this.active = false,
    this.tooltip,
  });

  final IconData icon;
  final VoidCallback onTap;
  final bool active;
  final String? tooltip;

  @override
  State<_HeaderIconBtn> createState() => _HeaderIconBtnState();
}

class _HeaderIconBtnState extends State<_HeaderIconBtn> {
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    final bg = widget.active
        ? const Color(0x220A84FF)
        : (_hover ? const Color(0xFF31343A) : const Color(0xFF252830));
    final border = widget.active
        ? const Color(0x660A84FF)
        : (_hover ? const Color(0xFF4A5362) : const Color(0xFF3A3F48));
    final fg = widget.active
        ? const Color(0xFF0A84FF)
        : (_hover ? const Color(0xFFE2E6EF) : const Color(0xFFA5ACB9));

    final button = MouseRegion(
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: border),
          ),
          child: Icon(widget.icon, size: 16, color: fg),
        ),
      ),
    );
    if (widget.tooltip == null || widget.tooltip!.trim().isEmpty) {
      return button;
    }
    return Tooltip(
      message: widget.tooltip!,
      waitDuration: const Duration(milliseconds: 250),
      child: button,
    );
  }
}

class _WindowButtons extends StatelessWidget {
  const _WindowButtons();

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _HeaderIconBtn(icon: Icons.remove_rounded, onTap: appWindow.minimize),
        const SizedBox(width: 4),
        _HeaderIconBtn(
          icon: Icons.crop_square_rounded,
          onTap: appWindow.maximizeOrRestore,
        ),
        const SizedBox(width: 4),
        _HeaderIconBtn(icon: Icons.close_rounded, onTap: appWindow.close),
      ],
    );
  }
}



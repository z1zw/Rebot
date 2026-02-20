from pathlib import Path
path = Path('desktop/flutter_agentgpt/lib/views/main_layout.dart')
txt = path.read_text(encoding='utf-8')
start = txt.index('class _RdsGlobalHeader')
end = txt.index('class _RailIcon', start)
new_header = """class _RdsGlobalHeader extends StatelessWidget {
  const _RdsGlobalHeader({
    required this.projectName,
    required this.workspacePath,
    required this.conversationTitle,
    required this.buildStatus,
    required this.editingTitle,
    required this.titleController,
    required this.selectedDevice,
    required this.isRunning,
    required this.onBack,
    required this.onNewConversation,
    required this.onToggleSidebar,
    required this.onStartTitleEdit,
    required this.onSubmitTitle,
    required this.onCancelTitleEdit,
    required this.onRun,
    required this.onRefresh,
    required this.onScreenshot,
    required this.onConsole,
    required this.onNetwork,
    required this.onDeviceChanged,
  });

  final String projectName;
  final String workspacePath;
  final String conversationTitle;
  final String buildStatus;
  final bool editingTitle;
  final TextEditingController titleController;
  final String selectedDevice;
  final bool isRunning;
  final VoidCallback onBack;
  final VoidCallback onNewConversation;
  final VoidCallback onToggleSidebar;
  final VoidCallback onStartTitleEdit;
  final ValueChanged<String> onSubmitTitle;
  final VoidCallback onCancelTitleEdit;
  final VoidCallback onRun;
  final VoidCallback onRefresh;
  final VoidCallback onScreenshot;
  final VoidCallback onConsole;
  final VoidCallback onNetwork;
  final ValueChanged<String> onDeviceChanged;

  static const String _headerVersionTag = "RDS_HEADER_V3_20260214";
  static const String _gitCommitHash = "commit unknown";

  @override
  Widget build(BuildContext context) {
    final resolvedPath = workspacePath.trim().isEmpty ? "./" : workspacePath.trim();
    final breadcrumbs = <String>[projectName, conversationTitle].where((e) => e.trim().isNotEmpty).toList();
    return WindowTitleBarBox(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final width = constraints.maxWidth;
          debugPrint("RDS HEADER MOUNTED width=");
          final bool showBreadcrumb = width >= 760;
          final bool showIconsInline = width >= 900;
          final double searchWidth = width < 900
              ? (width < 760 ? 160 : 240)
              : (width < 1100 ? 240 : 320);
          final double searchMin = width < 900 ? 120 : 180;
          return Container(
            height: 48,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: const Color(0xFFF3F4F6),
              border: Border(bottom: BorderSide(color: Colors.black.withValues(alpha: 0.08))),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Row(
                  children: [
                    _HoverIconButton(
                      icon: Icons.menu_rounded,
                      tooltip: "Toggle navigation",
                      onTap: onToggleSidebar,
                    ),
                    const SizedBox(width: 6),
                    _HoverIconButton(icon: Icons.arrow_back_rounded, tooltip: "Back", onTap: onBack),
                    const SizedBox(width: 6),
                    _HoverIconButton(icon: Icons.add_rounded, tooltip: "New conversation", onTap: onNewConversation),
                    const SizedBox(width: 8),
                    _AppBadge(),
                  ],
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: MoveWindow(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        if (showBreadcrumb)
                          Flexible(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Flexible(
                                      child: Text(
                                        breadcrumbs.isEmpty ? "Rebot Workspace" : breadcrumbs.first,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: -0.3,
                                        ),
                                      ),
                                    ),
                                    if (breadcrumbs.length > 1) ...[
                                      const SizedBox(width: 6),
                                      const Icon(Icons.chevron_right, size: 16, color: Color(0xFF94A3B8)),
                                      const SizedBox(width: 6),
                                      Flexible(
                                        child: GestureDetector(
                                          onDoubleTap: onStartTitleEdit,
                                          child: editingTitle
                                              ? SizedBox(
                                                  width: 210,
                                                  child: TextField(
                                                    controller: titleController,
                                                    onSubmitted: onSubmitTitle,
                                                    autofocus: true,
                                                    onTapOutside: (_) => onCancelTitleEdit(),
                                                    decoration: const InputDecoration(
                                                      isDense: true,
                                                      contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                                                    ),
                                                  ),
                                                )
                                              : Text(
                                                  conversationTitle,
                                                  maxLines: 1,
                                                  overflow: TextOverflow.ellipsis,
                                                  style: const TextStyle(
                                                    fontSize: 13,
                                                    fontWeight: FontWeight.w600,
                                                    letterSpacing: -0.2,
                                                  ),
                                                ),
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                                const SizedBox(height: 2),
                                InkWell(
                                  borderRadius: BorderRadius.circular(6),
                                  onTap: () async {
                                    final messenger = ScaffoldMessenger.maybeOf(context);
                                    await Clipboard.setData(ClipboardData(text: resolvedPath));
                                    messenger?.showSnackBar(
                                      SnackBar(content: Text("Path copied: ")),
                                    );
                                  },
                                  child: Row(
                                    children: [
                                      const Icon(Icons.folder, size: 13, color: Color(0xFF94A3B8)),
                                      const SizedBox(width: 4),
                                      Text(
                                        resolvedPath,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280)),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          )
                        else
                          Flexible(
                            child: Text(
                              projectName,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, letterSpacing: -0.3),
                            ),
                          ),
                        const SizedBox(width: 12),
                        ConstrainedBox(
                          constraints: BoxConstraints(maxWidth: searchWidth, minWidth: searchMin),
                          child: const _HeaderSearchBox(),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _RunButton(onRun: onRun, isRunning: isRunning),
                    const SizedBox(width: 6),
                    _HoverIconButton(icon: Icons.refresh_outlined, tooltip: "Refresh preview", onTap: onRefresh, dense: true),
                    const SizedBox(width: 4),
                    if (showIconsInline) ...[
                      _HoverIconButton(icon: Icons.photo_camera_back_rounded, tooltip: "Screenshot", onTap: onScreenshot, dense: true),
                      const SizedBox(width: 4),
                      _HoverIconButton(icon: Icons.code_rounded, tooltip: "Console", onTap: onConsole, dense: true),
                      const SizedBox(width: 4),
                      _HoverIconButton(icon: Icons.network_check_rounded, tooltip: "Network", onTap: onNetwork, dense: true),
                    ] else
                      _HeaderOverflowMenu(
                        onScreenshot: onScreenshot,
                        onConsole: onConsole,
                        onNetwork: onNetwork,
                      ),
                    const SizedBox(width: 12),
                    PopupMenuButton<String>(
                      initialValue: selectedDevice,
                      tooltip: "Device",
                      onSelected: onDeviceChanged,
                      itemBuilder: (_) => _deviceOptions.map((d) => PopupMenuItem(value: d, child: Text(d))).toList(),
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFFCBD5E1)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.phone_android, size: 16, color: Color(0xFF475569)),
                            const SizedBox(width: 6),
                            Text(
                              selectedDevice,
                              style: const TextStyle(fontSize: 12, color: Color(0xFF475569)),
                            ),
                            const Icon(Icons.keyboard_arrow_down, size: 16, color: Color(0xFF94A3B8)),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          buildStatus,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 12, color: Color(0xFF6B7280)),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          workspacePath,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
                        ),
                      ],
                    ),
                    const SizedBox(width: 8),
                    const _DesktopWindowButtons(),
                    IconButton(
                      icon: const Icon(Icons.info_outline, size: 18, color: Color(0xFF475569)),
                      tooltip: "About Rebot",
                      onPressed: () {
                        showAboutDialog(
                          context: context,
                          applicationName: "Rebot Agent GPT",
                          applicationVersion: " ()",
                          applicationLegalese: "RDS workspace layout.",
                        );
                      },
                    ),
                    const SizedBox(width: 6),
                    Text(
                      _headerVersionTag,
                      style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8)),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
"""
path.write_text(txt[:start] + new_header + txt[end:], encoding='utf-8')

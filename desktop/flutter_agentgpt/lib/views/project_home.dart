import "dart:io";
import "package:bitsdojo_window/bitsdojo_window.dart";
import "package:file_selector/file_selector.dart";
import "package:flutter/material.dart";
import "package:provider/provider.dart";
import "../app_state.dart";
import "../core/l10n.dart";

class ProjectHome extends StatefulWidget {
  const ProjectHome({super.key});

  @override
  State<ProjectHome> createState() => _ProjectHomeState();
}

class _ProjectHomeState extends State<ProjectHome> {
  static const Color _xBg = Color(0xFF17181C);
  static const Color _xBgElevated = Color(0xFF202329);
  static const Color _xPanel = Color(0xFF252A33);
  static const Color _xBlue = Color(0xFF0A84FF);
  static const Color _xStroke = Color(0xFF343A46);
  static const Color _xHint = Color(0xFF99A1B3);
  final _searchController = TextEditingController();
  String _query = "";

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _openFolderDialog(BuildContext context) async {
    final appState = context.read<AppState>();
    await showGeneralDialog<void>(
      context: context,
      barrierDismissible: true,
      barrierLabel: "Open Folder",
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 200),
      pageBuilder: (ctx, _, __) => Center(
        child: _IdeaOpenFolderDialog(appState: appState),
      ),
    );
  }

  Future<void> _openCloneDialog(BuildContext context) async {
    final appState = context.read<AppState>();
    await showGeneralDialog<void>(
      context: context,
      barrierDismissible: true,
      barrierLabel: "Clone Repository",
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 200),
      pageBuilder: (ctx, _, __) => Center(
        child: _IdeaCloneDialog(appState: appState),
      ),
    );
  }

  void _openCreateDialog(BuildContext context) {
    showGeneralDialog(
      context: context,
      barrierDismissible: true,
      barrierLabel: "Create Project",
      barrierColor: Colors.black.withValues(alpha: 0.5),
      transitionDuration: const Duration(milliseconds: 200),
      pageBuilder: (ctx, _, __) => Center(
        child: _IdeaCreateProjectDialog(appState: context.read<AppState>()),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final allProjects =
        context.select<AppState, List<Project>>((s) => s.projects);
    final projects = allProjects.where((p) {
      if (_query.isEmpty) return true;
      final q = _query.toLowerCase();
      return p.name.toLowerCase().contains(q) ||
          p.framework.toLowerCase().contains(q);
    }).toList();

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          color: _xBg,
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [_xBgElevated, _xBg],
          ),
        ),
        child: Column(
          children: [
            // IDEA-style title bar
            SizedBox(
              height: 40,
              child: WindowTitleBarBox(
                child: Container(
                  color: _xBgElevated,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Row(
                    children: [
                      // Logo
                      Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF10A37F), Color(0xFF1A7F5A)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Center(
                          child: Text("R",
                              style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white)),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: MoveWindow(
                          child: const Text(
                            "Welcome to Rebot",
                            style: TextStyle(
                              fontSize: 12,
                              color: Color(0xFFE8ECF2),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                      const _IdeaWindowControls(),
                    ],
                  ),
                ),
              ),
            ),
            // Main content
            Expanded(
              child: Row(
                children: [
                  // Left sidebar - Projects list
                  Container(
                    width: 320,
                    decoration: const BoxDecoration(
                      color: _xBg,
                      border: Border(right: BorderSide(color: _xStroke)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // Projects header
                        Container(
                          padding: const EdgeInsets.fromLTRB(16, 16, 12, 12),
                          child: Row(
                            children: [
                              const Text(
                                "Projects",
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w700,
                                  color: Color(0xFFE8ECF2),
                                ),
                              ),
                              const Spacer(),
                              _IdeaMiniButton(
                                icon: Icons.add,
                                tooltip: S.newProject,
                                onTap: () => _openCreateDialog(context),
                              ),
                              const SizedBox(width: 4),
                              _IdeaMiniButton(
                                icon: Icons.folder_open_outlined,
                                tooltip: "Open Folder",
                                onTap: () => _openFolderDialog(context),
                              ),
                              const SizedBox(width: 4),
                              _IdeaMiniButton(
                                icon: Icons.cloud_download_outlined,
                                tooltip: "Clone from VCS",
                                onTap: () => _openCloneDialog(context),
                              ),
                            ],
                          ),
                        ),
                        // Search
                        Padding(
                          padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
                          child: Container(
                            height: 36,
                            decoration: BoxDecoration(
                              color: _xPanel,
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(color: _xStroke),
                            ),
                            child: Row(
                              children: [
                                const SizedBox(width: 10),
                                const Icon(Icons.search,
                                    size: 14, color: _xHint),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: TextField(
                                    controller: _searchController,
                                    onChanged: (v) =>
                                        setState(() => _query = v),
                                    cursorColor: _xBlue,
                                    style: const TextStyle(
                                        fontSize: 12, color: Color(0xFFE8ECF2)),
                                    decoration: const InputDecoration(
                                      border: InputBorder.none,
                                      enabledBorder: InputBorder.none,
                                      focusedBorder: InputBorder.none,
                                      disabledBorder: InputBorder.none,
                                      errorBorder: InputBorder.none,
                                      focusedErrorBorder: InputBorder.none,
                                      isDense: true,
                                      contentPadding:
                                          EdgeInsets.symmetric(vertical: 8),
                                      hintText: "Search",
                                      hintStyle: TextStyle(
                                          fontSize: 12, color: _xHint),
                                    ),
                                  ),
                                ),
                                if (_query.isNotEmpty)
                                  GestureDetector(
                                    onTap: () {
                                      _searchController.clear();
                                      setState(() => _query = "");
                                    },
                                    child: const Padding(
                                      padding: EdgeInsets.all(6),
                                      child: Icon(Icons.close,
                                          size: 14, color: _xHint),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ),
                        // Project list
                        Expanded(
                          child: projects.isEmpty
                              ? Center(
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(Icons.folder_outlined,
                                          size: 48,
                                          color: const Color(0xFF6B6B6B)),
                                      const SizedBox(height: 12),
                                      const Text(
                                        "No projects yet",
                                        style: TextStyle(
                                            fontSize: 13,
                                            color: Color(0xFF8E8E8E)),
                                      ),
                                      const SizedBox(height: 4),
                                      const Text(
                                        "Create or clone a project to begin",
                                        style: TextStyle(
                                            fontSize: 11,
                                            color: Color(0xFF6B6B6B)),
                                      ),
                                    ],
                                  ),
                                )
                              : ListView.builder(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 8, vertical: 4),
                                  itemCount: projects.length,
                                  itemBuilder: (context, index) {
                                    final p = projects[index];
                                    return _IdeaProjectItem(
                                      project: p,
                                      onTap: () => context
                                          .read<AppState>()
                                          .openProject(p.id),
                                    );
                                  },
                                ),
                        ),
                      ],
                    ),
                  ),
                  // Right content area
                  Expanded(
                    child: Container(
                      color: _xBg,
                      child: Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 480),
                          child: Padding(
                            padding: const EdgeInsets.all(48),
                            child: Container(
                              padding: const EdgeInsets.all(24),
                              decoration: BoxDecoration(
                                color: _xBgElevated,
                                borderRadius: BorderRadius.circular(18),
                                border: Border.all(color: _xStroke),
                                boxShadow: const [
                                  BoxShadow(
                                    color: Color(0x2A000000),
                                    blurRadius: 22,
                                    offset: Offset(0, 8),
                                  ),
                                ],
                              ),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  // Rebot logo
                                  Container(
                                    width: 80,
                                    height: 80,
                                    decoration: BoxDecoration(
                                      gradient: const LinearGradient(
                                        colors: [
                                          Color(0xFF2A98FF),
                                          Color(0xFF0A84FF)
                                        ],
                                        begin: Alignment.topLeft,
                                        end: Alignment.bottomRight,
                                      ),
                                      borderRadius: BorderRadius.circular(22),
                                    ),
                                    child: const Icon(
                                        Icons.auto_awesome_rounded,
                                        size: 40,
                                        color: Colors.white),
                                  ),
                                  const SizedBox(height: 24),
                                  const Text(
                                    "Rebot",
                                    style: TextStyle(
                                      fontSize: 28,
                                      fontWeight: FontWeight.w700,
                                      color: Color(0xFFE8ECF2),
                                      letterSpacing: -0.5,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  const Text(
                                    "AI-Powered Development Workspace",
                                    style:
                                        TextStyle(fontSize: 14, color: _xHint),
                                  ),
                                  const SizedBox(height: 28),
                                  _IdeaActionRow(
                                    icon: Icons.add_rounded,
                                    label: S.newProject,
                                    description:
                                        "Create empty project with AI assistance",
                                    onTap: () => _openCreateDialog(context),
                                  ),
                                  const SizedBox(height: 10),
                                  _IdeaActionRow(
                                    icon: Icons.folder_open_rounded,
                                    label: "Open",
                                    description:
                                        "Open local folder as workspace",
                                    onTap: () => _openFolderDialog(context),
                                  ),
                                  const SizedBox(height: 10),
                                  _IdeaActionRow(
                                    icon: Icons.cloud_download_rounded,
                                    label: "Get from VCS",
                                    description:
                                        "Clone repository from GitHub, GitLab, etc.",
                                    onTap: () => _openCloneDialog(context),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecentProjectCard extends StatefulWidget {
  const _RecentProjectCard({
    required this.project,
    required this.onTap,
  });

  final Project project;
  final VoidCallback onTap;

  @override
  State<_RecentProjectCard> createState() => _RecentProjectCardState();
}

class _RecentProjectCardState extends State<_RecentProjectCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final p = widget.project;
    final frameworkIcon = _frameworkIcon(p.framework);
    final frameworkColor = _frameworkColor(p.framework);
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        transform: Matrix4.translationValues(0, _hovered ? -4 : 0, 0),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(16),
            onTap: widget.onTap,
            child: Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: const Color(0xFF212121),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: _hovered
                      ? frameworkColor.withValues(alpha: 0.3)
                      : const Color(0xFF2A2A2A),
                  width: _hovered ? 1.5 : 1,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: frameworkColor.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(frameworkIcon,
                            size: 18, color: frameworkColor),
                      ),
                      const Spacer(),
                      Opacity(
                        opacity: _hovered ? 1 : 0,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: frameworkColor.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            p.framework.toUpperCase(),
                            style: TextStyle(
                              fontSize: 9,
                              fontWeight: FontWeight.w700,
                              color: frameworkColor,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  Text(
                    p.name,
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color:
                          _hovered ? frameworkColor : const Color(0xFF0F172A),
                      letterSpacing: -0.3,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    p.workspacePath.trim().isEmpty
                        ? "~/projects/${p.name}"
                        : p.workspacePath,
                    style: TextStyle(
                      fontSize: 11,
                      color: const Color(0xFF94A3B8).withValues(alpha: 0.9),
                      fontWeight: FontWeight.w400,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  IconData _frameworkIcon(String framework) {
    final f = framework.toLowerCase();
    if (f == "flutter") return Icons.flutter_dash_rounded;
    if (f == "react") return Icons.bubble_chart_rounded;
    if (f == "vue") return Icons.eco_outlined;
    if (f == "python") return Icons.code_rounded;
    if (f == "uniapp") return Icons.web_rounded;
    if (f == "wechat_miniprogram") return Icons.chat_bubble_outline_rounded;
    if (f == "general") return Icons.developer_mode_rounded;
    return Icons.folder_rounded;
  }

  Color _frameworkColor(String framework) {
    final f = framework.toLowerCase();
    if (f == "flutter") return const Color(0xFF0175C2);
    if (f == "react") return const Color(0xFF61DAFB);
    if (f == "vue") return const Color(0xFF42B883);
    if (f == "python") return const Color(0xFF3776AB);
    if (f == "uniapp") return const Color(0xFF2B9939);
    if (f == "wechat_miniprogram") return const Color(0xFF07C160);
    if (f == "general") return const Color(0xFF6366F1);
    return const Color(0xFF64748B);
  }
}

class _ActionCard extends StatefulWidget {
  const _ActionCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String description;
  final VoidCallback onTap;

  @override
  State<_ActionCard> createState() => _ActionCardState();
}

class _ActionCardState extends State<_ActionCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    const accent = Color(0xFF10A37F);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: widget.onTap,
        borderRadius: BorderRadius.circular(14),
        child: MouseRegion(
          cursor: SystemMouseCursors.click,
          onEnter: (_) => setState(() => _hovered = true),
          onExit: (_) => setState(() => _hovered = false),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: _hovered
                  ? accent.withValues(alpha: 0.08)
                  : const Color(0xFF212121),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: _hovered
                    ? accent.withValues(alpha: 0.3)
                    : const Color(0xFF2A2A2A),
                width: _hovered ? 1.5 : 1,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 42,
                  height: 42,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(widget.icon, size: 20, color: accent),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.title,
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: _hovered ? accent : const Color(0xFF0F172A),
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        widget.description,
                        style: TextStyle(
                          fontSize: 12,
                          color: const Color(0xFF64748B).withValues(alpha: 0.9),
                          height: 1.3,
                        ),
                      ),
                    ],
                  ),
                ),
                Opacity(
                  opacity: _hovered ? 1 : 0,
                  child: Icon(
                    Icons.arrow_forward_rounded,
                    size: 18,
                    color: accent.withValues(alpha: 0.7),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PrimaryActionButton extends StatefulWidget {
  const _PrimaryActionButton({
    required this.onPressed,
    required this.icon,
    required this.label,
  });

  final VoidCallback onPressed;
  final IconData icon;
  final String label;

  @override
  State<_PrimaryActionButton> createState() => _PrimaryActionButtonState();
}

class _PrimaryActionButtonState extends State<_PrimaryActionButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: Container(
          height: 40,
          padding: const EdgeInsets.symmetric(horizontal: 18),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: _hovered
                  ? [const Color(0xFF2563EB), const Color(0xFF1D4ED8)]
                  : [const Color(0xFF3B82F6), const Color(0xFF2563EB)],
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
            ),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(widget.icon, size: 17, color: Colors.white),
              const SizedBox(width: 8),
              Text(
                widget.label,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: Colors.white,
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _WindowControlButton extends StatefulWidget {
  const _WindowControlButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  State<_WindowControlButton> createState() => _WindowControlButtonState();
}

class _WindowControlButtonState extends State<_WindowControlButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final hoverBg = const Color(0xFF2A2A2A);
    final iconColor =
        _hovered ? const Color(0xFFFFFFFF) : const Color(0xFF8E8E8E);
    return Tooltip(
      message: widget.tooltip,
      child: MouseRegion(
        cursor: SystemMouseCursors.click,
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: GestureDetector(
          onTap: widget.onTap,
          child: Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: _hovered ? hoverBg : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
            ),
            alignment: Alignment.center,
            child: Icon(widget.icon, size: 15, color: iconColor),
          ),
        ),
      ),
    );
  }
}

class _FrameworkCard extends StatefulWidget {
  const _FrameworkCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String value;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<_FrameworkCard> createState() => _FrameworkCardState();
}

class _FrameworkCardState extends State<_FrameworkCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final accentColor =
        widget.selected ? const Color(0xFF3B82F6) : const Color(0xFF64748B);
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          height: 56,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: widget.selected
                ? const Color(0xFF10A37F).withValues(alpha: 0.15)
                : _hovered
                    ? const Color(0xFF35373B)
                    : const Color(0xFF212121),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: widget.selected
                  ? const Color(0xFF10A37F)
                  : _hovered
                      ? const Color(0xFF4E5157)
                      : const Color(0xFF2A2A2A),
              width: widget.selected ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(widget.icon, size: 18, color: accentColor),
              const SizedBox(width: 8),
              Text(
                widget.label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight:
                      widget.selected ? FontWeight.w600 : FontWeight.w500,
                  color: widget.selected
                      ? const Color(0xFF3B82F6)
                      : const Color(0xFF334155),
                  letterSpacing: -0.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// 锟斤拷锟斤拷锟斤拷 IDEA-style Open Folder Dialog 锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷

class _IdeaOpenFolderDialog extends StatefulWidget {
  const _IdeaOpenFolderDialog({required this.appState});
  final AppState appState;

  @override
  State<_IdeaOpenFolderDialog> createState() => _IdeaOpenFolderDialogState();
}

class _IdeaOpenFolderDialogState extends State<_IdeaOpenFolderDialog> {
  final _pathController = TextEditingController();
  bool _isOpening = false;
  String? _errorMessage;

  @override
  void dispose() {
    _pathController.dispose();
    super.dispose();
  }

  Future<void> _selectDir() async {
    final picked = await getDirectoryPath(confirmButtonText: "Select");
    if (picked != null && picked.trim().isNotEmpty) {
      setState(() => _pathController.text = picked);
    }
  }

  Future<void> _open() async {
    final path = _pathController.text.trim();
    if (path.isEmpty) {
      setState(() => _errorMessage = "Please select a folder");
      return;
    }

    setState(() {
      _isOpening = true;
      _errorMessage = null;
    });

    try {
      await widget.appState.openFolderAsProject(
        folderPath: path,
        framework: "general", // Auto-detect
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isOpening = false;
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Container(
        width: 580,
        decoration: BoxDecoration(
          color: const Color(0xFF202329),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF343A46)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: Color(0xFF343A46))),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFF8B5CF6).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.folder_open_outlined,
                        color: Color(0xFF8B5CF6), size: 20),
                  ),
                  const SizedBox(width: 16),
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Open Folder",
                        style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFFFFFFFF),
                            letterSpacing: -0.3),
                      ),
                      SizedBox(height: 2),
                      Text(
                        "Open an existing project folder",
                        style:
                            TextStyle(fontSize: 12, color: Color(0xFF8E8E8E)),
                      ),
                    ],
                  ),
                  const Spacer(),
                  _IdeaIconButton(
                      icon: Icons.close,
                      onTap: () => Navigator.of(context).pop()),
                ],
              ),
            ),
            // Content
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _IdeaFieldLabel(label: "Folder Path", required: true),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _IdeaTextField(
                          controller: _pathController,
                          placeholder: r"C:\dev\my-project",
                          prefix: const Icon(Icons.folder_outlined,
                              size: 16, color: Color(0xFF8E8E8E)),
                        ),
                      ),
                      const SizedBox(width: 8),
                      _IdeaButton(
                          label: "Browse", onTap: _selectDir, secondary: true),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: const [
                      Icon(Icons.info_outline,
                          size: 14, color: Color(0xFF7C879D)),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          "Project type will be auto-detected based on folder contents",
                          style:
                              TextStyle(fontSize: 12, color: Color(0xFF99A1B3)),
                        ),
                      ),
                    ],
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF4B2828),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF7B3B3B)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline,
                              size: 18, color: Color(0xFFE06C75)),
                          const SizedBox(width: 10),
                          Expanded(
                              child: Text(_errorMessage!,
                                  style: const TextStyle(
                                      fontSize: 13, color: Color(0xFFE06C75)))),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            // Footer
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: const BoxDecoration(
                color: Color(0xFF1D2027),
                border: Border(top: BorderSide(color: Color(0xFF343A46))),
                borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(14),
                    bottomRight: Radius.circular(14)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  _IdeaButton(
                      label: S.cancel,
                      onTap: () => Navigator.of(context).pop(),
                      secondary: true),
                  const SizedBox(width: 12),
                  _IdeaButton(
                      label: "Open",
                      onTap: _isOpening ? null : _open,
                      primary: true,
                      icon: Icons.folder_open_outlined),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 锟斤拷锟斤拷锟斤拷 IDEA-style Create Project Dialog 锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷

class _IdeaCreateProjectDialog extends StatefulWidget {
  const _IdeaCreateProjectDialog({required this.appState});
  final AppState appState;

  @override
  State<_IdeaCreateProjectDialog> createState() =>
      _IdeaCreateProjectDialogState();
}

class _IdeaCreateProjectDialogState extends State<_IdeaCreateProjectDialog> {
  final _nameController = TextEditingController();
  final _descController = TextEditingController();
  String _framework = "flutter";
  bool _isCreating = false;
  String? _errorMessage;

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final name = _nameController.text.trim();
    if (name.isEmpty) {
      setState(() => _errorMessage = "Please enter a project name");
      return;
    }

    setState(() {
      _isCreating = true;
      _errorMessage = null;
    });

    try {
      widget.appState.createProject(
        name: name,
        description: _descController.text.trim(),
        framework: _framework,
        projectType: _framework,
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isCreating = false;
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Container(
        width: 680,
        constraints: const BoxConstraints(maxHeight: 620),
        decoration: BoxDecoration(
          color: const Color(0xFF202329),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF343A46)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              decoration: const BoxDecoration(
                border: Border(bottom: BorderSide(color: Color(0xFF343A46))),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFF10B981).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.add_rounded,
                        color: Color(0xFF10B981), size: 20),
                  ),
                  const SizedBox(width: 16),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        S.newProject,
                        style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFFFFFFFF),
                            letterSpacing: -0.3),
                      ),
                      const SizedBox(height: 2),
                      const Text(
                        "Create a new project with AI assistance",
                        style:
                            TextStyle(fontSize: 12, color: Color(0xFF8E8E8E)),
                      ),
                    ],
                  ),
                  const Spacer(),
                  _IdeaIconButton(
                      icon: Icons.close,
                      onTap: () => Navigator.of(context).pop()),
                ],
              ),
            ),
            // Content
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _IdeaFieldLabel(label: "Project Name", required: true),
                  const SizedBox(height: 8),
                  _IdeaTextField(
                    controller: _nameController,
                    placeholder: "my-awesome-project",
                    autofocus: true,
                    prefix: const Icon(Icons.edit_outlined,
                        size: 16, color: Color(0xFF8E8E8E)),
                  ),
                  const SizedBox(height: 20),
                  const _IdeaFieldLabel(label: "Description"),
                  const SizedBox(height: 8),
                  _IdeaTextArea(
                    controller: _descController,
                    placeholder: "Describe your project idea...",
                    minLines: 2,
                    maxLines: 3,
                  ),
                  const SizedBox(height: 20),
                  const _IdeaFieldLabel(label: "Framework"),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: [
                      _IdeaDarkFrameworkCard(
                          label: "Flutter",
                          value: "flutter",
                          icon: Icons.flutter_dash_rounded,
                          selected: _framework == "flutter",
                          onTap: () => setState(() => _framework = "flutter")),
                      _IdeaDarkFrameworkCard(
                          label: "React",
                          value: "react",
                          icon: Icons.bubble_chart_rounded,
                          selected: _framework == "react",
                          onTap: () => setState(() => _framework = "react")),
                      _IdeaDarkFrameworkCard(
                          label: "Vue",
                          value: "vue",
                          icon: Icons.eco_outlined,
                          selected: _framework == "vue",
                          onTap: () => setState(() => _framework = "vue")),
                      _IdeaDarkFrameworkCard(
                          label: "Python",
                          value: "python",
                          icon: Icons.code_rounded,
                          selected: _framework == "python",
                          onTap: () => setState(() => _framework = "python")),
                      _IdeaDarkFrameworkCard(
                          label: "Uniapp",
                          value: "uniapp",
                          icon: Icons.web_rounded,
                          selected: _framework == "uniapp",
                          onTap: () => setState(() => _framework = "uniapp")),
                      _IdeaDarkFrameworkCard(
                          label: "MiniProgram",
                          value: "wechat_miniprogram",
                          icon: Icons.chat_bubble_outline_rounded,
                          selected: _framework == "wechat_miniprogram",
                          onTap: () => setState(
                              () => _framework = "wechat_miniprogram")),
                      _IdeaDarkFrameworkCard(
                          label: "General",
                          value: "general",
                          icon: Icons.developer_mode_rounded,
                          selected: _framework == "general",
                          onTap: () => setState(() => _framework = "general")),
                    ],
                  ),
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF4B2828),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFF7B3B3B)),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.error_outline,
                              size: 18, color: Color(0xFFE06C75)),
                          const SizedBox(width: 10),
                          Expanded(
                              child: Text(_errorMessage!,
                                  style: const TextStyle(
                                      fontSize: 13, color: Color(0xFFE06C75)))),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
            // Footer
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: const BoxDecoration(
                color: Color(0xFF1D2027),
                border: Border(top: BorderSide(color: Color(0xFF343A46))),
                borderRadius: BorderRadius.only(
                    bottomLeft: Radius.circular(14),
                    bottomRight: Radius.circular(14)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  _IdeaButton(
                      label: S.cancel,
                      onTap: () => Navigator.of(context).pop(),
                      secondary: true),
                  const SizedBox(width: 12),
                  _IdeaButton(
                      label: S.create,
                      onTap: _isCreating ? null : _create,
                      primary: true,
                      icon: Icons.add_rounded),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 锟斤拷锟斤拷锟斤拷 IDEA-style Dark Framework Card 锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷

class _IdeaDarkFrameworkCard extends StatefulWidget {
  const _IdeaDarkFrameworkCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final String value;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  State<_IdeaDarkFrameworkCard> createState() => _IdeaDarkFrameworkCardState();
}

class _IdeaDarkFrameworkCardState extends State<_IdeaDarkFrameworkCard> {
  bool _hovered = false;

  Color get _color {
    switch (widget.value) {
      case "flutter":
        return const Color(0xFF0175C2);
      case "react":
        return const Color(0xFF61DAFB);
      case "vue":
        return const Color(0xFF42B883);
      case "python":
        return const Color(0xFF3776AB);
      case "uniapp":
        return const Color(0xFF2B9939);
      case "wechat_miniprogram":
        return const Color(0xFF07C160);
      case "general":
        return const Color(0xFF6366F1);
      default:
        return const Color(0xFF8E8E8E);
    }
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 90,
          height: 72,
          decoration: BoxDecoration(
            color: widget.selected
                ? _color.withValues(alpha: 0.16)
                : _hovered
                    ? const Color(0xFF2D3340)
                    : const Color(0xFF252A33),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: widget.selected
                  ? _color
                  : _hovered
                      ? const Color(0xFF4C5870)
                      : const Color(0xFF343A46),
              width: widget.selected ? 2 : 1,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(widget.icon,
                  size: 24,
                  color: widget.selected ? _color : const Color(0xFF8E8E8E)),
              const SizedBox(height: 6),
              Text(
                widget.label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight:
                      widget.selected ? FontWeight.w600 : FontWeight.w500,
                  color: widget.selected ? _color : const Color(0xFFA4ADBD),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// 锟斤拷锟斤拷锟斤拷 IDEA-style Text Area 锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷

class _IdeaTextArea extends StatefulWidget {
  const _IdeaTextArea({
    required this.controller,
    this.placeholder,
    this.minLines = 2,
    this.maxLines = 4,
  });
  final TextEditingController controller;
  final String? placeholder;
  final int minLines;
  final int maxLines;

  @override
  State<_IdeaTextArea> createState() => _IdeaTextAreaState();
}

class _IdeaTextAreaState extends State<_IdeaTextArea> {
  bool _focused = false;
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        decoration: BoxDecoration(
          color: _focused ? const Color(0xFF2D3340) : const Color(0xFF252A33),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: _focused
                ? const Color(0xFF0A84FF)
                : _hovered
                    ? const Color(0xFF4C5870)
                    : const Color(0xFF343A46),
            width: _focused ? 1.5 : 1,
          ),
        ),
        child: Focus(
          onFocusChange: (f) => setState(() => _focused = f),
          child: TextField(
            controller: widget.controller,
            minLines: widget.minLines,
            maxLines: widget.maxLines,
            style: const TextStyle(fontSize: 13, color: Color(0xFFE8ECF2)),
            decoration: InputDecoration(
              hintText: widget.placeholder,
              hintStyle:
                  const TextStyle(fontSize: 13, color: Color(0xFF99A1B3)),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.all(12),
            ),
          ),
        ),
      ),
    );
  }
}

// 锟斤拷锟斤拷锟斤拷 IDEA-style Clone Dialog 锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷

class _IdeaCloneDialog extends StatefulWidget {
  const _IdeaCloneDialog({required this.appState});
  final AppState appState;

  @override
  State<_IdeaCloneDialog> createState() => _IdeaCloneDialogState();
}

class _IdeaCloneDialogState extends State<_IdeaCloneDialog> {
  final _urlController = TextEditingController();
  final _directoryController = TextEditingController();
  final _branchController = TextEditingController();
  bool _isCloning = false;
  String? _errorMessage;
  String? _successMessage;
  double _progress = 0;

  @override
  void initState() {
    super.initState();
    _directoryController.text = r"C:\dev";
    _urlController.addListener(_onUrlChanged);
  }

  @override
  void dispose() {
    _urlController.removeListener(_onUrlChanged);
    _urlController.dispose();
    _directoryController.dispose();
    _branchController.dispose();
    super.dispose();
  }

  void _onUrlChanged() {
    // Auto-detect repo name from URL and append to directory
    final url = _urlController.text.trim();
    if (url.isEmpty) return;

    final repoName = _extractRepoName(url);
    if (repoName.isNotEmpty) {
      final baseDir = _directoryController.text.trim();
      final basePath = baseDir.contains(RegExp(r'[\\/][^\\/]+$'))
          ? baseDir.replaceFirst(RegExp(r'[\\/][^\\/]+$'), '')
          : baseDir;
      if (!_directoryController.text.endsWith(repoName)) {
        final sep = basePath.contains('/') ? '/' : '\\';
        _directoryController.text = "$basePath$sep$repoName";
      }
    }
  }

  String _extractRepoName(String url) {
    // Handle various git URL formats
    final patterns = [
      RegExp(r'github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$'),
      RegExp(r'gitlab\.com[/:]([^/]+)/([^/]+?)(?:\.git)?$'),
      RegExp(r'bitbucket\.org[/:]([^/]+)/([^/]+?)(?:\.git)?$'),
      RegExp(r'/([^/]+?)(?:\.git)?$'),
    ];

    for (final pattern in patterns) {
      final match = pattern.firstMatch(url);
      if (match != null) {
        return match.group(match.groupCount)?.replaceAll('.git', '') ?? '';
      }
    }
    return '';
  }

  Future<void> _selectDirectory() async {
    final picked = await getDirectoryPath(confirmButtonText: "Select");
    if (picked != null && picked.trim().isNotEmpty) {
      final repoName = _extractRepoName(_urlController.text);
      final sep = picked.contains('/') ? '/' : '\\';
      setState(() {
        _directoryController.text =
            repoName.isEmpty ? picked : "$picked$sep$repoName";
      });
    }
  }

  Future<void> _clone() async {
    final url = _urlController.text.trim();
    final directory = _directoryController.text.trim();
    final branch = _branchController.text.trim();

    if (url.isEmpty) {
      setState(() => _errorMessage = "Please enter a repository URL");
      return;
    }

    if (directory.isEmpty) {
      setState(() => _errorMessage = "Please select a directory");
      return;
    }

    setState(() {
      _isCloning = true;
      _errorMessage = null;
      _successMessage = null;
      _progress = 0;
    });

    // Simulate progress updates
    final progressTimer =
        Stream.periodic(const Duration(milliseconds: 100), (i) => i)
            .take(50)
            .listen((i) {
      if (mounted && _isCloning) {
        setState(() => _progress = (i / 50) * 0.9);
      }
    });

    try {
      await widget.appState.cloneProjectFromGit(
        repoUrl: url,
        destination: directory,
        branch: branch,
        framework: "general", // Will be auto-detected
      );

      progressTimer.cancel();

      if (!mounted) return;
      setState(() {
        _isCloning = false;
        _progress = 1.0;
        _successMessage = "Repository cloned successfully!";
      });

      await Future.delayed(const Duration(milliseconds: 800));
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      progressTimer.cancel();
      if (!mounted) return;
      setState(() {
        _isCloning = false;
        _errorMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Container(
        width: 680,
        constraints: const BoxConstraints(maxHeight: 580),
        decoration: BoxDecoration(
          color: const Color(0xFF202329),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFF343A46)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
              decoration: const BoxDecoration(
                border: Border(
                  bottom: BorderSide(color: Color(0xFF343A46)),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFF10A37F).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.cloud_download_outlined,
                        color: Color(0xFF10A37F), size: 20),
                  ),
                  const SizedBox(width: 16),
                  const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "Clone Repository",
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFFFFFFFF),
                          letterSpacing: -0.3,
                        ),
                      ),
                      SizedBox(height: 2),
                      Text(
                        "Get a project from a version control system",
                        style: TextStyle(
                          fontSize: 12,
                          color: Color(0xFF8E8E8E),
                        ),
                      ),
                    ],
                  ),
                  const Spacer(),
                  _IdeaIconButton(
                    icon: Icons.close,
                    onTap: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
            ),

            // Content
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // URL Field
                  _IdeaFieldLabel(label: "URL", required: true),
                  const SizedBox(height: 8),
                  _IdeaTextField(
                    controller: _urlController,
                    placeholder: "https://github.com/user/repository.git",
                    autofocus: true,
                    prefix: const Icon(Icons.link,
                        size: 16, color: Color(0xFF8E8E8E)),
                  ),
                  const SizedBox(height: 20),

                  // Directory Field
                  _IdeaFieldLabel(label: "Directory", required: true),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: _IdeaTextField(
                          controller: _directoryController,
                          placeholder: r"C:\dev\project",
                          prefix: const Icon(Icons.folder_outlined,
                              size: 16, color: Color(0xFF8E8E8E)),
                        ),
                      ),
                      const SizedBox(width: 8),
                      _IdeaButton(
                        label: "Browse",
                        onTap: _selectDirectory,
                        secondary: true,
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // Branch field (full width)
                  _IdeaFieldLabel(label: "Branch (optional)"),
                  const SizedBox(height: 8),
                  _IdeaTextField(
                    controller: _branchController,
                    placeholder: "Leave empty for default branch",
                    prefix: const Icon(Icons.call_split,
                        size: 16, color: Color(0xFF8E8E8E)),
                  ),
                  const SizedBox(height: 12),
                  // Info text
                  Row(
                    children: [
                      Icon(Icons.info_outline,
                          size: 14, color: const Color(0xFF6B6B6B)),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          "Project type will be auto-detected after cloning",
                          style: TextStyle(
                              fontSize: 12, color: const Color(0xFF6B6B6B)),
                        ),
                      ),
                    ],
                  ),

                  // Progress/Error/Success
                  if (_isCloning ||
                      _errorMessage != null ||
                      _successMessage != null) ...[
                    const SizedBox(height: 24),
                    if (_isCloning) ...[
                      Row(
                        children: [
                          const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              valueColor:
                                  AlwaysStoppedAnimation(Color(0xFF10A37F)),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            "Cloning repository...",
                            style: TextStyle(
                              fontSize: 13,
                              color: const Color(0xFF8E8E8E),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(4),
                        child: LinearProgressIndicator(
                          value: _progress,
                          minHeight: 4,
                          backgroundColor: const Color(0xFF2B3240),
                          valueColor:
                              const AlwaysStoppedAnimation(Color(0xFF0A84FF)),
                        ),
                      ),
                    ],
                    if (_errorMessage != null)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF4B2828),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF7B3B3B)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.error_outline,
                                size: 18, color: Color(0xFFE06C75)),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _errorMessage!,
                                style: const TextStyle(
                                    fontSize: 13, color: Color(0xFFE06C75)),
                              ),
                            ),
                          ],
                        ),
                      ),
                    if (_successMessage != null)
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF2A4B37),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF3B7B50)),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.check_circle_outline,
                                size: 18, color: Color(0xFF98C379)),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _successMessage!,
                                style: const TextStyle(
                                    fontSize: 13, color: Color(0xFF98C379)),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ],
              ),
            ),

            // Footer
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: const BoxDecoration(
                color: Color(0xFF1D2027),
                border: Border(
                  top: BorderSide(color: Color(0xFF343A46)),
                ),
                borderRadius: BorderRadius.only(
                  bottomLeft: Radius.circular(14),
                  bottomRight: Radius.circular(14),
                ),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  _IdeaButton(
                    label: "Cancel",
                    onTap: () => Navigator.of(context).pop(),
                    secondary: true,
                  ),
                  const SizedBox(width: 12),
                  _IdeaButton(
                    label: "Clone",
                    onTap: _isCloning ? null : _clone,
                    primary: true,
                    icon: Icons.cloud_download_outlined,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// 锟斤拷锟斤拷锟斤拷 IDEA-style Components 锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷锟斤拷

class _IdeaFieldLabel extends StatelessWidget {
  const _IdeaFieldLabel({required this.label, this.required = false});
  final String label;
  final bool required;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          label,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: Color(0xFFFFFFFF),
          ),
        ),
        if (required) ...[
          const SizedBox(width: 4),
          const Text("*",
              style: TextStyle(fontSize: 12, color: Color(0xFFE06C75))),
        ],
      ],
    );
  }
}

class _IdeaTextField extends StatefulWidget {
  const _IdeaTextField({
    required this.controller,
    this.placeholder,
    this.autofocus = false,
    this.prefix,
  });
  final TextEditingController controller;
  final String? placeholder;
  final bool autofocus;
  final Widget? prefix;

  @override
  State<_IdeaTextField> createState() => _IdeaTextFieldState();
}

class _IdeaTextFieldState extends State<_IdeaTextField> {
  static const Color _xBlue = Color(0xFF0A84FF);
  static const Color _xStroke = Color(0xFF343A46);
  static const Color _xStrokeHover = Color(0xFF4C5870);
  static const Color _xPanel = Color(0xFF252A33);
  static const Color _xPanelHover = Color(0xFF2D3340);
  static const Color _xHint = Color(0xFF99A1B3);
  bool _focused = false;
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    // Modern gradient border effect when focused
    final borderColor = _focused
        ? _xBlue
        : _hovered
            ? _xStrokeHover
            : _xStroke;

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        height: 40,
        decoration: BoxDecoration(
          color: _focused ? _xPanelHover : _xPanel,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: borderColor,
            width: _focused ? 1.5 : 1,
          ),
          boxShadow: _focused
              ? const [
                  BoxShadow(
                    color: Color(0x330A84FF),
                    blurRadius: 16,
                    offset: Offset(0, 0),
                  ),
                ]
              : const [],
        ),
        child: Row(
          children: [
            if (widget.prefix != null) ...[
              const SizedBox(width: 12),
              IconTheme(
                data: IconThemeData(
                  color: _focused ? _xBlue : _xHint,
                  size: 18,
                ),
                child: widget.prefix!,
              ),
            ],
            Expanded(
              child: Focus(
                onFocusChange: (f) => setState(() => _focused = f),
                child: TextField(
                  controller: widget.controller,
                  autofocus: widget.autofocus,
                  cursorColor: _xBlue,
                  cursorWidth: 1.5,
                  style: const TextStyle(
                    fontSize: 13,
                    color: Color(0xFFE6E8EE),
                    letterSpacing: 0.2,
                  ),
                  decoration: InputDecoration(
                    hintText: widget.placeholder,
                    hintStyle: TextStyle(
                      fontSize: 13,
                      color: _xHint,
                      letterSpacing: 0.2,
                    ),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    disabledBorder: InputBorder.none,
                    errorBorder: InputBorder.none,
                    focusedErrorBorder: InputBorder.none,
                    contentPadding: EdgeInsets.only(
                      left: widget.prefix != null ? 8 : 14,
                      right: 14,
                      top: 11,
                      bottom: 11,
                    ),
                    isDense: true,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _IdeaButton extends StatefulWidget {
  const _IdeaButton({
    required this.label,
    this.onTap,
    this.primary = false,
    this.secondary = false,
    this.icon,
  });
  final String label;
  final VoidCallback? onTap;
  final bool primary;
  final bool secondary;
  final IconData? icon;

  @override
  State<_IdeaButton> createState() => _IdeaButtonState();
}

class _IdeaButtonState extends State<_IdeaButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final disabled = widget.onTap == null;
    Color bgColor;
    Color textColor;
    Color borderColor;

    if (widget.primary) {
      bgColor = disabled
          ? const Color(0xFF375074)
          : _hovered
              ? const Color(0xFF2A98FF)
              : const Color(0xFF0A84FF);
      textColor = disabled ? const Color(0xFF98A9C5) : Colors.white;
      borderColor = bgColor;
    } else {
      bgColor = _hovered ? const Color(0xFF2D3340) : const Color(0xFF252A33);
      textColor = disabled ? const Color(0xFF6D778B) : const Color(0xFFE8ECF2);
      borderColor = const Color(0xFF343A46);
    }

    return MouseRegion(
      cursor: disabled ? SystemMouseCursors.basic : SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          height: 34,
          padding:
              EdgeInsets.symmetric(horizontal: widget.icon != null ? 16 : 20),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(9),
            border: Border.all(color: borderColor),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (widget.icon != null) ...[
                Icon(widget.icon, size: 16, color: textColor),
                const SizedBox(width: 8),
              ],
              Text(
                widget.label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: textColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _IdeaIconButton extends StatefulWidget {
  const _IdeaIconButton({required this.icon, required this.onTap});
  final IconData icon;
  final VoidCallback onTap;

  @override
  State<_IdeaIconButton> createState() => _IdeaIconButtonState();
}

class _IdeaIconButtonState extends State<_IdeaIconButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 30,
          height: 30,
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF2D3340) : const Color(0xFF252A33),
            borderRadius: BorderRadius.circular(9),
            border: Border.all(color: const Color(0xFF343A46)),
          ),
          child: Icon(
            widget.icon,
            size: 18,
            color: _hovered ? const Color(0xFF2A98FF) : const Color(0xFF99A1B3),
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// IDEA-style Window Controls (minimize, maximize, close)
// ============================================================================
class _IdeaWindowControls extends StatelessWidget {
  const _IdeaWindowControls();

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _WindowButton(
          icon: Icons.remove,
          onTap: appWindow.minimize,
          hoverColor: const Color(0xFF4A4D50),
        ),
        const SizedBox(width: 2),
        _WindowButton(
          icon: Icons.crop_square_rounded,
          onTap: appWindow.maximizeOrRestore,
          hoverColor: const Color(0xFF4A4D50),
        ),
        const SizedBox(width: 2),
        _WindowButton(
          icon: Icons.close,
          onTap: appWindow.close,
          hoverColor: const Color(0xFFE81123),
          hoverIconColor: Colors.white,
        ),
      ],
    );
  }
}

class _WindowButton extends StatefulWidget {
  const _WindowButton({
    required this.icon,
    required this.onTap,
    required this.hoverColor,
    this.hoverIconColor,
  });
  final IconData icon;
  final VoidCallback onTap;
  final Color hoverColor;
  final Color? hoverIconColor;

  @override
  State<_WindowButton> createState() => _WindowButtonState();
}

class _WindowButtonState extends State<_WindowButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 46,
          height: 32,
          color: _hovered ? widget.hoverColor : Colors.transparent,
          child: Icon(
            widget.icon,
            size: 14,
            color: _hovered && widget.hoverIconColor != null
                ? widget.hoverIconColor
                : const Color(0xFF8E8E8E),
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// IDEA-style Mini Button (small header buttons)
// ============================================================================
class _IdeaMiniButton extends StatefulWidget {
  const _IdeaMiniButton(
      {required this.icon, required this.onTap, this.tooltip});
  final IconData icon;
  final VoidCallback onTap;
  final String? tooltip;

  @override
  State<_IdeaMiniButton> createState() => _IdeaMiniButtonState();
}

class _IdeaMiniButtonState extends State<_IdeaMiniButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final button = MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 28,
          height: 28,
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF43454A) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Icon(widget.icon, size: 16, color: const Color(0xFF9D9D9D)),
        ),
      ),
    );
    if (widget.tooltip != null) {
      return Tooltip(message: widget.tooltip!, child: button);
    }
    return button;
  }
}

// ============================================================================
// IDEA-style Project Item (sidebar project list item)
// ============================================================================
class _IdeaProjectItem extends StatefulWidget {
  const _IdeaProjectItem({required this.project, required this.onTap});
  final Project project;
  final VoidCallback onTap;

  @override
  State<_IdeaProjectItem> createState() => _IdeaProjectItemState();
}

class _IdeaProjectItemState extends State<_IdeaProjectItem> {
  bool _hovered = false;

  IconData _frameworkIcon(String framework) {
    final f = framework.toLowerCase();
    if (f == "flutter") return Icons.flutter_dash_rounded;
    if (f == "react") return Icons.bubble_chart_rounded;
    if (f == "vue") return Icons.eco_outlined;
    if (f == "python") return Icons.code_rounded;
    if (f == "uniapp" || f == "uni-app") return Icons.web_rounded;
    if (f == "wechat_miniprogram") return Icons.chat_bubble_outline_rounded;
    if (f == "general") return Icons.developer_mode_rounded;
    return Icons.folder_rounded;
  }

  Color _frameworkColor(String framework) {
    final f = framework.toLowerCase();
    if (f == "flutter") return const Color(0xFF0175C2);
    if (f == "react") return const Color(0xFF61DAFB);
    if (f == "vue") return const Color(0xFF42B883);
    if (f == "python") return const Color(0xFF3776AB);
    if (f == "uniapp" || f == "uni-app") return const Color(0xFF2B9939);
    if (f == "wechat_miniprogram") return const Color(0xFF07C160);
    if (f == "general") return const Color(0xFF6366F1);
    return const Color(0xFF8E8E8E);
  }

  void _onHover(bool hovered) {
    setState(() => _hovered = hovered);
  }

  Future<void> _openTerminal() async {
    final path = _resolveWorkspacePath();
    if (path.isEmpty) return;
    final dir = Directory(path);
    if (!await dir.exists()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Workspace not found: $path")),
      );
      return;
    }
    try {
      if (Platform.isWindows) {
        try {
          await Process.start("wt.exe", ["-d", path], runInShell: true);
          return;
        } catch (_) {}
        try {
          await Process.start(
            "powershell.exe",
            ["-NoExit", "-Command", "Set-Location -LiteralPath \"$path\""],
            runInShell: true,
          );
          return;
        } catch (_) {}
        await Process.start(
          "cmd.exe",
          ["/c", "start", "", "cmd.exe", "/K", "cd /d \"$path\""],
          runInShell: true,
        );
        return;
      }
      if (Platform.isMacOS) {
        await Process.start("open", ["-a", "Terminal", path]);
        return;
      }
      if (Platform.isLinux) {
        await Process.start(
            "x-terminal-emulator", ["--working-directory=$path"]);
        return;
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to open terminal: $path")),
      );
    }
  }

  Future<void> _revealInExplorer() async {
    final path = _resolveWorkspacePath();
    if (path.isEmpty) return;
    final dir = Directory(path);
    if (!await dir.exists()) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Workspace not found: $path")),
      );
      return;
    }
    try {
      if (Platform.isWindows) {
        await Process.start("explorer.exe", [path]);
        return;
      }
      if (Platform.isMacOS) {
        await Process.start("open", [path]);
        return;
      }
      if (Platform.isLinux) {
        await Process.start("xdg-open", [path]);
        return;
      }
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to reveal folder: $path")),
      );
    }
  }

  String _resolveWorkspacePath() {
    final raw = widget.project.workspacePath.trim().isEmpty
        ? "./workspace/${widget.project.name}"
        : widget.project.workspacePath.trim();
    if (raw.isEmpty) return "";
    var value = raw;
    if (value.startsWith("~")) {
      final home = Platform.environment["USERPROFILE"] ??
          Platform.environment["HOME"] ??
          "";
      if (home.isNotEmpty) {
        value = "$home${value.substring(1)}";
      }
    }
    if (_isAbsolutePath(value)) return value;
    return Directory.current.uri
        .resolve(value)
        .toFilePath(windows: Platform.isWindows);
  }

  bool _isAbsolutePath(String path) {
    if (path.startsWith("/") || path.startsWith("\\")) return true;
    return RegExp(r"^[A-Za-z]:[\\/]").hasMatch(path);
  }

  Future<void> _showMoreActionsMenu() async {
    final selected = await showModalBottomSheet<String>(
      context: context,
      backgroundColor: const Color(0xFF252A33),
      builder: (ctx) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              dense: true,
              leading: const Icon(Icons.open_in_new_rounded,
                  color: Color(0xFFE6E8EE)),
              title: const Text("Open Project",
                  style: TextStyle(color: Color(0xFFE6E8EE))),
              onTap: () => Navigator.of(ctx).pop("open"),
            ),
            ListTile(
              dense: true,
              leading:
                  const Icon(Icons.terminal_rounded, color: Color(0xFFE6E8EE)),
              title: const Text("Open Terminal",
                  style: TextStyle(color: Color(0xFFE6E8EE))),
              onTap: () => Navigator.of(ctx).pop("terminal"),
            ),
            ListTile(
              dense: true,
              leading: const Icon(Icons.folder_open_rounded,
                  color: Color(0xFFE6E8EE)),
              title: const Text("Reveal in Explorer",
                  style: TextStyle(color: Color(0xFFE6E8EE))),
              onTap: () => Navigator.of(ctx).pop("reveal"),
            ),
          ],
        ),
      ),
    );
    if (!mounted || selected == null) return;
    if (selected == "open") {
      widget.onTap();
      return;
    }
    if (selected == "terminal") {
      await _openTerminal();
      return;
    }
    if (selected == "reveal") {
      await _revealInExplorer();
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.project;
    final color = _frameworkColor(p.framework);
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => _onHover(true),
      onExit: (_) => _onHover(false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF2A2A2A) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
            border: _hovered
                ? Border.all(color: color.withValues(alpha: 0.3), width: 1)
                : null,
          ),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  gradient: _hovered
                      ? LinearGradient(
                          colors: [
                            color.withValues(alpha: 0.3),
                            color.withValues(alpha: 0.15)
                          ],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        )
                      : null,
                  color: _hovered ? null : color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child:
                    Icon(_frameworkIcon(p.framework), size: 16, color: color),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            p.name,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              color: _hovered ? color : const Color(0xFFFFFFFF),
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (_hovered) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: color.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              p.framework.toUpperCase(),
                              style: TextStyle(
                                fontSize: 8,
                                fontWeight: FontWeight.w700,
                                color: color,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            p.workspacePath.isNotEmpty
                                ? p.workspacePath
                                : "~/projects/${p.name}",
                            style: const TextStyle(
                                fontSize: 11, color: Color(0xFF6E6E6E)),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              AnimatedOpacity(
                duration: const Duration(milliseconds: 120),
                opacity: _hovered ? 1 : 0.82,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _ProjectQuickAction(
                      icon: Icons.terminal,
                      tooltip: "Open Terminal",
                      onTap: _openTerminal,
                    ),
                    const SizedBox(width: 4),
                    _ProjectQuickAction(
                      icon: Icons.folder_open_outlined,
                      tooltip: "Reveal in Explorer",
                      onTap: _revealInExplorer,
                    ),
                    const SizedBox(width: 4),
                    _ProjectQuickAction(
                      icon: Icons.more_horiz,
                      tooltip: "More",
                      onTap: _showMoreActionsMenu,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProjectQuickAction extends StatefulWidget {
  const _ProjectQuickAction({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  State<_ProjectQuickAction> createState() => _ProjectQuickActionState();
}

class _ProjectQuickActionState extends State<_ProjectQuickAction> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: widget.tooltip,
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: widget.onTap,
          child: Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: _hovered ? const Color(0xFF3A3A3A) : Colors.transparent,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Icon(
              widget.icon,
              size: 14,
              color:
                  _hovered ? const Color(0xFF10A37F) : const Color(0xFF8E8E8E),
            ),
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// IDEA-style Action Row (action button with icon, label, description)
// ============================================================================
class _IdeaActionRow extends StatefulWidget {
  const _IdeaActionRow({
    required this.icon,
    required this.label,
    required this.description,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final String description;
  final VoidCallback onTap;

  @override
  State<_IdeaActionRow> createState() => _IdeaActionRowState();
}

class _IdeaActionRowState extends State<_IdeaActionRow> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            gradient: _hovered
                ? const LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [Color(0xFF2B3240), Color(0xFF242A35)],
                  )
                : const LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [Color(0xFF262B35), Color(0xFF212630)],
                  ),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color:
                  _hovered ? const Color(0xFF4A5C7C) : const Color(0xFF343A46),
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: const Color(0xFF0A84FF).withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(10),
                ),
                child:
                    Icon(widget.icon, size: 20, color: const Color(0xFF2A98FF)),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.label,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: Color(0xFFE8ECF2),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      widget.description,
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFF99A1B3)),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.arrow_forward_ios_rounded,
                size: 14,
                color: _hovered
                    ? const Color(0xFF2A98FF)
                    : const Color(0xFF6F7A8F),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

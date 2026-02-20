import "package:flutter/material.dart";
import "package:rebot_agentgpt/app_state.dart";
import "package:rebot_agentgpt/theme/app_tokens.dart";

class FileExplorer extends StatelessWidget {
  const FileExplorer({
    super.key,
    required this.workspacePath,
    required this.nodes,
    required this.activePath,
    required this.expandedDirs,
    required this.isFileWriting,
    required this.onToggleDir,
    required this.onOpenFile,
    this.onDeleteFile,
  });

  final String workspacePath;
  final List<FileNode> nodes;
  final String activePath;
  final Set<String> expandedDirs;
  final bool Function(String path) isFileWriting;
  final ValueChanged<String> onToggleDir;
  final ValueChanged<String> onOpenFile;
  final Future<void> Function(String path)? onDeleteFile;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: AppTokens.bg,
      child: Column(
        children: [
          Container(
            height: 44,
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppTokens.borderSubtle)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text("EXPLORER", style: AppTokens.text(size: 11, color: AppTokens.textTertiary, weight: FontWeight.w700)),
                Text(
                  workspacePath,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppTokens.text(size: 10, color: AppTokens.textDisabled),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              children: _buildTree(nodes),
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildTree(List<FileNode> nodes, {int depth = 0}) {
    final items = <Widget>[];
    final sorted = [...nodes]..sort((a, b) {
        if (a.isDir && !b.isDir) return -1;
        if (!a.isDir && b.isDir) return 1;
        return a.name.toLowerCase().compareTo(b.name.toLowerCase());
      });
    for (final node in sorted) {
      final expanded = expandedDirs.contains(node.path);
      final active = node.path == activePath;
      items.add(_FileNodeTile(
        node: node,
        depth: depth,
        expanded: expanded,
        active: active,
        writing: !node.isDir && (node.isGenerating || isFileWriting(node.path)),
        path: node.path,
        isDir: node.isDir,
        onDeleteFile: onDeleteFile,
        onTap: () => node.isDir ? onToggleDir(node.path) : onOpenFile(node.path),
      ));
      if (node.isDir && expanded && node.children.isNotEmpty) {
        items.addAll(_buildTree(node.children, depth: depth + 1));
      }
    }
    return items;
  }
}

class _FileNodeTile extends StatelessWidget {
  const _FileNodeTile({
    required this.path,
    required this.isDir,
    required this.node,
    required this.depth,
    required this.expanded,
    required this.active,
    required this.writing,
    required this.onTap,
    this.onDeleteFile,
  });

  final String path;
  final bool isDir;
  final FileNode node;
  final int depth;
  final bool expanded;
  final bool active;
  final bool writing;
  final VoidCallback onTap;
  final Future<void> Function(String path)? onDeleteFile;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      onSecondaryTapDown: isDir || onDeleteFile == null
          ? null
          : (details) async {
              final selected = await showMenu<String>(
                context: context,
                position: RelativeRect.fromLTRB(
                  details.globalPosition.dx,
                  details.globalPosition.dy,
                  details.globalPosition.dx,
                  details.globalPosition.dy,
                ),
                color: AppTokens.surfaceElevated,
                items: const [
                  PopupMenuItem(
                    value: "delete",
                    child: Text("Delete", style: TextStyle(fontSize: 13, color: AppTokens.textSecondary)),
                  ),
                ],
              );
              if (selected == "delete") {
                await onDeleteFile!(path);
              }
            },
      child: Container(
        padding: EdgeInsets.fromLTRB(10 + depth * 14, 4, 8, 4),
        decoration: BoxDecoration(
          color: active ? AppTokens.primary.withOpacity(0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(AppTokens.radiusSm),
        ),
        child: Row(
          children: [
            if (node.isDir)
              Icon(expanded ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_right, size: 14, color: AppTokens.textTertiary)
            else
              const SizedBox(width: 14),
            const SizedBox(width: 2),
            Icon(
              node.isDir ? (expanded ? Icons.folder_open : Icons.folder) : Icons.description_outlined,
              size: 14,
              color: AppTokens.textTertiary,
            ),
            const SizedBox(width: 6),
            if (writing) ...[
              const SizedBox(width: 10, height: 10, child: CircularProgressIndicator(strokeWidth: 1.5)),
              const SizedBox(width: 6),
            ],
            Expanded(
              child: Text(
                node.name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppTokens.text(size: 12, color: active ? AppTokens.textPrimary : AppTokens.textSecondary),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

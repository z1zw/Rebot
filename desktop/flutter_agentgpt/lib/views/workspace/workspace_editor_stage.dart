import "dart:async";
import "dart:math" as math;

import "package:flutter/material.dart";
import "package:provider/provider.dart";
import "package:rebot_agentgpt/app_state.dart";
import "package:rebot_agentgpt/views/editor/ai_diff_view.dart";
import "package:rebot_agentgpt/views/editor/code_editor.dart";
import "package:rebot_agentgpt/views/editor/empty_state.dart";
import "package:rebot_agentgpt/views/editor/editor_mode_bar.dart";
import "package:rebot_agentgpt/views/editor/editor_tabs.dart";
import "package:rebot_agentgpt/views/editor/file_explorer.dart";
import "package:rebot_agentgpt/views/workspace/editor_bottom_panel.dart";

class WorkspaceEditorStage extends StatefulWidget {
  const WorkspaceEditorStage({super.key});

  @override
  State<WorkspaceEditorStage> createState() => _WorkspaceEditorStageState();
}

class _WorkspaceEditorStageState extends State<WorkspaceEditorStage> {
  static const Color _xSurface = Color(0xFF1D1E22);
  static const Color _xPanel = Color(0xFF22242A);
  static const Color _xPanel2 = Color(0xFF2A2D34);
  static const Color _xStroke = Color(0xFF343944);
  static const Color _xBlue = Color(0xFF0A84FF);
  final TextEditingController _editorController = TextEditingController();
  final ScrollController _editorScrollController = ScrollController();
  String _lastSyncedPath = "";
  String _lastSyncedContent = "";
  bool _dirty = false;
  bool _useMonaco = true;
  bool _showAiDiff = false;
  bool _bottomOpen = true;
  String _bottomTab = "terminal";
  final Set<String> _expandedDirs = <String>{};
  Timer? _autoSaveTimer;

  @override
  void dispose() {
    _autoSaveTimer?.cancel();
    _editorController.dispose();
    _editorScrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    context.select<AppState, int>((s) => Object.hash(s.openFileTabs.length, s.activeFilePath, s.activeFileContent.length, s.suppressEditorRefresh));
    final state = context.read<AppState>();
    _syncEditorFromState(state);
    return Column(
      children: [
        _buildTabBar(state),
        Expanded(
          child: Row(
            children: [
              SizedBox(
                width: 240,
                child: FileExplorer(
                  workspacePath: state.activeWorkspacePath,
                  nodes: state.fileTree,
                  activePath: state.activeFilePath,
                  expandedDirs: _expandedDirs,
                  isFileWriting: state.isFileWriting,
                  onToggleDir: (path) {
                    setState(() {
                      if (_expandedDirs.contains(path)) {
                        _expandedDirs.remove(path);
                      } else {
                        _expandedDirs.add(path);
                      }
                    });
                  },
                  onOpenFile: (path) => state.readFile(path),
                  onDeleteFile: (path) async {
                    await state.deleteFile(path);
                    await state.loadFiles();
                  },
                ),
              ),
              Expanded(
                child: Column(
                  children: [
                    Expanded(
                      child: state.activeFilePath.isEmpty
                          ? EditorEmptyState(
                              title: "Start building with AI",
                              description: "Open a file from explorer, or run generation first.",
                              primaryLabel: "Search Files",
                              onPrimary: () => _showSearchFilesDialog(state),
                              secondaryLabel: "Run Build",
                              onSecondary: () => unawaited(_runPreview(state)),
                            )
                          : _buildEditor(state),
                    ),
                    EditorBottomPanel(
                      open: _bottomOpen,
                      tab: _bottomTab,
                      onTabChange: (tab) => setState(() {
                        _bottomTab = tab;
                        _bottomOpen = true;
                      }),
                      onToggleOpen: () => setState(() => _bottomOpen = !_bottomOpen),
                      terminalLogs: state.consoleLogs,
                      warningCount: state.warningCount,
                      executionProgress: state.executionProgress,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildTabBar(AppState state) {
    if (state.openFileTabs.isEmpty) {
      return Container(
        height: 38,
        alignment: Alignment.centerLeft,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: const BoxDecoration(
          color: _xPanel,
          border: Border(bottom: BorderSide(color: _xStroke)),
        ),
        child: const Text("No file opened", style: TextStyle(color: Color(0xFFA0A8B8), fontSize: 12)),
      );
    }
    return Container(
      height: 38,
      decoration: const BoxDecoration(
        color: _xPanel,
        border: Border(bottom: BorderSide(color: _xStroke)),
      ),
      child: EditorTabs(tabs: state.openFileTabs, activePath: state.activeFilePath, isDirty: _dirty, onTap: state.switchOpenFileTab, onClose: state.closeOpenFileTab),
    );
  }

  Widget _buildEditor(AppState state) {
    final lineCount = _editorController.text.split("\n").length;
    final language = _guessLanguage(state.activeFilePath);
    return Column(
      children: [
        Container(
          height: 40,
          decoration: const BoxDecoration(
            color: _xPanel2,
            border: Border(bottom: BorderSide(color: _xStroke)),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  state.activeFilePath,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Color(0xFFE6E8EE), fontSize: 12),
                ),
              ),
              if (_dirty)
                OutlinedButton(
                  onPressed: () => _save(state),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: _xStroke),
                    foregroundColor: const Color(0xFFE6E8EE),
                    backgroundColor: const Color(0xFF252830),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                  ),
                  child: const Text("Save"),
                ),
              const SizedBox(width: 8),
              FilledButton(
                onPressed: () => unawaited(_runPreview(state)),
                style: FilledButton.styleFrom(
                  backgroundColor: _xBlue,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
                ),
                child: const Text("Run"),
              ),
            ],
          ),
        ),
        EditorModeBar(
          useMonaco: _useMonaco,
          showAiDiff: _showAiDiff,
          onMonacoChanged: (v) => setState(() => _useMonaco = v),
          onShowCode: () => setState(() => _showAiDiff = false),
          onShowDiff: () => setState(() => _showAiDiff = true),
        ),
        Expanded(
          child: _showAiDiff
              ? AiDiffView(
                  baseContent: _currentAiBaseline(state),
                  currentContent: _editorController.text,
                  onApplyContent: (content) => _applyContent(state, content),
                )
              : (_useMonaco
                  ? MonacoPreview(
                      content: _editorController.text,
                      language: language,
                      onChanged: (value) => _onEditorChanged(state, value),
                      onUnavailable: () {
                        if (!_useMonaco || !mounted) return;
                        setState(() => _useMonaco = false);
                        ScaffoldMessenger.maybeOf(context)?.showSnackBar(const SnackBar(content: Text("Monaco unavailable, switched to native editor.")));
                      },
                    )
                  : Row(
                      children: [
                        Container(
                          width: 52,
                          color: const Color(0xFF24272D),
                          child: ListView.builder(
                            itemCount: math.max(lineCount, 1),
                            itemBuilder: (_, i) => SizedBox(
                              height: 21,
                              child: Align(
                                alignment: Alignment.centerRight,
                                child: Padding(
                                  padding: const EdgeInsets.only(right: 8),
                                  child: Text("${i + 1}", style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 12, color: Color(0xFF6E7482))),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const VerticalDivider(width: 1, color: _xStroke),
                        Expanded(
                          child: TextField(
                            controller: _editorController,
                            scrollController: _editorScrollController,
                            maxLines: null,
                            onChanged: (value) => _onEditorChanged(state, value),
                            cursorColor: _xBlue,
                            style: const TextStyle(fontFamily: "JetBrains Mono", fontSize: 13, height: 1.6, color: Color(0xFFB8C2D2)),
                            decoration: const InputDecoration(
                              border: InputBorder.none,
                              enabledBorder: InputBorder.none,
                              focusedBorder: InputBorder.none,
                              disabledBorder: InputBorder.none,
                              errorBorder: InputBorder.none,
                              focusedErrorBorder: InputBorder.none,
                              filled: true,
                              fillColor: _xSurface,
                              contentPadding: EdgeInsets.all(12),
                            ),
                          ),
                        ),
                      ],
                    )),
        ),
      ],
    );
  }

  void _onEditorChanged(AppState state, String value) {
    _dirty = value != _lastSyncedContent;
    state.updateActiveContent(value);
    _scheduleAutoSave(state);
    if (mounted) setState(() {});
  }

  void _applyContent(AppState state, String content) {
    _editorController.value = TextEditingValue(text: content, selection: TextSelection.collapsed(offset: content.length));
    _onEditorChanged(state, content);
  }

  void _syncEditorFromState(AppState state) {
    final pathChanged = state.activeFilePath != _lastSyncedPath;
    if (state.suppressEditorRefresh && !pathChanged) return;
    final contentChanged = state.activeFileContent != _lastSyncedContent && !_dirty;
    if (!pathChanged && !contentChanged) return;
    _lastSyncedPath = state.activeFilePath;
    _lastSyncedContent = state.activeFileContent;
    _dirty = false;
    _editorController.value = TextEditingValue(text: state.activeFileContent, selection: TextSelection.collapsed(offset: state.activeFileContent.length));
  }

  String _currentAiBaseline(AppState state) {
    final path = state.activeFilePath.trim().replaceAll("\\", "/");
    if (path.isEmpty) return _lastSyncedContent;
    for (final f in state.generatedFiles.reversed) {
      if (f.path.trim().replaceAll("\\", "/") == path && f.content.trim().isNotEmpty) return f.content;
    }
    return _lastSyncedContent;
  }

  String _guessLanguage(String path) {
    final lower = path.toLowerCase();
    if (lower.endsWith(".dart")) return "dart";
    if (lower.endsWith(".ts")) return "typescript";
    if (lower.endsWith(".js")) return "javascript";
    if (lower.endsWith(".json")) return "json";
    if (lower.endsWith(".html")) return "html";
    if (lower.endsWith(".css")) return "css";
    if (lower.endsWith(".py")) return "python";
    if (lower.endsWith(".md")) return "markdown";
    if (lower.endsWith(".yaml") || lower.endsWith(".yml")) return "yaml";
    return "plaintext";
  }

  Future<void> _save(AppState state) async {
    await state.saveFile();
    _lastSyncedContent = state.activeFileContent;
    _dirty = false;
    if (mounted) setState(() {});
  }

  void _scheduleAutoSave(AppState state) {
    if (state.activeFilePath.trim().isEmpty) return;
    _autoSaveTimer?.cancel();
    _autoSaveTimer = Timer(const Duration(milliseconds: 900), () {
      if (!_dirty) return;
      unawaited(_save(state));
    });
  }

  Future<void> _showSearchFilesDialog(AppState state) async {
    await state.loadFiles();
    if (!mounted) return;
    final all = <String>[];
    void collect(List<FileNode> nodes) {
      for (final n in nodes) {
        if (n.isDir) {
          collect(n.children);
        } else {
          all.add(n.path);
        }
      }
    }
    collect(state.fileTree);
    final query = await showDialog<String>(
      context: context,
      builder: (ctx) {
        final c = TextEditingController();
        var filtered = List<String>.from(all);
        return StatefulBuilder(builder: (ctx, setDlg) {
          return AlertDialog(
            title: const Text("Search Files"),
            content: SizedBox(
              width: 560,
              height: 360,
              child: Column(
                children: [
                  TextField(
                    controller: c,
                    autofocus: true,
                    onChanged: (v) {
                      final q = v.trim().toLowerCase();
                      setDlg(() {
                        filtered = q.isEmpty
                            ? List<String>.from(all)
                            : all.where((p) => p.toLowerCase().contains(q)).toList();
                      });
                    },
                    onSubmitted: (v) => Navigator.of(ctx).pop(v),
                  ),
                  const SizedBox(height: 10),
                  Expanded(
                    child: filtered.isEmpty
                        ? const Center(child: Text("No matching files"))
                        : ListView.builder(
                            itemCount: filtered.length,
                            itemBuilder: (_, i) => ListTile(
                              dense: true,
                              title: Text(filtered[i], maxLines: 1, overflow: TextOverflow.ellipsis),
                              onTap: () => Navigator.of(ctx).pop(filtered[i]),
                            ),
                          ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(onPressed: () => Navigator.of(ctx).pop(""), child: const Text("Cancel")),
              FilledButton(onPressed: () => Navigator.of(ctx).pop(c.text), child: const Text("Open")),
            ],
          );
        });
      },
    );
    final q = (query ?? "").trim().toLowerCase();
    if (q.isEmpty) return;
    final exact = all.firstWhere((p) => p == query, orElse: () => "");
    final match = exact.isNotEmpty ? exact : all.firstWhere((p) => p.toLowerCase().contains(q), orElse: () => "");
    if (match.isNotEmpty) {
      await state.readFile(match);
      return;
    }
    if (mounted) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(content: Text("No matching file found.")),
      );
    }
  }

  Future<void> _runPreview(AppState state) async {
    final result = await state.startFrameworkServer(framework: state.selectedFramework);
    final ok = result["running"] == true;
    if (!mounted) return;
    if (ok) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(content: Text("Preview started.")),
      );
      return;
    }
    final reason = (result["reason"] ?? "unknown").toString();
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      SnackBar(content: Text("Run failed: $reason")),
    );
  }
}

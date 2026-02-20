import "dart:async";

import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:multi_split_view/multi_split_view.dart";
import "package:provider/provider.dart";
import "package:rebot_agentgpt/views/agents_view.dart";
import "package:rebot_agentgpt/views/devserver_view.dart";
import "package:rebot_agentgpt/views/git_view.dart";
import "package:rebot_agentgpt/views/history_view.dart";
import "package:rebot_agentgpt/views/plugin_market_view.dart";
import "package:rebot_agentgpt/views/template_market_view.dart";
// ignore: uri_does_not_exist
import "package:rebot_agentgpt/views/right_panel.dart";
import "package:rebot_agentgpt/views/settings_view.dart";
import "package:rebot_agentgpt/views/workspace/left_pane.dart";
import "package:rebot_agentgpt/views/workspace/nav_rail.dart";
import "package:rebot_agentgpt/views/workspace/top_header.dart";
import "package:rebot_agentgpt/views/workspace/workspace_editor_stage.dart";

import "../app_state.dart";

class Workspace extends StatefulWidget {
  const Workspace({super.key});

  @override
  State<Workspace> createState() => _WorkspaceState();
}

class _WorkspaceState extends State<Workspace> {
  bool _settingsOpen = false;
  String _leftPanel = "chat";
  String _activeView = "workspace";
  String _rightPanelTab = "preview";
  String _selectedDevice = "iPhone 15 Pro";
  int _lastRightPanelSignal = 0;
  String _cloneStatus = "Clone idle";
  final List<_CloneHistoryItem> _cloneHistory = <_CloneHistoryItem>[];
  late final MultiSplitViewController _splitController;

  @override
  void initState() {
    super.initState();
    _splitController = MultiSplitViewController(
      areas: [Area(size: 340, min: 280), Area(flex: 0.6, min: 460), Area(size: 420, min: 340)],
    );
  }

  @override
  void dispose() {
    _splitController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final project = context.select<AppState, Project?>((s) => s.activeProject);
    final preferredSignal = context.select<AppState, int>((s) => s.preferredRightPanelSignal);
    final preferredTab = context.select<AppState, String>((s) => s.preferredRightPanelTab);
    final state = context.read<AppState>();
    final status = context.select<AppState, String>((s) => s.status);
    final executionStatus = context.select<AppState, String>((s) => s.executionStatus);
    final executionProgress = context.select<AppState, String>((s) => s.executionProgress);

    if (preferredSignal != _lastRightPanelSignal) {
      _lastRightPanelSignal = preferredSignal;
      _rightPanelTab = preferredTab;
    }
    if (project == null) return const SizedBox.shrink();
    final running = status == "running" || executionStatus == "running";

    return Shortcuts(
      shortcuts: const <ShortcutActivator, Intent>{
        SingleActivator(LogicalKeyboardKey.backquote, control: true): _OpenConsoleIntent(),
        SingleActivator(LogicalKeyboardKey.keyN, control: true, shift: true): _OpenNetworkIntent(),
        SingleActivator(LogicalKeyboardKey.digit1, control: true): _OpenChatIntent(),
        SingleActivator(LogicalKeyboardKey.digit2, control: true): _OpenCodeIntent(),
        SingleActivator(LogicalKeyboardKey.digit3, control: true): _OpenDevServerIntent(),
        SingleActivator(LogicalKeyboardKey.digit4, control: true): _OpenPluginsIntent(),
        SingleActivator(LogicalKeyboardKey.digit5, control: true): _OpenGitIntent(),
        SingleActivator(LogicalKeyboardKey.digit6, control: true): _OpenTemplatesIntent(),
        SingleActivator(LogicalKeyboardKey.comma, control: true): _OpenSettingsIntent(),
      },
      child: Actions(
        actions: <Type, Action<Intent>>{
          _OpenConsoleIntent: CallbackAction<_OpenConsoleIntent>(
            onInvoke: (_) {
              _openConsole(state);
              return null;
            },
          ),
          _OpenNetworkIntent: CallbackAction<_OpenNetworkIntent>(
            onInvoke: (_) {
              _openNetwork(state);
              return null;
            },
          ),
          _OpenChatIntent: CallbackAction<_OpenChatIntent>(
            onInvoke: (_) {
              setState(() {
                _activeView = "workspace";
                _leftPanel = "chat";
                _settingsOpen = false;
              });
              return null;
            },
          ),
          _OpenCodeIntent: CallbackAction<_OpenCodeIntent>(
            onInvoke: (_) {
              setState(() {
                _activeView = "workspace";
                _leftPanel = "code";
                _settingsOpen = false;
              });
              return null;
            },
          ),
          _OpenDevServerIntent: CallbackAction<_OpenDevServerIntent>(
            onInvoke: (_) {
              setState(() {
                _activeView = "devserver";
                _settingsOpen = false;
              });
              return null;
            },
          ),
          _OpenSettingsIntent: CallbackAction<_OpenSettingsIntent>(
            onInvoke: (_) {
              setState(() => _settingsOpen = true);
              return null;
            },
          ),
          _OpenPluginsIntent: CallbackAction<_OpenPluginsIntent>(
            onInvoke: (_) {
              setState(() {
                _activeView = "plugins";
                _settingsOpen = false;
              });
              return null;
            },
          ),
          _OpenGitIntent: CallbackAction<_OpenGitIntent>(
            onInvoke: (_) {
              setState(() {
                _activeView = "git";
                _settingsOpen = false;
              });
              return null;
            },
          ),
          _OpenTemplatesIntent: CallbackAction<_OpenTemplatesIntent>(
            onInvoke: (_) {
              setState(() {
                _activeView = "templates";
                _settingsOpen = false;
              });
              return null;
            },
          ),
        },
        child: Focus(
          autofocus: true,
          child: Scaffold(
            body: Column(
              children: [
                WorkspaceTopHeader(
            projectName: project.name,
            buildStatus: executionProgress.isEmpty ? executionStatus : executionProgress,
            running: running,
            cloneStatus: _cloneStatus,
            rightPanelTab: _rightPanelTab,
            onBack: state.closeProject,
            onNewConversation: state.createConversation,
            onToggleSidebar: () => setState(() => _leftPanel = _leftPanel == "chat" ? "code" : "chat"),
            onRun: running ? state.cancelActiveRun : () => unawaited(_runPreview(state)),
            onRefresh: () async {
              await state.forceFileSynchronization();
              state.triggerPreviewReload();
            },
            onGitClone: () => _showGitCloneDialog(state),
            onOpenGit: () => setState(() {
              _activeView = "git";
              _settingsOpen = false;
            }),
            onRetryClone: () => _retryLastClone(state),
            onConsole: () => _openConsole(state),
            onNetwork: () => _openNetwork(state),
          ),
          Expanded(
            child: Row(
              children: [
                WorkspaceNavRail(
                  leftPanel: _leftPanel,
                  activeView: _activeView,
                  settingsOpen: _settingsOpen,
                  onChat: () => setState(() {
                    _activeView = "workspace";
                    _leftPanel = "chat";
                  }),
                  onCode: () => setState(() {
                    _activeView = "workspace";
                    _leftPanel = "code";
                  }),
                  onSettings: () => setState(() => _settingsOpen = true),
                  onViewChange: (v) => setState(() {
                    _activeView = v;
                    _settingsOpen = false;
                  }),
                ),
                Expanded(
                  child: Stack(
                    children: [
                      _activeView == "workspace"
                          ? MultiSplitView(
                              axis: Axis.horizontal,
                              controller: _splitController,
                              builder: (context, area) {
                                switch (area.index) {
                                  case 0:
                                    return WorkspaceLeftPane(mode: _leftPanel, path: state.activeFilePath, content: state.activeFileContent, onNewConversation: state.createConversation);
                                  case 1:
                                    return const WorkspaceEditorStage();
                                  default:
                                    // ignore: undefined_method
                                    return RightPanel(
                                      selectedDevice: _selectedDevice,
                                      onDeviceChanged: (v) => setState(() => _selectedDevice = v),
                                      activeTab: _rightPanelTab,
                                      onActiveTabChanged: (v) => setState(() {
                                        _rightPanelTab = v;
                                        state.setPreferredRightPanelTab(v);
                                      }),
                                    );
                                }
                              },
                            )
                          : _activeView == "devserver"
                              ? const DevServerView()
                          : _activeView == "history"
                                  ? const HistoryView()
                                  : _activeView == "agents"
                                      ? const AgentsView()
                                      : _activeView == "plugins"
                                          ? const PluginMarketView()
                                          : _activeView == "templates"
                                              ? const TemplateMarketView()
                                          : _activeView == "git"
                                              ? const GitView()
                                      : const SizedBox.shrink(),
                      if (_settingsOpen) _SettingsOverlay(onClose: () => setState(() => _settingsOpen = false)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          _StatusBar(state: state),
        ],
            ),
          ),
        ),
      ),
    );
  }

  void _openConsole(AppState state) {
    setState(() {
      _activeView = "workspace";
      _rightPanelTab = "console";
      _settingsOpen = false;
    });
    state.setPreferredRightPanelTab("console");
  }

  void _openNetwork(AppState state) {
    setState(() {
      _activeView = "workspace";
      _rightPanelTab = "network";
      _settingsOpen = false;
    });
    state.setPreferredRightPanelTab("network");
  }

  Future<void> _runPreview(AppState state) async {
    final result = await state.runPreviewWithSelfHeal(framework: state.selectedFramework);
    final ok = result["running"] == true;
    if (!mounted) return;
    if (ok) {
      setState(() {
        _activeView = "workspace";
        _rightPanelTab = "preview";
        _settingsOpen = false;
      });
      state.setPreferredRightPanelTab("preview");
      if (state.isWebPreviewFramework(state.selectedFramework)) {
        await state.openPreviewInExternalBrowser(url: state.previewUrl);
        if (!mounted) return;
      }
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(content: Text("Preview started.")),
      );
      return;
    }
    final reason = state.previewFailureMessage(result);
    final logs = (result["devserver_logs"] ?? "").toString();
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      SnackBar(
        content: Text("Run failed: $reason"),
        action: logs.trim().isEmpty
            ? null
            : SnackBarAction(
                label: "View Logs",
                onPressed: () => _showDevserverLogsDialog(logs),
              ),
      ),
    );
  }

  Future<void> _showDevserverLogsDialog(String logs) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E222A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFF343A46)),
        ),
        title: const Text("Devserver Logs"),
        content: SizedBox(
          width: 860,
          height: 520,
          child: SingleChildScrollView(
            child: SelectableText(
              logs.trim().isEmpty ? "No logs available." : logs,
              style: const TextStyle(
                fontFamily: "JetBrains Mono",
                fontSize: 12,
                color: Color(0xFFDCE4F2),
                height: 1.35,
              ),
            ),
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(ctx).pop(), child: const Text("Close")),
        ],
      ),
    );
  }

  Future<void> _showGitCloneDialog(AppState state) async {
    final repoCtrl = TextEditingController();
    final branchCtrl = TextEditingController();
    final destCtrl = TextEditingController();
    String framework = state.selectedFramework;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              backgroundColor: const Color(0xFF22242A),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: const BorderSide(color: Color(0xFF3A3F48)),
              ),
              title: const Text("Git Clone Project"),
              content: SizedBox(
                width: 520,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextField(
                      controller: repoCtrl,
                      autofocus: true,
                      style: const TextStyle(color: Color(0xFFE6E8EE)),
                      decoration: const InputDecoration(
                        labelText: "Repository URL",
                        hintText: "https://github.com/org/repo.git",
                        filled: true,
                        fillColor: Color(0xFF2A2C31),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)),
                          borderSide: BorderSide(color: Color(0xFF3A3F48)),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)),
                          borderSide: BorderSide(color: Color(0xFF3A3F48)),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)),
                          borderSide: BorderSide(color: Color(0xFF0A84FF), width: 1.4),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: branchCtrl,
                            style: const TextStyle(color: Color(0xFFE6E8EE)),
                            decoration: const InputDecoration(
                              labelText: "Branch (optional)",
                              filled: true,
                              fillColor: Color(0xFF2A2C31),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.all(Radius.circular(10)),
                                borderSide: BorderSide(color: Color(0xFF3A3F48)),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.all(Radius.circular(10)),
                                borderSide: BorderSide(color: Color(0xFF3A3F48)),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.all(Radius.circular(10)),
                                borderSide: BorderSide(color: Color(0xFF0A84FF), width: 1.4),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: TextField(
                            controller: destCtrl,
                            style: const TextStyle(color: Color(0xFFE6E8EE)),
                            decoration: const InputDecoration(
                              labelText: "Destination (optional)",
                              filled: true,
                              fillColor: Color(0xFF2A2C31),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.all(Radius.circular(10)),
                                borderSide: BorderSide(color: Color(0xFF3A3F48)),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.all(Radius.circular(10)),
                                borderSide: BorderSide(color: Color(0xFF3A3F48)),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.all(Radius.circular(10)),
                                borderSide: BorderSide(color: Color(0xFF0A84FF), width: 1.4),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      initialValue: framework,
                      items: const [
                        DropdownMenuItem(value: "flutter", child: Text("flutter")),
                        DropdownMenuItem(value: "react", child: Text("react")),
                        DropdownMenuItem(value: "vue", child: Text("vue")),
                        DropdownMenuItem(value: "nextjs", child: Text("nextjs")),
                        DropdownMenuItem(value: "python", child: Text("python")),
                      ],
                      onChanged: (v) => setDialogState(() => framework = v ?? "flutter"),
                      dropdownColor: const Color(0xFF2A2C31),
                      style: const TextStyle(color: Color(0xFFE6E8EE)),
                      decoration: const InputDecoration(
                        labelText: "Framework",
                        filled: true,
                        fillColor: Color(0xFF2A2C31),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)),
                          borderSide: BorderSide(color: Color(0xFF3A3F48)),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)),
                          borderSide: BorderSide(color: Color(0xFF3A3F48)),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.all(Radius.circular(10)),
                          borderSide: BorderSide(color: Color(0xFF0A84FF), width: 1.4),
                        ),
                      ),
                    ),
                    if (_cloneHistory.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: Text("Recent", style: Theme.of(ctx).textTheme.labelLarge),
                      ),
                      const SizedBox(height: 6),
                      SizedBox(
                        height: 140,
                        child: ListView.builder(
                          itemCount: _cloneHistory.length,
                          itemBuilder: (_, i) {
                            final item = _cloneHistory[i];
                            return ListTile(
                              dense: true,
                              leading: Icon(item.ok ? Icons.check_circle_outline : Icons.error_outline, color: item.ok ? const Color(0xFF22C55E) : const Color(0xFFEF4444)),
                              title: Text(item.repo, maxLines: 1, overflow: TextOverflow.ellipsis),
                              subtitle: Text("branch=${item.branch.isEmpty ? 'default' : item.branch} | ${item.framework}"),
                              onTap: () {
                                repoCtrl.text = item.repo;
                                branchCtrl.text = item.branch;
                                destCtrl.text = item.destination;
                                setDialogState(() => framework = item.framework);
                              },
                              trailing: IconButton(
                                icon: const Icon(Icons.replay_rounded),
                                tooltip: "Retry",
                                onPressed: () {
                                  Navigator.of(ctx).pop(true);
                                  _retryCloneItem(state, item);
                                },
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
                FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Clone")),
              ],
            );
          },
        );
      },
    );
    if (ok != true) return;
    if (mounted) {
      setState(() => _cloneStatus = "Cloning...");
    }
    try {
      await state.cloneProjectFromGit(
        repoUrl: repoCtrl.text.trim(),
        destination: destCtrl.text.trim(),
        framework: framework,
        branch: branchCtrl.text.trim(),
      );
      if (!mounted) return;
      _pushCloneHistory(
        repo: repoCtrl.text.trim(),
        branch: branchCtrl.text.trim(),
        destination: destCtrl.text.trim(),
        framework: framework,
        ok: true,
      );
      setState(() => _cloneStatus = "Clone success");
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(const SnackBar(content: Text("Clone completed and project opened.")));
    } catch (e) {
      if (!mounted) return;
      _pushCloneHistory(
        repo: repoCtrl.text.trim(),
        branch: branchCtrl.text.trim(),
        destination: destCtrl.text.trim(),
        framework: framework,
        ok: false,
      );
      setState(() => _cloneStatus = "Clone failed");
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text("Clone failed: $e")));
    }
  }

  Future<void> _retryLastClone(AppState state) async {
    if (_cloneHistory.isEmpty) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(const SnackBar(content: Text("No clone history to retry.")));
      return;
    }
    await _retryCloneItem(state, _cloneHistory.first);
  }

  Future<void> _retryCloneItem(AppState state, _CloneHistoryItem item) async {
    if (mounted) setState(() => _cloneStatus = "Retry cloning...");
    try {
      await state.cloneProjectFromGit(
        repoUrl: item.repo,
        destination: item.destination,
        framework: item.framework,
        branch: item.branch,
      );
      if (!mounted) return;
      _pushCloneHistory(
        repo: item.repo,
        branch: item.branch,
        destination: item.destination,
        framework: item.framework,
        ok: true,
      );
      setState(() => _cloneStatus = "Retry success");
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(const SnackBar(content: Text("Retry clone completed.")));
    } catch (e) {
      if (!mounted) return;
      _pushCloneHistory(
        repo: item.repo,
        branch: item.branch,
        destination: item.destination,
        framework: item.framework,
        ok: false,
      );
      setState(() => _cloneStatus = "Retry failed");
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text("Retry clone failed: $e")));
    }
  }

  void _pushCloneHistory({
    required String repo,
    required String branch,
    required String destination,
    required String framework,
    required bool ok,
  }) {
    final item = _CloneHistoryItem(
      repo: repo,
      branch: branch,
      destination: destination,
      framework: framework,
      ok: ok,
      at: DateTime.now(),
    );
    _cloneHistory.insert(0, item);
    if (_cloneHistory.length > 8) {
      _cloneHistory.removeRange(8, _cloneHistory.length);
    }
  }
}

class _OpenConsoleIntent extends Intent {
  const _OpenConsoleIntent();
}

class _OpenNetworkIntent extends Intent {
  const _OpenNetworkIntent();
}

class _OpenChatIntent extends Intent {
  const _OpenChatIntent();
}

class _OpenCodeIntent extends Intent {
  const _OpenCodeIntent();
}

class _OpenDevServerIntent extends Intent {
  const _OpenDevServerIntent();
}

class _OpenSettingsIntent extends Intent {
  const _OpenSettingsIntent();
}

class _OpenPluginsIntent extends Intent {
  const _OpenPluginsIntent();
}

class _OpenGitIntent extends Intent {
  const _OpenGitIntent();
}

class _OpenTemplatesIntent extends Intent {
  const _OpenTemplatesIntent();
}

class _SettingsOverlay extends StatelessWidget {
  const _SettingsOverlay({required this.onClose});
  final VoidCallback onClose;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        GestureDetector(onTap: onClose, child: Container(color: const Color(0x80000000))),
        Positioned(
          right: 0,
          top: 0,
          bottom: 0,
          child: Container(
            width: 450,
            decoration: const BoxDecoration(color: Color(0xFF2B2D30), border: Border(left: BorderSide(color: Color(0xFF1E1F22)))),
            child: Column(
              children: [
                Container(
                  height: 52,
                  color: const Color(0xFF3C3F41),
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    children: [
                      const Text("Settings", style: TextStyle(color: Color(0xFFD1D5DB), fontWeight: FontWeight.w600)),
                      const Spacer(),
                      IconButton(onPressed: onClose, icon: const Icon(Icons.close_rounded, size: 18, color: Color(0xFF8E8E8E))),
                    ],
                  ),
                ),
                const Expanded(child: SettingsView()),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _StatusBar extends StatelessWidget {
  const _StatusBar({required this.state});
  final AppState state;

  @override
  Widget build(BuildContext context) {
    final fileName = state.activeFilePath.isEmpty ? "No file" : state.activeFilePath.split("/").last;
    return Container(
      height: 26,
      color: const Color(0xFF171717),
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        children: [
          Text(fileName, style: const TextStyle(fontSize: 11, color: Colors.white70)),
          const SizedBox(width: 12),
          Text("Warnings: ${state.warningCount}", style: const TextStyle(fontSize: 11, color: Colors.white70)),
          const Spacer(),
          Text(state.executionStatus.isEmpty ? "Ready" : state.executionStatus, style: const TextStyle(fontSize: 11, color: Colors.white70)),
        ],
      ),
    );
  }
}

class _CloneHistoryItem {
  const _CloneHistoryItem({
    required this.repo,
    required this.branch,
    required this.destination,
    required this.framework,
    required this.ok,
    required this.at,
  });

  final String repo;
  final String branch;
  final String destination;
  final String framework;
  final bool ok;
  final DateTime at;
}

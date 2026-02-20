import "package:flutter/material.dart";
import "package:provider/provider.dart";

import "../app_state.dart";
import "../services/api_service.dart";

class GitView extends StatefulWidget {
  const GitView({super.key});

  @override
  State<GitView> createState() => _GitViewState();
}

class _GitViewState extends State<GitView> {
  GitStatusSnapshot? _status;
  List<GitBranch> _branches = const [];
  List<GitCommit> _commits = const [];
  String _diff = "";
  String _error = "";
  bool _busy = false;
  String _selectedPath = "";
  final TextEditingController _commitController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _refreshAll();
  }

  @override
  void dispose() {
    _commitController.dispose();
    super.dispose();
  }

  String get _workspace {
    final state = context.read<AppState>();
    return state.activeProject?.workspacePath ?? state.workspacePath;
  }

  Future<void> _refreshAll() async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = "";
    });
    final api = context.read<AppState>().api;
    final ws = _workspace;
    if (ws.trim().isEmpty) {
      setState(() {
        _error = "No active workspace.";
        _busy = false;
      });
      return;
    }
    try {
      final status = await api.getGitStatus(workspace: ws);
      final branches = await api.getGitBranches(workspace: ws);
      final commits = await api.getGitLog(workspace: ws, limit: 30);
      setState(() {
        _status = status;
        _branches = branches;
        _commits = commits;
        if (_selectedPath.isNotEmpty) {
          _selectedPath = status?.files.any((f) => f.path == _selectedPath) == true ? _selectedPath : "";
        }
      });
      if (_selectedPath.isNotEmpty) {
        await _loadDiff(path: _selectedPath);
      } else {
        setState(() => _diff = "");
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) {
        setState(() => _busy = false);
      }
    }
  }

  Future<void> _loadDiff({String? path, bool staged = false, String? ref}) async {
    final ws = _workspace;
    if (ws.trim().isEmpty) return;
    final api = context.read<AppState>().api;
    final text = await api.getGitDiff(workspace: ws, path: path, staged: staged, ref: ref);
    if (!mounted) return;
    setState(() => _diff = text.isEmpty ? "No diff output." : text);
  }

  Future<void> _stage(List<String> paths) async {
    final ok = await context.read<AppState>().api.stageGit(workspace: _workspace, paths: paths);
    if (!mounted) return;
    if (!ok) {
      setState(() => _error = "Stage failed.");
      return;
    }
    await _refreshAll();
  }

  Future<void> _unstage(List<String> paths) async {
    final ok = await context.read<AppState>().api.unstageGit(workspace: _workspace, paths: paths);
    if (!mounted) return;
    if (!ok) {
      setState(() => _error = "Unstage failed.");
      return;
    }
    await _refreshAll();
  }

  Future<void> _commit() async {
    final msg = _commitController.text.trim();
    if (msg.isEmpty) {
      setState(() => _error = "Commit message required.");
      return;
    }
    final ok = await context.read<AppState>().api.commitGit(workspace: _workspace, message: msg);
    if (!mounted) return;
    if (!ok) {
      setState(() => _error = "Commit failed.");
      return;
    }
    _commitController.clear();
    await _refreshAll();
  }

  Future<void> _pull() async {
    final ok = await context.read<AppState>().api.pullGit(workspace: _workspace);
    if (!mounted) return;
    if (!ok) {
      setState(() => _error = "Pull failed.");
      return;
    }
    await _refreshAll();
  }

  Future<void> _push() async {
    final status = _status;
    final branch = status?.branch ?? "";
    final ok = await context.read<AppState>().api.pushGit(
          workspace: _workspace,
          setUpstream: (status?.upstream ?? "").isEmpty && branch.isNotEmpty,
          branch: branch.isEmpty ? null : branch,
        );
    if (!mounted) return;
    if (!ok) {
      setState(() => _error = "Push failed.");
      return;
    }
    await _refreshAll();
  }

  Future<void> _checkout(String branch, {bool create = false}) async {
    final ok = await context.read<AppState>().api.checkoutGit(
          workspace: _workspace,
          branch: branch,
          create: create,
        );
    if (!mounted) return;
    if (!ok) {
      setState(() => _error = "Checkout failed.");
      return;
    }
    await _refreshAll();
  }

  @override
  Widget build(BuildContext context) {
    final status = _status;
    final branch = status?.branch.isNotEmpty == true ? status!.branch : "-";
    final upstream = status?.upstream ?? "";

    return Container(
      color: const Color(0xFF17181C),
      child: Column(
        children: [
          Container(
            height: 48,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: const BoxDecoration(
              color: Color(0xFF202329),
              border: Border(bottom: BorderSide(color: Color(0xFF343A46))),
            ),
            child: Row(
              children: [
                Text(
                  "Git • $branch",
                  style: const TextStyle(
                    color: Color(0xFFE8ECF2),
                    fontSize: 14,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (upstream.isNotEmpty) ...[
                  const SizedBox(width: 8),
                  Text(upstream, style: const TextStyle(color: Color(0xFF99A1B3), fontSize: 11)),
                ],
                if (status != null) ...[
                  const SizedBox(width: 10),
                  _Pill(label: "↑ ${status.ahead}", color: const Color(0xFF34D399)),
                  const SizedBox(width: 6),
                  _Pill(label: "↓ ${status.behind}", color: const Color(0xFF60A5FA)),
                ],
                const Spacer(),
                FilledButton.tonal(
                  onPressed: _busy ? null : _pull,
                  child: const Text("Pull"),
                ),
                const SizedBox(width: 8),
                FilledButton.tonal(
                  onPressed: _busy ? null : _push,
                  child: const Text("Push"),
                ),
                const SizedBox(width: 8),
                IconButton(
                  tooltip: "Refresh",
                  onPressed: _busy ? null : _refreshAll,
                  icon: const Icon(Icons.refresh_rounded, color: Color(0xFFAAB3C2)),
                ),
              ],
            ),
          ),
          if (_error.isNotEmpty)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
              color: const Color(0x332D1A1A),
              child: Text(_error, style: const TextStyle(color: Color(0xFFFFA3A3), fontSize: 12)),
            ),
          Expanded(
            child: Row(
              children: [
                SizedBox(
                  width: 360,
                  child: Container(
                    decoration: const BoxDecoration(
                      border: Border(right: BorderSide(color: Color(0xFF343A46))),
                    ),
                    child: Column(
                      children: [
                        _buildCommitBar(),
                        _buildBranchBar(),
                        const Divider(height: 1, color: Color(0xFF343A46)),
                        Expanded(child: _buildFileList()),
                      ],
                    ),
                  ),
                ),
                Expanded(
                  child: Column(
                    children: [
                      Expanded(child: _buildDiffPane()),
                      Container(
                        height: 220,
                        decoration: const BoxDecoration(
                          border: Border(top: BorderSide(color: Color(0xFF343A46))),
                        ),
                        child: _buildCommitList(),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCommitBar() {
    return Padding(
      padding: const EdgeInsets.all(10),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _commitController,
              style: const TextStyle(color: Color(0xFFE8ECF2), fontSize: 12),
              decoration: InputDecoration(
                hintText: "Commit message",
                hintStyle: const TextStyle(color: Color(0xFF99A1B3), fontSize: 12),
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                filled: true,
                fillColor: const Color(0xFF252A33),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF343A46)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF343A46)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF0A84FF), width: 1.2),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          FilledButton(onPressed: _busy ? null : _commit, child: const Text("Commit")),
        ],
      ),
    );
  }

  Widget _buildBranchBar() {
    final branches = _branches;
    GitBranch? current;
    for (final b in branches) {
      if (b.current) {
        current = b;
        break;
      }
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: DropdownButtonFormField<String>(
              initialValue: current?.name,
              items: branches
                  .map(
                    (b) => DropdownMenuItem<String>(
                      value: b.name,
                      child: Text(b.name, style: const TextStyle(fontSize: 12)),
                    ),
                  )
                  .toList(),
              onChanged: _busy
                  ? null
                  : (v) {
                      if (v == null || v.trim().isEmpty) return;
                      _checkout(v.trim());
                    },
              dropdownColor: const Color(0xFF252A33),
              style: const TextStyle(color: Color(0xFFE8ECF2)),
              decoration: InputDecoration(
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                filled: true,
                fillColor: const Color(0xFF252A33),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF343A46)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(color: Color(0xFF343A46)),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          OutlinedButton(
            onPressed: _busy ? null : _showCreateBranchDialog,
            child: const Text("New"),
          ),
          const SizedBox(width: 8),
          OutlinedButton(
            onPressed: _busy ? null : () => _stage(const []),
            child: const Text("Stage All"),
          ),
        ],
      ),
    );
  }

  Widget _buildFileList() {
    final status = _status;
    if (status == null) {
      return const Center(
        child: Text("No git repository detected.", style: TextStyle(color: Color(0xFF99A1B3))),
      );
    }
    if (status.files.isEmpty) {
      return const Center(
        child: Text("Working tree clean.", style: TextStyle(color: Color(0xFF99A1B3))),
      );
    }
    return ListView.separated(
      itemCount: status.files.length,
      separatorBuilder: (_, __) => const Divider(height: 1, color: Color(0xFF2A2E36)),
      itemBuilder: (context, i) {
        final f = status.files[i];
        final active = f.path == _selectedPath;
        return Material(
          color: active ? const Color(0x222A98FF) : Colors.transparent,
          child: InkWell(
            onTap: () {
              setState(() => _selectedPath = f.path);
              _loadDiff(path: f.path, staged: f.staged);
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              child: Row(
                children: [
                  SizedBox(
                    width: 24,
                    child: Text(
                      "${f.indexStatus}${f.worktreeStatus}",
                      style: const TextStyle(
                        color: Color(0xFF99A1B3),
                        fontSize: 11,
                        fontFeatures: [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      f.path,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Color(0xFFE8ECF2), fontSize: 12),
                    ),
                  ),
                  if (f.staged)
                    IconButton(
                      tooltip: "Unstage",
                      onPressed: _busy ? null : () => _unstage([f.path]),
                      icon: const Icon(Icons.remove_circle_outline, color: Color(0xFFF59E0B), size: 18),
                    )
                  else
                    IconButton(
                      tooltip: "Stage",
                      onPressed: _busy ? null : () => _stage([f.path]),
                      icon: const Icon(Icons.add_circle_outline, color: Color(0xFF34D399), size: 18),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildDiffPane() {
    return Container(
      color: const Color(0xFF15171C),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 36,
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            alignment: Alignment.centerLeft,
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: Color(0xFF2A2E36))),
            ),
            child: Text(
              _selectedPath.isEmpty ? "Diff Preview" : "Diff • $_selectedPath",
              style: const TextStyle(color: Color(0xFFAAB3C2), fontSize: 12, fontWeight: FontWeight.w600),
            ),
          ),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(12),
              child: SelectableText(
                _diff.isEmpty ? "Select a file to preview diff." : _diff,
                style: const TextStyle(
                  color: Color(0xFFD1D5DB),
                  fontSize: 12,
                  fontFamily: "Consolas",
                  height: 1.35,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCommitList() {
    if (_commits.isEmpty) {
      return const Center(
        child: Text("No commit history.", style: TextStyle(color: Color(0xFF99A1B3))),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: _commits.length,
      separatorBuilder: (_, __) => const Divider(height: 1, color: Color(0xFF2A2E36)),
      itemBuilder: (context, i) {
        final c = _commits[i];
        return ListTile(
          dense: true,
          leading: Text(c.shortHash, style: const TextStyle(color: Color(0xFF60A5FA), fontSize: 11)),
          title: Text(
            c.subject,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Color(0xFFE8ECF2), fontSize: 12),
          ),
          subtitle: Text("${c.author} • ${c.date}", style: const TextStyle(color: Color(0xFF99A1B3), fontSize: 11)),
          onTap: () => _loadDiff(ref: c.hash),
        );
      },
    );
  }

  Future<void> _showCreateBranchDialog() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF22242A),
          title: const Text("Create Branch"),
          content: TextField(
            controller: ctrl,
            autofocus: true,
            style: const TextStyle(color: Color(0xFFE8ECF2)),
            decoration: const InputDecoration(
              hintText: "feature/my-branch",
              hintStyle: TextStyle(color: Color(0xFF99A1B3)),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.of(ctx).pop(false), child: const Text("Cancel")),
            FilledButton(onPressed: () => Navigator.of(ctx).pop(true), child: const Text("Create")),
          ],
        );
      },
    );
    if (ok != true) return;
    final branch = ctrl.text.trim();
    if (branch.isEmpty) return;
    await _checkout(branch, create: true);
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700),
      ),
    );
  }
}

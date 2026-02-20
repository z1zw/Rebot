import "dart:async";
import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:provider/provider.dart";
import "../app_state.dart";
import "../core/l10n.dart";
import "../services/api_service.dart";

class HistoryView extends StatefulWidget {
  const HistoryView({super.key});

  @override
  State<HistoryView> createState() => _HistoryViewState();
}

class _HistoryViewState extends State<HistoryView> {
  List<ExecutionRecord> _executions = [];
  bool _loading = true;
  String? _selectedId;
  Timer? _refreshTimer;
  String _filter = "all";

  @override
  void initState() {
    super.initState();
    _loadHistory();
        _refreshTimer = Timer.periodic(const Duration(seconds: 60), (_) => _loadHistory());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  List<ExecutionRecord> get _filteredExecutions {
    if (_filter == "all") return _executions;
    return _executions.where((e) => e.status == _filter).toList();
  }

  Map<String, int> get _statusCounts {
    final counts = <String, int>{"all": _executions.length};
    for (final e in _executions) {
      counts[e.status] = (counts[e.status] ?? 0) + 1;
    }
    return counts;
  }

  Future<void> _loadHistory() async {
    if (!mounted) return;
    final state = context.read<AppState>();
    
    try {
      final records = await state.api.listExecutions(limit: 50);
      if (mounted) {
        setState(() {
          _executions = records;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _cancelExecution(String id) async {
    final state = context.read<AppState>();
    final ok = await state.api.cancelExecution(id);
    if (!mounted) return;
    if (ok) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Execution cancelled"), backgroundColor: Color(0xFF10A37F)),
      );
      await _loadHistory();
    }
  }

  @override
  Widget build(BuildContext context) {
    final counts = _statusCounts;
    final filtered = _filteredExecutions;
    final runningCount = counts["running"] ?? 0;

    return Container(
      color: const Color(0xFF171717),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _HistoryHeader(
            total: _executions.length,
            runningCount: runningCount,
            onRefresh: _loadHistory,
          ),
          _FilterTabs(
            selected: _filter,
            counts: counts,
            onSelect: (f) => setState(() => _filter = f),
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator(color: Color(0xFF10A37F)))
                : filtered.isEmpty
                    ? _EmptyState(filter: _filter)
                    : ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: filtered.length,
                        itemBuilder: (context, index) {
                          final item = filtered[index];
                          final selected = _selectedId == item.runId;
                          final isRunning = item.status == "running" || item.status == "queued";
                          return _ExecutionCard(
                            item: item,
                            selected: selected,
                            index: index,
                            onTap: () => setState(() => _selectedId = selected ? null : item.runId),
                            onCancel: isRunning ? () => _cancelExecution(item.runId) : null,
                            onCopyId: () {
                              Clipboard.setData(ClipboardData(text: item.runId));
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text("Run ID copied"),
                                  backgroundColor: Color(0xFF323232),
                                  duration: Duration(seconds: 2),
                                ),
                              );
                            },
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

class _HistoryHeader extends StatelessWidget {
  const _HistoryHeader({
    required this.total,
    required this.runningCount,
    required this.onRefresh,
  });

  final int total;
  final int runningCount;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: const BoxDecoration(
        color: Color(0xFF212121),
        border: Border(bottom: BorderSide(color: Color(0xFF2A2A2A))),
      ),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: const Color(0xFF10A37F).withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.history, color: Color(0xFF10A37F), size: 18),
          ),
          const SizedBox(width: 12),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "Execution History",
                style: TextStyle(
                  color: Color(0xFFFFFFFF),
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
              Text(
                "$total total executions",
                style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 11),
              ),
            ],
          ),
          const Spacer(),
          if (runningCount > 0)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFFFACC15).withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFACC15).withValues(alpha: 0.3)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: const AlwaysStoppedAnimation(Color(0xFFFACC15)),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    "$runningCount running",
                    style: const TextStyle(
                      color: Color(0xFFFACC15),
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
          const SizedBox(width: 12),
          _RefreshIconButton(onTap: onRefresh),
        ],
      ),
    );
  }
}

class _RefreshIconButton extends StatefulWidget {
  const _RefreshIconButton({required this.onTap});
  final VoidCallback onTap;

  @override
  State<_RefreshIconButton> createState() => _RefreshIconButtonState();
}

class _RefreshIconButtonState extends State<_RefreshIconButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          width: 32,
          height: 32,
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF2A2A2A) : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Icon(
            Icons.refresh,
            size: 18,
            color: _hovered ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
          ),
        ),
      ),
    );
  }
}

class _FilterTabs extends StatelessWidget {
  const _FilterTabs({
    required this.selected,
    required this.counts,
    required this.onSelect,
  });

  final String selected;
  final Map<String, int> counts;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 40,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: const BoxDecoration(
        color: Color(0xFF1A1A1A),
        border: Border(bottom: BorderSide(color: Color(0xFF2A2A2A))),
      ),
      child: Row(
        children: [
          _FilterTab(
            label: S.all,
            count: counts["all"] ?? 0,
            selected: selected == "all",
            onTap: () => onSelect("all"),
          ),
          _FilterTab(
            label: S.running,
            count: counts["running"] ?? 0,
            selected: selected == "running",
            color: const Color(0xFFFACC15),
            onTap: () => onSelect("running"),
          ),
          _FilterTab(
            label: S.finished,
            count: counts["finished"] ?? 0,
            selected: selected == "finished",
            color: const Color(0xFF4ADE80),
            onTap: () => onSelect("finished"),
          ),
          _FilterTab(
            label: S.failed,
            count: counts["failed"] ?? 0,
            selected: selected == "failed",
            color: const Color(0xFFEF4444),
            onTap: () => onSelect("failed"),
          ),
        ],
      ),
    );
  }
}

class _FilterTab extends StatefulWidget {
  const _FilterTab({
    required this.label,
    required this.count,
    required this.selected,
    required this.onTap,
    this.color,
  });

  final String label;
  final int count;
  final bool selected;
  final Color? color;
  final VoidCallback onTap;

  @override
  State<_FilterTab> createState() => _FilterTabState();
}

class _FilterTabState extends State<_FilterTab> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final color = widget.color ?? const Color(0xFF10A37F);
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          margin: const EdgeInsets.only(right: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: widget.selected
                ? color.withValues(alpha: 0.15)
                : _hovered
                    ? const Color(0xFF2A2A2A)
                    : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
            border: widget.selected
                ? Border.all(color: color.withValues(alpha: 0.3))
                : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                widget.label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: widget.selected ? FontWeight.w600 : FontWeight.w400,
                  color: widget.selected ? color : const Color(0xFF8E8E8E),
                ),
              ),
              if (widget.count > 0) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: widget.selected ? color.withValues(alpha: 0.2) : const Color(0xFF333333),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    "${widget.count}",
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: widget.selected ? color : const Color(0xFF6E6E6E),
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.filter});
  final String filter;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.inbox_outlined, size: 48, color: const Color(0xFF333333)),
          const SizedBox(height: 12),
          Text(
            filter == "all" ? S.noExecutions : "No $filter executions",
            style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 13),
          ),
          const SizedBox(height: 4),
          const Text(
            "Run a task to see it here",
            style: TextStyle(color: Color(0xFF4A4A4A), fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class _ExecutionCard extends StatefulWidget {
  const _ExecutionCard({
    required this.item,
    required this.selected,
    required this.index,
    required this.onTap,
    required this.onCopyId,
    this.onCancel,
  });
  final ExecutionRecord item;
  final bool selected;
  final int index;
  final VoidCallback onTap;
  final VoidCallback onCopyId;
  final VoidCallback? onCancel;

  @override
  State<_ExecutionCard> createState() => _ExecutionCardState();
}

class _ExecutionCardState extends State<_ExecutionCard> {
  bool _hovered = false;

  Color get _statusColor {
    switch (widget.item.status) {
      case "running":
      case "queued":
        return const Color(0xFFFACC15);
      case "finished":
        return const Color(0xFF4ADE80);
      case "failed":
      case "cancelled":
        return const Color(0xFFEF4444);
      default:
        return const Color(0xFF6E6E6E);
    }
  }

  IconData get _statusIcon {
    switch (widget.item.status) {
      case "running":
      case "queued":
        return Icons.sync;
      case "finished":
        return Icons.check_circle_outline;
      case "failed":
      case "cancelled":
        return Icons.error_outline;
      default:
        return Icons.pending_outlined;
    }
  }

  String _formatTime(DateTime? dt) {
    if (dt == null) return "Unknown";
    final now = DateTime.now();
    final diff = now.difference(dt);
    if (diff.inMinutes < 1) return "Just now";
    if (diff.inMinutes < 60) return "${diff.inMinutes}m ago";
    if (diff.inHours < 24) return "${diff.inHours}h ago";
    if (diff.inDays < 7) return "${diff.inDays}d ago";
    return "${dt.month}/${dt.day}";
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
          onEnter: (_) => setState(() => _hovered = true),
          onExit: (_) => setState(() => _hovered = false),
          child: Container(
            margin: const EdgeInsets.only(bottom: 8),
            decoration: BoxDecoration(
              color: widget.selected
                  ? const Color(0xFF2A3A2A)
                  : _hovered
                      ? const Color(0xFF262626)
                      : const Color(0xFF1E1E1E),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: widget.selected 
                    ? const Color(0xFF10A37F) 
                    : _hovered 
                        ? const Color(0xFF333333)
                        : const Color(0xFF262626),
                width: widget.selected ? 1.5 : 1,
              ),
            ),
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: widget.onTap,
                borderRadius: BorderRadius.circular(10),
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 28,
                            height: 28,
                            decoration: BoxDecoration(
                              color: _statusColor.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Icon(_statusIcon, size: 14, color: _statusColor),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Flexible(
                                      child: Text(
                                        widget.item.runId.length > 20 
                                            ? "${widget.item.runId.substring(0, 8)}...${widget.item.runId.substring(widget.item.runId.length - 8)}"
                                            : widget.item.runId,
                                        style: const TextStyle(
                                          color: Color(0xFFD1D5DB),
                                          fontSize: 12,
                                          fontFamily: "JetBrains Mono",
                                          fontWeight: FontWeight.w500,
                                        ),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    if (_hovered) ...[
                                      const SizedBox(width: 8),
                                      _CopyButton(onTap: widget.onCopyId),
                                    ],
                                  ],
                                ),
                                const SizedBox(height: 2),
                                Text(
                                  _formatTime(widget.item.updatedAt),
                                  style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 10),
                                ),
                              ],
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: _statusColor.withValues(alpha: 0.12),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              widget.item.status.toUpperCase(),
                              style: TextStyle(
                                color: _statusColor,
                                fontSize: 9,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.5,
                              ),
                            ),
                          ),
                        ],
                      ),
                      if (widget.item.progress.isNotEmpty) ...[
                        const SizedBox(height: 10),
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(10),
                          decoration: BoxDecoration(
                            color: const Color(0xFF171717),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            widget.item.progress,
                            style: const TextStyle(
                              color: Color(0xFF8E8E8E),
                              fontSize: 11,
                              height: 1.4,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                      if (widget.selected && widget.onCancel != null) ...[
                        const SizedBox(height: 12),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            _SmallButton(
                              icon: Icons.stop,
                              label: "Cancel Execution",
                              color: const Color(0xFFEF4444),
                              onTap: widget.onCancel!,
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
    );
  }
}

class _CopyButton extends StatefulWidget {
  const _CopyButton({required this.onTap});
  final VoidCallback onTap;

  @override
  State<_CopyButton> createState() => _CopyButtonState();
}

class _CopyButtonState extends State<_CopyButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Icon(
          Icons.copy_outlined,
          size: 12,
          color: _hovered ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
        ),
      ),
    );
  }
}

class _SmallButton extends StatefulWidget {
  const _SmallButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  State<_SmallButton> createState() => _SmallButtonState();
}

class _SmallButtonState extends State<_SmallButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: _hovered ? widget.color.withValues(alpha: 0.2) : widget.color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: widget.color.withValues(alpha: _hovered ? 0.5 : 0.2)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(widget.icon, size: 12, color: widget.color),
              const SizedBox(width: 6),
              Text(
                widget.label,
                style: TextStyle(
                  color: widget.color,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}


import "dart:async";
import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:provider/provider.dart";
import "../app_state.dart";

class DevServerView extends StatefulWidget {
  const DevServerView({super.key});

  @override
  State<DevServerView> createState() => _DevServerViewState();
}

class _DevServerViewState extends State<DevServerView> {
  bool _loading = false;
  String _logs = "";
  Map<String, dynamic>? _status;
  Timer? _refreshTimer;
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _refresh();
        _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) => _refresh());
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    final state = context.read<AppState>();
    try {
      final status = await state.api.getDevServerStatus(
        workspace: state.activeWorkspacePath,
        framework: state.selectedFramework,
      );
      final logs = await state.getDevServerLogs(lines: 100);
      if (mounted) {
        setState(() {
          _status = status;
          _logs = logs;
        });
      }
    } catch (_) {}
  }

  Future<void> _start() async {
    setState(() => _loading = true);
    final state = context.read<AppState>();
    try {
      await state.api.startDevServer(
        workspace: state.activeWorkspacePath,
        framework: state.selectedFramework,
      );
      await Future.delayed(const Duration(seconds: 2));
      await _refresh();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _stop() async {
    setState(() => _loading = true);
    final state = context.read<AppState>();
    try {
      await state.api.stopDevServer(
        workspace: state.activeWorkspacePath,
        framework: state.selectedFramework,
      );
      await Future.delayed(const Duration(seconds: 1));
      await _refresh();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _restart() async {
    setState(() => _loading = true);
    final state = context.read<AppState>();
    try {
      await state.api.restartDevServer(
        workspace: state.activeWorkspacePath,
        framework: state.selectedFramework,
      );
      await Future.delayed(const Duration(seconds: 2));
      await _refresh();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final running = _status?["running"] == true;
    final url = _status?["url"]?.toString() ?? "";
    final port = _status?["port"]?.toString() ?? "";
    final pid = _status?["pid"]?.toString() ?? "";

    return Container(
      color: const Color(0xFF171717),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _DevServerHeader(
            running: running,
            onRefresh: _refresh,
          ),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (running) ...[
                  _ServerInfoGrid(url: url, port: port, pid: pid),
                  const SizedBox(height: 20),
                ],
                _ActionButtonsRow(
                  running: running,
                  loading: _loading,
                  onStart: _start,
                  onStop: _stop,
                  onRestart: _restart,
                  onRefresh: _refresh,
                ),
              ],
            ),
          ),
          Container(height: 1, color: const Color(0xFF2A2A2A)),
          _LogsHeader(
            onClear: () => setState(() => _logs = ""),
            onScrollToBottom: _scrollToBottom,
          ),
          Expanded(
            child: _LogsTerminal(
              logs: _logs,
              scrollController: _scrollController,
            ),
          ),
        ],
      ),
    );
  }
}

class _DevServerHeader extends StatelessWidget {
  const _DevServerHeader({
    required this.running,
    required this.onRefresh,
  });

  final bool running;
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
              color: const Color(0xFF10A37F).withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.dns_outlined, color: Color(0xFF10A37F), size: 18),
          ),
          const SizedBox(width: 12),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "Development Server",
                style: TextStyle(
                  color: Color(0xFFFFFFFF),
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
              Text(
                running ? "Server is active" : "Server is stopped",
                style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 11),
              ),
            ],
          ),
          const Spacer(),
          _StatusBadge(running: running),
        ],
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.running});
  final bool running;

  @override
  Widget build(BuildContext context) {
    final color = running ? const Color(0xFF4ADE80) : const Color(0xFFEF4444);
    final bgColor = running ? const Color(0xFF2E5A3A) : const Color(0xFF5A2E2E);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: running ? bgColor : bgColor,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            running ? "Running" : "Stopped",
            style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }
}

class _ServerInfoGrid extends StatelessWidget {
  const _ServerInfoGrid({
    required this.url,
    required this.port,
    required this.pid,
  });

  final String url;
  final String port;
  final String pid;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: _InfoCard(icon: Icons.link, label: "URL", value: url, copyable: true)),
        const SizedBox(width: 12),
        _InfoCard(icon: Icons.numbers, label: "Port", value: port, width: 100),
        const SizedBox(width: 12),
        _InfoCard(icon: Icons.memory, label: "PID", value: pid, width: 100),
      ],
    );
  }
}

class _InfoCard extends StatefulWidget {
  const _InfoCard({
    required this.icon,
    required this.label,
    required this.value,
    this.copyable = false,
    this.width,
  });

  final IconData icon;
  final String label;
  final String value;
  final bool copyable;
  final double? width;

  @override
  State<_InfoCard> createState() => _InfoCardState();
}

class _InfoCardState extends State<_InfoCard> {
  bool _hovered = false;
  bool _copied = false;

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.value));
    setState(() => _copied = true);
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) setState(() => _copied = false);
    });
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        width: widget.width,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: _hovered ? const Color(0xFF262626) : const Color(0xFF1E1E1E),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: _hovered ? const Color(0xFF333333) : const Color(0xFF2A2A2A),
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: const Color(0xFF10A37F).withOpacity(0.1),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Icon(widget.icon, size: 14, color: const Color(0xFF10A37F)),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.label,
                    style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 10),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    widget.value.isEmpty ? "N/A" : widget.value,
                    style: const TextStyle(
                      color: Color(0xFFD1D5DB),
                      fontSize: 12,
                      fontFamily: "JetBrains Mono",
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            if (widget.copyable && _hovered)
              GestureDetector(
                onTap: _copy,
                child: Icon(
                  _copied ? Icons.check : Icons.copy_outlined,
                  size: 14,
                  color: _copied ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ActionButtonsRow extends StatelessWidget {
  const _ActionButtonsRow({
    required this.running,
    required this.loading,
    required this.onStart,
    required this.onStop,
    required this.onRestart,
    required this.onRefresh,
  });

  final bool running;
  final bool loading;
  final VoidCallback onStart;
  final VoidCallback onStop;
  final VoidCallback onRestart;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _ActionButton(
          icon: Icons.play_arrow,
          label: "Start",
          color: const Color(0xFF4ADE80),
          loading: loading && !running,
          disabled: running || loading,
          onTap: onStart,
        ),
        const SizedBox(width: 10),
        _ActionButton(
          icon: Icons.stop,
          label: "Stop",
          color: const Color(0xFFEF4444),
          loading: loading && running,
          disabled: !running || loading,
          onTap: onStop,
        ),
        const SizedBox(width: 10),
        _ActionButton(
          icon: Icons.refresh,
          label: "Restart",
          color: const Color(0xFFFACC15),
          loading: false,
          disabled: !running || loading,
          onTap: onRestart,
        ),
        const Spacer(),
        _RefreshIconButton(onTap: onRefresh),
      ],
    );
  }
}

class _ActionButton extends StatefulWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
    this.loading = false,
    this.disabled = false,
  });
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;
  final bool loading;
  final bool disabled;

  @override
  State<_ActionButton> createState() => _ActionButtonState();
}

class _ActionButtonState extends State<_ActionButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final effectiveDisabled = widget.disabled;
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: effectiveDisabled ? SystemMouseCursors.forbidden : SystemMouseCursors.click,
      child: GestureDetector(
        onTap: effectiveDisabled ? null : widget.onTap,
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 150),
          opacity: effectiveDisabled ? 0.4 : 1.0,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: _hovered && !effectiveDisabled
                  ? widget.color.withOpacity(0.25)
                  : widget.color.withOpacity(0.12),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: _hovered && !effectiveDisabled
                    ? widget.color.withOpacity(0.5)
                    : widget.color.withOpacity(0.2),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                widget.loading
                    ? SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2, color: widget.color),
                      )
                    : Icon(widget.icon, size: 16, color: widget.color),
                const SizedBox(width: 8),
                Text(
                  widget.label,
                  style: TextStyle(
                    color: widget.color,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
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
          width: 34,
          height: 34,
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF2A2A2A) : Colors.transparent,
            borderRadius: BorderRadius.circular(6),
          ),
          child: Icon(
            Icons.sync,
            size: 18,
            color: _hovered ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
          ),
        ),
      ),
    );
  }
}

class _LogsHeader extends StatelessWidget {
  const _LogsHeader({required this.onClear, required this.onScrollToBottom});
  final VoidCallback onClear;
  final VoidCallback onScrollToBottom;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: const Color(0xFF262626),
              borderRadius: BorderRadius.circular(4),
            ),
            child: const Icon(Icons.terminal, color: Color(0xFF6E6E6E), size: 14),
          ),
          const SizedBox(width: 8),
          const Text(
            "Server Logs",
            style: TextStyle(color: Color(0xFF8E8E8E), fontSize: 12, fontWeight: FontWeight.w600),
          ),
          const Spacer(),
          _SmallIconButton(icon: Icons.vertical_align_bottom, tooltip: "Scroll to bottom", onTap: onScrollToBottom),
          const SizedBox(width: 4),
          _SmallIconButton(icon: Icons.delete_outline, tooltip: "Clear logs", onTap: onClear),
        ],
      ),
    );
  }
}

class _SmallIconButton extends StatefulWidget {
  const _SmallIconButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  @override
  State<_SmallIconButton> createState() => _SmallIconButtonState();
}

class _SmallIconButtonState extends State<_SmallIconButton> {
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
          onTap: widget.onTap,
          child: Container(
            width: 26,
            height: 26,
            decoration: BoxDecoration(
              color: _hovered ? const Color(0xFF2A2A2A) : Colors.transparent,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Icon(
              widget.icon,
              size: 14,
              color: _hovered ? const Color(0xFFD1D5DB) : const Color(0xFF6E6E6E),
            ),
          ),
        ),
      ),
    );
  }
}

class _LogsTerminal extends StatelessWidget {
  const _LogsTerminal({
    required this.logs,
    required this.scrollController,
  });

  final String logs;
  final ScrollController scrollController;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      decoration: BoxDecoration(
        color: const Color(0xFF0D0E10),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1F1F1F)),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Stack(
          children: [
            Positioned.fill(
              child: SingleChildScrollView(
                controller: scrollController,
                padding: const EdgeInsets.all(14),
                child: SelectableText(
                  logs.isEmpty ? "No logs available. Start the server to see output here." : logs,
                  style: TextStyle(
                    fontFamily: "JetBrains Mono",
                    fontSize: 11,
                    color: logs.isEmpty ? const Color(0xFF4A4A4A) : const Color(0xFFA9B7C6),
                    height: 1.6,
                  ),
                ),
              ),
            ),
            Positioned(
              top: 0,
              left: 0,
              right: 0,
              height: 20,
              child: Container(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [const Color(0xFF0D0E10), const Color(0xFF0D0E10).withOpacity(0)],
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

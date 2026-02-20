import "dart:async";
import "package:flutter/material.dart";
import "package:flutter/services.dart";
import "package:provider/provider.dart";
import "../app_state.dart";
import "../services/api_service.dart";

class AgentsView extends StatefulWidget {
  const AgentsView({super.key});

  @override
  State<AgentsView> createState() => _AgentsViewState();
}

class _AgentsViewState extends State<AgentsView> {
  List<AutoGPTAgent> _agents = [];
  bool _loading = true;
  String _searchQuery = "";
  String? _selectedAgentId;
  WorkflowAnalysis? _analysis;
  bool _importing = false;
  bool _analyzing = false;
  final _searchFocusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _loadAgents();
  }

  @override
  void dispose() {
    _searchFocusNode.dispose();
    super.dispose();
  }

  Future<void> _loadAgents() async {
    setState(() => _loading = true);
    final state = context.read<AppState>();
    try {
      final agents = await state.getAutoGPTCatalog(limit: 100);
      if (mounted) {
        setState(() {
          _agents = agents;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _analyzeAgent(String agentId) async {
    setState(() => _analyzing = true);
    final state = context.read<AppState>();
    final analysis = await state.analyzeAutoGPTWorkflow(agentId);
    if (mounted) {
      setState(() {
        _analysis = analysis;
        _analyzing = false;
      });
    }
  }

  Future<void> _importAgent(String agentId) async {
    setState(() => _importing = true);
    final state = context.read<AppState>();
    try {
      final ok = await state.importAutoGPTAgent(agentId);
      if (ok && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Agent imported successfully!"),
            backgroundColor: Color(0xFF4ADE80),
          ),
        );
        await state.loadFiles();
      }
    } finally {
      if (mounted) setState(() => _importing = false);
    }
  }

  List<AutoGPTAgent> get _filteredAgents {
    if (_searchQuery.isEmpty) return _agents;
    final q = _searchQuery.toLowerCase();
    return _agents.where((a) {
      return a.name.toLowerCase().contains(q) ||
          a.description.toLowerCase().contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: const Color(0xFF171717),
      child: Row(
        children: [
          SizedBox(
            width: 340,
            child: Column(
              children: [
                _AgentListHeader(
                  count: _agents.length,
                  onRefresh: _loadAgents,
                  onSearch: () => _searchFocusNode.requestFocus(),
                ),
                _SearchField(
                  focusNode: _searchFocusNode,
                  onChanged: (v) => setState(() => _searchQuery = v),
                ),
                Expanded(
                  child: _loading
                      ? _LoadingShimmer()
                      : _filteredAgents.isEmpty
                          ? _EmptyState(hasQuery: _searchQuery.isNotEmpty)
                          : _AgentList(
                              agents: _filteredAgents,
                              selectedId: _selectedAgentId,
                              onSelect: (id) {
                                setState(() {
                                  _selectedAgentId = id;
                                  _analysis = null;
                                });
                                _analyzeAgent(id);
                              },
                            ),
                ),
              ],
            ),
          ),
          Container(width: 1, color: const Color(0xFF2A2A2A)),
          Expanded(
            child: _selectedAgentId == null
                ? _NoSelectionState()
                : _buildDetailPanel(),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailPanel() {
    final agent = _agents.firstWhere(
      (a) => a.agentId == _selectedAgentId,
      orElse: () => AutoGPTAgent(agentId: "", name: "", description: "", sourcePath: ""),
    );

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _AgentDetailHeader(
            agent: agent,
            importing: _importing,
            onImport: () => _importAgent(agent.agentId),
          ),
          const SizedBox(height: 28),
          _SectionTitle(title: "Description"),
          const SizedBox(height: 10),
          Text(
            agent.description.isEmpty ? "No description available" : agent.description,
            style: const TextStyle(color: Color(0xFFD1D5DB), fontSize: 14, height: 1.6),
          ),
          const SizedBox(height: 24),
          _SectionTitle(title: "Source Path"),
          const SizedBox(height: 10),
          _SourcePathBox(path: agent.sourcePath),
          if (_analyzing)
            Padding(
              padding: const EdgeInsets.only(top: 32),
              child: Center(
                child: Column(
                  children: [
                    const CircularProgressIndicator(color: Color(0xFF10A37F), strokeWidth: 2),
                    const SizedBox(height: 12),
                    const Text("Analyzing workflow...", style: TextStyle(color: Color(0xFF6E6E6E), fontSize: 12)),
                  ],
                ),
              ),
            )
          else if (_analysis != null) ...[
            const SizedBox(height: 32),
            _SectionTitle(title: "Workflow Analysis"),
            const SizedBox(height: 16),
            _AnalysisStatsRow(analysis: _analysis!),
            if (_analysis!.inferredFiles.isNotEmpty) ...[
              const SizedBox(height: 20),
              _SectionTitle(title: "Inferred Files"),
              const SizedBox(height: 10),
              _InferredFilesWrap(files: _analysis!.inferredFiles),
            ],
            if (_analysis!.summary.isNotEmpty) ...[
              const SizedBox(height: 20),
              _SectionTitle(title: "Summary"),
              const SizedBox(height: 10),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E1E1E),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: const Color(0xFF2A2A2A)),
                ),
                child: Text(
                  _analysis!.summary,
                  style: const TextStyle(color: Color(0xFFD1D5DB), fontSize: 13, height: 1.6),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}

class _AgentListHeader extends StatelessWidget {
  const _AgentListHeader({
    required this.count,
    required this.onRefresh,
    required this.onSearch,
  });

  final int count;
  final VoidCallback onRefresh;
  final VoidCallback onSearch;

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
              gradient: LinearGradient(
                colors: [
                  const Color(0xFF10A37F).withOpacity(0.25),
                  const Color(0xFF10A37F).withOpacity(0.35),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(Icons.smart_toy_outlined, color: Color(0xFF10A37F), size: 18),
          ),
          const SizedBox(width: 12),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                "Agent Market",
                style: TextStyle(
                  color: Color(0xFFFFFFFF),
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
              Text(
                "$count agents available",
                style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 11),
              ),
            ],
          ),
          const Spacer(),
          _IconBtn(icon: Icons.search, onTap: onSearch, tooltip: "Search"),
          const SizedBox(width: 4),
          _IconBtn(icon: Icons.refresh, onTap: onRefresh, tooltip: "Refresh"),
        ],
      ),
    );
  }
}

class _IconBtn extends StatefulWidget {
  const _IconBtn({required this.icon, required this.onTap, this.tooltip});
  final IconData icon;
  final VoidCallback onTap;
  final String? tooltip;

  @override
  State<_IconBtn> createState() => _IconBtnState();
}

class _IconBtnState extends State<_IconBtn> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: widget.tooltip ?? "",
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        cursor: SystemMouseCursors.click,
        child: GestureDetector(
          onTap: widget.onTap,
          child: Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: _hovered ? const Color(0xFF2A2A2A) : Colors.transparent,
              borderRadius: BorderRadius.circular(6),
            ),
            child: Icon(
              widget.icon,
              size: 16,
              color: _hovered ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
            ),
          ),
        ),
      ),
    );
  }
}

class _SearchField extends StatefulWidget {
  const _SearchField({required this.focusNode, required this.onChanged});
  final FocusNode focusNode;
  final ValueChanged<String> onChanged;

  @override
  State<_SearchField> createState() => _SearchFieldState();
}

class _SearchFieldState extends State<_SearchField> {
  bool _focused = false;

  @override
  void initState() {
    super.initState();
    widget.focusNode.addListener(_onFocusChange);
  }

  void _onFocusChange() {
    setState(() => _focused = widget.focusNode.hasFocus);
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
        ),
        child: TextField(
          focusNode: widget.focusNode,
          style: const TextStyle(color: Color(0xFFD1D5DB), fontSize: 13),
          decoration: InputDecoration(
            hintText: "Search agents...",
            hintStyle: const TextStyle(color: Color(0xFF6E6E6E)),
            prefixIcon: const Icon(Icons.search, size: 18, color: Color(0xFF6E6E6E)),
            suffixIcon: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  margin: const EdgeInsets.only(right: 8),
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: const Color(0xFF333333),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    "Ctrl+K",
                    style: TextStyle(color: Color(0xFF6E6E6E), fontSize: 9),
                  ),
                ),
              ],
            ),
            filled: true,
            fillColor: const Color(0xFF1E1E1E),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: Color(0xFF2A2A2A)),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: Color(0xFF2A2A2A)),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(8),
              borderSide: const BorderSide(color: Color(0xFF10A37F), width: 1.5),
            ),
          ),
          onChanged: widget.onChanged,
        ),
      ),
    );
  }
}

class _LoadingShimmer extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      itemCount: 6,
      itemBuilder: (context, index) {
        return TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.3, end: 0.6),
          duration: Duration(milliseconds: 800 + index * 100),
          curve: Curves.easeInOut,
          builder: (context, opacity, child) {
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              height: 72,
              decoration: BoxDecoration(
                color: Color.lerp(const Color(0xFF1E1E1E), const Color(0xFF262626), opacity),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(
                children: [
                  const SizedBox(width: 12),
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFF333333),
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 120,
                          height: 12,
                          decoration: BoxDecoration(
                            color: const Color(0xFF333333),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        const SizedBox(height: 8),
                        Container(
                          width: 180,
                          height: 10,
                          decoration: BoxDecoration(
                            color: const Color(0xFF2A2A2A),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.hasQuery});
  final bool hasQuery;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            hasQuery ? Icons.search_off : Icons.smart_toy_outlined,
            size: 48,
            color: const Color(0xFF333333),
          ),
          const SizedBox(height: 12),
          Text(
            hasQuery ? "No matching agents" : "No agents available",
            style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 13),
          ),
          const SizedBox(height: 4),
          const Text(
            "Try refreshing or changing your search",
            style: TextStyle(color: Color(0xFF4A4A4A), fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class _AgentList extends StatelessWidget {
  const _AgentList({
    required this.agents,
    required this.selectedId,
    required this.onSelect,
  });

  final List<AutoGPTAgent> agents;
  final String? selectedId;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      itemCount: agents.length,
      itemBuilder: (context, index) {
        final agent = agents[index];
        final selected = selectedId == agent.agentId;
        return _AgentCard(
          agent: agent,
          selected: selected,
          index: index,
          onTap: () => onSelect(agent.agentId),
        );
      },
    );
  }
}

class _NoSelectionState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: const Color(0xFF1E1E1E),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF2A2A2A)),
            ),
            child: const Icon(Icons.touch_app_outlined, size: 28, color: Color(0xFF4A4A4A)),
          ),
          const SizedBox(height: 16),
          const Text(
            "Select an agent",
            style: TextStyle(color: Color(0xFF8E8E8E), fontSize: 14, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 4),
          const Text(
            "Choose from the list to view details",
            style: TextStyle(color: Color(0xFF6E6E6E), fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _AgentDetailHeader extends StatelessWidget {
  const _AgentDetailHeader({
    required this.agent,
    required this.importing,
    required this.onImport,
  });

  final AutoGPTAgent agent;
  final bool importing;
  final VoidCallback onImport;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.8, end: 1.0),
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOutBack,
          builder: (context, scale, child) {
            return Transform.scale(scale: scale, child: child);
          },
          child: Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF0D8A6A), Color(0xFF10A37F)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Center(
              child: Icon(Icons.smart_toy, color: Colors.white, size: 32),
            ),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                agent.name,
                style: const TextStyle(
                  color: Color(0xFFFFFFFF),
                  fontSize: 22,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: const Color(0xFF2A2A2A),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      agent.agentId.length > 16
                          ? "${agent.agentId.substring(0, 8)}..."
                          : agent.agentId,
                      style: const TextStyle(
                        color: Color(0xFF6E6E6E),
                        fontSize: 11,
                        fontFamily: "JetBrains Mono",
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  _CopyIdButton(id: agent.agentId),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(width: 16),
        _ImportButton(importing: importing, onTap: onImport),
      ],
    );
  }
}

class _CopyIdButton extends StatefulWidget {
  const _CopyIdButton({required this.id});
  final String id;

  @override
  State<_CopyIdButton> createState() => _CopyIdButtonState();
}

class _CopyIdButtonState extends State<_CopyIdButton> {
  bool _hovered = false;
  bool _copied = false;

  void _copy() {
    Clipboard.setData(ClipboardData(text: widget.id));
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
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: _copy,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
          decoration: BoxDecoration(
            color: _hovered ? const Color(0xFF333333) : Colors.transparent,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Icon(
            _copied ? Icons.check : Icons.copy_outlined,
            size: 12,
            color: _copied ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
          ),
        ),
      ),
    );
  }
}

class _ImportButton extends StatefulWidget {
  const _ImportButton({required this.importing, required this.onTap});
  final bool importing;
  final VoidCallback onTap;

  @override
  State<_ImportButton> createState() => _ImportButtonState();
}

class _ImportButtonState extends State<_ImportButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    if (widget.importing) {
      return Container(
        width: 120,
        height: 42,
        decoration: BoxDecoration(
          color: const Color(0xFF10A37F).withOpacity(0.2),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Center(
          child: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF10A37F)),
          ),
        ),
      );
    }
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: _hovered
                  ? [const Color(0xFF0D8A6A), const Color(0xFF10A37F)]
                  : [const Color(0xFF10A37F), const Color(0xFF10A37F)],
            ),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.download, size: 18, color: Colors.white.withOpacity(_hovered ? 1 : 0.9)),
              const SizedBox(width: 8),
              const Text(
                "Import",
                style: TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 3,
          height: 14,
          decoration: BoxDecoration(
            color: const Color(0xFF10A37F),
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          title,
          style: const TextStyle(
            color: Color(0xFF8E8E8E),
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.5,
          ),
        ),
      ],
    );
  }
}

class _SourcePathBox extends StatefulWidget {
  const _SourcePathBox({required this.path});
  final String path;

  @override
  State<_SourcePathBox> createState() => _SourcePathBoxState();
}

class _SourcePathBoxState extends State<_SourcePathBox> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: _hovered ? const Color(0xFF262626) : const Color(0xFF1E1E1E),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: _hovered ? const Color(0xFF333333) : const Color(0xFF2A2A2A)),
        ),
        child: SelectableText(
          widget.path.isEmpty ? "N/A" : widget.path,
          style: const TextStyle(color: Color(0xFFA9B7C6), fontSize: 12, fontFamily: "JetBrains Mono"),
        ),
      ),
    );
  }
}

class _AnalysisStatsRow extends StatelessWidget {
  const _AnalysisStatsRow({required this.analysis});
  final WorkflowAnalysis analysis;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        _AnimatedStatCard(label: "Nodes", value: analysis.nodeCount, color: const Color(0xFF10A37F)),
        const SizedBox(width: 12),
        _AnimatedStatCard(label: "Edges", value: analysis.edgeCount, color: const Color(0xFF3B82F6)),
        const SizedBox(width: 12),
        _AnimatedStatCard(label: "Levels", value: analysis.levels, color: const Color(0xFFA855F7)),
      ],
    );
  }
}

class _AnimatedStatCard extends StatefulWidget {
  const _AnimatedStatCard({
    required this.label,
    required this.value,
    required this.color,
  });
  final String label;
  final int value;
  final Color color;

  @override
  State<_AnimatedStatCard> createState() => _AnimatedStatCardState();
}

class _AnimatedStatCardState extends State<_AnimatedStatCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          color: _hovered ? widget.color.withOpacity(0.1) : const Color(0xFF1E1E1E),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: _hovered ? widget.color.withOpacity(0.3) : const Color(0xFF2A2A2A),
          ),
        ),
        child: Column(
          children: [
            TweenAnimationBuilder<int>(
              tween: IntTween(begin: 0, end: widget.value),
              duration: const Duration(milliseconds: 800),
              curve: Curves.easeOutCubic,
              builder: (context, val, child) {
                return Text(
                  "$val",
                  style: TextStyle(
                    color: widget.color,
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                  ),
                );
              },
            ),
            const SizedBox(height: 4),
            Text(
              widget.label,
              style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }
}

class _InferredFilesWrap extends StatelessWidget {
  const _InferredFilesWrap({required this.files});
  final List<String> files;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: files.asMap().entries.map((e) {
        return TweenAnimationBuilder<double>(
          tween: Tween(begin: 0.0, end: 1.0),
          duration: Duration(milliseconds: 200 + e.key * 50),
          curve: Curves.easeOutCubic,
          builder: (context, opacity, child) {
            return Opacity(opacity: opacity, child: child);
          },
          child: _FileChip(name: e.value),
        );
      }).toList(),
    );
  }
}

class _FileChip extends StatefulWidget {
  const _FileChip({required this.name});
  final String name;

  @override
  State<_FileChip> createState() => _FileChipState();
}

class _FileChipState extends State<_FileChip> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: _hovered ? const Color(0xFF333333) : const Color(0xFF262626),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: _hovered ? const Color(0xFF10A37F).withOpacity(0.3) : Colors.transparent),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.insert_drive_file_outlined, size: 12, color: _hovered ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E)),
            const SizedBox(width: 6),
            Text(
              widget.name,
              style: TextStyle(
                color: _hovered ? const Color(0xFFD1D5DB) : const Color(0xFFA9B7C6),
                fontSize: 11,
                fontFamily: "JetBrains Mono",
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AgentCard extends StatefulWidget {
  const _AgentCard({
    required this.agent,
    required this.selected,
    required this.index,
    required this.onTap,
  });
  final AutoGPTAgent agent;
  final bool selected;
  final int index;
  final VoidCallback onTap;

  @override
  State<_AgentCard> createState() => _AgentCardState();
}

class _AgentCardState extends State<_AgentCard> {
  bool _hovered = false;

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
                  padding: const EdgeInsets.all(12),
                  child: Row(
                    children: [
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          gradient: widget.selected || _hovered
                              ? const LinearGradient(
                                  colors: [Color(0xFF0D8A6A), Color(0xFF10A37F)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                )
                              : null,
                          color: widget.selected || _hovered ? null : const Color(0xFF262626),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(
                          Icons.smart_toy_outlined,
                          size: 20,
                          color: widget.selected || _hovered ? Colors.white : const Color(0xFF6E6E6E),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              widget.agent.name,
                              style: TextStyle(
                                color: widget.selected ? Colors.white : const Color(0xFFD1D5DB),
                                fontSize: 13,
                                fontWeight: widget.selected ? FontWeight.w600 : FontWeight.w500,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 3),
                            Text(
                              widget.agent.description,
                              style: const TextStyle(color: Color(0xFF6E6E6E), fontSize: 11),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                      AnimatedOpacity(
                        duration: const Duration(milliseconds: 150),
                        opacity: _hovered || widget.selected ? 1.0 : 0.0,
                        child: Icon(
                          Icons.arrow_forward_ios,
                          size: 14,
                          color: widget.selected ? const Color(0xFF10A37F) : const Color(0xFF6E6E6E),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
    );
  }
}

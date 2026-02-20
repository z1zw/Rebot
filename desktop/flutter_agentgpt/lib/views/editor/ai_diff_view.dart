import "package:flutter/material.dart";
import "package:rebot_agentgpt/theme/app_tokens.dart";

class AiDiffView extends StatefulWidget {
  const AiDiffView({
    super.key,
    required this.baseContent,
    required this.currentContent,
    required this.onApplyContent,
  });

  final String baseContent;
  final String currentContent;
  final ValueChanged<String> onApplyContent;

  @override
  State<AiDiffView> createState() => _AiDiffViewState();
}

class _AiDiffViewState extends State<AiDiffView> {
  final Set<String> _dismissed = <String>{};

  @override
  Widget build(BuildContext context) {
    final hunks = _buildHunks()
        .where((h) => !_dismissed.contains(h.key))
        .toList();
    if (hunks.isEmpty) {
      return Center(
        child: Text(
          "No differences",
          style: AppTokens.text(size: 13, color: AppTokens.textTertiary),
        ),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.all(10),
      itemCount: hunks.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, i) {
        final h = hunks[i];
        return Container(
          decoration: BoxDecoration(
            color: AppTokens.bgElevated,
            borderRadius: BorderRadius.circular(AppTokens.radiusMd),
            border: Border.all(color: AppTokens.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: const BoxDecoration(
                  border: Border(bottom: BorderSide(color: AppTokens.borderSubtle)),
                ),
                child: Row(
                  children: [
                    Text(
                      "Hunk ${i + 1} · lines ${h.currentStart + 1}-${h.currentEnd}",
                      style: AppTokens.text(size: 12, color: AppTokens.textSecondary, weight: FontWeight.w600),
                    ),
                    const Spacer(),
                    OutlinedButton(
                      onPressed: () => setState(() => _dismissed.add(h.key)),
                      child: const Text("Reject"),
                    ),
                    const SizedBox(width: 6),
                    FilledButton(
                      onPressed: () => widget.onApplyContent(_applyHunk(h)),
                      child: const Text("Accept AI"),
                    ),
                  ],
                ),
              ),
              ...h.previewRows.map((r) => _DiffRowView(row: r)),
            ],
          ),
        );
      },
    );
  }

  String _applyHunk(_DiffHunk hunk) {
    final lines = widget.currentContent.split("\n");
    final head = lines.take(hunk.currentStart).toList();
    final tail = lines.skip(hunk.currentEnd).toList();
    return [...head, ...hunk.aiLines, ...tail].join("\n");
  }

  List<_DiffHunk> _buildHunks() {
    final current = widget.currentContent.split("\n");
    final ai = widget.baseContent.split("\n");
    final m = current.length;
    final n = ai.length;
    final dp = List.generate(m + 1, (_) => List<int>.filled(n + 1, 0));
    for (var i = m - 1; i >= 0; i--) {
      for (var j = n - 1; j >= 0; j--) {
        if (current[i] == ai[j]) {
          dp[i][j] = dp[i + 1][j + 1] + 1;
        } else {
          dp[i][j] = dp[i + 1][j] >= dp[i][j + 1] ? dp[i + 1][j] : dp[i][j + 1];
        }
      }
    }
    final hunks = <_DiffHunk>[];
    var i = 0;
    var j = 0;
    while (i < m && j < n) {
      if (current[i] == ai[j]) {
        i++;
        j++;
        continue;
      }
      final start = i;
      final aiLines = <String>[];
      final rows = <_DiffRow>[];
      while (i < m && j < n && current[i] != ai[j]) {
        if (dp[i + 1][j] >= dp[i][j + 1]) {
          rows.add(_DiffRow(type: _DiffType.removeCurrent, line: current[i]));
          i++;
        } else {
          aiLines.add(ai[j]);
          rows.add(_DiffRow(type: _DiffType.addAi, line: ai[j]));
          j++;
        }
      }
      while (i < m && (j >= n || (j < n && dp[i + 1][j] >= dp[i][j + 1] && current[i] != ai[j]))) {
        rows.add(_DiffRow(type: _DiffType.removeCurrent, line: current[i]));
        i++;
      }
      while (j < n && (i >= m || (i < m && dp[i][j + 1] > dp[i + 1][j] && current[i] != ai[j]))) {
        aiLines.add(ai[j]);
        rows.add(_DiffRow(type: _DiffType.addAi, line: ai[j]));
        j++;
      }
      final end = i;
      if (rows.isNotEmpty || aiLines.isNotEmpty || end > start) {
        hunks.add(_DiffHunk(
          currentStart: start,
          currentEnd: end,
          aiLines: aiLines,
          previewRows: rows,
        ));
      }
    }
    if (i < m) {
      final rows = <_DiffRow>[];
      for (var k = i; k < m; k++) {
        rows.add(_DiffRow(type: _DiffType.removeCurrent, line: current[k]));
      }
      hunks.add(_DiffHunk(
        currentStart: i,
        currentEnd: m,
        aiLines: const [],
        previewRows: rows,
      ));
    }
    if (j < n) {
      final rows = <_DiffRow>[];
      final aiLines = <String>[];
      for (var k = j; k < n; k++) {
        aiLines.add(ai[k]);
        rows.add(_DiffRow(type: _DiffType.addAi, line: ai[k]));
      }
      hunks.add(_DiffHunk(
        currentStart: m,
        currentEnd: m,
        aiLines: aiLines,
        previewRows: rows,
      ));
    }
    return hunks;
  }
}

class _DiffHunk {
  const _DiffHunk({
    required this.currentStart,
    required this.currentEnd,
    required this.aiLines,
    required this.previewRows,
  });

  final int currentStart;
  final int currentEnd;
  final List<String> aiLines;
  final List<_DiffRow> previewRows;

  String get key => "$currentStart:$currentEnd:${aiLines.join("|")}";
}

enum _DiffType { addAi, removeCurrent }

class _DiffRow {
  const _DiffRow({required this.type, required this.line});
  final _DiffType type;
  final String line;
}

class _DiffRowView extends StatelessWidget {
  const _DiffRowView({required this.row});
  final _DiffRow row;

  @override
  Widget build(BuildContext context) {
    final add = row.type == _DiffType.addAi;
    return Container(
      color: add ? const Color(0x3322C55E) : const Color(0x33EF4444),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 20,
            child: Text(
              add ? "+" : "-",
              style: AppTokens.text(
                mono: true,
                size: 12,
                color: add ? const Color(0xFF22C55E) : const Color(0xFFEF4444),
              ),
            ),
          ),
          Expanded(
            child: SelectableText(
              row.line,
              style: AppTokens.text(
                mono: true,
                size: 12,
                height: 1.6,
                color: AppTokens.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

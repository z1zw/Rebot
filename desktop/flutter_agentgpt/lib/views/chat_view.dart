import "dart:convert";
import "package:flutter/material.dart";
import "package:flutter/rendering.dart";
import "package:flutter/services.dart";
import "package:provider/provider.dart";
import "package:rebot_agentgpt/theme/app_tokens.dart";
import "package:rebot_agentgpt/services/api_service.dart";

import "../app_state.dart";

class ChatView extends StatefulWidget {
  const ChatView({super.key});

  @override
  State<ChatView> createState() => _ChatViewState();
}

class _ChatViewState extends State<ChatView> {
  static const _bg = Color(0xFF17181C);
  static const _panel = Color(0xFF202329);
  static const _panelSoft = Color(0xFF272B33);
  static const _text = Color(0xFFE9ECF3);
  static const _muted = Color(0xFF99A1B3);
  static const _border = Color(0xFF343A46);
  static const _accent = Color(0xFF0A84FF);
  static const _danger = Color(0xFFD54C4C);
  static const _assistantBubble = Color(0xFF242832);

  final ScrollController _scrollController = ScrollController();
  final TextEditingController _composerController = TextEditingController();
  final FocusNode _composerFocus = FocusNode();
  int _lastAutoScrollMsgCount = 0;
  bool _lastAutoScrollRunning = false;
  bool _followBottom = true;
  bool _autoScrollScheduled = false;
  DateTime _manualScrollLockUntil = DateTime.fromMillisecondsSinceEpoch(0);

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_trackFollowBottom);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_trackFollowBottom);
    _scrollController.dispose();
    _composerController.dispose();
    _composerFocus.dispose();
    super.dispose();
  }

  void _trackFollowBottom() {
    if (!_scrollController.hasClients) return;
    final distance =
        _scrollController.position.maxScrollExtent - _scrollController.offset;
    _followBottom = distance <= 120;
  }

  void _scrollToBottomSoon() {
    if (_autoScrollScheduled) return;
    _autoScrollScheduled = true;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _autoScrollScheduled = false;
      if (!_scrollController.hasClients) return;
      if (!_followBottom) return;
      if (DateTime.now().isBefore(_manualScrollLockUntil)) return;
      final max = _scrollController.position.maxScrollExtent;
      final delta = max - _scrollController.offset;
      if (delta <= 1) return;
      if (delta <= 180) {
        _scrollController.jumpTo(max);
      } else {
        _scrollController.animateTo(
          max,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
        );
      }
    });
  }

  void _send(AppState state) {
    final text = _composerController.text.trim();
    if (text.isEmpty) return;
    _composerController.clear();
    state.sendMessage(text);
    _followBottom = true;
    _composerFocus.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    context.select<AppState, int>((s) {
      final msgs = s.messages;
      final lastLen = msgs.isEmpty ? 0 : msgs.last.content.length;
      return Object.hash(
        msgs.length,
        lastLen,
        s.status,
        s.executionStatus,
        s.generatedFiles.length,
        s.activeRunId ?? "",
        s.lastCompletedRunId ?? "",
        s.latestQualityGate.length,
        s.latestPrdScore.length,
        s.latestVisualScore.length,
        s.latestSmokeGate.length,
        s.lastRunPreviewUrl,
        s.previewUrl,
        s.lastRunWorkspace,
        s.lastRunGitKnown,
        s.lastRunGitStatus?.branch ?? "",
        s.lastRunGitStatus?.files.length ?? 0,
      );
    });
    final state = context.read<AppState>();
    final messages = List<Message>.from(state.messages);
    final running = state.status == "running" ||
        state.executionStatus == "running" ||
        state.executionStatus == "queued";

    final shouldAutoScroll = messages.length != _lastAutoScrollMsgCount ||
        running != _lastAutoScrollRunning;
    _lastAutoScrollMsgCount = messages.length;
    _lastAutoScrollRunning = running;
    if (shouldAutoScroll && (messages.isNotEmpty || running)) {
      _scrollToBottomSoon();
    }

    return DecoratedBox(
      decoration: const BoxDecoration(
        color: _bg,
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [_panel, _bg],
        ),
      ),
      child: Column(
        children: [
          Expanded(
            child: messages.isEmpty
                ? _ChatEmptyState(running: running)
                : NotificationListener<UserScrollNotification>(
                    onNotification: (notification) {
                      if (notification.direction == ScrollDirection.forward) {
                        _followBottom = false;
                        _manualScrollLockUntil =
                            DateTime.now().add(const Duration(seconds: 2));
                      } else if (notification.direction ==
                          ScrollDirection.reverse) {
                        _trackFollowBottom();
                      } else {
                        _trackFollowBottom();
                        if (!_followBottom) {
                          _manualScrollLockUntil = DateTime.now()
                              .add(const Duration(milliseconds: 1200));
                        }
                      }
                      return false;
                    },
                    child: ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
                      itemCount: messages.length + (running ? 1 : 0),
                      itemBuilder: (context, i) {
                        if (running && i == messages.length) {
                          return const _TypingMessage();
                        }
                        final message = messages[i];
                        final isUser = message.role.toLowerCase() == "user";
                        final lastAssistantIndex = messages.lastIndexWhere(
                          (m) =>
                              m.role.toLowerCase() == "assistant" &&
                              (m.mode ?? "") != "reasoning",
                        );
                        final estimatedRunSeconds =
                            _estimateRunSeconds(messages, i);
                        final checkpointRunId =
                            state.activeRunId ?? state.lastCompletedRunId;
                        return _MessageCard(
                          message: message,
                          isUser: isUser,
                          modelName: state.model,
                          isLastAssistant: i == lastAssistantIndex,
                          fallbackGeneratedFiles:
                              state.generatedFiles.map((f) => f.path).toList(),
                          estimatedRunSeconds: estimatedRunSeconds,
                          checkpointRunId: checkpointRunId,
                          qualityGate: state.latestQualityGate,
                          prdScore: state.latestPrdScore,
                          visualScore: state.latestVisualScore,
                          smokeGate: state.latestSmokeGate,
                          runPreviewUrl: state.lastRunPreviewUrl.isEmpty
                              ? state.previewUrl
                              : state.lastRunPreviewUrl,
                          runWorkspace: state.lastRunWorkspace,
                          runGitStatus: state.lastRunGitStatus,
                          runGitKnown: state.lastRunGitKnown,
                        );
                      },
                    ),
                  ),
          ),
          _ComposerBar(
            controller: _composerController,
            focusNode: _composerFocus,
            running: running,
            model: state.model,
            models: state.currentModels,
            onModelChanged: state.setModel,
            onSend: () => _send(state),
            onStop: state.cancelActiveRun,
          ),
        ],
      ),
    );
  }

  int _estimateRunSeconds(List<Message> messages, int index) {
    if (index <= 0 || index >= messages.length) return 0;
    DateTime? userAt;
    for (int i = index - 1; i >= 0; i -= 1) {
      if (messages[i].role.toLowerCase() == "user") {
        userAt = messages[i].createdAt;
        break;
      }
    }
    if (userAt == null) return 0;
    final secs = messages[index].createdAt.difference(userAt).inSeconds;
    if (secs <= 0) return 0;
    return secs > 999 ? 999 : secs;
  }
}

class _ChatEmptyState extends StatelessWidget {
  const _ChatEmptyState({required this.running});

  final bool running;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        width: 420,
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 20),
        decoration: BoxDecoration(
          color: _ChatViewState._panel.withValues(alpha: 0.92),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: _ChatViewState._border),
          boxShadow: const [
            BoxShadow(
              color: Color(0x2A000000),
              blurRadius: 20,
              offset: Offset(0, 8),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(AppTokens.radiusXl),
                gradient: const LinearGradient(
                  colors: [Color(0xFF2F3643), Color(0xFF212630)],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
                border: Border.all(color: _ChatViewState._border),
              ),
              child: running
                  ? const Padding(
                      padding: EdgeInsets.all(14),
                      child: CircularProgressIndicator(
                        strokeWidth: 2.3,
                        color: _ChatViewState._accent,
                      ),
                    )
                  : const Icon(
                      Icons.auto_awesome_rounded,
                      color: _ChatViewState._accent,
                      size: 24,
                    ),
            ),
            const SizedBox(height: 12),
            Text(
              running ? "Working on your request..." : "Build with Rebot AI",
              style: const TextStyle(
                color: _ChatViewState._text,
                fontSize: 20,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.2,
              ),
            ),
            const SizedBox(height: 6),
            const Text(
              "Describe what you want. Rebot can generate, edit, and explain project files.",
              textAlign: TextAlign.center,
              style: TextStyle(
                color: _ChatViewState._muted,
                fontSize: 13,
                height: 1.45,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TypingMessage extends StatefulWidget {
  const _TypingMessage();

  @override
  State<_TypingMessage> createState() => _TypingMessageState();
}

class _TypingMessageState extends State<_TypingMessage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller = AnimationController(
    duration: const Duration(milliseconds: 900),
    vsync: this,
  )..repeat();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _Avatar(label: "R", isUser: false),
          const SizedBox(width: 10),
          Container(
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
            decoration: BoxDecoration(
              color: _ChatViewState._assistantBubble,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: _ChatViewState._border),
            ),
            child: AnimatedBuilder(
              animation: _controller,
              builder: (_, __) {
                final t = _controller.value;
                return Row(
                  mainAxisSize: MainAxisSize.min,
                  children: List.generate(3, (i) {
                    final active = ((t * 3).floor() % 3) == i;
                    return Container(
                      width: 7,
                      height: 7,
                      margin: const EdgeInsets.only(right: 6),
                      decoration: BoxDecoration(
                        color: active
                            ? _ChatViewState._accent
                            : _ChatViewState._muted.withValues(alpha: 0.5),
                        borderRadius: BorderRadius.circular(9),
                      ),
                    );
                  }),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({
    required this.message,
    required this.isUser,
    required this.modelName,
    required this.isLastAssistant,
    required this.fallbackGeneratedFiles,
    required this.estimatedRunSeconds,
    required this.checkpointRunId,
    required this.qualityGate,
    required this.prdScore,
    required this.visualScore,
    required this.smokeGate,
    required this.runPreviewUrl,
    required this.runWorkspace,
    required this.runGitStatus,
    required this.runGitKnown,
  });

  final Message message;
  final bool isUser;
  final String modelName;
  final bool isLastAssistant;
  final List<String> fallbackGeneratedFiles;
  final int estimatedRunSeconds;
  final String? checkpointRunId;
  final Map<String, dynamic> qualityGate;
  final Map<String, dynamic> prdScore;
  final Map<String, dynamic> visualScore;
  final Map<String, dynamic> smokeGate;
  final String runPreviewUrl;
  final String runWorkspace;
  final GitStatusSnapshot? runGitStatus;
  final bool runGitKnown;

  @override
  Widget build(BuildContext context) {
    if (isUser) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              "User",
              style: TextStyle(
                color: Color(0xFF95A0B5),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            SelectableText(
              message.content,
              style: const TextStyle(
                color: Color(0xFFE8ECF2),
                fontSize: 18,
                height: 1.35,
              ),
            ),
          ],
        ),
      );
    }

    final files = message.generatedFiles ??
        (isLastAssistant ? fallbackGeneratedFiles : const <String>[]);
    final modelTitle = _modelPreviewTitle(modelName);
    final runText = estimatedRunSeconds > 0
        ? "Ran for ${estimatedRunSeconds}s"
        : _timeText(message.createdAt);
    final thinking = _normalizeThinking(message.content);

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            "$modelTitle - $runText",
            style: const TextStyle(
              color: Color(0xFF95A0B5),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 10),
          _ThoughtCard(
            content: thinking,
            seconds: _extractThoughtSeconds(thinking, estimatedRunSeconds),
          ),
          if (files.isNotEmpty) ...[
            const SizedBox(height: 12),
            _EditedFilesCard(
              files: files,
              runId: checkpointRunId,
              qualityGate: qualityGate,
              prdScore: prdScore,
              visualScore: visualScore,
              smokeGate: smokeGate,
              runPreviewUrl: runPreviewUrl,
              runWorkspace: runWorkspace,
              runGitStatus: runGitStatus,
              runGitKnown: runGitKnown,
            ),
          ],
        ],
      ),
    );
  }

  int _extractThoughtSeconds(String content, int fallback) {
    final m =
        RegExp(r"(\d+)\s*seconds?", caseSensitive: false).firstMatch(content);
    if (m != null) {
      final parsed = int.tryParse(m.group(1) ?? "");
      if (parsed != null && parsed > 0) return parsed;
    }
    return fallback > 0 ? fallback : 8;
  }

  String _modelPreviewTitle(String model) {
    final trimmed = model.trim();
    if (trimmed.isEmpty) return "Model Preview";
    final lower = trimmed.toLowerCase();
    if (lower.contains("preview")) return trimmed;
    final normalized = trimmed
        .replaceAll("_", " ")
        .replaceAll("-", " ")
        .split(" ")
        .where((s) => s.trim().isNotEmpty)
        .map((s) => s[0].toUpperCase() + s.substring(1))
        .join(" ");
    return "$normalized Preview";
  }

  String _timeText(DateTime t) {
    final h = t.hour.toString().padLeft(2, "0");
    final m = t.minute.toString().padLeft(2, "0");
    return "$h:$m";
  }

  String _normalizeThinking(String raw) {
    final text = raw.replaceAll("\r\n", "\n").trim();
    if (text.isEmpty) return "Thinking...";
    final lines = text
        .split("\n")
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    final kept = <String>[];
    var shortOrBroken = 0;
    var codeish = 0;
    for (final s in lines) {
      if (s.length <= 2 || s.length > 180) {
        shortOrBroken += 1;
        continue;
      }
      if (RegExp(
              r"^(import |export |const |let |var |function |class |return |if\s*\(|for\s*\(|while\s*\()",
              caseSensitive: false)
          .hasMatch(s)) {
        codeish += 1;
        continue;
      }
      if (RegExp(r"^[A-Za-z_][A-Za-z0-9_]*$").hasMatch(s) && s.length <= 14) {
        shortOrBroken += 1;
        continue;
      }
      final letterCount = RegExp(r"[A-Za-z]").allMatches(s).length;
      final symbolCount =
          RegExp(r"[{};<>:=/_\\[\\]\\(\\)]").allMatches(s).length;
      if (symbolCount > letterCount) {
        codeish += 1;
        shortOrBroken += 1;
        continue;
      }
      final words = s.split(RegExp(r"\s+")).where((e) => e.isNotEmpty).length;
      if (words <= 2 && !RegExp(r"[.!?]$").hasMatch(s)) {
        shortOrBroken += 1;
        continue;
      }
      kept.add(s);
      if (kept.length >= 8) break;
    }
    if (kept.isEmpty) return "Thinking...";
    if (codeish >= (lines.length * 0.35).ceil()) return "Thinking...";
    if (shortOrBroken >= 8 && kept.length <= 3) return "Thinking...";
    return kept.join("\n");
  }
}

class _ThoughtCard extends StatefulWidget {
  const _ThoughtCard({required this.content, required this.seconds});

  final String content;
  final int seconds;

  @override
  State<_ThoughtCard> createState() => _ThoughtCardState();
}

class _ThoughtCardState extends State<_ThoughtCard> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF1E222A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Column(
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              child: Row(
                children: [
                  const Icon(Icons.lightbulb_outline_rounded,
                      size: 17, color: Color(0xFFA8B3C8)),
                  const SizedBox(width: 8),
                  const Text(
                    "Thinking",
                    style: TextStyle(
                        color: Color(0xFFD9E1F0),
                        fontSize: 13,
                        fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    "${widget.seconds}s",
                    style: const TextStyle(
                        color: Color(0xFF98A2B6),
                        fontSize: 12,
                        fontWeight: FontWeight.w500),
                  ),
                  const Spacer(),
                  Icon(
                    _expanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    color: const Color(0xFF98A2B6),
                  ),
                ],
              ),
            ),
          ),
          if (_expanded)
            Container(
              width: double.infinity,
              margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFF171B23),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF343A46)),
              ),
              child: _ThoughtContent(content: widget.content),
            ),
        ],
      ),
    );
  }
}

class _ThoughtContent extends StatelessWidget {
  const _ThoughtContent({required this.content});

  final String content;

  @override
  Widget build(BuildContext context) {
    final sections = _parseSections(content);
    if (sections.isEmpty) {
      return SelectableText(
        content,
        style: const TextStyle(
          color: Color(0xFFC9D3E5),
          fontSize: 13,
          height: 1.6,
        ),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < sections.length; i++) ...[
          if (sections[i].title.isNotEmpty)
            Text(
              sections[i].title,
              style: const TextStyle(
                color: Color(0xFFDDE6F7),
                fontSize: 13,
                fontWeight: FontWeight.w700,
              ),
            ),
          if (sections[i].body.isNotEmpty) ...[
            const SizedBox(height: 4),
            SelectableText(
              sections[i].body,
              style: const TextStyle(
                color: Color(0xFFC9D3E5),
                fontSize: 13,
                height: 1.6,
              ),
            ),
          ],
          if (i != sections.length - 1) const SizedBox(height: 12),
        ],
      ],
    );
  }

  List<_ThoughtSection> _parseSections(String raw) {
    final text = raw.replaceAll("\r\n", "\n").trim();
    if (text.isEmpty) return const <_ThoughtSection>[];
    final lines = text.split("\n");
    final out = <_ThoughtSection>[];
    String currentTitle = "";
    final bodyLines = <String>[];

    bool isHeading(String line) {
      final s = line.trim();
      if (s.isEmpty || s.length > 80) return false;
      if (s.endsWith(".") || s.endsWith(":")) return false;
      return RegExp(r"^[A-Z][A-Za-z0-9 ,/&()'_-]{2,}$").hasMatch(s);
    }

    void flush() {
      final body = bodyLines.join("\n").trim();
      if (currentTitle.isNotEmpty || body.isNotEmpty) {
        out.add(_ThoughtSection(title: currentTitle, body: body));
      }
      currentTitle = "";
      bodyLines.clear();
    }

    for (final line in lines) {
      final s = line.trim();
      if (s.isEmpty) {
        if (bodyLines.isNotEmpty) bodyLines.add("");
        continue;
      }
      if (isHeading(s)) {
        flush();
        currentTitle = s;
        continue;
      }
      bodyLines.add(s);
    }
    flush();
    if (out.isEmpty) {
      out.add(_ThoughtSection(title: "", body: text));
    }
    return out;
  }
}

class _ThoughtSection {
  const _ThoughtSection({required this.title, required this.body});

  final String title;
  final String body;
}

class _EditedFilesCard extends StatelessWidget {
  const _EditedFilesCard({
    required this.files,
    required this.runId,
    required this.qualityGate,
    required this.prdScore,
    required this.visualScore,
    required this.smokeGate,
    required this.runPreviewUrl,
    required this.runWorkspace,
    required this.runGitStatus,
    required this.runGitKnown,
  });

  final List<String> files;
  final String? runId;
  final Map<String, dynamic> qualityGate;
  final Map<String, dynamic> prdScore;
  final Map<String, dynamic> visualScore;
  final Map<String, dynamic> smokeGate;
  final String runPreviewUrl;
  final String runWorkspace;
  final GitStatusSnapshot? runGitStatus;
  final bool runGitKnown;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.edit_outlined, size: 16, color: Color(0xFF9BA8BF)),
            const SizedBox(width: 8),
            Text(
              "Edited ${files.length} files",
              style: const TextStyle(
                color: Color(0xFFC7D2E5),
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFF1E222A),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFF343A46)),
          ),
          child: Column(
            children: [
              for (int i = 0; i < files.length; i += 1)
                Container(
                  height: 38,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    border: i == files.length - 1
                        ? null
                        : const Border(
                            bottom: BorderSide(color: Color(0xFF2D3442))),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          files[i],
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: Color(0xFFDCE4F2),
                            fontSize: 13,
                          ),
                        ),
                      ),
                      const Icon(Icons.check_circle_outline_rounded,
                          size: 19, color: Color(0xFF46C271)),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        _QualitySummaryPanel(
          qualityGate: qualityGate,
          prdScore: prdScore,
          visualScore: visualScore,
          smokeGate: smokeGate,
        ),
        const SizedBox(height: 10),
        _RunDeliveryPanel(
          previewUrl: runPreviewUrl,
          workspace: runWorkspace,
          gitStatus: runGitStatus,
          gitKnown: runGitKnown,
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            const Icon(Icons.flag_outlined, size: 15, color: Color(0xFF8FA0BB)),
            const SizedBox(width: 6),
            const Text(
              "Checkpoint",
              style: TextStyle(color: Color(0xFFB7C4DA), fontSize: 13),
            ),
            const Spacer(),
            TextButton(
              onPressed: () => _showDiffDialog(context),
              child: const Text("View diff"),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: () => _restoreFromCheckpoint(context),
              icon: const Icon(Icons.settings_backup_restore_rounded, size: 16),
              label: const Text("Restore"),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Color(0xFF4B5568)),
                foregroundColor: const Color(0xFFD6DEEC),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Future<void> _showDiffDialog(BuildContext context) async {
    final state = context.read<AppState>();
    final rid =
        (runId ?? state.lastCompletedRunId ?? state.activeRunId ?? "").trim();
    if (rid.isEmpty) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(content: Text("No checkpoint run found yet.")),
      );
      return;
    }

    final checkpoint = await state.getExecutionCheckpoint(runId: rid);
    if (checkpoint == null) {
      if (context.mounted) {
        ScaffoldMessenger.maybeOf(context)?.showSnackBar(
          SnackBar(content: Text("Failed to load checkpoint for run $rid")),
        );
      }
      return;
    }
    final checkpointBody = checkpoint["checkpoint"];
    final stage = checkpointBody is Map<String, dynamic>
        ? (checkpointBody["stage"] ?? "unknown").toString()
        : "unknown";
    final cpText = const JsonEncoder.withIndent("  ")
        .convert(checkpointBody ?? checkpoint);
    final diffText = await state.getWorkspaceDiff();

    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (ctx) {
        return AlertDialog(
          backgroundColor: const Color(0xFF1E222A),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: const BorderSide(color: Color(0xFF343A46)),
          ),
          title: Text("Checkpoint $rid"),
          content: SizedBox(
            width: 860,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("Stage: $stage",
                    style: const TextStyle(color: Color(0xFFD6DEEC))),
                const SizedBox(height: 8),
                const Text("Git diff",
                    style: TextStyle(
                        color: Color(0xFFAAB7CD), fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                Expanded(
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF171B23),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF343A46)),
                    ),
                    child: SelectableText(
                      diffText.trim().isEmpty
                          ? "No git diff available."
                          : diffText,
                      style: const TextStyle(
                        fontFamily: "JetBrains Mono",
                        fontSize: 12,
                        color: Color(0xFFDCE4F2),
                        height: 1.35,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                const Text("Checkpoint payload",
                    style: TextStyle(
                        color: Color(0xFFAAB7CD), fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                Expanded(
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: const Color(0xFF171B23),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: const Color(0xFF343A46)),
                    ),
                    child: SingleChildScrollView(
                      child: SelectableText(
                        cpText,
                        style: const TextStyle(
                          fontFamily: "JetBrains Mono",
                          fontSize: 12,
                          color: Color(0xFFC9D3E5),
                          height: 1.35,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text("Close")),
          ],
        );
      },
    );
  }

  Future<void> _restoreFromCheckpoint(BuildContext context) async {
    final state = context.read<AppState>();
    final rid =
        (runId ?? state.lastCompletedRunId ?? state.activeRunId ?? "").trim();
    if (rid.isEmpty) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(content: Text("No checkpoint run found yet.")),
      );
      return;
    }

    final ok = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1E222A),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(14),
              side: const BorderSide(color: Color(0xFF343A46)),
            ),
            title: const Text("Restore from checkpoint"),
            content: Text("Resume from run $rid ?"),
            actions: [
              TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: const Text("Cancel")),
              FilledButton(
                  onPressed: () => Navigator.of(ctx).pop(true),
                  child: const Text("Restore")),
            ],
          ),
        ) ??
        false;
    if (!ok) return;

    final resumedId = await state.restoreFromCheckpoint(runId: rid);
    if (!context.mounted) return;
    if (resumedId == null || resumedId.isEmpty) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        const SnackBar(content: Text("Checkpoint restore failed.")),
      );
      return;
    }
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      SnackBar(content: Text("Restore started: $resumedId")),
    );
  }
}

class _RunDeliveryPanel extends StatefulWidget {
  const _RunDeliveryPanel({
    required this.previewUrl,
    required this.workspace,
    required this.gitStatus,
    required this.gitKnown,
  });

  final String previewUrl;
  final String workspace;
  final GitStatusSnapshot? gitStatus;
  final bool gitKnown;

  @override
  State<_RunDeliveryPanel> createState() => _RunDeliveryPanelState();
}

class _RunDeliveryPanelState extends State<_RunDeliveryPanel> {
  bool _refreshingGit = false;
  bool _stagingGit = false;
  bool _committingGit = false;

  void _toast(String text, {bool error = false}) {
    ScaffoldMessenger.maybeOf(context)?.showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: error ? const Color(0xFFB94A48) : null,
      ),
    );
  }

  Future<void> _openPreviewInPanel() async {
    final state = context.read<AppState>();
    if (widget.previewUrl.trim().isEmpty) {
      _toast("Preview URL is not available yet.", error: true);
      return;
    }
    state.setPreferredRightPanelTab("preview");
    state.triggerPreviewReload();
    _toast("Preview panel switched.");
  }

  Future<void> _openPreviewInBrowser() async {
    final state = context.read<AppState>();
    final url = widget.previewUrl.trim();
    if (url.isEmpty) {
      _toast("Preview URL is not available yet.", error: true);
      return;
    }
    final ok = await state.openPreviewInExternalBrowser(url: url);
    if (!ok) {
      _toast("Failed to open preview in browser.", error: true);
    }
  }

  Future<void> _copyPreviewUrl() async {
    final url = widget.previewUrl.trim();
    if (url.isEmpty) {
      _toast("Preview URL is not available yet.", error: true);
      return;
    }
    await Clipboard.setData(ClipboardData(text: url));
    _toast("Preview URL copied.");
  }

  Future<void> _refreshGitStatus() async {
    if (_refreshingGit) return;
    setState(() => _refreshingGit = true);
    final state = context.read<AppState>();
    final status = await state.refreshRunGitStatus();
    if (!mounted) return;
    setState(() => _refreshingGit = false);
    if (status == null) {
      _toast("Git status unavailable for workspace.", error: true);
      return;
    }
    _toast("Git status refreshed.");
  }

  Future<void> _stageAll() async {
    if (_stagingGit) return;
    setState(() => _stagingGit = true);
    final state = context.read<AppState>();
    final ok = await state.stageAllRunWorkspace();
    if (!mounted) return;
    setState(() => _stagingGit = false);
    _toast(ok ? "Git add -A completed." : "Git add -A failed.", error: !ok);
  }

  Future<void> _quickCommit() async {
    if (_committingGit) return;
    final ctrl = TextEditingController(text: "feat: run delivery update");
    final msg = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E222A),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: Color(0xFF343A46)),
        ),
        title: const Text("Quick Commit"),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: "Commit message",
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(""),
            child: const Text("Cancel"),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(ctrl.text.trim()),
            child: const Text("Commit"),
          ),
        ],
      ),
    );
    ctrl.dispose();
    if (!mounted) return;
    final commitMessage = (msg ?? "").trim();
    if (commitMessage.isEmpty) return;
    setState(() => _committingGit = true);
    final state = context.read<AppState>();
    final ok = await state.quickCommitRunWorkspace(
      message: commitMessage,
      stageAll: true,
    );
    if (!mounted) return;
    setState(() => _committingGit = false);
    _toast(ok ? "Commit created." : "Commit failed.", error: !ok);
  }

  @override
  Widget build(BuildContext context) {
    final previewUrl = widget.previewUrl.trim();
    final workspace = widget.workspace.trim();
    final git = widget.gitStatus;
    final gitSummary = git == null
        ? (widget.gitKnown ? "Git status unavailable" : "Git not initialized")
        : "branch=${git.branch.isEmpty ? "(detached)" : git.branch}, changed=${git.files.length}, clean=${git.isClean}";

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E222A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.rocket_launch_outlined,
                  size: 15, color: Color(0xFF8FA0BB)),
              SizedBox(width: 6),
              Text(
                "Run Delivery",
                style: TextStyle(
                    color: Color(0xFFC7D2E5),
                    fontSize: 13,
                    fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            "Preview: ${previewUrl.isEmpty ? "n/a" : previewUrl}",
            style: const TextStyle(color: Color(0xFFA9B7CD), fontSize: 12),
          ),
          const SizedBox(height: 3),
          Text(
            "Workspace: ${workspace.isEmpty ? "n/a" : workspace}",
            style: const TextStyle(color: Color(0xFFA9B7CD), fontSize: 12),
          ),
          const SizedBox(height: 3),
          Text(
            "Git: $gitSummary",
            style: const TextStyle(color: Color(0xFFA9B7CD), fontSize: 12),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton.icon(
                onPressed: _openPreviewInPanel,
                icon: const Icon(Icons.play_circle_outline_rounded, size: 16),
                label: const Text("Open Preview"),
              ),
              OutlinedButton.icon(
                onPressed: _openPreviewInBrowser,
                icon: const Icon(Icons.open_in_browser_rounded, size: 16),
                label: const Text("Open Browser"),
              ),
              OutlinedButton.icon(
                onPressed: _copyPreviewUrl,
                icon: const Icon(Icons.copy_rounded, size: 16),
                label: const Text("Copy URL"),
              ),
              OutlinedButton.icon(
                onPressed: _refreshingGit ? null : _refreshGitStatus,
                icon: _refreshingGit
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 1.7),
                      )
                    : const Icon(Icons.sync_rounded, size: 16),
                label: const Text("Git Status"),
              ),
              OutlinedButton.icon(
                onPressed: _stagingGit ? null : _stageAll,
                icon: _stagingGit
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(strokeWidth: 1.7),
                      )
                    : const Icon(Icons.playlist_add_check_rounded, size: 16),
                label: const Text("Git Add -A"),
              ),
              FilledButton.icon(
                onPressed: _committingGit ? null : _quickCommit,
                icon: _committingGit
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                            strokeWidth: 1.7, color: Colors.white),
                      )
                    : const Icon(Icons.done_all_rounded, size: 16),
                label: const Text("Quick Commit"),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _QualitySummaryPanel extends StatelessWidget {
  const _QualitySummaryPanel({
    required this.qualityGate,
    required this.prdScore,
    required this.visualScore,
    required this.smokeGate,
  });

  final Map<String, dynamic> qualityGate;
  final Map<String, dynamic> prdScore;
  final Map<String, dynamic> visualScore;
  final Map<String, dynamic> smokeGate;

  @override
  Widget build(BuildContext context) {
    final qStatus = (qualityGate["final_status"] ?? "unknown").toString();
    final qReworks = int.tryParse("${qualityGate["auto_reworks"] ?? 0}") ?? 0;
    final prdTotal = double.tryParse("${prdScore["total"] ?? 0}") ?? 0;
    final prdVerdict = (prdScore["verdict"] ?? "n/a").toString();
    final prdScoresRaw = prdScore["scores"];
    final prdScores = prdScoresRaw is Map
        ? Map<String, dynamic>.from(prdScoresRaw)
        : const <String, dynamic>{};
    final visualTotal = double.tryParse("${visualScore["total"] ?? 0}") ?? 0;
    final visualVerdict = (visualScore["verdict"] ?? "n/a").toString();
    final visualScoresRaw = visualScore["scores"];
    final visualScores = visualScoresRaw is Map
        ? Map<String, dynamic>.from(visualScoresRaw)
        : const <String, dynamic>{};
    final smokeOk = smokeGate["ok"] == true;
    final smokeSummary = (smokeGate["summary"] ?? "n/a").toString();
    final history = qualityGate["history"];
    final rows =
        history is List ? history.whereType<Map>().toList() : const <Map>[];
    final finalIssues =
        int.tryParse("${qualityGate["final_issues_count"] ?? 0}") ?? 0;

    Color statusColor(String s) {
      switch (s.toLowerCase()) {
        case "ok":
        case "pass":
          return const Color(0xFF46C271);
        case "warn":
          return const Color(0xFFF4B740);
        case "fail":
          return const Color(0xFFD96A6A);
        default:
          return const Color(0xFF8FA0BB);
      }
    }

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFF1E222A),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            "Quality Gate",
            style: TextStyle(
                color: Color(0xFFC7D2E5),
                fontSize: 13,
                fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MetricChip(
                label: "Review",
                value: qStatus,
                color: statusColor(qStatus),
              ),
              _MetricChip(
                label: "Auto Rework",
                value: "$qReworks",
                color: const Color(0xFF8FA0BB),
              ),
              _MetricChip(
                label: "PRD",
                value: "${prdTotal.toStringAsFixed(1)} ($prdVerdict)",
                color: statusColor(prdVerdict),
              ),
              _MetricChip(
                label: "Visual",
                value: "${visualTotal.toStringAsFixed(1)} ($visualVerdict)",
                color: statusColor(visualVerdict),
              ),
              _MetricChip(
                label: "Smoke",
                value: smokeOk ? "pass" : "fail",
                color:
                    smokeOk ? const Color(0xFF46C271) : const Color(0xFFD96A6A),
              ),
              _MetricChip(
                label: "Issues",
                value: "$finalIssues",
                color: finalIssues == 0
                    ? const Color(0xFF46C271)
                    : const Color(0xFFD96A6A),
              ),
            ],
          ),
          if (prdScores.isNotEmpty) ...[
            const SizedBox(height: 10),
            _ScoreBar(
                label: "File",
                value:
                    double.tryParse("${prdScores["file_coverage"] ?? 0}") ?? 0),
            _ScoreBar(
                label: "Runtime",
                value:
                    double.tryParse("${prdScores["runtime_entry"] ?? 0}") ?? 0),
            _ScoreBar(
                label: "Interact",
                value:
                    double.tryParse("${prdScores["interaction"] ?? 0}") ?? 0),
            _ScoreBar(
                label: "UX",
                value: double.tryParse("${prdScores["ux_design"] ?? 0}") ?? 0),
            _ScoreBar(
                label: "Hygiene",
                value: double.tryParse("${prdScores["hygiene"] ?? 0}") ?? 0),
          ],
          if (visualScores.isNotEmpty) ...[
            const SizedBox(height: 10),
            _ScoreBar(
                label: "Token",
                value:
                    double.tryParse("${visualScores["design_tokens"] ?? 0}") ??
                        0),
            _ScoreBar(
                label: "Visual",
                value: double.tryParse(
                        "${visualScores["visual_hierarchy"] ?? 0}") ??
                    0),
            _ScoreBar(
                label: "Type",
                value:
                    double.tryParse("${visualScores["typography"] ?? 0}") ?? 0),
            _ScoreBar(
                label: "Motion",
                value: double.tryParse(
                        "${visualScores["motion_feedback"] ?? 0}") ??
                    0),
            _ScoreBar(
                label: "Polish",
                value: double.tryParse("${visualScores["game_polish"] ?? 0}") ??
                    0),
          ],
          if (rows.isNotEmpty) ...[
            const SizedBox(height: 8),
            for (final item in rows)
              _CycleRow(item: Map<String, dynamic>.from(item)),
          ],
          if (rows.isEmpty && smokeSummary.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              smokeSummary,
              style: const TextStyle(color: Color(0xFF9BA8BF), fontSize: 12),
            ),
          ],
        ],
      ),
    );
  }
}

class _ScoreBar extends StatelessWidget {
  const _ScoreBar({required this.label, required this.value});

  final String label;
  final double value;

  @override
  Widget build(BuildContext context) {
    final clamped = value.isNaN ? 0.0 : value.clamp(0, 100).toDouble();
    final Color c = clamped >= 80
        ? const Color(0xFF46C271)
        : (clamped >= 65 ? const Color(0xFFF4B740) : const Color(0xFFD96A6A));
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Row(
        children: [
          SizedBox(
            width: 58,
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFF9BA8BF), fontSize: 11),
            ),
          ),
          Expanded(
            child: Container(
              height: 7,
              decoration: BoxDecoration(
                color: const Color(0xFF11151D),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF2D3442)),
              ),
              child: FractionallySizedBox(
                alignment: Alignment.centerLeft,
                widthFactor: clamped / 100.0,
                child: Container(
                  decoration: BoxDecoration(
                    color: c,
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 34,
            child: Text(
              clamped.toStringAsFixed(0),
              textAlign: TextAlign.right,
              style: TextStyle(
                  color: c, fontSize: 11, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip(
      {required this.label, required this.value, required this.color});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF171B23),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF343A46)),
      ),
      child: RichText(
        text: TextSpan(
          style: const TextStyle(fontSize: 12, color: Color(0xFF9BA8BF)),
          children: [
            TextSpan(text: "$label: "),
            TextSpan(
              text: value,
              style: TextStyle(color: color, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}

class _CycleRow extends StatelessWidget {
  const _CycleRow({required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context) {
    final cycle = int.tryParse("${item["cycle"] ?? 0}") ?? 0;
    final status = (item["status"] ?? "unknown").toString();
    final issueCount = int.tryParse("${item["issues_count"] ?? 0}") ?? 0;
    final filesRaw = item["issue_files"];
    final issueFiles = filesRaw is List
        ? filesRaw.map((e) => "$e").where((e) => e.trim().isNotEmpty).toList()
        : const <String>[];
    final reasonsRaw = item["reasons"];
    final reasons = reasonsRaw is List
        ? reasonsRaw.map((e) => "$e").where((e) => e.isNotEmpty).toList()
        : const <String>[];
    final fileSummary =
        issueFiles.isEmpty ? "" : " files=${issueFiles.take(3).join("|")}";
    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Text(
        "Cycle $cycle  $status  issues=$issueCount  ${reasons.join(", ")}$fileSummary",
        style: const TextStyle(
            color: Color(0xFF9BA8BF), fontSize: 12, height: 1.3),
      ),
    );
  }
}

class _Avatar extends StatelessWidget {
  const _Avatar({required this.label, required this.isUser});

  final String label;
  final bool isUser;

  @override
  Widget build(BuildContext context) {
    final initial = label.trim().isEmpty
        ? (isUser ? "Y" : "R")
        : label.trim()[0].toUpperCase();
    return Container(
      width: 30,
      height: 30,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(9),
        gradient: isUser
            ? const LinearGradient(
                colors: [Color(0xFF3D90FA), Color(0xFF0A84FF)],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              )
            : const LinearGradient(
                colors: [Color(0xFF2E7A6D), Color(0xFF1F504A)],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
        border: Border.all(color: _ChatViewState._border),
      ),
      child: Center(
        child: Text(
          initial,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class _ComposerBar extends StatefulWidget {
  const _ComposerBar({
    required this.controller,
    required this.focusNode,
    required this.running,
    required this.model,
    required this.models,
    required this.onModelChanged,
    required this.onSend,
    required this.onStop,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final bool running;
  final String model;
  final List<String> models;
  final ValueChanged<String> onModelChanged;
  final VoidCallback onSend;
  final VoidCallback onStop;

  @override
  State<_ComposerBar> createState() => _ComposerBarState();
}

class _ComposerBarState extends State<_ComposerBar> {
  bool _focused = false;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _hasText = widget.controller.text.trim().isNotEmpty;
    widget.controller.addListener(_onTextChanged);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_onTextChanged);
    super.dispose();
  }

  void _onTextChanged() {
    final next = widget.controller.text.trim().isNotEmpty;
    if (next != _hasText) {
      setState(() => _hasText = next);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: _ChatViewState._bg,
        border: Border(top: BorderSide(color: _ChatViewState._border)),
      ),
      padding: const EdgeInsets.fromLTRB(16, 10, 16, 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _ModelDropdown(
            value: widget.model,
            items: widget.models,
            onChanged: widget.onModelChanged,
          ),
          const SizedBox(height: 10),
          Focus(
            onFocusChange: (focused) => setState(() => _focused = focused),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 140),
              padding: const EdgeInsets.fromLTRB(AppTokens.space10,
                  AppTokens.space8, AppTokens.space8, AppTokens.space8),
              decoration: BoxDecoration(
                color: _ChatViewState._panelSoft,
                borderRadius: BorderRadius.circular(AppTokens.radiusXl),
                border: Border.all(
                  color: _focused
                      ? _ChatViewState._accent
                      : _ChatViewState._border,
                  width: _focused ? 1.4 : 1.0,
                ),
                boxShadow: _focused
                    ? const [
                        BoxShadow(
                          color: Color(0x220A84FF),
                          blurRadius: 10,
                          offset: Offset(0, 2),
                        ),
                      ]
                    : null,
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Expanded(
                    child: TextField(
                      controller: widget.controller,
                      focusNode: widget.focusNode,
                      minLines: 1,
                      maxLines: 7,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => widget.onSend(),
                      cursorColor: _ChatViewState._accent,
                      style: const TextStyle(
                        color: AppTokens.textPrimary,
                        fontSize: AppTokens.textMd,
                        height: 1.35,
                      ),
                      decoration: const InputDecoration(
                        hintText: "Message Rebot...",
                        hintStyle: TextStyle(
                          color: AppTokens.textTertiary,
                          fontSize: AppTokens.textMd,
                        ),
                        isDense: true,
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(
                          vertical: 10,
                          horizontal: 2,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: AppTokens.space8),
                  _SendOrStopButton(
                    running: widget.running,
                    enabled: _hasText || widget.running,
                    onSend: widget.onSend,
                    onStop: widget.onStop,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ModelDropdown extends StatelessWidget {
  const _ModelDropdown({
    required this.value,
    required this.items,
    required this.onChanged,
  });

  final String value;
  final List<String> items;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final selected = items.contains(value)
        ? value
        : (items.isNotEmpty ? items.first : value);
    return Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: 11),
      decoration: BoxDecoration(
        color: _ChatViewState._panelSoft,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: _ChatViewState._border),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          value: selected,
          iconEnabledColor: _ChatViewState._muted,
          dropdownColor: _ChatViewState._panel,
          style: const TextStyle(
            color: _ChatViewState._text,
            fontSize: 12,
          ),
          items: items
              .map(
                (m) => DropdownMenuItem<String>(
                  value: m,
                  child: Text(m, overflow: TextOverflow.ellipsis),
                ),
              )
              .toList(),
          onChanged: (next) {
            if (next != null) {
              onChanged(next);
            }
          },
        ),
      ),
    );
  }
}

class _SendOrStopButton extends StatefulWidget {
  const _SendOrStopButton({
    required this.running,
    required this.enabled,
    required this.onSend,
    required this.onStop,
  });

  final bool running;
  final bool enabled;
  final VoidCallback onSend;
  final VoidCallback onStop;

  @override
  State<_SendOrStopButton> createState() => _SendOrStopButtonState();
}

class _SendOrStopButtonState extends State<_SendOrStopButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final bg = widget.running
        ? (_hovered ? const Color(0xFFE05C5C) : _ChatViewState._danger)
        : widget.enabled
            ? (_hovered ? const Color(0xFF2A98FF) : _ChatViewState._accent)
            : const Color(0xFF3B4150);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      cursor:
          widget.enabled ? SystemMouseCursors.click : SystemMouseCursors.basic,
      child: GestureDetector(
        onTap: widget.enabled
            ? (widget.running ? widget.onStop : widget.onSend)
            : null,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(11),
            border: Border.all(
              color: widget.enabled
                  ? const Color(0x66FFFFFF)
                  : const Color(0xFF52596B),
            ),
          ),
          child: Icon(
            widget.running ? Icons.stop_rounded : Icons.arrow_upward_rounded,
            size: 19,
            color: widget.enabled ? Colors.white : const Color(0xFF8B92A5),
          ),
        ),
      ),
    );
  }
}

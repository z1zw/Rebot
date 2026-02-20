// ══════════════════════════════════════════════════════════�?// app_state.dart �?Required models & interface reference
//
// This file shows the MINIMUM interface your AppState must
// provide for the new UI to compile. Merge these additions
// into your existing AppState.
// ══════════════════════════════════════════════════════════�?
import "package:flutter/material.dart";
import "package:http/http.dart" as http;
import "dart:async";
import "dart:convert";
import "dart:io";
import "services/agent_service.dart";
import "services/sse_service.dart";
import "services/api_service.dart";

// ─── Models ───────────────────────────────────────────────

class Project {
  final String id;
  final String name;
  final String description;
  final String framework; // canonical runtime framework
  final String
      projectType; // user-facing type: flutter/react/vue/python/uniapp/wechat_miniprogram/general
  final String workspacePath;
  final DateTime createdAt;
  final DateTime updatedAt;

  Project({
    required this.id,
    required this.name,
    this.description = "",
    this.framework = "flutter",
    this.projectType = "flutter",
    this.workspacePath = "",
    DateTime? createdAt,
    DateTime? updatedAt,
  })  : createdAt = createdAt ?? DateTime.now(),
        updatedAt = updatedAt ?? DateTime.now();
}

class Conversation {
  final String id;
  final String title;
  final String lastMessage;
  final DateTime createdAt;

  Conversation({
    required this.id,
    this.title = "",
    this.lastMessage = "",
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();

  Conversation copyWith({
    String? title,
    String? lastMessage,
  }) {
    return Conversation(
      id: id,
      title: title ?? this.title,
      lastMessage: lastMessage ?? this.lastMessage,
      createdAt: createdAt,
    );
  }
}

class Message {
  final String role; // "user" | "assistant"
  final String content;
  final DateTime createdAt;
  final String? mode; // "Code Agent", "Designer", etc.
  final double? attention;
  final String? agentName; // "Alex", "Sam", etc.
  final String? agentRole; // "Engineer", "Designer", etc.
  final int? steps;
  final int? stepsComplete;
  final List<String>? generatedFiles;

  Message({
    required this.role,
    required this.content,
    DateTime? createdAt,
    this.mode,
    this.attention,
    this.agentName,
    this.agentRole,
    this.steps,
    this.stepsComplete,
    this.generatedFiles,
  }) : createdAt = createdAt ?? DateTime.now();
}

class FileNode {
  final String name;
  final String path;
  final bool isDir;
  final bool isGenerating;
  final List<FileNode> children;

  FileNode({
    required this.name,
    required this.path,
    this.isDir = false,
    this.isGenerating = false,
    this.children = const [],
  });

  FileNode copyWith({
    String? name,
    String? path,
    bool? isDir,
    bool? isGenerating,
    List<FileNode>? children,
  }) {
    return FileNode(
      name: name ?? this.name,
      path: path ?? this.path,
      isDir: isDir ?? this.isDir,
      isGenerating: isGenerating ?? this.isGenerating,
      children: children ?? this.children,
    );
  }
}

class GeneratedFile {
  final String path;
  final String status; // "writing" | "done"
  final String content;

  GeneratedFile(
      {required this.path, this.status = "writing", this.content = ""});
}

class ConsoleLog {
  final String text;
  final String level; // "info" | "success" | "warning" | "error" | "default"

  ConsoleLog({required this.text, this.level = "default"});
}

// ─── AppState ─────────────────────────────────────────────

class AppState extends ChangeNotifier {
  AppState() {
    _loadSettings();
    // Delay self-healing loop to avoid blocking startup
    Future.delayed(const Duration(seconds: 3), () {
      _startSelfHealingLoop();
    });
  }

  @override
  void dispose() {
    _fileTreeRefreshTimer?.cancel();
    _selfHealTimer?.cancel();
    _notifyThrottleTimer?.cancel();
    _saveDebouncerTimer?.cancel();
    super.dispose();
  }

  // ── Global throttle: the first call fires immediately; subsequent
  //    calls within 50 ms are coalesced into a single delayed notify.
  Timer? _notifyThrottleTimer;
  bool _notifyPending = false;

  @override
  void notifyListeners() {
    if (_notifyThrottleTimer?.isActive == true) {
      _notifyPending = true;
      return;
    }
    super.notifyListeners();
    _notifyThrottleTimer = Timer(const Duration(milliseconds: 50), () {
      if (_notifyPending) {
        _notifyPending = false;
        super.notifyListeners();
      }
    });
  }

  // ─── API Service (Unified Backend Integration) ───
  String get _resolvedServerApiKey {
    final explicit = _backendApiKey.trim();
    if (explicit.isNotEmpty) return explicit;
    return _apiKey.trim();
  }

  Map<String, String> _backendHeaders({bool json = false}) {
    final headers = <String, String>{};
    if (json) headers["Content-Type"] = "application/json";
    final key = _resolvedServerApiKey;
    if (key.isNotEmpty) headers["X-API-Key"] = key;
    return headers;
  }

  ApiService get api => ApiService(
        baseUrl: _baseUrl,
        serverApiKey: _resolvedServerApiKey,
      );

  // ������ Project management ������
  final List<Project> _projects = [];
  Project? _activeProject;
  String? _currentProjectId;
  final Map<String, List<Conversation>> _scopedConversations = {};
  final Map<String, String?> _scopedActiveConversationId = {};
  final Map<String, Map<String, List<Message>>> _scopedConversationMessages =
      {};
  final Map<String, List<Message>> _scopedMessages = {};
  final Map<String, List<ConsoleLog>> _scopedConsoleLogs = {};
  final Map<String, List<GeneratedFile>> _scopedGeneratedFiles = {};
  final Map<String, List<FileNode>> _scopedFileTree = {};
  final Map<String, String> _scopedActiveFilePath = {};
  final Map<String, String> _scopedActiveFileContent = {};
  final Map<String, List<String>> _scopedOpenFileTabs = {};

  List<Project> get projects => _projects;
  Project? get activeProject => _activeProject;
  String? get currentProjectId => _currentProjectId;

  void createProject({
    required String name,
    String description = "",
    String framework = "flutter",
    String? projectType,
    String workspacePath = "",
  }) {
    _persistCurrentProjectScope();
    final normalizedType = _normalizeProjectType(projectType ?? framework);
    final runtimeFramework =
        _runtimeFrameworkForProjectType(normalizedType, fallback: framework);
    final project = Project(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      name: name,
      description: description,
      framework: runtimeFramework,
      projectType: normalizedType,
      workspacePath: workspacePath,
    );
    _projects.insert(0, project);
    _activeProject = project;
    _currentProjectId = project.id;
    _selectedFramework = runtimeFramework;
    _applyScopedState(project.id, cleanSlateIfMissing: true);
    _saveSettingsSoon();
    notifyListeners();
  }

  void openProject(String id) {
    _persistCurrentProjectScope();
    _activeProject = _projects.firstWhere((p) => p.id == id);
    _currentProjectId = id;
    _selectedFramework = _runtimeFrameworkForProjectType(
      _activeProject?.projectType ??
          _activeProject?.framework ??
          _selectedFramework,
      fallback: _activeProject?.framework ?? _selectedFramework,
    );
    _applyScopedState(id, cleanSlateIfMissing: true);
    notifyListeners();
  }

  void closeProject() {
    _persistCurrentProjectScope();
    _activeProject = null;
    _currentProjectId = null;
    resetState(notify: false);
    notifyListeners();
  }

  void deleteProject(String id) {
    if (_currentProjectId == id) {
      _persistCurrentProjectScope();
      _currentProjectId = null;
      _activeProject = null;
      resetState(notify: false);
    }
    _scopedConversations.remove(id);
    _scopedActiveConversationId.remove(id);
    _scopedConversationMessages.remove(id);
    _scopedMessages.remove(id);
    _scopedConsoleLogs.remove(id);
    _scopedGeneratedFiles.remove(id);
    _scopedFileTree.remove(id);
    _scopedActiveFilePath.remove(id);
    _scopedActiveFileContent.remove(id);
    _scopedOpenFileTabs.remove(id);
    _projects.removeWhere((p) => p.id == id);
    if (_activeProject?.id == id) _activeProject = null;
    notifyListeners();
  }

  void resetState({bool notify = true}) {
    _conversations = [];
    _activeConversationId = null;
    _conversationMessages.clear();
    _messages = [];
    _consoleLogs.clear();
    _generatedFiles = [];
    _fileTree = [];
    _activeFilePath = "";
    _activeFileContent = "";
    _workspaceResolvedPath = "";
    _openFileTabs.clear();
    _activeRunId = null;
    _activeRunStream = null;
    _status = "idle";
    _executionStatus = "idle";
    _executionProgress = "";
    _stepMessageIndex.clear();
    _explorerBecameEmptyAt = null;
    _previewBecameUnavailableAt = null;
    _previewBlockedByMissingEntry = false;
    _lastRunPreviewUrl = "";
    _lastRunWorkspace = "";
    _lastRunGitStatus = null;
    _lastRunGitKnown = false;
    _silentGenerateUI = false;
    _activeStage = "";
    _planSummary = "";
    _planFiles = [];
    _astDepAddedLinks = 0;
    _astDepTouchedFiles = 0;
    _astDepTotalEdges = 0;
    _astDepAttempt = 0;
    _astDepAddedEdges = [];
    for (final k in _stageStatus.keys) {
      _stageStatus[k] = "pending";
    }
    if (notify) {
      notifyListeners();
    }
  }

  void _persistCurrentProjectScope() {
    final pid = _currentProjectId;
    if (pid == null || pid.trim().isEmpty) return;
    _scopedConversations[pid] = List<Conversation>.from(_conversations);
    _scopedActiveConversationId[pid] = _activeConversationId;
    final convMap = <String, List<Message>>{};
    _conversationMessages.forEach((k, v) {
      convMap[k] = List<Message>.from(v);
    });
    _scopedConversationMessages[pid] = convMap;
    _scopedMessages[pid] = List<Message>.from(_messages);
    _scopedConsoleLogs[pid] = List<ConsoleLog>.from(_consoleLogs);
    _scopedGeneratedFiles[pid] = List<GeneratedFile>.from(_generatedFiles);
    _scopedFileTree[pid] = List<FileNode>.from(_fileTree);
    _scopedActiveFilePath[pid] = _activeFilePath;
    _scopedActiveFileContent[pid] = _activeFileContent;
    _scopedOpenFileTabs[pid] = List<String>.from(_openFileTabs);
  }

  void _applyScopedState(String pid, {bool cleanSlateIfMissing = true}) {
    if (!_scopedConversations.containsKey(pid) && cleanSlateIfMissing) {
      resetState(notify: false);
      return;
    }
    _conversations = List<Conversation>.from(
        _scopedConversations[pid] ?? const <Conversation>[]);
    _activeConversationId = _scopedActiveConversationId[pid];
    _conversationMessages.clear();
    final storedConvMap =
        _scopedConversationMessages[pid] ?? const <String, List<Message>>{};
    storedConvMap.forEach((k, v) {
      _conversationMessages[k] = List<Message>.from(v);
    });
    _messages = List<Message>.from(_scopedMessages[pid] ?? const <Message>[]);
    _consoleLogs
      ..clear()
      ..addAll(_scopedConsoleLogs[pid] ?? const <ConsoleLog>[]);
    _generatedFiles = List<GeneratedFile>.from(
        _scopedGeneratedFiles[pid] ?? const <GeneratedFile>[]);
    _fileTree = List<FileNode>.from(_scopedFileTree[pid] ?? const <FileNode>[]);
    _activeFilePath = _scopedActiveFilePath[pid] ?? "";
    _activeFileContent = _scopedActiveFileContent[pid] ?? "";
    _workspaceResolvedPath = "";
    _openFileTabs
      ..clear()
      ..addAll(_scopedOpenFileTabs[pid] ?? const <String>[]);
    _activeRunId = null;
    _activeRunStream = null;
    _status = "idle";
    _executionStatus = "idle";
    _executionProgress = "";
    _stepMessageIndex.clear();
    _explorerBecameEmptyAt = null;
    _previewBecameUnavailableAt = null;
    _previewBlockedByMissingEntry = false;
    _lastRunPreviewUrl = "";
    _lastRunWorkspace = "";
    _lastRunGitStatus = null;
    _lastRunGitKnown = false;
    _silentGenerateUI = false;
    _activeStage = "";
    _planSummary = "";
    _planFiles = [];
    _astDepAddedLinks = 0;
    _astDepTouchedFiles = 0;
    _astDepTotalEdges = 0;
    _astDepAttempt = 0;
    _astDepAddedEdges = [];
    for (final k in _stageStatus.keys) {
      _stageStatus[k] = "pending";
    }
  }

  // ─── Conversations ───
  List<Conversation> _conversations = [];
  String? _activeConversationId;
  final Map<String, List<Message>> _conversationMessages = {};

  /// Raw JSON kept so we can lazily parse conversations on demand
  /// instead of deserializing every message at startup.
  dynamic _rawConversationMessagesJson;

  List<Conversation> get conversations => _conversations;
  String? get activeConversationId => _activeConversationId;
  String get activeConversationTitle {
    final id = _activeConversationId;
    if (id == null) return "Welcome";
    final idx = _conversations.indexWhere((c) => c.id == id);
    if (idx < 0) return "Welcome";
    final title = _conversations[idx].title.trim();
    return title.isEmpty ? "Welcome" : title;
  }

  void createConversation() {
    _persistActiveConversation();
    final conv = Conversation(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
    );
    _conversations.insert(0, conv);
    _activeConversationId = conv.id;
    _messages.clear();
    _conversationMessages[conv.id] = [];
    _saveSettingsSoon();
    notifyListeners();
  }

  void switchConversation(String id) {
    if (!_conversations.any((c) => c.id == id)) return;
    _persistActiveConversation();
    _activeConversationId = id;
    // Lazy-load messages from raw JSON if not yet deserialized.
    if (!_conversationMessages.containsKey(id)) {
      _lazyLoadConversationMessages(id);
    }
    _messages =
        List<Message>.from(_conversationMessages[id] ?? const <Message>[]);
    _stepMessageIndex.clear();
    _saveSettingsSoon();
    notifyListeners();
  }

  /// Deserialize a single conversation's messages from the raw JSON cache.
  void _lazyLoadConversationMessages(String id) {
    final raw = _rawConversationMessagesJson;
    if (raw is Map && raw.containsKey(id)) {
      final value = raw[id];
      if (value is List) {
        final msgs = <Message>[];
        for (final m in value) {
          if (m is Map<String, dynamic>) {
            msgs.add(_messageFromJson(m));
          }
        }
        _conversationMessages[id] = msgs;
      }
    }
  }

  void renameConversation(String id, String title) {
    final next = title.trim();
    if (next.isEmpty) return;
    final idx = _conversations.indexWhere((c) => c.id == id);
    if (idx < 0) return;
    _conversations[idx] = _conversations[idx].copyWith(title: next);
    _saveSettingsSoon();
    notifyListeners();
  }

  void deleteConversation(String id) {
    _conversationMessages.remove(id);
    // Also remove from raw JSON cache so it won't reappear on save.
    if (_rawConversationMessagesJson is Map) {
      (_rawConversationMessagesJson as Map).remove(id);
    }
    _conversations.removeWhere((c) => c.id == id);
    if (_activeConversationId == id) {
      _activeConversationId =
          _conversations.isEmpty ? null : _conversations.first.id;
      if (_activeConversationId != null &&
          !_conversationMessages.containsKey(_activeConversationId!)) {
        _lazyLoadConversationMessages(_activeConversationId!);
      }
      _messages = _activeConversationId == null
          ? <Message>[]
          : List<Message>.from(_conversationMessages[_activeConversationId!] ??
              const <Message>[]);
    }
    _saveSettingsSoon();
    notifyListeners();
  }

  void clearMessages() {
    _messages.clear();
    _stepMessageIndex.clear();
    if (_activeConversationId != null) {
      _conversationMessages[_activeConversationId!] = [];
    }
    _saveSettingsSoon();
    notifyListeners();
  }

  // ─── Chat ───
  List<Message> _messages = [];
  String _lastPrompt = "";
  String _status = "idle";
  String? _activeRunId;
  String? _lastCompletedRunId;
  final Map<String, dynamic> _lastRunMetrics = {};
  String _executionStatus = "idle";
  String _executionProgress = "";
  final AgentService _agentService = AgentService();
  AgentRunStream? _activeRunStream;
  int _runWatchdogEpoch = 0;
  final Map<int, int> _stepMessageIndex = {};
  Timer? _fileTreeRefreshTimer;
  DateTime _lastExplorerRefreshAt = DateTime.fromMillisecondsSinceEpoch(0);
  DateTime _lastExplorerSyncLogAt = DateTime.fromMillisecondsSinceEpoch(0);
  int _pendingExplorerSyncEvents = 0;
  DateTime _lastExecutionProgressAt = DateTime.fromMillisecondsSinceEpoch(0);
  String _lastExecutionProgressText = "";
  int _loadFilesRequestSeq = 0;
  int _loadFilesAppliedSeq = 0;
  Timer? _selfHealTimer;
  bool _selfHealingBusy = false;
  DateTime? _explorerBecameEmptyAt;
  DateTime? _previewBecameUnavailableAt;
  DateTime _lastSelfHealActionAt = DateTime.fromMillisecondsSinceEpoch(0);
  DateTime _lastPreview404RepairAt = DateTime.fromMillisecondsSinceEpoch(0);
  String _lastPreviewHealthReason = "unknown";
  bool _previewHealthy = false;
  bool _previewBlockedByMissingEntry = false;
  String _preferredRightPanelTab = "preview";
  int _preferredRightPanelSignal = 0;
  final Map<String, String> _stageStatus = {
    "design": "pending",
    "implement": "pending",
    "review": "pending",
    "test": "pending",
    "deploy": "pending",
  };
  String _activeStage = "";
  bool _silentGenerateUI = false;
  String _planSummary = "";
  List<String> _planFiles = [];
  int _astDepAddedLinks = 0;
  int _astDepTouchedFiles = 0;
  int _astDepTotalEdges = 0;
  int _astDepAttempt = 0;
  List<String> _astDepAddedEdges = [];
  Map<String, dynamic> _latestQualityGate = {};
  Map<String, dynamic> _latestPrdScore = {};
  Map<String, dynamic> _latestVisualScore = {};
  Map<String, dynamic> _latestSmokeGate = {};
  String _lastRunPreviewUrl = "";
  String _lastRunWorkspace = "";
  GitStatusSnapshot? _lastRunGitStatus;
  bool _lastRunGitKnown = false;
  String _linkedAutoGptAgentId = "";
  bool _linkedAutoGptWorkflowEnabled = true;

  List<Message> get messages => _messages;
  String get status => _status;
  String? get activeRunId => _activeRunId;
  String? get lastCompletedRunId => _lastCompletedRunId;
  Map<String, dynamic> get lastRunMetrics => _lastRunMetrics;
  String get executionStatus => _executionStatus;
  String get executionProgress => _executionProgress;
  String get preferredRightPanelTab => _preferredRightPanelTab;
  int get preferredRightPanelSignal => _preferredRightPanelSignal;
  bool get suppressEditorRefresh => _silentGenerateUI;
  bool get previewHealthy => _previewHealthy;
  String get previewHealthReason => _lastPreviewHealthReason;
  int get warningCount {
    var n = _consoleLogs
        .where((e) => e.level == "warning" || e.level == "error")
        .length;
    if (_executionStatus == "failed") n += 1;
    return n;
  }

  bool get cloudBusy =>
      _status == "running" || ((_activeRunId ?? "").isNotEmpty);
  String get planSummary => _planSummary;
  List<String> get planFiles => List.unmodifiable(_planFiles);
  int get astDepAddedLinks => _astDepAddedLinks;
  int get astDepTouchedFiles => _astDepTouchedFiles;
  int get astDepTotalEdges => _astDepTotalEdges;
  int get astDepAttempt => _astDepAttempt;
  List<String> get astDepAddedEdges => List.unmodifiable(_astDepAddedEdges);
  Map<String, dynamic> get latestQualityGate =>
      Map<String, dynamic>.from(_latestQualityGate);
  Map<String, dynamic> get latestPrdScore =>
      Map<String, dynamic>.from(_latestPrdScore);
  Map<String, dynamic> get latestVisualScore =>
      Map<String, dynamic>.from(_latestVisualScore);
  Map<String, dynamic> get latestSmokeGate =>
      Map<String, dynamic>.from(_latestSmokeGate);
  String get lastRunPreviewUrl => _lastRunPreviewUrl.trim();
  String get lastRunWorkspace => _lastRunWorkspace.trim().isEmpty
      ? activeWorkspacePath
      : _lastRunWorkspace.trim();
  GitStatusSnapshot? get lastRunGitStatus => _lastRunGitStatus;
  bool get lastRunGitKnown => _lastRunGitKnown;
  String get linkedAutoGptAgentId => _linkedAutoGptAgentId;
  bool get linkedAutoGptWorkflowEnabled => _linkedAutoGptWorkflowEnabled;

  void setLinkedAutoGptWorkflowEnabled(bool enabled) {
    _linkedAutoGptWorkflowEnabled = enabled;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setPreferredRightPanelTab(String tab) {
    final next = tab.trim().isEmpty ? "preview" : tab.trim();
    if (_preferredRightPanelTab == next) return;
    _preferredRightPanelTab = next;
    _preferredRightPanelSignal += 1;
    notifyListeners();
  }

  void sendMessage(String text) {
    final prompt = text.trim();
    if (prompt.isEmpty) return;
    _ensureActiveConversation();
    _messages.add(Message(role: "user", content: prompt));
    _lastPrompt = prompt;
    _syncActiveConversationMessages();
    _touchConversation(prompt);
    _status = "running";
    _executionStatus = "queued";
    _executionProgress = "Task queued";
    _activeRunId = DateTime.now().millisecondsSinceEpoch.toString();
    _generatedFiles = [];
    _explorerBecameEmptyAt = DateTime.now();
    _previewBecameUnavailableAt = DateTime.now();
    _previewBlockedByMissingEntry = false;
    _stepMessageIndex.clear();
    _planSummary = "";
    _planFiles = [];
    _astDepAddedLinks = 0;
    _astDepTouchedFiles = 0;
    _astDepTotalEdges = 0;
    _astDepAttempt = 0;
    _astDepAddedEdges = [];
    _latestQualityGate = {};
    _latestPrdScore = {};
    _latestVisualScore = {};
    _latestSmokeGate = {};
    _lastRunPreviewUrl = "";
    _lastRunWorkspace = activeWorkspacePath;
    _lastRunGitStatus = null;
    _lastRunGitKnown = false;
    for (final k in _stageStatus.keys) {
      _stageStatus[k] = "pending";
    }
    notifyListeners();
    _startSseRun(prompt);
  }

  /// 重新生成最后一条回复
  void regenerateLastResponse() {
    // 找到最后一条用户消息
    String? lastUserPrompt;
    int lastAssistantIndex = -1;

    for (int i = _messages.length - 1; i >= 0; i--) {
      if (_messages[i].role == "assistant" && lastAssistantIndex == -1) {
        lastAssistantIndex = i;
      }
      if (_messages[i].role == "user") {
        lastUserPrompt = _messages[i].content;
        break;
      }
    }

    if (lastUserPrompt == null) return;

    // 移除最后一条助手回复
    if (lastAssistantIndex != -1) {
      _messages.removeAt(lastAssistantIndex);
    }

    // 重新发送请求
    _lastPrompt = lastUserPrompt;
    _status = "running";
    _executionStatus = "queued";
    _executionProgress = "Regenerating...";
    _activeRunId = DateTime.now().millisecondsSinceEpoch.toString();
    _generatedFiles = [];
    _stepMessageIndex.clear();
    _planSummary = "";
    _planFiles = [];
    _astDepAddedLinks = 0;
    _astDepTouchedFiles = 0;
    _astDepTotalEdges = 0;
    _astDepAttempt = 0;
    _astDepAddedEdges = [];
    _latestQualityGate = {};
    _latestPrdScore = {};
    _latestVisualScore = {};
    _latestSmokeGate = {};
    _lastRunPreviewUrl = "";
    _lastRunWorkspace = activeWorkspacePath;
    _lastRunGitStatus = null;
    _lastRunGitKnown = false;
    for (final k in _stageStatus.keys) {
      _stageStatus[k] = "pending";
    }
    notifyListeners();
    _startSseRun(lastUserPrompt);
  }

  Future<void> _startSseRun(String prompt) async {
    try {
      _alignProviderAndBaseUrlWithModel();
      await _activeRunStream?.cancel();
      _runWatchdogEpoch += 1;
      // Debug log for framework
      _consoleLogs.add(ConsoleLog(
        text:
            "[frontend] Sending request with framework=$_selectedFramework, projectType=${_activeProject?.projectType}",
        level: "info",
      ));
      _activeRunStream = await _agentService.streamRun(
        prompt,
        baseUrl: _baseUrl,
        workspace: _workspacePath(),
        projectId: _activeProject?.id,
        projectType: _activeProject?.projectType ??
            _activeProject?.framework ??
            _selectedFramework,
        framework: _selectedFramework,
        apiKey: _apiKey,
        provider: _llmProvider,
        model: _model,
        llmBaseUrl: _llmBaseUrl,
        modelMaxConcurrency: _modelMaxConcurrency,
        priority: _runPriority,
        maxTokenBudget: _maxTokenBudget,
        maxCostBudget: _maxCostBudget,
        roleModelOverrides:
            _roleModelOverrides.isEmpty ? null : _roleModelOverrides,
        autogptAgentId: _linkedAutoGptAgentId.trim().isEmpty
            ? null
            : _linkedAutoGptAgentId.trim(),
        autogptWorkflowEnabled: _linkedAutoGptAgentId.trim().isNotEmpty &&
            _linkedAutoGptWorkflowEnabled,
        checkpointEnabled: _checkpointEnabled,
        smokeCheckEnabled: _smokeCheckEnabled,
        smokeReworkBudget: _smokeReworkBudget,
        serverApiKey: _resolvedServerApiKey,
      );

      _activeRunId = _activeRunStream!.runId;
      _executionStatus = "running";
      _executionProgress = "Run started";
      _consoleLogs
          .add(ConsoleLog(text: "Run started: $_activeRunId", level: "info"));
      _startRunWatchdog(_activeRunId!);
      notifyListeners();

      _activeRunStream!.stream.listen(
        _handleSseEvent,
        onError: (err) {
          _runWatchdogEpoch += 1;
          _executionStatus = "failed";
          _executionProgress = "SSE error: $err";
          _consoleLogs.add(ConsoleLog(text: "SSE error: $err", level: "error"));
          _status = "idle";
          _activeRunId = null;
          _activeRunStream = null;
          _saveSettingsSoon();
          notifyListeners();
        },
        onDone: () {
          _runWatchdogEpoch += 1;
          if (_status == "running") {
            _status = "idle";
            if (_executionStatus == "running" || _executionStatus == "queued") {
              _executionStatus = "completed";
              if (_executionProgress.isEmpty) _executionProgress = "Completed";
            }
            _activeRunId = null;
            _activeRunStream = null;
            _saveSettingsSoon();
            notifyListeners();
          }
        },
        cancelOnError: false,
      );
    } catch (err) {
      _runWatchdogEpoch += 1;
      _executionStatus = "failed";
      _executionProgress = "Run start failed: $err";
      _consoleLogs
          .add(ConsoleLog(text: "Run start failed: $err", level: "error"));
      _status = "idle";
      _activeRunId = null;
      _activeRunStream = null;
      _saveSettingsSoon();
      notifyListeners();
    }
  }

  void _startRunWatchdog(String runId) {
    final epoch = ++_runWatchdogEpoch;
    unawaited(Future<void>(() async {
      while (epoch == _runWatchdogEpoch) {
        if ((_activeRunId ?? "") != runId) break;
        final record = await api.getExecution(runId);
        if (record == null) {
          await Future.delayed(const Duration(seconds: 2));
          continue;
        }
        final status = record.status.trim().toLowerCase();
        if (record.progress.trim().isNotEmpty &&
            (_executionStatus == "running" || _executionStatus == "queued")) {
          _executionProgress = record.progress;
          notifyListeners();
        }
        if (status == "finished" ||
            status == "failed" ||
            status == "cancelled") {
          if (status == "finished") {
            _lastCompletedRunId = runId;
          }
          _updateRunQualityFromResult(record.result);
          _status = "idle";
          _executionStatus = status == "finished" ? "completed" : status;
          _executionProgress =
              record.progress.isEmpty ? _executionStatus : record.progress;
          if (status == "failed" && record.progress.trim().isNotEmpty) {
            _consoleLogs.add(ConsoleLog(
                text: "Run failed: ${record.progress}", level: "error"));
          }
          _activeRunId = null;
          _activeRunStream = null;
          _silentGenerateUI = false;
          _saveSettingsSoon();
          notifyListeners();
          break;
        }
        await Future.delayed(const Duration(seconds: 2));
      }
    }));
  }

  Future<void> forceRestartSseStream() async {
    if (_lastPrompt.isEmpty) {
      _consoleLogs.add(
          ConsoleLog(text: "No active prompt to reconnect.", level: "warning"));
      notifyListeners();
      return;
    }
    _consoleLogs
        .add(ConsoleLog(text: "Reconnecting SSE stream...", level: "info"));
    await _activeRunStream?.cancel();
    _activeRunStream = null;
    _messages.clear();
    _stepMessageIndex.clear();
    _executionStatus = "running";
    _executionProgress = "Reconnecting stream...";
    _status = "running";
    _ensureActiveConversation();
    notifyListeners();
    await _startSseRun(_lastPrompt);
  }

  Future<void> forceFileSynchronization() async {
    _consoleLogs
        .add(ConsoleLog(text: "Force file sync triggered.", level: "info"));
    await loadFiles();
    _consoleLogs.add(
        ConsoleLog(text: "File tree refreshed from disk.", level: "success"));
    notifyListeners();
  }

  void _handleSseEvent(SSEEvent evt) {
    final data = evt.data;
    switch (evt.event) {
      case "stage_update":
        final stage = (data["stage"] ?? "").toString();
        final status = (data["status"] ?? "").toString();
        if (stage.isNotEmpty) {
          _stageStatus[stage] = status.isEmpty ? "running" : status;
        }
        if (stage.isNotEmpty && (status.isEmpty || status == "running")) {
          _activeStage = stage;
        } else if (_activeStage == stage &&
            (status == "done" || status == "completed")) {
          _activeStage = "";
        }
        _executionStatus = status.isEmpty ? "running" : status;
        _executionProgress = stage.isEmpty
            ? _executionProgress
            : "Stage $stage: ${_stageStatus[stage]}";
        break;
      case "agent_message":
        final content = _sanitizeStreamText((data["content"] ?? "").toString());
        if (content.trim().isEmpty) break;
        if (_isNoisyStreamingFragment(content) ||
            _isCorruptedStreamText(content)) {
          _setExecutionProgressThinking();
          break;
        }
        if (_isProgressLikeMessage(content) || _isLikelyCodeNoise(content)) {
          _setExecutionProgressSmooth(_summarizeProgressMessage(content));
          break;
        }
        final compact = _compactAssistantNarrative(content);
        if (compact.isEmpty) {
          _setExecutionProgressThinking();
          break;
        }
        final payload = Map<String, dynamic>.from(data);
        payload["content"] = compact;
        _appendOrMergeAgentMessage(payload);
        if (_activeStage == "design") {
          _consumeDesignPlanMessage(compact);
        }
        break;
      case "plan_summary":
        _planSummary = (data["summary"] ?? "").toString();
        _planFiles = _coercePlanFiles(data["files"]);
        _consoleLogs.add(
          ConsoleLog(
            text: "Plan ready: ${_planFiles.length} files",
            level: "info",
          ),
        );
        break;
      case "agent_thought":
        final thought = (data["data"] ?? data["text"] ?? "").toString();
        if (thought.isNotEmpty) {
          _consoleLogs.add(ConsoleLog(text: thought, level: "info"));
          _appendReasoningMessage(thought);
        }
        break;
      case "plan_review":
        final confirmed = (data["confirmed"] ?? false) == true;
        final note = (data["notes"] ?? "").toString();
        _consoleLogs.add(ConsoleLog(
          text: confirmed
              ? "Plan review confirmed"
              : "Plan review requested changes",
          level: confirmed ? "success" : "warning",
        ));
        if (note.isNotEmpty) {
          _consoleLogs.add(ConsoleLog(text: note, level: "info"));
        }
        break;
      case "plan_ast_deps":
        _astDepAddedLinks = int.tryParse("${data["added_links"] ?? 0}") ?? 0;
        _astDepTouchedFiles =
            int.tryParse("${data["touched_files"] ?? 0}") ?? 0;
        _astDepTotalEdges = int.tryParse("${data["total_edges"] ?? 0}") ?? 0;
        _astDepAttempt = int.tryParse("${data["attempt"] ?? 0}") ?? 0;
        final edges = data["added_edges"];
        if (edges is List) {
          _astDepAddedEdges =
              edges.map((e) => "$e").where((e) => e.trim().isNotEmpty).toList();
        } else {
          _astDepAddedEdges = [];
        }
        _consoleLogs.add(
          ConsoleLog(
            text:
                "AST deps (attempt ${_astDepAttempt + 1}): +$_astDepAddedLinks links, $_astDepTouchedFiles files, total edges $_astDepTotalEdges",
            level: "info",
          ),
        );
        break;
      case "file_created":
        final path = (data["path"] ?? "").toString();
        final content = (data["content"] ?? "").toString();
        _markEntryCandidateSeen(path);
        _upsertGeneratedFile(path: path, status: "done", content: content);
        _upsertFileTreePath(path, isGenerating: false);
        if (path.isNotEmpty) {
          _consoleLogs
              .add(ConsoleLog(text: "Generated $path", level: "success"));
        }
        _refreshGeneratingUiFlag();
        _refreshExplorerAfterWrite(reason: "file_created:$path");
        break;
      case "file_generating":
        final path = (data["path"] ?? "").toString();
        _markEntryCandidateSeen(path);
        _upsertGeneratedFile(
          path: path,
          status: (data["status"] ?? "writing").toString(),
        );
        _upsertFileTreePath(path, isGenerating: true);
        _silentGenerateUI = true;
        _refreshGeneratingUiFlag();
        _refreshExplorerAfterWrite(
          reason: "file_generating:$path",
          minIntervalMs: 900,
          logEvent: false,
        );
        break;
      case "file_done":
        final path = (data["path"] ?? "").toString();
        final content = (data["content"] ?? "").toString();
        _markEntryCandidateSeen(path);
        _upsertGeneratedFile(
          path: path,
          status: (data["status"] ?? "done").toString(),
          content: content,
        );
        _upsertFileTreePath(path, isGenerating: false);
        _refreshGeneratingUiFlag();
        _refreshExplorerAfterWrite(reason: "file_done:$path");
        break;
      case "console_log":
        _consoleLogs.add(
          ConsoleLog(
            text: (data["text"] ?? "").toString(),
            level: (data["level"] ?? "default").toString(),
          ),
        );
        break;
      case "quality_gate_report":
        _latestQualityGate = Map<String, dynamic>.from(data);
        break;
      case "quality_gate_cycle":
        final cycle = Map<String, dynamic>.from(data);
        final next = Map<String, dynamic>.from(_latestQualityGate);
        final historyRaw = next["history"];
        final history = historyRaw is List
            ? historyRaw
                .whereType<Map>()
                .map((e) => Map<String, dynamic>.from(e))
                .toList()
            : <Map<String, dynamic>>[];
        final cycleNum = int.tryParse("${cycle["cycle"] ?? 0}") ?? 0;
        history
            .removeWhere((e) => int.tryParse("${e["cycle"] ?? 0}") == cycleNum);
        history.add(cycle);
        history.sort((a, b) => (int.tryParse("${a["cycle"] ?? 0}") ?? 0)
            .compareTo(int.tryParse("${b["cycle"] ?? 0}") ?? 0));
        next["history"] = history;
        next["final_status"] =
            cycle["status"] ?? next["final_status"] ?? "unknown";
        next["final_integration"] =
            cycle["integration"] ?? next["final_integration"] ?? "";
        next["final_issues_count"] =
            cycle["issues_count"] ?? next["final_issues_count"] ?? 0;
        _latestQualityGate = next;
        break;
      case "prd_score":
        _latestPrdScore = Map<String, dynamic>.from(data);
        break;
      case "visual_score":
        _latestVisualScore = Map<String, dynamic>.from(data);
        break;
      case "context_digest":
        final xml = (data["xml"] ?? "").toString();
        if (xml.isNotEmpty) {
          _consoleLogs.add(
            ConsoleLog(
              text: "Context digest generated (structured):\n$xml",
              level: "info",
            ),
          );
        }
        break;
      case "preview_ready":
        final url = (data["url"] ?? "").toString();
        if (url.isNotEmpty) {
          _previewUrl = url;
          _lastRunPreviewUrl = url;
          _lastRunWorkspace = activeWorkspacePath;
          unawaited(_ensurePreviewBridgeHealthy(retries: 3));
        }
        break;
      case "preview_health":
        _previewHealthy = (data["healthy"] ?? false) == true;
        _lastPreviewHealthReason = (data["reason"] ?? "unknown").toString();
        break;
      case "done":
        final doneRunId = (data["run_id"] ?? _activeRunId ?? "").toString();
        if (doneRunId.isNotEmpty) {
          _lastCompletedRunId = doneRunId;
        }
        final donePreview = (data["preview_url"] ?? "").toString().trim();
        if (donePreview.isNotEmpty) {
          _lastRunPreviewUrl = donePreview;
          _previewUrl = donePreview;
        }
        final doneWorkspace = (data["workspace"] ?? "").toString().trim();
        if (doneWorkspace.isNotEmpty) {
          _lastRunWorkspace = doneWorkspace;
        } else if (_lastRunWorkspace.trim().isEmpty) {
          _lastRunWorkspace = activeWorkspacePath;
        }
        if (data["quality_gate"] is Map<String, dynamic>) {
          _latestQualityGate = Map<String, dynamic>.from(
              data["quality_gate"] as Map<String, dynamic>);
        }
        if (data["prd_score"] is Map<String, dynamic>) {
          _latestPrdScore = Map<String, dynamic>.from(
              data["prd_score"] as Map<String, dynamic>);
        }
        if (data["visual_score"] is Map<String, dynamic>) {
          _latestVisualScore = Map<String, dynamic>.from(
              data["visual_score"] as Map<String, dynamic>);
        }
        if (data["smoke_gate"] is Map<String, dynamic>) {
          _latestSmokeGate = Map<String, dynamic>.from(
              data["smoke_gate"] as Map<String, dynamic>);
        }
        _runWatchdogEpoch += 1;
        _executionStatus = (data["status"] ?? "completed").toString();
        _executionProgress = _executionStatus;
        _status = "idle";
        _silentGenerateUI = false;
        _activeRunId = null;
        _activeRunStream = null;
        if (_executionStatus == "completed") {
          unawaited(_finalizeDelivery());
          unawaited(refreshRunGitStatus());
        }
        _saveSettingsSoon();
        break;
      default:
        break;
    }
    _syncActiveConversationMessages();
    notifyListeners(); // globally throttled by override
  }

  void _updateRunQualityFromResult(Map<String, dynamic>? result) {
    if (result == null) return;
    final preview = (result["preview_url"] ?? "").toString().trim();
    if (preview.isNotEmpty) {
      _lastRunPreviewUrl = preview;
      _previewUrl = preview;
    }
    final ws = (result["workspace"] ?? "").toString().trim();
    if (ws.isNotEmpty) {
      _lastRunWorkspace = ws;
    } else if (_lastRunWorkspace.trim().isEmpty) {
      _lastRunWorkspace = activeWorkspacePath;
    }
    final qualityGate = result["quality_gate"];
    final prdScore = result["prd_score"];
    final visualScore = result["visual_score"];
    final smokeGate = result["smoke_gate"];
    if (qualityGate is Map<String, dynamic>) {
      _latestQualityGate = Map<String, dynamic>.from(qualityGate);
    }
    if (prdScore is Map<String, dynamic>) {
      _latestPrdScore = Map<String, dynamic>.from(prdScore);
    }
    if (visualScore is Map<String, dynamic>) {
      _latestVisualScore = Map<String, dynamic>.from(visualScore);
    }
    if (smokeGate is Map<String, dynamic>) {
      _latestSmokeGate = Map<String, dynamic>.from(smokeGate);
    }
  }

  void _scheduleFileTreeRefresh() {
    // Keep explorer responsive during streaming writes while still coalescing.
    _fileTreeRefreshTimer?.cancel();
    _fileTreeRefreshTimer = Timer(const Duration(milliseconds: 250), () {
      unawaited(loadFiles());
    });
  }

  void _refreshExplorerAfterWrite({
    required String reason,
    bool immediate = false,
    int minIntervalMs = 0,
    bool logEvent = true,
  }) {
    final now = DateTime.now();
    if (minIntervalMs > 0 && !immediate) {
      final elapsed = now.difference(_lastExplorerRefreshAt).inMilliseconds;
      if (elapsed < minIntervalMs) {
        return;
      }
    }
    _lastExplorerRefreshAt = now;
    if (immediate) {
      unawaited(loadFiles());
    } else {
      _scheduleFileTreeRefresh();
    }
    if (!logEvent) {
      return;
    }
    _pendingExplorerSyncEvents += 1;
    final elapsedLogMs = now.difference(_lastExplorerSyncLogAt).inMilliseconds;
    if (elapsedLogMs < 1100) {
      return;
    }
    final count = _pendingExplorerSyncEvents;
    _pendingExplorerSyncEvents = 0;
    _lastExplorerSyncLogAt = now;
    final text = count <= 1
        ? "Explorer synced: $reason"
        : "Explorer synced: $count updates (latest: $reason)";
    _consoleLogs.add(ConsoleLog(text: text, level: "info"));
  }

  void _startSelfHealingLoop() {
    _selfHealTimer?.cancel();
    _selfHealTimer = Timer.periodic(const Duration(seconds: 24), (_) {
      if (_selfHealingBusy) return;
      if (_activeProject == null) return; // Skip when no project
      if (_status != "running" && _executionStatus != "running") {
        return; // Only heal during active runs
      }
      _selfHealingBusy = true;
      unawaited(() async {
        try {
          await _runSelfHealingChecks();
        } catch (e) {
          debugPrint("Self-healing error: $e");
        } finally {
          _selfHealingBusy = false;
        }
      }());
    });
  }

  Future<void> _runSelfHealingChecks() async {
    if (_activeProject == null) return;
    final now = DateTime.now();
    final runActive = _status == "running" ||
        _executionStatus == "running" ||
        _executionStatus == "queued";

    if (runActive) {
      final hasSkeleton = _hasUsefulWorkspaceFiles();
      if (hasSkeleton) {
        _explorerBecameEmptyAt = null;
      } else {
        _explorerBecameEmptyAt ??= now;
        if (now.difference(_explorerBecameEmptyAt!).inSeconds >= 3) {
          await _throttledSelfHeal(
              "Explorer empty >3s, scanning and repairing workspace paths.");
          await _repairWorkspaceFiles();
          await loadFiles();
        }
      }
    } else {
      _explorerBecameEmptyAt = null;
    }

    final hasFiles = _hasUsefulWorkspaceFiles();
    if (!hasFiles) {
      return;
    }
    if (_previewBlockedByMissingEntry) {
      return;
    }
    final needPreview = _executionStatus == "completed" || runActive;
    if (!needPreview) {
      _previewBecameUnavailableAt = null;
      return;
    }
    final probe = await _pingPreviewReason(_previewUrl);
    final previewHealthy = probe["healthy"] == true;
    _lastPreviewHealthReason = (probe["reason"] ?? "unknown").toString();
    if (previewHealthy) {
      _previewBecameUnavailableAt = null;
      _lastPreview404RepairAt = DateTime.fromMillisecondsSinceEpoch(0);
      return;
    }
    _previewBecameUnavailableAt ??= now;
    if (now.difference(_previewBecameUnavailableAt!).inSeconds >= 3) {
      if (_lastPreviewHealthReason == "http_404" ||
          _lastPreviewHealthReason == "http_404_body") {
        final shouldRepair =
            now.difference(_lastPreview404RepairAt).inSeconds >= 12;
        if (shouldRepair) {
          _lastPreview404RepairAt = now;
          await _throttledSelfHeal(
              "Preview 404: fixing workspace mapping before restart.");
          await _repairWorkspaceFiles();
          await loadFiles();
        } else {
          await _throttledSelfHeal(
              "Preview still 404 after repair, restarting preview bridge.");
          await _recoverPreviewBridge();
        }
        return;
      }
      await _throttledSelfHeal("Preview unavailable >3s, retrying bridge.");
      await _recoverPreviewBridge();
    }
  }

  bool _isEntrypointCandidate(String path) {
    final p = path.trim().toLowerCase().replaceAll("\\", "/");
    if (p.isEmpty) return false;
    return p.endsWith("/index.html") ||
        p == "index.html" ||
        p.endsWith("/package.json") ||
        p == "package.json" ||
        p.endsWith("/pubspec.yaml") ||
        p == "pubspec.yaml" ||
        p.endsWith("/main.dart") ||
        p == "main.dart";
  }

  void _markEntryCandidateSeen(String path) {
    if (_isEntrypointCandidate(path)) {
      _previewBlockedByMissingEntry = false;
    }
  }

  Future<void> _throttledSelfHeal(String message) async {
    final now = DateTime.now();
    if (now.difference(_lastSelfHealActionAt).inSeconds < 3) return;
    _lastSelfHealActionAt = now;
    _consoleLogs.add(ConsoleLog(text: message, level: "warning"));
    notifyListeners();
  }

  Future<void> _repairWorkspaceFiles() async {
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/files/repair");
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode({
              "workspace": _workspacePath(),
              "max_depth": 10,
            }),
          )
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        _consoleLogs.add(ConsoleLog(
            text: "Workspace repair failed (${resp.statusCode})",
            level: "warning"));
        return;
      }
      final body = jsonDecode(resp.body);
      if (body is! Map<String, dynamic>) return;
      final moved = body["moved"];
      if (moved is List && moved.isNotEmpty) {
        _consoleLogs.add(ConsoleLog(
            text:
                "Workspace repaired: moved ${moved.length} file(s) back to root.",
            level: "success"));
      }
    } catch (err) {
      _consoleLogs.add(
          ConsoleLog(text: "Workspace repair error: $err", level: "warning"));
    }
  }

  Future<void> _finalizeDelivery() async {
    _executionProgress = "Finalizing delivery...";
    notifyListeners();
    await loadFiles();

    final restart = await restartFrameworkServer(framework: _selectedFramework);
    var running = restart["running"] == true;
    if (!running &&
        (restart["reason"] ?? "").toString() == "entry_point_missing") {
      _previewBlockedByMissingEntry = true;
      _executionProgress = "Build finished but entry point is missing.";
      _consoleLogs.add(ConsoleLog(
          text: "Preview skipped: entry point missing.", level: "warning"));
      notifyListeners();
      return;
    }

    if (!running) {
      final fallbackFrameworks = _fallbackFrameworksForWorkspace();
      for (final fw in fallbackFrameworks) {
        final started = await startFrameworkServer(framework: fw);
        if (started["running"] == true) {
          _selectedFramework = fw;
          running = true;
          break;
        }
        if ((started["reason"] ?? "").toString() == "entry_point_missing") {
          _previewBlockedByMissingEntry = true;
          _executionProgress = "Build finished but entry point is missing.";
          _consoleLogs.add(ConsoleLog(
              text: "Preview skipped: entry point missing.", level: "warning"));
          notifyListeners();
          return;
        }
      }
    }

    if (running) {
      running = await _ensurePreviewBridgeHealthy(retries: 6);
    }

    if (running) {
      _preferredRightPanelTab = "preview";
      _preferredRightPanelSignal += 1;
      triggerPreviewReload();
      await loadFiles();
      _executionProgress = "Preview running";
      _consoleLogs.add(ConsoleLog(
          text: "Delivery complete: preview is live.", level: "success"));
    } else {
      _executionProgress = "Build completed, but preview startup failed.";
      _consoleLogs.add(ConsoleLog(
          text: "Preview startup failed after retries.", level: "warning"));
    }
    notifyListeners();
  }

  Future<bool> _ensurePreviewBridgeHealthy({
    int retries = 3,
    int delayMs = 500,
  }) async {
    final url = _previewUrl.trim();
    if (url.isEmpty) return false;
    for (var i = 0; i < retries; i += 1) {
      final probe = await _pingPreviewReason(url);
      _lastPreviewHealthReason = (probe["reason"] ?? "unknown").toString();
      if (probe["healthy"] == true) return true;
      if (i < retries - 1) {
        await Future<void>.delayed(Duration(milliseconds: delayMs));
      }
    }
    return false;
  }

  Future<Map<String, dynamic>> _pingPreviewReason(String url) async {
    try {
      final resp =
          await http.get(Uri.parse(url)).timeout(const Duration(seconds: 2));
      if (resp.statusCode == 404) {
        return {"healthy": false, "reason": "http_404", "status_code": 404};
      }
      if (resp.statusCode >= 400) {
        return {
          "healthy": false,
          "reason": "http_${resp.statusCode}",
          "status_code": resp.statusCode
        };
      }
      final body = resp.body.toLowerCase();
      if (body.contains("cannot get /") ||
          body.contains("<title>404") ||
          body.contains("404 not found")) {
        return {
          "healthy": false,
          "reason": "http_404_body",
          "status_code": resp.statusCode
        };
      }
      return {"healthy": true, "reason": "ok", "status_code": resp.statusCode};
    } on SocketException {
      return {"healthy": false, "reason": "connection_refused"};
    } on TimeoutException {
      return {"healthy": false, "reason": "timeout"};
    } catch (err) {
      return {"healthy": false, "reason": "error:$err"};
    }
  }

  Future<void> _recoverPreviewBridge() async {
    final restart = await restartFrameworkServer(framework: _selectedFramework);
    var running = restart["running"] == true;
    final restartReason = (restart["reason"] ?? "").toString();
    if (!running && restartReason == "entry_point_missing") {
      _previewBlockedByMissingEntry = true;
      _executionProgress = "Entry point missing. Regenerating files required.";
      notifyListeners();
      return;
    }
    if (!running) {
      for (final fw in _fallbackFrameworksForWorkspace()) {
        final started = await startFrameworkServer(framework: fw);
        if (started["running"] == true) {
          _selectedFramework = fw;
          running = true;
          break;
        }
        if ((started["reason"] ?? "").toString() == "entry_point_missing") {
          _previewBlockedByMissingEntry = true;
          _executionProgress =
              "Entry point missing. Regenerating files required.";
          notifyListeners();
          return;
        }
      }
    }
    if (running && await _ensurePreviewBridgeHealthy(retries: 4)) {
      _preferredRightPanelTab = "preview";
      _preferredRightPanelSignal += 1;
      triggerPreviewReload();
      _executionProgress = "Preview running";
    }
    notifyListeners();
  }

  void _appendOrMergeAgentMessage(Map<String, dynamic> data) {
    final agent = (data["agent"] ?? "Agent").toString();
    final role = (data["role"] ?? "Assistant").toString();
    final content = _sanitizeStreamText((data["content"] ?? "").toString());
    final step = int.tryParse("${data["step"] ?? ""}");
    final totalSteps = int.tryParse("${data["total_steps"] ?? ""}");
    if (content.trim().isEmpty) return;
    final runActive = _status == "running" ||
        _executionStatus == "running" ||
        _executionStatus == "queued";
    if (_messages.isNotEmpty) {
      final last = _messages.last;
      if (last.role == "assistant" && last.content.trim() == content.trim()) {
        return;
      }
      if (step == null &&
          runActive &&
          last.role == "assistant" &&
          (last.mode ?? "") != "reasoning") {
        final merged = _mergeAssistantContent(last.content, content);
        _messages[_messages.length - 1] = Message(
          role: "assistant",
          content: merged,
          createdAt: last.createdAt,
          agentName: agent,
          agentRole: role,
          steps: totalSteps ?? last.steps,
          stepsComplete: last.stepsComplete,
          generatedFiles: last.generatedFiles,
        );
        _syncActiveConversationMessages();
        return;
      }
    }

    if (step != null && _stepMessageIndex.containsKey(step)) {
      final idx = _stepMessageIndex[step]!;
      if (idx >= 0 && idx < _messages.length) {
        final prev = _messages[idx];
        final merged = _mergeAssistantContent(prev.content, content);
        _messages[idx] = Message(
          role: "assistant",
          content: merged,
          createdAt: prev.createdAt,
          agentName: agent,
          agentRole: role,
          steps: totalSteps,
          stepsComplete: step,
        );
        _syncActiveConversationMessages();
        return;
      }
    }

    _messages.add(
      Message(
        role: "assistant",
        content: content,
        agentName: agent,
        agentRole: role,
        steps: totalSteps,
        stepsComplete: step,
      ),
    );
    if (step != null) {
      _stepMessageIndex[step] = _messages.length - 1;
    }
    _syncActiveConversationMessages();
  }

  String _sanitizeStreamText(String text) {
    if (text.isEmpty) return text;
    var cleaned = text.replaceAll("\r\n", "\n").replaceAll("\r", "\n");
    cleaned = cleaned.replaceAll(RegExp(r"\x1B\[[0-9;]*[A-Za-z]"), "");
    cleaned = cleaned.replaceAll(
        RegExp(r"[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]"), "");
    cleaned = cleaned.replaceAll(RegExp(r"\n{4,}"), "\n\n\n");
    return cleaned;
  }

  void _setExecutionProgressThinking() {
    final now = DateTime.now();
    if (_executionProgress == "Thinking..." &&
        now.difference(_lastExecutionProgressAt).inMilliseconds < 700) {
      return;
    }
    _executionProgress = "Thinking...";
    _lastExecutionProgressText = _executionProgress;
    _lastExecutionProgressAt = now;
  }

  void _setExecutionProgressSmooth(String text) {
    final normalized = _summarizeProgressMessage(text);
    if (normalized.isEmpty) return;
    final now = DateTime.now();
    if (normalized == _lastExecutionProgressText &&
        now.difference(_lastExecutionProgressAt).inMilliseconds < 1200) {
      return;
    }
    if (now.difference(_lastExecutionProgressAt).inMilliseconds < 220 &&
        normalized != _lastExecutionProgressText) {
      return;
    }
    _executionProgress = normalized;
    _lastExecutionProgressText = normalized;
    _lastExecutionProgressAt = now;
  }

  String _summarizeProgressMessage(String text) {
    final t = _sanitizeStreamText(text).trim();
    if (t.isEmpty) return "";
    final lower = t.toLowerCase();
    if (lower.startsWith("coder wave ")) return "Generating files...";
    if (lower.startsWith("coder file done")) return "File completed";
    if (lower.startsWith("starting chunk ")) return "Thinking...";
    if (lower.startsWith("entering stage:")) return t;
    if (lower.startsWith("stage ")) return t;
    if (lower.startsWith("[smoke_gate]")) return "Running smoke checks...";
    if (lower.startsWith("[quality_gate]")) return "Running quality gate...";
    if (lower.startsWith("[self_check]")) return "Running self-check...";
    if (lower.startsWith("[checkpoint]")) return "Checkpoint updated";
    if (lower.startsWith("[preview]")) return "Preparing preview...";
    if (lower.startsWith("[lint]")) return "Lint checks...";
    if (t.length > 120) {
      return "${t.substring(0, 117)}...";
    }
    return t;
  }

  bool _isCorruptedStreamText(String text) {
    final t = text.trim();
    if (t.isEmpty) return true;
    if (RegExp(r"^[^A-Za-z0-9\u4e00-\u9fff]+$").hasMatch(t)) return true;
    final lines =
        t.split("\n").map((e) => e.trim()).where((e) => e.isNotEmpty).toList();
    if (lines.isEmpty) return true;
    var short = 0;
    var symbolHeavy = 0;
    var codeish = 0;
    for (final line in lines.take(50)) {
      if (line.length <= 2) short += 1;
      final letters = RegExp(r"[A-Za-z\u4e00-\u9fff]").allMatches(line).length;
      final symbols =
          RegExp(r"[{};<>:=/_\\[\\]\\(\\)]").allMatches(line).length;
      if (symbols > letters) symbolHeavy += 1;
      if (RegExp(
              r"^(const|let|var|function|class|import|export|return|if\s*\(|for\s*\(|while\s*\()",
              caseSensitive: false)
          .hasMatch(line)) {
        codeish += 1;
      }
    }
    if (short >= 12 && lines.length >= 14) return true;
    if (symbolHeavy >= (lines.length * 0.45).ceil()) return true;
    if (codeish >= (lines.length * 0.4).ceil()) return true;
    return false;
  }

  String _compactAssistantNarrative(String text) {
    final lines = _sanitizeStreamText(text)
        .split("\n")
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    if (lines.isEmpty) return "";
    final kept = <String>[];
    for (final line in lines) {
      if (_isNoisyStreamingFragment(line)) continue;
      if (_isLikelyCodeNoise(line)) continue;
      if (RegExp(r"^[A-Za-z_][A-Za-z0-9_]*$").hasMatch(line) &&
          line.length <= 16) {
        continue;
      }
      kept.add(line);
      if (kept.length >= 10) break;
    }
    if (kept.isEmpty) return "";
    var merged = kept.join("\n");
    if (merged.length > 2600) {
      merged = merged.substring(0, 2600);
    }
    return merged.trim();
  }

  bool _isTokenLikeFragment(String text) {
    final t = text.trim();
    if (t.isEmpty) return false;
    if (t.contains("\n")) return false;
    if (t.length <= 20) return true;
    final words = t.split(RegExp(r"\s+")).where((e) => e.isNotEmpty).length;
    if (words <= 3 && t.length <= 40) return true;
    return false;
  }

  bool _startsWithPunctuation(String text) {
    if (text.isEmpty) return false;
    const punct = ",.;:!?)}]>'\"%";
    return punct.contains(text[0]);
  }

  bool _endsWithJoiner(String text) {
    if (text.isEmpty) return false;
    const joiners = " \t\r\n([{<'\"/-";
    return joiners.contains(text[text.length - 1]);
  }

  String _mergeAssistantContent(String previous, String incoming) {
    if (incoming.trim().isEmpty) return previous;
    if (previous.trim().isEmpty) return incoming;
    if (previous == incoming || previous.endsWith(incoming)) return previous;
    if (incoming.length > 1800 && _isLikelyCodeNoise(incoming)) return previous;
    if (_isTokenLikeFragment(incoming)) {
      final needsSpace =
          !_endsWithJoiner(previous) && !_startsWithPunctuation(incoming);
      final merged = needsSpace ? "$previous $incoming" : "$previous$incoming";
      return merged.length > 8000
          ? merged.substring(merged.length - 8000)
          : merged;
    }
    if (previous.endsWith("\n") || incoming.startsWith("\n")) {
      final merged = "$previous$incoming";
      return merged.length > 8000
          ? merged.substring(merged.length - 8000)
          : merged;
    }
    final merged = "$previous\n$incoming";
    return merged.length > 8000
        ? merged.substring(merged.length - 8000)
        : merged;
  }

  bool _isProgressLikeMessage(String text) {
    final t = text.trim().toLowerCase();
    if (t.isEmpty) return false;
    return t.startsWith("coder wave ") ||
        t.startsWith("coder file done") ||
        t.startsWith("stage ") ||
        t.startsWith("entering stage:") ||
        t.startsWith("starting chunk ") ||
        t.startsWith("[lint]") ||
        t.startsWith("[checkpoint]") ||
        t.startsWith("[retry]") ||
        t.startsWith("[rollback]") ||
        t.startsWith("[smoke_gate]") ||
        t.startsWith("[quality_gate]") ||
        t.startsWith("[self_check]") ||
        t.startsWith("[preview]") ||
        t.startsWith("repomap ready") ||
        t.startsWith("experiencememory backend=") ||
        (t.startsWith("running ") && t.contains(" smoke checks"));
  }

  bool _isNoisyStreamingFragment(String text) {
    final t = text.trim();
    if (t.isEmpty) return true;
    if (t.length <= 2) return true;
    if (t.contains("\n")) return false;
    if (RegExp(r"^[{}()[\];:,_=<>./\\\-+*%#@!~`|]+$").hasMatch(t)) return true;
    if (t.length <= 32) {
      final words = t.split(RegExp(r"\s+")).where((e) => e.isNotEmpty).length;
      final letters = RegExp(r"[A-Za-z\u4e00-\u9fff]").allMatches(t).length;
      final symbols = RegExp(r"[{};<>:=/_\\[\\]\\(\\)]").allMatches(t).length;
      if (words <= 3 && symbols >= letters) return true;
      if (words <= 2 &&
          !t.endsWith(".") &&
          !t.endsWith("!") &&
          !t.endsWith("?")) {
        return true;
      }
    }
    return false;
  }

  bool _isLikelyCodeNoise(String text) {
    final lines = text
        .split("\n")
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    if (lines.length < 3) return false;
    var score = 0;
    for (final l in lines) {
      final lower = l.toLowerCase();
      if (l.endsWith(";") ||
          l.endsWith("{") ||
          l.endsWith("}") ||
          l.contains("=>")) {
        score += 1;
      }
      if (RegExp(
              r"^(const|let|var|function|class|import|export|return|if\s*\(|for\s*\(|while\s*\()")
          .hasMatch(lower)) {
        score += 1;
      }
      if (RegExp(r"[{}<>:=;]").hasMatch(l) && l.length < 80) {
        score += 1;
      }
    }
    if (RegExp(r"</?[a-zA-Z][^>]*>").hasMatch(text) && lines.length >= 3) {
      return true;
    }
    return score >= (lines.length * 1.6).ceil();
  }

  void _appendReasoningMessage(String content) {
    final sanitized = _sanitizeStreamText(content).trim();
    if (sanitized.isEmpty || _isNoisyStreamingFragment(sanitized)) {
      return;
    }
    if (_messages.isNotEmpty) {
      final last = _messages.last;
      if (last.role == "assistant" && last.mode == "reasoning") {
        var merged = "${last.content}\n$sanitized";
        final lines =
            merged.split("\n").where((e) => e.trim().isNotEmpty).toList();
        if (lines.length > 60) {
          merged = lines.sublist(lines.length - 60).join("\n");
        }
        if (merged.length > 6000) {
          merged = merged.substring(merged.length - 6000);
        }
        _messages[_messages.length - 1] = Message(
          role: "assistant",
          content: merged,
          createdAt: last.createdAt,
          mode: "reasoning",
          agentName: last.agentName ?? "Alex",
          agentRole: last.agentRole ?? "Engineer",
        );
        _syncActiveConversationMessages();
        return;
      }
    }
    _messages.add(
      Message(
        role: "assistant",
        content: sanitized,
        mode: "reasoning",
        agentName: "Alex",
        agentRole: "Engineer",
      ),
    );
    _syncActiveConversationMessages();
  }

  void _upsertGeneratedFile({
    required String path,
    required String status,
    String content = "",
  }) {
    if (path.isEmpty) return;
    final idx = _generatedFiles.indexWhere((f) => f.path == path);
    final item = GeneratedFile(path: path, status: status, content: content);
    if (idx >= 0) {
      _generatedFiles[idx] = item;
    } else {
      _generatedFiles.add(item);
    }
  }

  void _upsertFileTreePath(String path, {bool? isGenerating}) {
    if (path.isEmpty) return;
    final target = path.replaceAll("\\", "/");
    if (_setGeneratingOnExistingNode(_fileTree, target, isGenerating)) {
      return;
    }
    final parts = path
        .replaceAll("\\", "/")
        .split("/")
        .where((e) => e.isNotEmpty)
        .toList();
    if (parts.isEmpty) return;
    if (parts.length == 1) {
      _fileTree.add(
        FileNode(
          name: parts.first,
          path: target,
          isDir: false,
          isGenerating: isGenerating ?? false,
          children: [],
        ),
      );
      return;
    }
    final dir = parts.first;
    var rootIdx = _fileTree.indexWhere((n) => n.path == dir && n.isDir);
    if (rootIdx < 0) {
      _fileTree.add(FileNode(name: dir, path: dir, isDir: true, children: []));
      rootIdx = _fileTree.length - 1;
    }
    final root = _fileTree[rootIdx];
    final existingChild = root.children.indexWhere((c) => c.path == target);
    if (existingChild >= 0) {
      final current = root.children[existingChild];
      root.children[existingChild] =
          current.copyWith(isGenerating: isGenerating ?? current.isGenerating);
      return;
    }
    root.children.add(
      FileNode(
        name: parts.last,
        path: target,
        isDir: false,
        isGenerating: isGenerating ?? false,
        children: [],
      ),
    );
  }

  bool _setGeneratingOnExistingNode(
      List<FileNode> nodes, String target, bool? isGenerating) {
    if (isGenerating == null) return false;
    for (var i = 0; i < nodes.length; i += 1) {
      final node = nodes[i];
      if (!node.isDir && node.path == target) {
        if (node.isGenerating != isGenerating) {
          nodes[i] = node.copyWith(isGenerating: isGenerating);
        }
        return true;
      }
      if (node.isDir && node.children.isNotEmpty) {
        final changed =
            _setGeneratingOnExistingNode(node.children, target, isGenerating);
        if (changed) return true;
      }
    }
    return false;
  }

  void _refreshGeneratingUiFlag() {
    _silentGenerateUI = _generatedFiles.any((f) => f.status == "writing");
  }

  void _consumeDesignPlanMessage(String content) {
    final parsed = _extractPlannedFiles(content);
    if (parsed.isEmpty) return;
    for (final path in parsed) {
      _upsertGeneratedFile(path: path, status: "writing");
      _upsertFileTreePath(path, isGenerating: true);
    }
    _refreshGeneratingUiFlag();
    _refreshExplorerAfterWrite(reason: "design_plan:${parsed.length}");
  }

  List<String> _extractPlannedFiles(String raw) {
    final content = raw.trim();
    if (content.isEmpty || !content.contains("files")) return const <String>[];
    String candidate = content;
    if (candidate.startsWith("```")) {
      candidate = candidate.replaceFirst(RegExp(r"^```[a-zA-Z0-9_-]*\s*"), "");
      candidate = candidate.replaceFirst(RegExp(r"\s*```$"), "");
    }
    Map<String, dynamic>? jsonObj;
    try {
      final parsed = jsonDecode(candidate);
      if (parsed is Map<String, dynamic>) jsonObj = parsed;
    } catch (_) {
      final m = RegExp(r"\{[\s\S]*\}").firstMatch(candidate);
      if (m != null) {
        try {
          final parsed = jsonDecode(m.group(0)!);
          if (parsed is Map<String, dynamic>) jsonObj = parsed;
        } catch (_) {}
      }
    }
    if (jsonObj == null) return const <String>[];
    final files = jsonObj["files"];
    if (files is! List) return const <String>[];
    final out = <String>[];
    for (final item in files) {
      if (item is Map<String, dynamic>) {
        final path =
            (item["path"] ?? "").toString().trim().replaceAll("\\", "/");
        if (path.isNotEmpty) out.add(path);
      }
    }
    return out;
  }

  List<String> _coercePlanFiles(Object? raw) {
    final out = <String>[];
    if (raw is List) {
      for (final item in raw) {
        if (item is Map<String, dynamic>) {
          final path =
              (item["path"] ?? "").toString().trim().replaceAll("\\", "/");
          if (path.isNotEmpty) {
            out.add(path);
          }
        } else {
          final text = "$item".trim();
          if (text.isNotEmpty) {
            out.add(text);
          }
        }
      }
    }
    return out;
  }

  void cancelActiveRun() {
    final runId = _activeRunId;
    unawaited(_activeRunStream?.cancel());
    _runWatchdogEpoch += 1;
    if (runId != null && runId.isNotEmpty) {
      final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
      unawaited(() async {
        try {
          await http.post(
            Uri.parse("$base/api/executions/$runId/cancel"),
            headers: _backendHeaders(),
          );
        } catch (_) {}
      }());
    }
    _status = "idle";
    _executionStatus = "cancelled";
    _executionProgress = "Run cancelled";
    _activeRunId = null;
    _activeRunStream = null;
    notifyListeners();
  }

  // ─── Stages ───
  List<String> get stageOrder =>
      ["design", "implement", "review", "test", "deploy"];
  Map<String, String> get stageStatus => _stageStatus;

  // ─── Generated files (live build stream) ───
  List<GeneratedFile> _generatedFiles = [];
  List<GeneratedFile> get generatedFiles => _generatedFiles;
  bool isFileWriting(String path) {
    final p = path.trim().replaceAll("\\", "/");
    if (p.isEmpty) return false;
    for (final f in _generatedFiles) {
      if (f.path.trim().replaceAll("\\", "/") == p) {
        return f.status.toLowerCase() == "writing";
      }
    }
    return false;
  }

  // ─── Console ───
  final List<ConsoleLog> _consoleLogs = [];
  List<ConsoleLog> get consoleLogs => _consoleLogs;
  void clearConsoleLogs() {
    _consoleLogs.clear();
    notifyListeners();
  }

  // ─── File system ───
  List<FileNode> _fileTree = [];
  String _activeFilePath = "";
  String _activeFileContent = "";
  String _workspaceResolvedPath = "";
  final List<String> _openFileTabs = [];

  List<FileNode> get fileTree => _fileTree;
  String get activeFilePath => _activeFilePath;
  String get activeFileContent => _activeFileContent;
  List<String> get openFileTabs => _openFileTabs;

  Future<void> loadFiles() async {
    final reqSeq = ++_loadFilesRequestSeq;
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/files/list");
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode({
              "workspace": _workspacePath(),
              "max_depth": 8,
              "tree": false,
            }),
          )
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        _consoleLogs.add(ConsoleLog(
            text: "Load files failed (${resp.statusCode})", level: "error"));
        notifyListeners();
        return;
      }
      final body = jsonDecode(resp.body);
      final raw = body is Map<String, dynamic> ? body["files"] : null;
      if (body is Map<String, dynamic>) {
        final resolved = (body["workspace_resolved"] ?? "").toString().trim();
        if (resolved.isNotEmpty) {
          _workspaceResolvedPath = resolved;
        }
      }
      final files = <String>[];
      if (raw is List) {
        for (final f in raw) {
          final s = _normalizeFilePath("$f");
          if (s.isNotEmpty && !_isInternalWorkspacePath(s)) files.add(s);
        }
      }
      final merged = <String>{...files};
      for (final g in _generatedFiles) {
        final p = _normalizeFilePath(g.path);
        if (p.isNotEmpty && !_isInternalWorkspacePath(p)) merged.add(p);
      }
      if (reqSeq < _loadFilesAppliedSeq) {
        return;
      }
      _loadFilesAppliedSeq = reqSeq;
      final mergedFiles = merged.toList()..sort();
      _fileTree = _buildFileTree(mergedFiles);
      if (_containsEntrypoint(mergedFiles)) {
        _previewBlockedByMissingEntry = false;
      }
      if (_fileTree.isNotEmpty || _generatedFiles.isNotEmpty) {
        _explorerBecameEmptyAt = null;
      } else {
        _explorerBecameEmptyAt ??= DateTime.now();
      }
      _autoDetectFramework(mergedFiles);
    } catch (err) {
      _consoleLogs
          .add(ConsoleLog(text: "Load files error: $err", level: "error"));
    }
    notifyListeners();
  }

  bool _containsEntrypoint(List<String> files) {
    for (final f in files) {
      final p = f.replaceAll("\\", "/").toLowerCase();
      if (p == "index.html" ||
          p.endsWith("/index.html") ||
          p == "package.json" ||
          p.endsWith("/package.json") ||
          p == "pubspec.yaml" ||
          p.endsWith("/pubspec.yaml") ||
          p == "lib/main.dart" ||
          p.endsWith("/lib/main.dart")) {
        return true;
      }
    }
    return false;
  }

  bool _hasUsefulWorkspaceFiles() {
    for (final node in _fileTree) {
      if (_nodeHasUsefulFile(node)) return true;
    }
    for (final g in _generatedFiles) {
      final p = _normalizeFilePath(g.path);
      if (p.isNotEmpty && !_isInternalWorkspacePath(p)) return true;
    }
    return false;
  }

  bool _nodeHasUsefulFile(FileNode node) {
    if (!node.isDir) {
      final p = _normalizeFilePath(node.path);
      return p.isNotEmpty && !_isInternalWorkspacePath(p);
    }
    for (final child in node.children) {
      if (_nodeHasUsefulFile(child)) return true;
    }
    return false;
  }

  Future<void> readFile(String path) async {
    final normalized = _normalizeFilePath(path);
    final preferred = _resolveExistingFilePath(normalized);
    final requestedPath = preferred.isNotEmpty ? preferred : normalized;
    _activeFilePath = requestedPath;
    _openFileTab(requestedPath);
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/files/read");
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode({
              "workspace": _workspacePath(),
              "path": requestedPath,
            }),
          )
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        _scheduleFileTreeRefresh();
        final fallback = _resolveExistingFilePath(normalized);
        if (fallback.isNotEmpty && fallback != requestedPath) {
          final retry = await http
              .post(
                uri,
                headers: _backendHeaders(json: true),
                body: jsonEncode({
                  "workspace": _workspacePath(),
                  "path": fallback,
                }),
              )
              .timeout(const Duration(seconds: 8));
          if (retry.statusCode >= 200 && retry.statusCode < 300) {
            final body = jsonDecode(retry.body);
            if (body is Map<String, dynamic>) {
              _activeFilePath = fallback;
              _activeFileContent = (body["content"] ?? "").toString();
              notifyListeners();
              return;
            }
          }
        }
        _consoleLogs.add(ConsoleLog(
            text: "Read file failed (${resp.statusCode}): $requestedPath",
            level: "error"));
        notifyListeners();
        return;
      }
      final body = jsonDecode(resp.body);
      if (body is Map<String, dynamic>) {
        _activeFileContent = (body["content"] ?? "").toString();
      }
    } catch (err) {
      _consoleLogs
          .add(ConsoleLog(text: "Read file error: $err", level: "error"));
    }
    notifyListeners();
  }

  void updateActiveContent(String content) {
    _activeFileContent = content;
    notifyListeners();
  }

  Future<void> saveFile() async {
    if (_activeFilePath.trim().isEmpty) return;
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/files/write");
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode({
              "workspace": _workspacePath(),
              "path": _activeFilePath,
              "content": _activeFileContent,
            }),
          )
          .timeout(const Duration(seconds: 10));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        _consoleLogs.add(ConsoleLog(
            text: "Save file failed (${resp.statusCode}): $_activeFilePath",
            level: "error"));
        notifyListeners();
        return;
      }
      _upsertFileTreePath(_activeFilePath);
      _upsertGeneratedFile(
          path: _activeFilePath, status: "done", content: _activeFileContent);
      _consoleLogs
          .add(ConsoleLog(text: "Saved $_activeFilePath", level: "success"));
      _refreshExplorerAfterWrite(
          reason: "save:$_activeFilePath", immediate: true);
    } catch (err) {
      _consoleLogs
          .add(ConsoleLog(text: "Save file error: $err", level: "error"));
    }
    notifyListeners();
  }

  Future<void> createFile(String path, {String content = ""}) async {
    final p = path.trim().replaceAll("\\", "/");
    if (p.isEmpty) return;
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/files/write");
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode({
              "workspace": _workspacePath(),
              "path": p,
              "content": content,
            }),
          )
          .timeout(const Duration(seconds: 10));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        _consoleLogs.add(ConsoleLog(
            text: "Create file failed (${resp.statusCode}): $p",
            level: "error"));
        notifyListeners();
        return;
      }
      _upsertFileTreePath(p);
      _activeFilePath = p;
      _activeFileContent = content;
      _openFileTab(p);
      _consoleLogs.add(ConsoleLog(text: "Created $p", level: "success"));
      _refreshExplorerAfterWrite(reason: "create:$p", immediate: true);
    } catch (err) {
      _consoleLogs
          .add(ConsoleLog(text: "Create file error: $err", level: "error"));
    }
    notifyListeners();
  }

  Future<void> createFolder(String path) async {
    final clean =
        path.trim().replaceAll("\\", "/").replaceAll(RegExp(r"/+$"), "");
    if (clean.isEmpty) return;
    await createFile("$clean/.gitkeep");
    await loadFiles();
  }

  Future<void> openFolderAsProject({
    required String folderPath,
    String framework = "flutter",
  }) async {
    final clean = folderPath.trim();
    if (clean.isEmpty) {
      throw Exception("Folder path is empty");
    }
    final dir = Directory(clean);
    if (!await dir.exists()) {
      throw Exception("Folder does not exist: $clean");
    }
    var name = dir.uri.pathSegments.isNotEmpty
        ? dir.uri.pathSegments.where((s) => s.isNotEmpty).last
        : "project";
    name = name.trim();
    if (name.isEmpty) name = "project";
    final existed = _projects.where((p) => p.name == name).length;
    if (existed > 0) {
      name = "$name-${existed + 1}";
    }
    createProject(
      name: name,
      description: clean,
      framework:
          _runtimeFrameworkForProjectType(framework, fallback: framework),
      projectType: framework,
      workspacePath: clean,
    );
    await loadFiles();
  }

  Future<void> cloneProjectFromGit({
    required String repoUrl,
    String destination = "",
    String framework = "flutter",
    String branch = "",
  }) async {
    final repo = repoUrl.trim();
    if (repo.isEmpty) {
      throw Exception("Repository URL is empty");
    }
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/projects/clone");
    final resp = await http
        .post(
          uri,
          headers: _backendHeaders(json: true),
          body: jsonEncode({
            "repo_url": repo,
            "destination": destination.trim(),
            "branch": branch.trim(),
          }),
        )
        .timeout(const Duration(minutes: 10));
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception(
          "Clone request failed (${resp.statusCode}): ${resp.body}");
    }
    final body = jsonDecode(resp.body);
    if (body is! Map<String, dynamic>) {
      throw Exception("Invalid clone response");
    }
    if (body["ok"] != true) {
      final err = (body["error"] ?? "Clone failed").toString();
      throw Exception(err);
    }
    final workspace = (body["workspace"] ?? "").toString();
    final name = (body["name"] ?? "").toString().trim().isEmpty
        ? "cloned-project"
        : (body["name"] ?? "").toString().trim();
    createProject(
      name: name,
      description: repo,
      framework:
          _runtimeFrameworkForProjectType(framework, fallback: framework),
      projectType: framework,
      workspacePath: workspace,
    );
    await loadFiles();
  }

  Future<void> saveCurrentProjectToTemplateMarket({
    String? name,
    String description = "",
    List<String> tags = const [],
  }) async {
    final p = _activeProject;
    if (p == null) {
      throw Exception("No active project");
    }
    final workspace = p.workspacePath.trim();
    if (workspace.isEmpty) {
      throw Exception("Active project workspace is empty");
    }
    final res = await api.saveTemplateMarket(
      workspace: workspace,
      name: (name ?? p.name).trim().isEmpty ? p.name : (name ?? p.name).trim(),
      description: description,
      tags: tags,
      framework: p.framework,
      projectType: p.projectType,
    );
    if (res == null || res["ok"] != true) {
      throw Exception((res?["error"] ?? "Save template failed").toString());
    }
    _consoleLogs.add(ConsoleLog(
        text: "Saved template to market: ${name ?? p.name}", level: "success"));
    notifyListeners();
  }

  String _normalizeFilePath(String path) {
    return path.trim().replaceAll("\\", "/").replaceFirst(RegExp(r"^\./+"), "");
  }

  bool _isInternalWorkspacePath(String path) {
    final p = _normalizeFilePath(path).toLowerCase();
    if (p.isEmpty) return true;
    return p == ".rebot" ||
        p.startsWith(".rebot/") ||
        p == ".git" ||
        p.startsWith(".git/") ||
        p == "__pycache__" ||
        p.startsWith("__pycache__/");
  }

  String _resolveExistingFilePath(String preferred) {
    final target = _normalizeFilePath(preferred).toLowerCase();
    final all = <String>[];
    void collect(List<FileNode> nodes) {
      for (final n in nodes) {
        if (n.isDir) {
          collect(n.children);
        } else {
          all.add(_normalizeFilePath(n.path));
        }
      }
    }

    collect(_fileTree);
    for (final p in all) {
      if (p.toLowerCase() == target) return p;
    }
    final leaf = target.split("/").last;
    for (final p in all) {
      final l = p.toLowerCase();
      if (l.endsWith("/$leaf") || l == leaf) return p;
    }
    return "";
  }

  Future<void> importTemplateToMarket({
    required String sourcePath,
    String? name,
    String description = "",
    List<String> tags = const [],
    String framework = "general",
  }) async {
    final clean = sourcePath.trim();
    if (clean.isEmpty) {
      throw Exception("Source path is empty");
    }
    final res = await api.importTemplateMarket(
      sourcePath: clean,
      name: name,
      description: description,
      tags: tags,
      framework: framework,
      projectType: framework,
    );
    if (res == null || res["ok"] != true) {
      throw Exception((res?["error"] ?? "Import template failed").toString());
    }
    _consoleLogs.add(ConsoleLog(
        text: "Imported template: ${name ?? clean}", level: "success"));
    notifyListeners();
  }

  Future<void> openTemplateAsProject({
    required String templateId,
    String? name,
    String? destination,
    String? framework,
    String? projectType,
  }) async {
    final res = await api.openTemplateMarket(
      templateId: templateId,
      destination: destination,
      name: name,
      framework: framework,
      projectType: projectType,
    );
    if (res == null || res["ok"] != true) {
      throw Exception((res?["error"] ?? "Open template failed").toString());
    }
    final workspace = (res["workspace"] ?? "").toString().trim();
    final projectName =
        (res["name"] ?? name ?? "template-project").toString().trim();
    final pType = (res["project_type"] ?? projectType ?? framework ?? "general")
        .toString();
    final fw = (res["framework"] ?? framework ?? pType).toString();
    createProject(
      name: projectName.isEmpty ? "template-project" : projectName,
      description: "Opened from template market: $templateId",
      framework: _runtimeFrameworkForProjectType(pType, fallback: fw),
      projectType: pType,
      workspacePath: workspace,
    );
    await loadFiles();
  }

  Future<void> deleteFile(String path) async {
    final p = path.trim().replaceAll("\\", "/");
    if (p.isEmpty) return;
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/files/delete");
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode({
              "workspace": _workspacePath(),
              "path": p,
            }),
          )
          .timeout(const Duration(seconds: 10));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        _consoleLogs.add(ConsoleLog(
            text: "Delete file failed (${resp.statusCode}): $p",
            level: "error"));
        notifyListeners();
        return;
      }
      _openFileTabs.remove(p);
      if (_activeFilePath == p) {
        _activeFilePath = "";
        _activeFileContent = "";
      }
      _generatedFiles.removeWhere((f) => f.path == p);
      _consoleLogs.add(ConsoleLog(text: "Deleted $p", level: "success"));
      _refreshExplorerAfterWrite(reason: "delete:$p", immediate: true);
    } catch (err) {
      _consoleLogs
          .add(ConsoleLog(text: "Delete file error: $err", level: "error"));
    }
    notifyListeners();
  }

  void _openFileTab(String path) {
    final p = path.trim();
    if (p.isEmpty) return;
    if (!_openFileTabs.contains(p)) {
      _openFileTabs.add(p);
    }
  }

  void switchOpenFileTab(String path) {
    final p = path.trim();
    if (p.isEmpty) return;
    if (!_openFileTabs.contains(p)) {
      _openFileTabs.add(p);
    }
    unawaited(readFile(p));
  }

  void clearActiveEditorSelection() {
    _activeFilePath = "";
    _activeFileContent = "";
    notifyListeners();
  }

  void closeOpenFileTab(String path) {
    final p = path.trim();
    if (p.isEmpty) return;
    final wasActive = _activeFilePath == p;
    _openFileTabs.remove(p);
    if (wasActive) {
      if (_openFileTabs.isEmpty) {
        _activeFilePath = "";
        _activeFileContent = "";
      } else {
        final next = _openFileTabs.last;
        unawaited(readFile(next));
      }
    }
    notifyListeners();
  }

  // ─── Settings ───
  String _apiKey = "";
  String _backendApiKey = "";
  String _llmProvider = "openai";
  String _model = "gpt-4";
  String _llmBaseUrl = "https://api.openai.com";
  String _baseUrl = "http://localhost:8001";
  int _modelMaxConcurrency = 2;
  int _runPriority = 5;
  int? _maxTokenBudget;
  double? _maxCostBudget;
  bool _checkpointEnabled = true;
  bool _smokeCheckEnabled = true;
  int _smokeReworkBudget = 1;
  Map<String, dynamic> _roleModelOverrides = {};
  int _splitMaxConcurrency = 2;
  int _maxContextTokens = 8000;
  double _contextHeadRatio = 0.25;
  String _contextCompressType = "graph_sparse";

  String get apiKey => _apiKey;
  String get backendApiKey => _backendApiKey;
  String get llmProvider => _llmProvider;
  String get model => _model;
  String get llmBaseUrl => _llmBaseUrl;
  String get baseUrl => _baseUrl;
  int get modelMaxConcurrency => _modelMaxConcurrency;
  int get runPriority => _runPriority;
  int? get maxTokenBudget => _maxTokenBudget;
  double? get maxCostBudget => _maxCostBudget;
  bool get checkpointEnabled => _checkpointEnabled;
  bool get smokeCheckEnabled => _smokeCheckEnabled;
  int get smokeReworkBudget => _smokeReworkBudget;
  Map<String, dynamic> get roleModelOverrides =>
      Map<String, dynamic>.from(_roleModelOverrides);
  int get splitMaxConcurrency => _splitMaxConcurrency;
  int get maxContextTokens => _maxContextTokens;
  double get contextHeadRatio => _contextHeadRatio;
  String get contextCompressType => _contextCompressType;
  List<String> get contextCompressTypes => const [
        "graph_sparse",
        "summary_xml",
        "summary_stub",
        "head_tail",
        "recent_only",
        "none"
      ];

  // ������ Compatibility aliases for advanced backend features ������
  String get _selectedProvider => _llmProvider;
  String get _selectedModel => _model;
  String get workspacePath => activeWorkspacePath;

  /// Helper method to add console log entries
  void addConsoleLog(String text, {String level = "info"}) {
    _consoleLogs.add(ConsoleLog(text: text, level: level));
    notifyListeners();
  }

  /// Refresh file tree from disk
  Future<void> refreshFileTree() async {
    _refreshExplorerAfterWrite(reason: "manual refresh", immediate: true);
  }

  List<String> get currentModels {
    const providerModels = <String, List<String>>{
      "openai": ["gpt-4o", "gpt-4.1", "gpt-4-turbo", "gpt-3.5-turbo"],
      "anthropic": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"],
      "deepseek": ["deepseek-chat", "deepseek-reasoner"],
      "moonshot": ["moonshot-v1-8k", "moonshot-v1-32k"],
      "gemini": ["gemini-2.5-pro", "gemini-2.5-flash"],
      "ollama": ["llama3.1", "qwen2.5-coder", "mistral"],
      "openrouter": [
        "openai/gpt-4o",
        "google/gemini-2.5-pro",
        "anthropic/claude-3.5-sonnet"
      ],
      "dashscope": ["qwen-max", "qwen-plus", "qwen-turbo"],
      "qianfan": ["ernie-4.0-turbo", "ernie-3.5-8k"],
      "bedrock": ["anthropic.claude-3-5-sonnet", "amazon.nova-pro"],
      "custom": [],
    };
    final models = providerModels[_llmProvider] ?? providerModels["openai"]!;
    if (_model.trim().isNotEmpty && !models.contains(_model)) {
      return <String>[_model, ...models];
    }
    return models;
  }

  Map<String, String> get providerBaseUrls => {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "ollama": "http://localhost:11434",
        "deepseek": "https://api.deepseek.com/v1",
        "moonshot": "https://api.moonshot.cn/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
        "qianfan": "https://qianfan.baidubce.com/v2",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "bedrock": "https://bedrock-runtime.us-east-1.amazonaws.com",
        "custom": "",
      };
  Map<String, String> get providerDocUrls => {
        "openai":
            "https://platform.openai.com/docs/api-reference/chat/create-chat-completion",
        "anthropic": "https://docs.anthropic.com/en/api/messages",
        "deepseek": "https://api-docs.deepseek.com/",
        "moonshot": "https://platform.moonshot.cn/docs",
        "openrouter":
            "https://openrouter.ai/docs/api-reference/chat-completion",
        "gemini": "https://ai.google.dev/gemini-api/docs/openai",
        "dashscope":
            "https://www.alibabacloud.com/help/doc-detail/3016807.html",
        "qianfan": "https://cloud.baidu.com/doc/WENXINWORKSHOP/index.html",
        "ollama": "https://github.com/ollama/ollama/blob/main/docs/openai.md",
        "bedrock":
            "https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html",
        "custom": "",
      };

  String get currentApiEndpoint {
    final base = _llmBaseUrl.replaceAll(RegExp(r"/+$"), "");
    if (_llmProvider == "anthropic") {
      return "$base/messages";
    }
    return "$base/chat/completions";
  }

  String get currentProviderDocUrl => providerDocUrls[_llmProvider] ?? "";

  String? _inferProviderFromModel(String model) {
    final m = model.trim().toLowerCase();
    if (m.isEmpty) return null;
    if (m.startsWith("deepseek-")) return "deepseek";
    if (m.startsWith("claude-")) return "anthropic";
    if (m.startsWith("gemini-")) return "gemini";
    if (m.startsWith("moonshot-") || m.contains("kimi")) return "moonshot";
    if (m.startsWith("qwen-")) return "dashscope";
    if (m.startsWith("ernie-")) return "qianfan";
    final slashIdx = m.indexOf("/");
    if (slashIdx > 0) {
      final prefix = m.substring(0, slashIdx);
      if (const {"openai", "google", "anthropic", "meta", "deepseek"}
          .contains(prefix)) {
        return "openrouter";
      }
    }
    return null;
  }

  void _alignProviderAndBaseUrlWithModel() {
    final inferred = _inferProviderFromModel(_model);
    if (inferred != null && inferred != _llmProvider) {
      _llmProvider = inferred;
    }
    final official = providerBaseUrls[_llmProvider];
    if (official != null && official.isNotEmpty) {
      _llmBaseUrl = official;
    }
  }

  Future<File> _settingsFile() async {
    final home = Platform.environment["USERPROFILE"] ??
        Platform.environment["HOME"] ??
        ".";
    final dir = Directory("$home\\.rebot");
    if (!await dir.exists()) {
      await dir.create(recursive: true);
    }
    return File("${dir.path}\\desktop_settings.json");
  }

  Future<void> _loadSettings() async {
    try {
      final file = await _settingsFile();
      if (!await file.exists()) return;
      final raw = await file.readAsString();
      final data = jsonDecode(raw);
      if (data is! Map<String, dynamic>) return;
      _apiKey = (data["api_key"] ?? _apiKey).toString();
      _backendApiKey = (data["backend_api_key"] ?? _backendApiKey).toString();
      _llmProvider = (data["provider"] ?? _llmProvider).toString();
      _model = (data["model"] ?? _model).toString();
      _llmBaseUrl = (data["llm_base_url"] ?? _llmBaseUrl).toString();
      _alignProviderAndBaseUrlWithModel();
      _baseUrl = (data["backend_base_url"] ?? _baseUrl).toString();
      _modelMaxConcurrency = int.tryParse(
              "${data["model_max_concurrency"] ?? _modelMaxConcurrency}") ??
          _modelMaxConcurrency;
      _runPriority = int.tryParse("${data["run_priority"] ?? _runPriority}") ??
          _runPriority;
      _maxTokenBudget = data["max_token_budget"] == null
          ? _maxTokenBudget
          : int.tryParse("${data["max_token_budget"]}");
      _maxCostBudget = data["max_cost_budget"] == null
          ? _maxCostBudget
          : double.tryParse("${data["max_cost_budget"]}");
      _checkpointEnabled = data["checkpoint_enabled"] is bool
          ? data["checkpoint_enabled"] as bool
          : _checkpointEnabled;
      _smokeCheckEnabled = data["smoke_check_enabled"] is bool
          ? data["smoke_check_enabled"] as bool
          : _smokeCheckEnabled;
      _smokeReworkBudget = int.tryParse(
              "${data["smoke_rework_budget"] ?? _smokeReworkBudget}") ??
          _smokeReworkBudget;
      if (_smokeReworkBudget < 0) _smokeReworkBudget = 0;
      if (_smokeReworkBudget > 3) _smokeReworkBudget = 3;
      final overridesRaw = data["role_model_overrides"];
      if (overridesRaw is Map) {
        _roleModelOverrides = Map<String, dynamic>.from(overridesRaw);
      }
      _splitMaxConcurrency = int.tryParse(
              "${data["split_max_concurrency"] ?? _splitMaxConcurrency}") ??
          _splitMaxConcurrency;
      _maxContextTokens =
          int.tryParse("${data["max_context_tokens"] ?? _maxContextTokens}") ??
              _maxContextTokens;
      _contextHeadRatio = double.tryParse(
              "${data["context_head_ratio"] ?? _contextHeadRatio}") ??
          _contextHeadRatio;
      _contextCompressType =
          (data["context_compress_type"] ?? _contextCompressType).toString();
      _linkedAutoGptAgentId =
          (data["linked_autogpt_agent_id"] ?? _linkedAutoGptAgentId).toString();
      _linkedAutoGptWorkflowEnabled =
          data["linked_autogpt_workflow_enabled"] is bool
              ? data["linked_autogpt_workflow_enabled"] as bool
              : _linkedAutoGptWorkflowEnabled;
      _loadProjectState(data);
      _loadConversationState(data);
      notifyListeners();
    } catch (_) {}
  }

  Timer? _saveDebouncerTimer;
  bool _saveScheduled = false;

  void _saveSettingsSoon() {
    // Debounce: at most one disk-write per 2 seconds no matter how many
    // calls arrive.  The first call schedules a timer; subsequent calls
    // only set the flag so the timer fires one final write at the end.
    if (_saveDebouncerTimer?.isActive == true) {
      _saveScheduled = true; // will be flushed when timer fires
      return;
    }
    _saveScheduled = false;
    _saveDebouncerTimer = Timer(const Duration(seconds: 2), _flushSave);
  }

  void _flushSave() {
    _saveScheduled = false;
    Future<void>(() async {
      try {
        final file = await _settingsFile();
        final data = {
          "api_key": _apiKey,
          "backend_api_key": _backendApiKey,
          "provider": _llmProvider,
          "model": _model,
          "llm_base_url": _llmBaseUrl,
          "backend_base_url": _baseUrl,
          "model_max_concurrency": _modelMaxConcurrency,
          "run_priority": _runPriority,
          "max_token_budget": _maxTokenBudget,
          "max_cost_budget": _maxCostBudget,
          "checkpoint_enabled": _checkpointEnabled,
          "smoke_check_enabled": _smokeCheckEnabled,
          "smoke_rework_budget": _smokeReworkBudget,
          "role_model_overrides": _roleModelOverrides,
          "split_max_concurrency": _splitMaxConcurrency,
          "max_context_tokens": _maxContextTokens,
          "context_head_ratio": _contextHeadRatio,
          "context_compress_type": _contextCompressType,
          "linked_autogpt_agent_id": _linkedAutoGptAgentId,
          "linked_autogpt_workflow_enabled": _linkedAutoGptWorkflowEnabled,
          "projects": _projects.map(_projectToJson).toList(),
          "active_project_id": _activeProject?.id,
          "conversations": _conversations.map(_conversationToJson).toList(),
          "active_conversation_id": _activeConversationId,
          "conversation_messages": _buildConversationMessagesForSave(),
        };
        await file.writeAsString(jsonEncode(data), flush: true);
      } catch (_) {}
      // If more saves were requested while we were writing, flush once more.
      if (_saveScheduled) {
        _saveScheduled = false;
        _flushSave();
      }
    });
  }

  /// Merge loaded (deserialized) conversation messages with the raw JSON
  /// for conversations that were never opened, so nothing is lost on save.
  Map<String, dynamic> _buildConversationMessagesForSave() {
    final result = <String, dynamic>{};
    // First, include any un-loaded conversations from the raw JSON cache.
    final raw = _rawConversationMessagesJson;
    if (raw is Map) {
      for (final entry in raw.entries) {
        result["${entry.key}"] = entry.value;
      }
    }
    // Then overwrite with the live (deserialized) data — these are the
    // conversations the user actually touched, so they're authoritative.
    for (final entry in _conversationMessages.entries) {
      result[entry.key] = entry.value.map(_messageToJson).toList();
    }
    return result;
  }

  void setApiKey(String v) {
    _apiKey = v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setBackendApiKey(String v) {
    _backendApiKey = v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setProvider(String v) {
    _llmProvider = v;
    final suggested = providerBaseUrls[v];
    if (suggested != null && suggested.isNotEmpty) {
      _llmBaseUrl = suggested;
    }
    notifyListeners();
    _saveSettingsSoon();
  }

  void setModel(String v) {
    _model = v;
    _alignProviderAndBaseUrlWithModel();
    notifyListeners();
    _saveSettingsSoon();
  }

  void setLlmBaseUrl(String v) {
    _llmBaseUrl = v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setBaseUrl(String v) {
    _baseUrl = v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setModelMaxConcurrency(int v) {
    _modelMaxConcurrency = v < 1 ? 1 : v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setRunPriority(int v) {
    _runPriority = v < 0 ? 0 : (v > 10 ? 10 : v);
    notifyListeners();
    _saveSettingsSoon();
  }

  void setMaxTokenBudget(int? v) {
    _maxTokenBudget = (v == null || v <= 0) ? null : v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setMaxCostBudget(double? v) {
    _maxCostBudget = (v == null || v < 0) ? null : v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setCheckpointEnabled(bool v) {
    _checkpointEnabled = v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setSmokeCheckEnabled(bool v) {
    _smokeCheckEnabled = v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setSmokeReworkBudget(int v) {
    _smokeReworkBudget = v < 0 ? 0 : (v > 3 ? 3 : v);
    notifyListeners();
    _saveSettingsSoon();
  }

  void setRoleModelOverride(String role, String? modelName) {
    final r = role.trim().toLowerCase();
    if (r.isEmpty) return;
    final m = (modelName ?? "").trim();
    if (m.isEmpty || m == _model) {
      _roleModelOverrides.remove(r);
    } else {
      _roleModelOverrides[r] = {"model": m};
    }
    notifyListeners();
    _saveSettingsSoon();
  }

  void setSplitMaxConcurrency(int v) {
    _splitMaxConcurrency = v < 1 ? 1 : v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setMaxContextTokens(int v) {
    _maxContextTokens = v < 512 ? 512 : v;
    notifyListeners();
    _saveSettingsSoon();
  }

  void setContextHeadRatio(double v) {
    _contextHeadRatio = v < 0 ? 0 : (v > 0.6 ? 0.6 : v);
    notifyListeners();
    _saveSettingsSoon();
  }

  void setContextCompressType(String v) {
    _contextCompressType = v;
    notifyListeners();
    _saveSettingsSoon();
  }

  String _normalizeProjectType(String v) {
    final s = v.trim().toLowerCase();
    if (s.isEmpty) return "general";
    if (s == "wechat" || s == "miniprogram" || s == "mini_program") {
      return "wechat_miniprogram";
    }
    if (s == "uni-app") return "uniapp";
    if (s == "native" || s == "generic") return "general";
    return s;
  }

  String _runtimeFrameworkForProjectType(String projectType,
      {String fallback = "general"}) {
    final t = _normalizeProjectType(projectType);
    if (t == "wechat_miniprogram") return "wechat_miniprogram";
    if (t == "uniapp") return "uniapp";
    if (t == "general") return "general";
    if (t == "python") return "python";
    if (t == "flutter") return "flutter";
    if (t == "nextjs") return "nextjs";
    if (t == "react") return "react";
    if (t == "vue") return "vue";
    if (t == "html") return "html";
    return fallback.toLowerCase();
  }

  void _autoDetectFramework(List<String> files) {
    final lowered =
        files.map((e) => e.replaceAll("\\", "/").toLowerCase()).toList();
    if (lowered
        .any((f) => f == "pubspec.yaml" || f.endsWith("/pubspec.yaml"))) {
      _selectedFramework = "flutter";
      return;
    }
    if (lowered
        .any((f) => f == "package.json" || f.endsWith("/package.json"))) {
      final hasNext = lowered.any((f) => f.contains("next.config"));
      _selectedFramework = hasNext ? "nextjs" : "react";
      return;
    }
    if (lowered.any((f) => f == "index.html" || f.endsWith("/index.html"))) {
      _selectedFramework = "html";
    }
  }

  List<String> _fallbackFrameworksForWorkspace() {
    final ordered = <String>[];
    final primary = _selectedFramework.toLowerCase();
    ordered.add(primary);
    if (!ordered.contains("html")) ordered.add("html");
    if (!ordered.contains("react")) ordered.add("react");
    if (!ordered.contains("uniapp")) ordered.add("uniapp");
    if (!ordered.contains("vue")) ordered.add("vue");
    if (!ordered.contains("python")) ordered.add("python");
    if (!ordered.contains("general")) ordered.add("general");
    if (!ordered.contains("flutter")) ordered.add("flutter");
    return ordered;
  }

  // ─── Preview ───
  String _previewUrl = "http://localhost:3000";
  String _selectedFramework = "flutter";
  int _previewReloadSignal = 0;
  int _previewCaptureSignal = 0;

  String get previewUrl => _previewUrl;
  String get selectedFramework => _selectedFramework;
  int get previewReloadSignal => _previewReloadSignal;
  int get previewCaptureSignal => _previewCaptureSignal;
  String get activeWorkspacePath {
    final resolved = _workspaceResolvedPath.trim();
    if (resolved.isNotEmpty) return resolved;
    return _workspacePath();
  }

  void triggerPreviewReload() {
    _previewReloadSignal += 1;
    notifyListeners();
  }

  void requestPreviewSnapshot() {
    _previewCaptureSignal += 1;
    notifyListeners();
  }

  String _workspacePath() {
    final p = _activeProject;
    if (p == null) return ".";
    final ws = p.workspacePath.trim();
    if (ws.isNotEmpty) return ws;
    final safe = p.name.trim().isEmpty ? "project" : p.name.trim();
    return "./workspace/$safe";
  }

  void _ensureActiveConversation() {
    if (_activeConversationId != null) return;
    createConversation();
  }

  void _persistActiveConversation() {
    final id = _activeConversationId;
    if (id == null) return;
    _conversationMessages[id] = List<Message>.from(_messages);
  }

  void _syncActiveConversationMessages() {
    final id = _activeConversationId;
    if (id == null) return;
    _conversationMessages[id] = List<Message>.from(_messages);
  }

  void _touchConversation(String prompt) {
    final id = _activeConversationId;
    if (id == null) return;
    final idx = _conversations.indexWhere((c) => c.id == id);
    if (idx < 0) return;
    final current = _conversations[idx];
    final short = prompt.length > 48 ? "${prompt.substring(0, 48)}..." : prompt;
    _conversations[idx] = current.copyWith(
      title: current.title.trim().isEmpty ? short : current.title,
      lastMessage: short,
    );
    _saveSettingsSoon();
  }

  void _loadConversationState(Map<String, dynamic> data) {
    final convList = data["conversations"];
    final convMapRaw = data["conversation_messages"];
    final active = data["active_conversation_id"];

    if (convList is List) {
      final parsed = <Conversation>[];
      for (final item in convList) {
        if (item is Map<String, dynamic>) {
          parsed.add(_conversationFromJson(item));
        }
      }
      _conversations = parsed;
    }

    // Only load the ACTIVE conversation's messages into memory to avoid
    // holding thousands of messages for every conversation at startup.
    _conversationMessages.clear();
    _rawConversationMessagesJson = convMapRaw; // keep raw JSON for lazy load
    if (convMapRaw is Map && active != null) {
      final activeKey = active.toString();
      final value = convMapRaw[activeKey];
      if (value is List) {
        final msgs = <Message>[];
        for (final m in value) {
          if (m is Map<String, dynamic>) {
            msgs.add(_messageFromJson(m));
          }
        }
        _conversationMessages[activeKey] = msgs;
      }
    }

    _activeConversationId = active?.toString();
    if ((_activeConversationId?.isNotEmpty ?? false) &&
        !_conversations.any((c) => c.id == _activeConversationId)) {
      _activeConversationId =
          _conversations.isEmpty ? null : _conversations.first.id;
    }
    if (_activeConversationId != null) {
      _messages = List<Message>.from(
          _conversationMessages[_activeConversationId!] ?? const <Message>[]);
    } else {
      _messages = <Message>[];
    }
  }

  void _loadProjectState(Map<String, dynamic> data) {
    final rawProjects = data["projects"];
    final activeId = data["active_project_id"]?.toString();
    _projects.clear();
    if (rawProjects is List) {
      for (final item in rawProjects) {
        if (item is Map<String, dynamic>) {
          _projects.add(_projectFromJson(item));
        }
      }
    }
    if (_projects.isEmpty) {
      _activeProject = null;
      _currentProjectId = null;
      return;
    }
    Project? found;
    if (activeId != null && activeId.isNotEmpty) {
      for (final p in _projects) {
        if (p.id == activeId) {
          found = p;
          break;
        }
      }
    }
    found ??= _projects.first;
    _activeProject = found;
    _currentProjectId = found.id;
    _selectedFramework = _runtimeFrameworkForProjectType(
      found.projectType,
      fallback: found.framework,
    );
  }

  Map<String, dynamic> _conversationToJson(Conversation c) {
    return {
      "id": c.id,
      "title": c.title,
      "last_message": c.lastMessage,
      "created_at": c.createdAt.millisecondsSinceEpoch,
    };
  }

  Map<String, dynamic> _projectToJson(Project p) {
    return {
      "id": p.id,
      "name": p.name,
      "description": p.description,
      "framework": p.framework,
      "project_type": p.projectType,
      "workspace_path": p.workspacePath,
      "created_at": p.createdAt.millisecondsSinceEpoch,
      "updated_at": p.updatedAt.millisecondsSinceEpoch,
    };
  }

  Project _projectFromJson(Map<String, dynamic> json) {
    final createdMs = int.tryParse("${json["created_at"] ?? ""}");
    final updatedMs = int.tryParse("${json["updated_at"] ?? ""}");
    final framework = (json["framework"] ?? "general").toString();
    final projectType =
        _normalizeProjectType((json["project_type"] ?? framework).toString());
    return Project(
      id: (json["id"] ?? DateTime.now().millisecondsSinceEpoch.toString())
          .toString(),
      name: (json["name"] ?? "project").toString(),
      description: (json["description"] ?? "").toString(),
      framework:
          _runtimeFrameworkForProjectType(projectType, fallback: framework),
      projectType: projectType,
      workspacePath: (json["workspace_path"] ?? "").toString(),
      createdAt: createdMs == null
          ? null
          : DateTime.fromMillisecondsSinceEpoch(createdMs),
      updatedAt: updatedMs == null
          ? null
          : DateTime.fromMillisecondsSinceEpoch(updatedMs),
    );
  }

  Conversation _conversationFromJson(Map<String, dynamic> json) {
    final ms = int.tryParse("${json["created_at"] ?? ""}");
    return Conversation(
      id: (json["id"] ?? "").toString(),
      title: (json["title"] ?? "").toString(),
      lastMessage: (json["last_message"] ?? "").toString(),
      createdAt:
          ms == null ? DateTime.now() : DateTime.fromMillisecondsSinceEpoch(ms),
    );
  }

  Map<String, dynamic> _messageToJson(Message m) {
    return {
      "role": m.role,
      "content": m.content,
      "created_at": m.createdAt.millisecondsSinceEpoch,
      "mode": m.mode,
      "attention": m.attention,
      "agent_name": m.agentName,
      "agent_role": m.agentRole,
      "steps": m.steps,
      "steps_complete": m.stepsComplete,
      "generated_files": m.generatedFiles,
    };
  }

  Message _messageFromJson(Map<String, dynamic> json) {
    final ms = int.tryParse("${json["created_at"] ?? ""}");
    final files = json["generated_files"];
    return Message(
      role: (json["role"] ?? "assistant").toString(),
      content: (json["content"] ?? "").toString(),
      createdAt:
          ms == null ? DateTime.now() : DateTime.fromMillisecondsSinceEpoch(ms),
      mode: json["mode"]?.toString(),
      attention: double.tryParse("${json["attention"] ?? ""}"),
      agentName: json["agent_name"]?.toString(),
      agentRole: json["agent_role"]?.toString(),
      steps: int.tryParse("${json["steps"] ?? ""}"),
      stepsComplete: int.tryParse("${json["steps_complete"] ?? ""}"),
      generatedFiles: files is List ? files.map((e) => "$e").toList() : null,
    );
  }

  List<FileNode> _buildFileTree(List<String> files) {
    final roots = <FileNode>[];
    for (final raw in files) {
      final path = raw.trim().replaceAll("\\", "/");
      if (path.isEmpty) continue;
      final parts = path.split("/").where((p) => p.isNotEmpty).toList();
      if (parts.isEmpty) continue;
      _insertPath(roots, parts, path);
    }
    return roots;
  }

  void _insertPath(List<FileNode> roots, List<String> parts, String fullPath) {
    if (parts.length == 1) {
      if (!roots.any((n) => n.path == fullPath)) {
        roots.add(FileNode(
            name: parts.first, path: fullPath, isDir: false, children: []));
      }
      return;
    }
    final dirName = parts.first;
    final dirPath = parts.take(1).join("/");
    var dir = roots
        .where((n) => n.isDir && n.name == dirName)
        .cast<FileNode?>()
        .firstWhere(
          (n) => n != null,
          orElse: () => null,
        );
    if (dir == null) {
      dir = FileNode(name: dirName, path: dirPath, isDir: true, children: []);
      roots.add(dir);
    }
    _insertPathInChildren(dir.children, parts.sublist(1), fullPath,
        prefix: dirName);
  }

  void _insertPathInChildren(
    List<FileNode> children,
    List<String> parts,
    String fullPath, {
    required String prefix,
  }) {
    if (parts.length == 1) {
      if (!children.any((n) => n.path == fullPath)) {
        children.add(FileNode(
            name: parts.first, path: fullPath, isDir: false, children: []));
      }
      return;
    }
    final dirName = parts.first;
    final dirPath = "$prefix/$dirName";
    var dir = children
        .where((n) => n.isDir && n.path == dirPath)
        .cast<FileNode?>()
        .firstWhere(
          (n) => n != null,
          orElse: () => null,
        );
    if (dir == null) {
      dir = FileNode(name: dirName, path: dirPath, isDir: true, children: []);
      children.add(dir);
    }
    _insertPathInChildren(dir.children, parts.sublist(1), fullPath,
        prefix: dirPath);
  }

  Future<Map<String, dynamic>> getFrameworkStatus(String framework) async {
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/devserver/status");
    final payload = {
      "workspace": _workspacePath(),
      "framework": framework,
      "project_type": _activeProject?.projectType ??
          _activeProject?.framework ??
          _selectedFramework,
    };
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        return {"running": false};
      }
      final body = jsonDecode(resp.body);
      if (body is! Map<String, dynamic>) {
        return {"running": false};
      }
      final info = body["info"];
      if (info is Map<String, dynamic>) {
        final url = info["url"]?.toString();
        if (url != null && url.isNotEmpty && url != _previewUrl) {
          _previewUrl = url;
          notifyListeners();
        }
      }
      return body;
    } catch (_) {
      return {"running": false, "reason": "request_error"};
    }
  }

  Future<Map<String, dynamic>> startFrameworkServer({
    String? framework,
    int? port,
    String? command,
  }) async {
    final fw = (framework ?? _selectedFramework).toLowerCase();
    _executionProgress = "Starting preview ($fw)...";
    notifyListeners();
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/devserver/start");
    final payload = {
      "workspace": _workspacePath(),
      "framework": fw,
      "project_type": _activeProject?.projectType ??
          _activeProject?.framework ??
          _selectedFramework,
      if (port != null) "port": port,
      if (command != null && command.isNotEmpty) "command": command,
    };
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 12));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        String reason = "http_${resp.statusCode}";
        String message = "";
        try {
          final body = jsonDecode(resp.body);
          if (body is Map<String, dynamic>) {
            final detail = body["detail"];
            if (detail is Map<String, dynamic>) {
              reason = (detail["error"] ?? reason).toString();
              message = (detail["message"] ?? "").toString();
            }
          }
        } catch (_) {}
        final friendly =
            _humanizePreviewFailure(reason: reason, backendMessage: message);
        _consoleLogs.add(ConsoleLog(text: friendly, level: "error"));
        _executionProgress = friendly;
        notifyListeners();
        return {"running": false, "reason": reason, "message": friendly};
      }
      final body = jsonDecode(resp.body);
      if (body is! Map<String, dynamic>) {
        const fallback = "Preview start failed: invalid backend response.";
        _executionProgress = fallback;
        _consoleLogs.add(ConsoleLog(text: fallback, level: "error"));
        notifyListeners();
        return {
          "running": false,
          "reason": "invalid_response",
          "message": fallback
        };
      }
      final url = body["url"]?.toString();
      if (url != null && url.isNotEmpty && url != _previewUrl) {
        _previewUrl = url;
        _lastRunPreviewUrl = url;
        _lastRunWorkspace = activeWorkspacePath;
        notifyListeners();
      }
      final healthy =
          await _ensurePreviewBridgeHealthy(retries: 5, delayMs: 500);
      if (!healthy) {
        final reason = "preview_unhealthy";
        final friendly = _humanizePreviewFailure(
            reason: reason, backendMessage: _lastPreviewHealthReason);
        _consoleLogs.add(
            ConsoleLog(text: "$friendly ($_previewUrl)", level: "warning"));
        _executionProgress = friendly;
        notifyListeners();
        return {
          "running": false,
          "reason": reason,
          "message": friendly,
          "info": body
        };
      }
      _previewBlockedByMissingEntry = false;
      _executionProgress = "Preview running";
      notifyListeners();
      return {"running": true, "info": body};
    } catch (err) {
      const reason = "request_error";
      final friendly =
          _humanizePreviewFailure(reason: reason, backendMessage: "$err");
      _consoleLogs.add(ConsoleLog(text: friendly, level: "error"));
      _executionProgress = friendly;
      notifyListeners();
      return {"running": false, "reason": reason, "message": friendly};
    }
  }

  Future<Map<String, dynamic>> runPreviewWithSelfHeal(
      {String? framework}) async {
    final requestedFramework =
        (framework ?? _selectedFramework).trim().toLowerCase();
    Map<String, dynamic> last =
        await startFrameworkServer(framework: requestedFramework);
    if (last["running"] == true) {
      await _logRunOutputSummary();
      return last;
    }

    final reason = (last["reason"] ?? "").toString();
    if (reason != "entry_point_missing") {
      _consoleLogs.add(ConsoleLog(
          text: "Preview self-heal: trying restart...", level: "warning"));
      notifyListeners();
      final restarted =
          await restartFrameworkServer(framework: requestedFramework);
      if (restarted["running"] == true) {
        restarted["recovered_by"] = "restart";
        await _logRunOutputSummary();
        return restarted;
      }
      last = restarted;
    }

    if ((last["reason"] ?? "").toString() != "entry_point_missing") {
      for (final fw in _fallbackFrameworksForWorkspace()) {
        if (fw == requestedFramework) continue;
        _consoleLogs.add(ConsoleLog(
            text: "Preview self-heal: trying fallback framework '$fw'...",
            level: "warning"));
        notifyListeners();
        final fallback = await startFrameworkServer(framework: fw);
        if (fallback["running"] == true) {
          _selectedFramework = fw;
          fallback["recovered_by"] = "fallback_framework";
          fallback["framework"] = fw;
          await _logRunOutputSummary();
          notifyListeners();
          return fallback;
        }
        last = fallback;
      }
    }

    final logs = await getDevServerLogs(lines: 180);
    if (logs.trim().isNotEmpty) {
      last["devserver_logs"] = logs;
      _consoleLogs.add(ConsoleLog(
          text: "Devserver logs captured for failure diagnosis.",
          level: "warning"));
    }
    notifyListeners();
    return last;
  }

  bool isWebPreviewFramework(String? framework) {
    final fw = (framework ?? _selectedFramework).trim().toLowerCase();
    return fw == "html" ||
        fw == "general" ||
        fw == "react" ||
        fw == "vue" ||
        fw == "nextjs" ||
        fw == "uniapp";
  }

  Future<bool> openPreviewInExternalBrowser({String? url}) async {
    final target = (url ?? _previewUrl).trim();
    if (target.isEmpty) {
      _consoleLogs
          .add(ConsoleLog(text: "No preview URL to open.", level: "warning"));
      notifyListeners();
      return false;
    }
    try {
      if (Platform.isWindows) {
        await Process.start("cmd.exe", ["/c", "start", "", target],
            runInShell: true);
      } else if (Platform.isMacOS) {
        await Process.start("open", [target], runInShell: true);
      } else if (Platform.isLinux) {
        await Process.start("xdg-open", [target], runInShell: true);
      } else {
        _consoleLogs.add(ConsoleLog(
            text: "External browser open is not supported on this platform.",
            level: "warning"));
        notifyListeners();
        return false;
      }
      _consoleLogs.add(ConsoleLog(
          text: "Opened preview in browser: $target", level: "success"));
      notifyListeners();
      return true;
    } catch (err) {
      _consoleLogs.add(
          ConsoleLog(text: "Failed to open browser: $err", level: "error"));
      notifyListeners();
      return false;
    }
  }

  Future<void> _logRunOutputSummary() async {
    final ws = activeWorkspacePath;
    _lastRunWorkspace = ws;
    _consoleLogs.add(ConsoleLog(text: "Workspace: $ws", level: "info"));
    _consoleLogs.add(
      ConsoleLog(
        text:
            "Git Quick: git status | git add -A | git commit -m \"feat: update\"",
        level: "info",
      ),
    );
    final git = await api.getGitStatus(workspace: ws);
    if (git == null) {
      _lastRunGitKnown = false;
      _lastRunGitStatus = null;
      _consoleLogs.add(ConsoleLog(
          text: "Git: not initialized for current workspace.",
          level: "warning"));
      notifyListeners();
      return;
    }
    _lastRunGitKnown = true;
    _lastRunGitStatus = git;
    final branch = git.branch.trim().isEmpty ? "(detached)" : git.branch;
    _consoleLogs.add(
      ConsoleLog(
        text:
            "Git: branch=$branch, changed=${git.files.length}, clean=${git.isClean}",
        level: git.isClean ? "success" : "warning",
      ),
    );
    notifyListeners();
  }

  Future<bool> stopFrameworkServer({String? framework}) async {
    final fw = (framework ?? _selectedFramework).toLowerCase();
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/devserver/stop");
    final payload = {
      "workspace": _workspacePath(),
      "framework": fw,
      "project_type": _activeProject?.projectType ??
          _activeProject?.framework ??
          _selectedFramework,
    };
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 8));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        return false;
      }
      final body = jsonDecode(resp.body);
      if (body is Map<String, dynamic>) {
        return body["stopped"] == true;
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  Future<Map<String, dynamic>> restartFrameworkServer({
    String? framework,
    int? port,
    String? command,
  }) async {
    final fw = (framework ?? _selectedFramework).toLowerCase();
    _executionProgress = "Restarting preview ($fw)...";
    notifyListeners();
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/devserver/restart");
    final payload = {
      "workspace": _workspacePath(),
      "framework": fw,
      "project_type": _activeProject?.projectType ??
          _activeProject?.framework ??
          _selectedFramework,
      if (port != null) "port": port,
      if (command != null && command.isNotEmpty) "command": command,
    };
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode(payload),
          )
          .timeout(const Duration(seconds: 15));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        String reason = "http_${resp.statusCode}";
        String message = "";
        try {
          final body = jsonDecode(resp.body);
          if (body is Map<String, dynamic>) {
            final detail = body["detail"];
            if (detail is Map<String, dynamic>) {
              reason = (detail["error"] ?? reason).toString();
              message = (detail["message"] ?? "").toString();
            }
          }
        } catch (_) {}
        final friendly =
            _humanizePreviewFailure(reason: reason, backendMessage: message);
        _consoleLogs.add(ConsoleLog(text: friendly, level: "error"));
        _executionProgress = friendly;
        notifyListeners();
        return {"running": false, "reason": reason, "message": friendly};
      }
      final body = jsonDecode(resp.body);
      if (body is! Map<String, dynamic>) {
        const fallback = "Preview restart failed: invalid backend response.";
        _executionProgress = fallback;
        _consoleLogs.add(ConsoleLog(text: fallback, level: "error"));
        notifyListeners();
        return {
          "running": false,
          "reason": "invalid_response",
          "message": fallback
        };
      }
      final url = body["url"]?.toString();
      if (url != null && url.isNotEmpty && url != _previewUrl) {
        _previewUrl = url;
        _lastRunPreviewUrl = url;
        _lastRunWorkspace = activeWorkspacePath;
        notifyListeners();
      }
      final healthy =
          await _ensurePreviewBridgeHealthy(retries: 5, delayMs: 500);
      if (!healthy) {
        final reason = "preview_unhealthy";
        final friendly = _humanizePreviewFailure(
            reason: reason, backendMessage: _lastPreviewHealthReason);
        _consoleLogs.add(
            ConsoleLog(text: "$friendly ($_previewUrl)", level: "warning"));
        _executionProgress = friendly;
        notifyListeners();
        return {
          "running": false,
          "reason": reason,
          "message": friendly,
          "info": body
        };
      }
      _previewBlockedByMissingEntry = false;
      _executionProgress = "Preview running";
      notifyListeners();
      return {"running": true, "info": body};
    } catch (err) {
      const reason = "request_error";
      final friendly =
          _humanizePreviewFailure(reason: reason, backendMessage: "$err");
      _consoleLogs.add(ConsoleLog(text: friendly, level: "error"));
      _executionProgress = friendly;
      notifyListeners();
      return {"running": false, "reason": reason, "message": friendly};
    }
  }

  String previewFailureMessage(Map<String, dynamic> result) {
    final reason = (result["reason"] ?? "unknown").toString();
    final message = (result["message"] ?? "").toString();
    return _humanizePreviewFailure(reason: reason, backendMessage: message);
  }

  String _humanizePreviewFailure({
    required String reason,
    String backendMessage = "",
  }) {
    final r = reason.trim().toLowerCase();
    String base;
    if (r == "entry_point_missing") {
      base =
          "Preview cannot start: entry point is missing. Generate project scaffold first.";
    } else if (r == "request_error") {
      base =
          "Preview request failed. Check backend connection on http://localhost:8001.";
    } else if (r.startsWith("http_")) {
      base = "Preview request failed with backend error ($r).";
    } else if (r == "preview_unhealthy") {
      base = "Preview server started but health check failed.";
    } else if (r == "invalid_response") {
      base = "Preview request failed: backend response is invalid.";
    } else if (r == "env_missing") {
      base = "Preview environment is incomplete (missing runtime tools).";
    } else {
      base = "Preview start failed: $r";
    }
    final extra = backendMessage.trim();
    if (extra.isEmpty) return base;
    return "$base Details: $extra";
  }

  Future<Map<String, dynamic>> getEmulatorStatus() async {
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/emulator/status");
    try {
      final resp = await http
          .get(uri, headers: _backendHeaders())
          .timeout(const Duration(seconds: 4));
      if (resp.statusCode < 200 || resp.statusCode >= 300) {
        return {"running": false, "device": "None", "mirror_running": false};
      }
      final body = jsonDecode(resp.body);
      if (body is! Map<String, dynamic>) {
        return {"running": false, "device": "None", "mirror_running": false};
      }
      return body;
    } catch (_) {
      return {"running": false, "device": "None", "mirror_running": false};
    }
  }

  Future<void> startEmulatorMirror() async {
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/emulator/mirror/start");
    try {
      await http
          .post(uri, headers: _backendHeaders())
          .timeout(const Duration(seconds: 4));
    } catch (_) {}
  }

  /// Get list of connected ADB devices (via backend or local ADB)
  Future<List<Map<String, dynamic>>> getConnectedDevices() async {
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/emulator/devices");
    try {
      final resp = await http
          .get(uri, headers: _backendHeaders())
          .timeout(const Duration(seconds: 6));
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final body = jsonDecode(resp.body);
        if (body is List) {
          return body.cast<Map<String, dynamic>>();
        }
      }
    } catch (_) {}
    // Fallback: try local adb
    try {
      final result =
          await Process.run("adb", ["devices", "-l"], runInShell: true);
      if (result.exitCode != 0) return [];
      final lines = (result.stdout as String).trim().split("\n").skip(1);
      final devices = <Map<String, dynamic>>[];
      for (final line in lines) {
        final parts = line.trim().split(RegExp(r"\s+"));
        if (parts.length >= 2 && parts[1] == "device") {
          final id = parts[0];
          String model = id;
          final modelMatch = RegExp(r"model:(\S+)").firstMatch(line);
          if (modelMatch != null) model = modelMatch.group(1) ?? id;
          devices.add(
              {"id": id, "model": model, "type": "device", "status": "online"});
        } else if (parts.length >= 2 && parts[1] == "offline") {
          devices.add({
            "id": parts[0],
            "model": parts[0],
            "type": "device",
            "status": "offline"
          });
        }
      }
      return devices;
    } catch (_) {
      return [];
    }
  }

  /// Start scrcpy mirror for a specific device
  Future<bool> startMirrorForDevice(String deviceId,
      {int? maxFps, int? bitRate, int? maxSize}) async {
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/emulator/mirror/start");
    try {
      final resp = await http
          .post(
            uri,
            headers: _backendHeaders(json: true),
            body: jsonEncode({
              "device_id": deviceId,
              "max_fps": maxFps ?? 30,
              "bit_rate": bitRate ?? 4000000,
              "max_size": maxSize ?? 1280,
            }),
          )
          .timeout(const Duration(seconds: 8));
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (_) {}
    // Fallback: local scrcpy
    try {
      await Process.start(
        "scrcpy",
        [
          "-s",
          deviceId,
          "--max-fps",
          "${maxFps ?? 30}",
          "-b",
          "${(bitRate ?? 4000000) ~/ 1000}K",
          "-m",
          "${maxSize ?? 1280}"
        ],
        runInShell: true,
        mode: ProcessStartMode.detached,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Stop scrcpy mirror
  Future<void> stopEmulatorMirror() async {
    final base = _baseUrl.replaceAll(RegExp(r"/+$"), "");
    final uri = Uri.parse("$base/api/emulator/mirror/stop");
    try {
      await http
          .post(uri, headers: _backendHeaders())
          .timeout(const Duration(seconds: 4));
    } catch (_) {}
    // Also try killing local scrcpy
    try {
      if (Platform.isWindows) {
        await Process.run("taskkill", ["/F", "/IM", "scrcpy.exe"],
            runInShell: true);
      } else {
        await Process.run("pkill", ["scrcpy"], runInShell: true);
      }
    } catch (_) {}
  }

  /// Check if ADB is available
  Future<bool> isAdbAvailable() async {
    try {
      final result = await Process.run("adb", ["version"], runInShell: true);
      return result.exitCode == 0;
    } catch (_) {
      return false;
    }
  }

  /// Check if scrcpy is available
  Future<bool> isScrcpyAvailable() async {
    try {
      final result =
          await Process.run("scrcpy", ["--version"], runInShell: true);
      return result.exitCode == 0;
    } catch (_) {
      return false;
    }
  }

  // �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T
  // Advanced Backend Features (Full API Coverage)
  // �T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T�T

  /// Get execution status by run_id
  Future<ExecutionRecord?> getExecutionStatus(String runId) async {
    return await api.getExecution(runId);
  }

  /// Load checkpoint payload for a completed run.
  Future<Map<String, dynamic>?> getExecutionCheckpoint({String? runId}) async {
    final rid = (runId ?? _lastCompletedRunId ?? _activeRunId ?? "").trim();
    if (rid.isEmpty) return null;
    final data = await api.getExecutionCheckpoint(rid);
    if (data == null || data["ok"] != true) {
      addConsoleLog("Checkpoint fetch failed for run: $rid", level: "warning");
      return null;
    }
    return data;
  }

  /// Get git diff for current workspace.
  Future<String> getWorkspaceDiff() async {
    final ws = _workspacePath().trim();
    if (ws.isEmpty) return "";
    return await api.getGitDiff(workspace: ws);
  }

  /// Refresh git status for the last run workspace.
  Future<GitStatusSnapshot?> refreshRunGitStatus() async {
    final ws = lastRunWorkspace.trim();
    if (ws.isEmpty) {
      _lastRunGitKnown = false;
      _lastRunGitStatus = null;
      notifyListeners();
      return null;
    }
    final status = await api.getGitStatus(workspace: ws);
    _lastRunGitKnown = status != null;
    _lastRunGitStatus = status;
    notifyListeners();
    return status;
  }

  /// Stage all files for the last run workspace (`git add -A`).
  Future<bool> stageAllRunWorkspace() async {
    final ws = lastRunWorkspace.trim();
    if (ws.isEmpty) return false;
    final ok = await api.stageGit(workspace: ws);
    if (ok) {
      addConsoleLog("Git staged all changes for $ws", level: "success");
      await refreshRunGitStatus();
    } else {
      addConsoleLog("Git stage failed for $ws", level: "error");
    }
    return ok;
  }

  /// Commit staged changes for the last run workspace.
  Future<bool> quickCommitRunWorkspace({
    required String message,
    bool stageAll = false,
  }) async {
    final ws = lastRunWorkspace.trim();
    final msg = message.trim();
    if (ws.isEmpty || msg.isEmpty) return false;
    if (stageAll) {
      final staged = await api.stageGit(workspace: ws);
      if (!staged) {
        addConsoleLog("Git stage failed for $ws", level: "error");
        return false;
      }
    }
    final ok = await api.commitGit(workspace: ws, message: msg);
    if (ok) {
      addConsoleLog("Git commit succeeded: $msg", level: "success");
      await refreshRunGitStatus();
    } else {
      addConsoleLog("Git commit failed: $msg", level: "error");
    }
    return ok;
  }

  /// Resume from a previous run checkpoint.
  Future<String?> restoreFromCheckpoint(
      {String? runId, String? resumeStage}) async {
    final sourceRunId =
        (runId ?? _lastCompletedRunId ?? _activeRunId ?? "").trim();
    if (sourceRunId.isEmpty) return null;

    _status = "running";
    _executionStatus = "queued";
    _executionProgress = "Restoring from checkpoint...";
    notifyListeners();

    final resumedRunId = await api.resumeExecution(
      runId: sourceRunId,
      apiKey: _apiKey,
      provider: _selectedProvider,
      model: _selectedModel,
      baseUrl: _llmBaseUrl,
      workspace: _workspacePath(),
      priority: _runPriority,
      maxTokenBudget: _maxTokenBudget,
      maxCostBudget: _maxCostBudget,
      checkpointEnabled: _checkpointEnabled,
      smokeCheckEnabled: _smokeCheckEnabled,
      smokeReworkBudget: _smokeReworkBudget,
      roleModelOverrides:
          _roleModelOverrides.isEmpty ? null : _roleModelOverrides,
      resumeStage: resumeStage,
    );

    if (resumedRunId == null || resumedRunId.trim().isEmpty) {
      _status = "idle";
      _executionStatus = "failed";
      _executionProgress = "Checkpoint restore failed.";
      addConsoleLog("Checkpoint restore failed for run: $sourceRunId",
          level: "error");
      notifyListeners();
      return null;
    }

    _activeRunId = resumedRunId.trim();
    _executionStatus = "running";
    _executionProgress = "Checkpoint restore started.";
    addConsoleLog(
        "Checkpoint restore started: $_activeRunId (from $sourceRunId)",
        level: "success");
    _startRunWatchdog(_activeRunId!);
    notifyListeners();
    return _activeRunId;
  }

  /// Run security test
  Future<SecurityTestResult?> runSecurityTest(String targetUrl,
      {List<String> tools = const ["zap"]}) async {
    final result =
        await api.runSecurityTest(targetUrl: targetUrl, tools: tools);
    if (result != null && result.started) {
      addConsoleLog("Security test started: ${result.runId}", level: "info");
    }
    return result;
  }

  /// Get dev server logs
  Future<String> getDevServerLogs({int lines = 200}) async {
    final ws = activeProject?.workspacePath ?? workspacePath;
    final logs = await api.getDevServerLogs(
      workspace: ws,
      framework: _selectedFramework,
      lines: lines,
    );
    return logs?.logs ?? "";
  }

  /// Start emulator
  Future<bool> startEmulator({String? avd}) async {
    addConsoleLog("Starting emulator${avd != null ? ' ($avd)' : ''}...",
        level: "info");
    final ok = await api.startEmulator(avd: avd);
    if (ok) {
      addConsoleLog("Emulator started", level: "success");
    } else {
      addConsoleLog("Failed to start emulator", level: "error");
    }
    return ok;
  }

  /// Stop emulator
  Future<bool> stopEmulator() async {
    final ok = await api.stopEmulator();
    if (ok) {
      addConsoleLog("Emulator stopped", level: "info");
    }
    return ok;
  }

  /// Get AutoGPT agent catalog
  Future<List<AutoGPTAgent>> getAutoGPTCatalog({int limit = 100}) async {
    return await api.getAutoGPTCatalog(limit: limit);
  }

  /// Import AutoGPT agent to current workspace
  Future<bool> importAutoGPTAgent(String agentId) async {
    final ws = activeProject?.workspacePath ?? workspacePath;
    addConsoleLog("Importing AutoGPT agent: $agentId", level: "info");
    final result =
        await api.importAutoGPTAgent(agentId: agentId, workspace: ws);
    if (result != null && result["ok"] == true) {
      _linkedAutoGptAgentId = agentId.trim();
      addConsoleLog("AutoGPT agent imported successfully", level: "success");
      addConsoleLog("Linked AutoGPT agent for run: $_linkedAutoGptAgentId",
          level: "info");
      await refreshFileTree();
      _saveSettingsSoon();
      notifyListeners();
      return true;
    }
    addConsoleLog("Failed to import AutoGPT agent", level: "error");
    return false;
  }

  /// Analyze AutoGPT workflow
  Future<WorkflowAnalysis?> analyzeAutoGPTWorkflow(String agentId) async {
    return await api.analyzeAutoGPTWorkflow(agentId);
  }

  /// Execute a workflow
  Future<String?> executeWorkflow({
    required WorkflowSpec workflow,
    Map<String, dynamic> inputs = const {},
  }) async {
    final ws = activeProject?.workspacePath ?? workspacePath;
    addConsoleLog("Executing workflow with ${workflow.nodes.length} nodes...",
        level: "info");
    final runId = await api.executeWorkflow(
      workflow: workflow,
      workspace: ws,
      apiKey: _apiKey,
      provider: _selectedProvider,
      model: _selectedModel,
      baseUrl: _llmBaseUrl,
      inputs: inputs,
    );
    if (runId != null) {
      addConsoleLog("Workflow started: $runId", level: "success");
    }
    return runId;
  }

  /// Generate code from requirements
  Future<GenerateResult?> generateCode({
    required String requirement,
    required String language,
    required List<String> platforms,
    bool includeCi = true,
    bool includeSecurity = true,
    bool aiCodegen = true,
    bool metagptChain = false,
    bool metagptNative = false,
  }) async {
    final ws = activeProject?.workspacePath ?? workspacePath;
    addConsoleLog("Generating code: $requirement", level: "info");
    _status = "generating";
    notifyListeners();

    final result = await api.generate(
      requirement: requirement,
      language: language,
      platforms: platforms,
      workspace: ws,
      apiKey: _apiKey,
      provider: _selectedProvider,
      model: _selectedModel,
      baseUrl: _llmBaseUrl,
      includeCi: includeCi,
      includeSecurity: includeSecurity,
      aiCodegen: aiCodegen,
      metagptChain: metagptChain,
      metagptNative: metagptNative,
    );

    if (result != null) {
      addConsoleLog("Code generation started: ${result.runId}",
          level: "success");
      _activeRunId = result.runId;
      notifyListeners();
    } else {
      addConsoleLog("Failed to start code generation", level: "error");
      _status = "error";
      notifyListeners();
    }

    return result;
  }

  /// Get connected devices and AVDs
  Future<Map<String, dynamic>> getEmulatorDevices() async {
    return await api.getEmulatorDevices();
  }

  /// Poll execution status until complete
  Future<ExecutionRecord?> pollExecution(String runId,
      {Duration interval = const Duration(seconds: 2),
      Duration timeout = const Duration(minutes: 30)}) async {
    final stopwatch = Stopwatch()..start();
    while (stopwatch.elapsed < timeout) {
      final record = await api.getExecution(runId);
      if (record == null) return null;

      if (record.status == "finished" ||
          record.status == "failed" ||
          record.status == "cancelled") {
        return record;
      }

      await Future.delayed(interval);
    }
    return null;
  }
}

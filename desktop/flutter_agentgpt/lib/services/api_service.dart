import "dart:async";
import "dart:convert";
import "package:rebot_agentgpt/core/http_retry.dart";
import "package:rebot_agentgpt/core/performance_monitor.dart";

class ExecutionRecord {
  final String runId;
  final String status;
  final String stage;
  final String progress;
  final Map<String, dynamic> metrics;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final Map<String, dynamic>? result;

  ExecutionRecord({
    required this.runId,
    required this.status,
    required this.stage,
    required this.progress,
    this.metrics = const {},
    this.createdAt,
    this.updatedAt,
    this.result,
  });

  factory ExecutionRecord.fromJson(Map<String, dynamic> json) {
    return ExecutionRecord(
      runId: json["run_id"] ?? "",
      status: json["status"] ?? "unknown",
      stage: json["stage"] ?? "",
      progress: json["progress"] ?? "",
      metrics: json["metrics"] ?? {},
      createdAt: json["created_at"] != null
          ? DateTime.tryParse(json["created_at"].toString())
          : null,
      updatedAt: json["updated_at"] != null
          ? DateTime.tryParse(json["updated_at"].toString())
          : null,
      result: json["result"],
    );
  }
}

class DevServerInfo {
  final String url;
  final String command;
  final int port;
  final int pid;
  final Map<String, dynamic>? previewHealth;

  DevServerInfo({
    required this.url,
    required this.command,
    required this.port,
    required this.pid,
    this.previewHealth,
  });

  factory DevServerInfo.fromJson(Map<String, dynamic> json) {
    return DevServerInfo(
      url: json["url"] ?? "",
      command: json["command"] ?? "",
      port: json["port"] ?? 0,
      pid: json["pid"] ?? 0,
      previewHealth: json["preview_health"],
    );
  }
}

class AutoGPTAgent {
  final String agentId;
  final String name;
  final String description;
  final String sourcePath;

  AutoGPTAgent({
    required this.agentId,
    required this.name,
    required this.description,
    required this.sourcePath,
  });

  factory AutoGPTAgent.fromJson(Map<String, dynamic> json) {
    return AutoGPTAgent(
      agentId: json["agent_id"] ?? "",
      name: json["name"] ?? "",
      description: json["description"] ?? "",
      sourcePath: json["source_path"] ?? "",
    );
  }
}

class WorkflowAnalysis {
  final String agentId;
  final String name;
  final int nodeCount;
  final int edgeCount;
  final int levels;
  final List<String> inferredFiles;
  final String summary;

  WorkflowAnalysis({
    required this.agentId,
    required this.name,
    required this.nodeCount,
    required this.edgeCount,
    required this.levels,
    required this.inferredFiles,
    required this.summary,
  });

  factory WorkflowAnalysis.fromJson(Map<String, dynamic> json) {
    return WorkflowAnalysis(
      agentId: json["agent_id"] ?? "",
      name: json["name"] ?? "",
      nodeCount: json["node_count"] ?? 0,
      edgeCount: json["edge_count"] ?? 0,
      levels: json["levels"] ?? 0,
      inferredFiles: List<String>.from(json["inferred_files"] ?? []),
      summary: json["summary"] ?? "",
    );
  }
}

class SecurityTestResult {
  final String runId;
  final bool started;

  SecurityTestResult({required this.runId, required this.started});

  factory SecurityTestResult.fromJson(Map<String, dynamic> json) {
    return SecurityTestResult(
      runId: json["run_id"] ?? "",
      started: json["run_id"] != null,
    );
  }
}

class GenerateResult {
  final String runId;

  GenerateResult({required this.runId});

  factory GenerateResult.fromJson(Map<String, dynamic> json) {
    return GenerateResult(runId: json["run_id"] ?? "");
  }
}

class DevServerLogs {
  final String logs;
  final int lines;

  DevServerLogs({required this.logs, required this.lines});

  factory DevServerLogs.fromJson(Map<String, dynamic> json) {
    return DevServerLogs(
      logs: json["logs"] ?? "",
      lines: json["lines"] ?? 0,
    );
  }
}

class EmulatorStatus {
  final bool running;
  final String? device;
  final String? avd;
  final bool mirrorActive;

  EmulatorStatus({
    required this.running,
    this.device,
    this.avd,
    this.mirrorActive = false,
  });

  factory EmulatorStatus.fromJson(Map<String, dynamic> json) {
    return EmulatorStatus(
      running: json["running"] ?? false,
      device: json["device"],
      avd: json["avd"],
      mirrorActive: json["mirror_active"] ?? false,
    );
  }
}

class ProviderCapability {
  final String id;
  final String name;
  final bool enabled;
  final bool supportsStream;
  final bool supportsReasoning;
  final String defaultBaseUrl;
  final List<String> models;

  ProviderCapability({
    required this.id,
    required this.name,
    required this.enabled,
    required this.supportsStream,
    required this.supportsReasoning,
    required this.defaultBaseUrl,
    required this.models,
  });

  factory ProviderCapability.fromJson(Map<String, dynamic> json) {
    return ProviderCapability(
      id: (json["id"] ?? "").toString(),
      name: (json["name"] ?? "").toString(),
      enabled: json["enabled"] == true,
      supportsStream: json["supports_stream"] == true,
      supportsReasoning: json["supports_reasoning"] == true,
      defaultBaseUrl: (json["default_base_url"] ?? "").toString(),
      models: List<String>.from(json["models"] ?? const <String>[]),
    );
  }
}

class ToolCapability {
  final String id;
  final String name;
  final String category;
  final bool enabled;
  final String description;

  ToolCapability({
    required this.id,
    required this.name,
    required this.category,
    required this.enabled,
    required this.description,
  });

  factory ToolCapability.fromJson(Map<String, dynamic> json) {
    return ToolCapability(
      id: (json["id"] ?? "").toString(),
      name: (json["name"] ?? "").toString(),
      category: (json["category"] ?? "").toString(),
      enabled: json["enabled"] == true,
      description: (json["description"] ?? "").toString(),
    );
  }
}

class TemplateMarketItem {
  final String id;
  final String name;
  final String description;
  final String framework;
  final String projectType;
  final List<String> tags;
  final String createdAt;
  final String updatedAt;
  final String projectPath;
  final String templatePath;

  TemplateMarketItem({
    required this.id,
    required this.name,
    required this.description,
    required this.framework,
    required this.projectType,
    required this.tags,
    required this.createdAt,
    required this.updatedAt,
    required this.projectPath,
    required this.templatePath,
  });

  factory TemplateMarketItem.fromJson(Map<String, dynamic> json) {
    return TemplateMarketItem(
      id: (json["id"] ?? "").toString(),
      name: (json["name"] ?? "").toString(),
      description: (json["description"] ?? "").toString(),
      framework: (json["framework"] ?? "general").toString(),
      projectType: (json["project_type"] ?? json["framework"] ?? "general").toString(),
      tags: List<String>.from(json["tags"] ?? const <String>[]),
      createdAt: (json["created_at"] ?? "").toString(),
      updatedAt: (json["updated_at"] ?? "").toString(),
      projectPath: (json["project_path"] ?? "").toString(),
      templatePath: (json["template_path"] ?? "").toString(),
    );
  }
}

class InstalledPlugin {
  final String id;
  final String name;
  final String version;
  final String description;
  final bool enabled;
  final List<String> permissions;
  final String indexStatus;
  final String signatureAlg;
  final String digest;
  final String installedAt;
  final String updatedAt;
  final String currentPath;
  final List<Map<String, dynamic>> versions;

  InstalledPlugin({
    required this.id,
    required this.name,
    required this.version,
    required this.description,
    required this.enabled,
    required this.permissions,
    required this.indexStatus,
    required this.signatureAlg,
    required this.digest,
    required this.installedAt,
    required this.updatedAt,
    required this.currentPath,
    required this.versions,
  });

  factory InstalledPlugin.fromJson(Map<String, dynamic> json) {
    return InstalledPlugin(
      id: (json["id"] ?? "").toString(),
      name: (json["name"] ?? "").toString(),
      version: (json["version"] ?? "").toString(),
      description: (json["description"] ?? "").toString(),
      enabled: json["enabled"] == true,
      permissions: List<String>.from(json["permissions"] ?? const <String>[]),
      indexStatus: (json["index_status"] ?? "ok").toString(),
      signatureAlg: (json["signature_alg"] ?? "").toString(),
      digest: (json["digest"] ?? "").toString(),
      installedAt: (json["installed_at"] ?? "").toString(),
      updatedAt: (json["updated_at"] ?? "").toString(),
      currentPath: (json["current_path"] ?? "").toString(),
      versions: (json["versions"] as List? ?? const [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
    );
  }
}

class GitFileStatus {
  final String path;
  final String? renamedFrom;
  final String indexStatus;
  final String worktreeStatus;
  final bool staged;
  final bool unstaged;
  final bool untracked;
  final bool deleted;
  final bool renamed;

  GitFileStatus({
    required this.path,
    this.renamedFrom,
    required this.indexStatus,
    required this.worktreeStatus,
    required this.staged,
    required this.unstaged,
    required this.untracked,
    required this.deleted,
    required this.renamed,
  });

  factory GitFileStatus.fromJson(Map<String, dynamic> json) {
    return GitFileStatus(
      path: (json["path"] ?? "").toString(),
      renamedFrom: json["renamed_from"]?.toString(),
      indexStatus: (json["index_status"] ?? " ").toString(),
      worktreeStatus: (json["worktree_status"] ?? " ").toString(),
      staged: json["staged"] == true,
      unstaged: json["unstaged"] == true,
      untracked: json["untracked"] == true,
      deleted: json["deleted"] == true,
      renamed: json["renamed"] == true,
    );
  }
}

class GitStatusSnapshot {
  final String root;
  final String branch;
  final String upstream;
  final int ahead;
  final int behind;
  final bool isClean;
  final List<GitFileStatus> files;

  GitStatusSnapshot({
    required this.root,
    required this.branch,
    required this.upstream,
    required this.ahead,
    required this.behind,
    required this.isClean,
    required this.files,
  });

  factory GitStatusSnapshot.fromJson(Map<String, dynamic> json) {
    return GitStatusSnapshot(
      root: (json["root"] ?? "").toString(),
      branch: (json["branch"] ?? "").toString(),
      upstream: (json["upstream"] ?? "").toString(),
      ahead: (json["ahead"] ?? 0) as int,
      behind: (json["behind"] ?? 0) as int,
      isClean: json["is_clean"] == true,
      files: (json["files"] as List? ?? const [])
          .map((e) => GitFileStatus.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
    );
  }
}

class GitBranch {
  final String name;
  final String upstream;
  final bool current;

  GitBranch({
    required this.name,
    required this.upstream,
    required this.current,
  });

  factory GitBranch.fromJson(Map<String, dynamic> json) {
    return GitBranch(
      name: (json["name"] ?? "").toString(),
      upstream: (json["upstream"] ?? "").toString(),
      current: json["current"] == true,
    );
  }
}

class GitCommit {
  final String hash;
  final String shortHash;
  final String author;
  final String date;
  final String subject;

  GitCommit({
    required this.hash,
    required this.shortHash,
    required this.author,
    required this.date,
    required this.subject,
  });

  factory GitCommit.fromJson(Map<String, dynamic> json) {
    return GitCommit(
      hash: (json["hash"] ?? "").toString(),
      shortHash: (json["short_hash"] ?? "").toString(),
      author: (json["author"] ?? "").toString(),
      date: (json["date"] ?? "").toString(),
      subject: (json["subject"] ?? "").toString(),
    );
  }
}

class WorkflowNode {
  final String id;
  final String type;
  final Map<String, dynamic> data;

  WorkflowNode({
    required this.id,
    required this.type,
    required this.data,
  });

  Map<String, dynamic> toJson() => {
        "id": id,
        "type": type,
        "data": data,
      };
}

class WorkflowEdge {
  final String source;
  final String target;

  WorkflowEdge({required this.source, required this.target});

  Map<String, dynamic> toJson() => {
        "source": source,
        "target": target,
      };
}

class WorkflowSpec {
  final List<WorkflowNode> nodes;
  final List<WorkflowEdge> edges;

  WorkflowSpec({required this.nodes, required this.edges});

  Map<String, dynamic> toJson() => {
        "nodes": nodes.map((n) => n.toJson()).toList(),
        "edges": edges.map((e) => e.toJson()).toList(),
      };
}

class ApiService {
  final String baseUrl;
  final String? serverApiKey;
  final Duration timeout;
  late final HttpRetryClient _http;

  ApiService({
    required this.baseUrl,
    this.serverApiKey,
    this.timeout = const Duration(seconds: 30),
    HttpRetryClient? httpClient,
  }) {
    _http = httpClient ??
        HttpRetryClient(
          maxRetries: 2,
          baseDelay: const Duration(milliseconds: 400),
          strategy: RetryStrategy.exponential,
          onRetry: (attempt, delay, error) {
            PerformanceMonitor.instance.recordMetric(
              "api_retry",
              attempt,
            );
          },
        );
  }

  String get _base => baseUrl.replaceAll(RegExp(r"/+$"), "");

  Map<String, String> get _authHeaders {
    final key = (serverApiKey ?? "").trim();
    if (key.isEmpty) return const {};
    return {"X-API-Key": key};
  }

  Map<String, String> get _jsonHeaders => {
        "Content-Type": "application/json",
        ..._authHeaders,
      };

  Future<List<ExecutionRecord>> listExecutions({int limit = 50}) async {
    try {
      final uri = Uri.parse("$_base/api/executions?limit=$limit");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        final executions = json["executions"] as List? ?? [];
        return executions.map((e) => ExecutionRecord.fromJson(e)).toList();
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "listExecutions");
    }
    return [];
  }

  Future<ExecutionRecord?> getExecution(String runId) async {
    try {
      final uri = Uri.parse("$_base/api/executions/$runId");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        if (json["error"] != null) return null;
        return ExecutionRecord.fromJson(json);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getExecution");
    }
    return null;
  }

  Future<bool> cancelExecution(String runId) async {
    try {
      final uri = Uri.parse("$_base/api/executions/$runId/cancel");
      final resp = await _http.post(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        return json["ok"] == true;
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "cancelExecution");
    }
    return false;
  }

  Future<SecurityTestResult?> runSecurityTest({
    required String targetUrl,
    List<String> tools = const ["zap"],
  }) async {
    try {
      final uri = Uri.parse("$_base/api/security/test");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "target_url": targetUrl,
          "tools": tools,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return SecurityTestResult.fromJson(jsonDecode(resp.body));
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "runSecurityTest");
    }
    return null;
  }

  Future<DevServerLogs?> getDevServerLogs({
    required String workspace,
    required String framework,
    int lines = 200,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/devserver/logs");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "framework": framework,
          "lines": lines,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return DevServerLogs.fromJson(jsonDecode(resp.body));
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getDevServerLogs");
    }
    return null;
  }

  Future<DevServerInfo?> startDevServer({
    required String workspace,
    required String framework,
    String? projectType,
    int? port,
    String? command,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/devserver/start");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "framework": framework,
          if (projectType != null) "project_type": projectType,
          if (port != null) "port": port,
          if (command != null) "command": command,
        }),
        timeout: const Duration(seconds: 120),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return DevServerInfo.fromJson(jsonDecode(resp.body));
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "startDevServer");
    }
    return null;
  }

  Future<bool> stopDevServer({
    required String workspace,
    required String framework,
    String? projectType,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/devserver/stop");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "framework": framework,
          if (projectType != null) "project_type": projectType,
        }),
        timeout: timeout,
      );
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "stopDevServer");
    }
    return false;
  }

  Future<DevServerInfo?> restartDevServer({
    required String workspace,
    required String framework,
    String? projectType,
    int? port,
    String? command,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/devserver/restart");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "framework": framework,
          if (projectType != null) "project_type": projectType,
          if (port != null) "port": port,
          if (command != null) "command": command,
        }),
        timeout: const Duration(seconds: 120),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return DevServerInfo.fromJson(jsonDecode(resp.body));
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "restartDevServer");
    }
    return null;
  }

  Future<Map<String, dynamic>?> getDevServerStatus({
    required String workspace,
    required String framework,
    String? projectType,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/devserver/status");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "framework": framework,
          if (projectType != null) "project_type": projectType,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return jsonDecode(resp.body);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getDevServerStatus");
    }
    return null;
  }

  Future<bool> startEmulator({String? avd}) async {
    try {
      final uri = Uri.parse("$_base/api/emulator/start");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          if (avd != null) "avd": avd,
        }),
        timeout: const Duration(seconds: 60),
      );
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "startEmulator");
    }
    return false;
  }

  Future<bool> stopEmulator() async {
    try {
      final uri = Uri.parse("$_base/api/emulator/stop");
      final resp = await _http.post(uri, headers: _authHeaders, timeout: timeout);
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "stopEmulator");
    }
    return false;
  }

  Future<EmulatorStatus?> getEmulatorStatus() async {
    try {
      final uri = Uri.parse("$_base/api/emulator/status");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return EmulatorStatus.fromJson(jsonDecode(resp.body));
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getEmulatorStatus");
    }
    return null;
  }

  Future<bool> startEmulatorMirror({String? device}) async {
    try {
      final uri = Uri.parse("$_base/api/emulator/mirror/start");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          if (device != null) "device": device,
        }),
        timeout: timeout,
      );
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "startEmulatorMirror");
    }
    return false;
  }

  Future<bool> stopEmulatorMirror() async {
    try {
      final uri = Uri.parse("$_base/api/emulator/mirror/stop");
      final resp = await _http.post(uri, headers: _authHeaders, timeout: timeout);
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "stopEmulatorMirror");
    }
    return false;
  }

  Future<Map<String, dynamic>> getEmulatorDevices() async {
    try {
      final uri = Uri.parse("$_base/api/emulator/devices");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return jsonDecode(resp.body);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getEmulatorDevices");
    }
    return {"devices": [], "avds": [], "count": 0};
  }

  Future<List<AutoGPTAgent>> getAutoGPTCatalog({int limit = 100}) async {
    try {
      final uri = Uri.parse("$_base/api/autogpt/catalog?limit=$limit");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        final agents = json["agents"] as List? ?? [];
        return agents.map((a) => AutoGPTAgent.fromJson(a)).toList();
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getAutoGPTCatalog");
    }
    return [];
  }

  Future<List<ProviderCapability>> getProviderCapabilities() async {
    try {
      final uri = Uri.parse("$_base/api/capabilities/providers");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        final providers = json["providers"] as List? ?? const [];
        return providers.map((e) => ProviderCapability.fromJson(e)).toList();
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getProviderCapabilities");
    }
    return const [];
  }

  Future<List<ToolCapability>> getToolCapabilities() async {
    try {
      final uri = Uri.parse("$_base/api/capabilities/tools");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        final tools = json["tools"] as List? ?? const [];
        return tools.map((e) => ToolCapability.fromJson(e)).toList();
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getToolCapabilities");
    }
    return const [];
  }

  Future<Map<String, dynamic>> getResourceCapabilities() async {
    try {
      final uri = Uri.parse("$_base/api/capabilities/resources");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        return Map<String, dynamic>.from(json["resources"] ?? const {});
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getResourceCapabilities");
    }
    return const {};
  }

  Future<List<InstalledPlugin>> listInstalledPlugins() async {
    try {
      final uri = Uri.parse("$_base/api/plugins/installed");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        final plugins = json["plugins"] as List? ?? const [];
        return plugins
            .map((e) => InstalledPlugin.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList();
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "listInstalledPlugins");
    }
    return const [];
  }

  Future<Map<String, dynamic>?> installPlugin({required String sourcePath}) async {
    try {
      final uri = Uri.parse("$_base/api/plugins/install");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"source_path": sourcePath}),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "installPlugin");
    }
    return null;
  }

  Future<Map<String, dynamic>?> upgradePlugin({
    required String pluginId,
    required String sourcePath,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/plugins/upgrade");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "plugin_id": pluginId,
          "source_path": sourcePath,
        }),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "upgradePlugin");
    }
    return null;
  }

  Future<Map<String, dynamic>?> rollbackPlugin({required String pluginId}) async {
    try {
      final uri = Uri.parse("$_base/api/plugins/rollback");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"plugin_id": pluginId}),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "rollbackPlugin");
    }
    return null;
  }

  Future<Map<String, dynamic>?> togglePlugin({
    required String pluginId,
    required bool enabled,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/plugins/toggle");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "plugin_id": pluginId,
          "enabled": enabled,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "togglePlugin");
    }
    return null;
  }

  Future<Map<String, dynamic>?> executePlugin({
    required String pluginId,
    required String operation,
    Map<String, dynamic> args = const {},
    String? workspace,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/plugins/execute");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "plugin_id": pluginId,
          "operation": operation,
          "args": args,
          if (workspace != null && workspace.trim().isNotEmpty) "workspace": workspace.trim(),
        }),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "executePlugin");
    }
    return null;
  }

  Future<Map<String, dynamic>?> getPluginSdkTemplate() async {
    try {
      final uri = Uri.parse("$_base/api/plugins/sdk/template");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getPluginSdkTemplate");
    }
    return null;
  }

  Future<Map<String, dynamic>?> initPluginSdk({
    required String destination,
    required String pluginId,
    required String name,
    String version = "0.1.0",
    String description = "",
    List<String> permissions = const [],
  }) async {
    try {
      final uri = Uri.parse("$_base/api/plugins/sdk/init");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "destination": destination,
          "plugin_id": pluginId,
          "name": name,
          "version": version,
          "description": description,
          "permissions": permissions,
        }),
        timeout: const Duration(seconds: 120),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "initPluginSdk");
    }
    return null;
  }

  Future<Map<String, dynamic>?> importAutoGPTAgent({
    required String agentId,
    required String workspace,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/autogpt/import");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "agent_id": agentId,
          "workspace": workspace,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return jsonDecode(resp.body);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "importAutoGPTAgent");
    }
    return null;
  }

  Future<WorkflowAnalysis?> analyzeAutoGPTWorkflow(String agentId) async {
    try {
      final uri = Uri.parse("$_base/api/autogpt/workflow/analyze");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"agent_id": agentId}),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return WorkflowAnalysis.fromJson(jsonDecode(resp.body));
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "analyzeAutoGPTWorkflow");
    }
    return null;
  }

  Future<String?> executeWorkflow({
    required WorkflowSpec workflow,
    required String workspace,
    required String apiKey,
    String provider = "openai",
    String model = "gpt-4o-mini",
    String baseUrl = "https://api.openai.com/v1",
    Map<String, dynamic> inputs = const {},
    bool enableFileTools = true,
    bool enableCommandTools = false,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/workflow/execute");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workflow": workflow.toJson(),
          "workspace": workspace,
          "api_key": apiKey,
          "provider": provider,
          "model": model,
          "base_url": baseUrl,
          "inputs": inputs,
          "enable_file_tools": enableFileTools,
          "enable_command_tools": enableCommandTools,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        return json["run_id"];
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "executeWorkflow");
    }
    return null;
  }

  Future<GenerateResult?> generate({
    required String requirement,
    required String language,
    required List<String> platforms,
    required String workspace,
    required String apiKey,
    String provider = "openai",
    String model = "gpt-4o-mini",
    String baseUrl = "https://api.openai.com/v1",
    bool includeCi = true,
    bool includeSecurity = true,
    bool executeWorkflow = false,
    bool aiCodegen = true,
    bool metagptChain = false,
    bool metagptNative = false,
    bool perspective = true,
    List<String> validateCommands = const [],
    List<String> domainTargets = const [],
  }) async {
    try {
      final uri = Uri.parse("$_base/api/generate");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "requirement": requirement,
          "language": language,
          "platforms": platforms,
          "workspace": workspace,
          "api_key": apiKey,
          "provider": provider,
          "model": model,
          "base_url": baseUrl,
          "include_ci": includeCi,
          "include_security": includeSecurity,
          "execute_workflow": executeWorkflow,
          "ai_codegen": aiCodegen,
          "metagpt_chain": metagptChain,
          "metagpt_native": metagptNative,
          "perspective": perspective,
          "validate_commands": validateCommands,
          "domain_targets": domainTargets,
        }),
        timeout: const Duration(seconds: 120),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return GenerateResult.fromJson(jsonDecode(resp.body));
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "generate");
    }
    return null;
  }

  Future<List<Map<String, dynamic>>> listFiles({
    required String workspace,
    int maxDepth = 3,
    bool tree = false,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/files/list");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "max_depth": maxDepth,
          "tree": tree,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        return List<Map<String, dynamic>>.from(json["files"] ?? json["tree"] ?? []);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "listFiles");
    }
    return [];
  }

  Future<String?> readFile({
    required String workspace,
    required String path,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/files/read");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "path": path,
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = jsonDecode(resp.body);
        return json["content"];
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "readFile");
    }
    return null;
  }

  Future<bool> writeFile({
    required String workspace,
    required String path,
    required String content,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/files/write");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "path": path,
          "content": content,
        }),
        timeout: timeout,
      );
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "writeFile");
    }
    return false;
  }

  Future<bool> deleteFile({
    required String workspace,
    required String path,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/files/delete");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "path": path,
        }),
        timeout: timeout,
      );
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "deleteFile");
    }
    return false;
  }

  Future<bool> repairFiles({
    required String workspace,
    int maxDepth = 8,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/files/repair");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "max_depth": maxDepth,
        }),
        timeout: timeout,
      );
      return resp.statusCode >= 200 && resp.statusCode < 300;
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "repairFiles");
    }
    return false;
  }

  Future<Map<String, dynamic>?> cloneProject({
    required String repoUrl,
    String? destination,
    String? branch,
    int depth = 1,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/projects/clone");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "repo_url": repoUrl,
          if (destination != null) "destination": destination,
          if (branch != null) "branch": branch,
          "depth": depth,
        }),
        timeout: const Duration(seconds: 600),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return jsonDecode(resp.body);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "cloneProject");
    }
    return null;
  }

  Future<List<TemplateMarketItem>> listTemplateMarket({
    String query = "",
    int limit = 200,
  }) async {
    try {
      final uri = Uri.parse(
        "$_base/api/templates/market?q=${Uri.encodeQueryComponent(query)}&limit=$limit",
      );
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        final items = json["items"] as List? ?? const [];
        return items
            .map((e) => TemplateMarketItem.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList();
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "listTemplateMarket");
    }
    return const [];
  }

  Future<Map<String, dynamic>?> saveTemplateMarket({
    required String workspace,
    required String name,
    String description = "",
    List<String> tags = const [],
    String? framework,
    String? projectType,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/templates/market/save");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "name": name,
          "description": description,
          "tags": tags,
          if (framework != null && framework.trim().isNotEmpty) "framework": framework.trim(),
          if (projectType != null && projectType.trim().isNotEmpty) "project_type": projectType.trim(),
        }),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "saveTemplateMarket");
    }
    return null;
  }

  Future<Map<String, dynamic>?> importTemplateMarket({
    required String sourcePath,
    String? name,
    String description = "",
    List<String> tags = const [],
    String? framework,
    String? projectType,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/templates/market/import");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "source_path": sourcePath,
          if (name != null && name.trim().isNotEmpty) "name": name.trim(),
          "description": description,
          "tags": tags,
          if (framework != null && framework.trim().isNotEmpty) "framework": framework.trim(),
          if (projectType != null && projectType.trim().isNotEmpty) "project_type": projectType.trim(),
        }),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "importTemplateMarket");
    }
    return null;
  }

  Future<Map<String, dynamic>?> openTemplateMarket({
    required String templateId,
    String? destination,
    String? name,
    String? framework,
    String? projectType,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/templates/market/open");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "template_id": templateId,
          if (destination != null && destination.trim().isNotEmpty) "destination": destination.trim(),
          if (name != null && name.trim().isNotEmpty) "name": name.trim(),
          if (framework != null && framework.trim().isNotEmpty) "framework": framework.trim(),
          if (projectType != null && projectType.trim().isNotEmpty) "project_type": projectType.trim(),
        }),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "openTemplateMarket");
    }
    return null;
  }

  Future<GitStatusSnapshot?> getGitStatus({required String workspace}) async {
    try {
      final uri = Uri.parse("$_base/api/git/status?workspace=${Uri.encodeQueryComponent(workspace)}");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        if (json["ok"] == true) {
          return GitStatusSnapshot.fromJson(json);
        }
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getGitStatus");
    }
    return null;
  }

  Future<List<GitBranch>> getGitBranches({required String workspace}) async {
    try {
      final uri = Uri.parse("$_base/api/git/branches?workspace=${Uri.encodeQueryComponent(workspace)}");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        if (json["ok"] == true) {
          final branches = json["branches"] as List? ?? const [];
          return branches.map((e) => GitBranch.fromJson(Map<String, dynamic>.from(e as Map))).toList();
        }
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getGitBranches");
    }
    return const [];
  }

  Future<List<GitCommit>> getGitLog({
    required String workspace,
    int limit = 30,
  }) async {
    try {
      final uri = Uri.parse(
        "$_base/api/git/log?workspace=${Uri.encodeQueryComponent(workspace)}&limit=$limit",
      );
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        if (json["ok"] == true) {
          final commits = json["commits"] as List? ?? const [];
          return commits.map((e) => GitCommit.fromJson(Map<String, dynamic>.from(e as Map))).toList();
        }
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getGitLog");
    }
    return const [];
  }

  Future<String> getGitDiff({
    required String workspace,
    String? path,
    bool staged = false,
    String? ref,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/git/diff");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          if (path != null && path.trim().isNotEmpty) "path": path.trim(),
          "staged": staged,
          if (ref != null && ref.trim().isNotEmpty) "ref": ref.trim(),
        }),
        timeout: const Duration(seconds: 60),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        if (json["ok"] == true) {
          return (json["diff"] ?? "").toString();
        }
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getGitDiff");
    }
    return "";
  }

  Future<bool> stageGit({
    required String workspace,
    List<String> paths = const [],
  }) async {
    try {
      final uri = Uri.parse("$_base/api/git/stage");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"workspace": workspace, "paths": paths}),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        return json["ok"] == true;
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "stageGit");
    }
    return false;
  }

  Future<bool> unstageGit({
    required String workspace,
    List<String> paths = const [],
  }) async {
    try {
      final uri = Uri.parse("$_base/api/git/unstage");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"workspace": workspace, "paths": paths}),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        return json["ok"] == true;
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "unstageGit");
    }
    return false;
  }

  Future<bool> commitGit({
    required String workspace,
    required String message,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/git/commit");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"workspace": workspace, "message": message}),
        timeout: const Duration(seconds: 90),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        return json["ok"] == true;
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "commitGit");
    }
    return false;
  }

  Future<bool> checkoutGit({
    required String workspace,
    required String branch,
    bool create = false,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/git/checkout");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"workspace": workspace, "branch": branch, "create": create}),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        return json["ok"] == true;
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "checkoutGit");
    }
    return false;
  }

  Future<bool> pullGit({
    required String workspace,
    bool rebase = false,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/git/pull");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({"workspace": workspace, "rebase": rebase}),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        return json["ok"] == true;
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "pullGit");
    }
    return false;
  }

  Future<bool> pushGit({
    required String workspace,
    bool setUpstream = false,
    String? branch,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/git/push");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "workspace": workspace,
          "set_upstream": setUpstream,
          if (branch != null && branch.trim().isNotEmpty) "branch": branch.trim(),
        }),
        timeout: const Duration(seconds: 180),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        return json["ok"] == true;
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "pushGit");
    }
    return false;
  }

  Future<Map<String, dynamic>?> probeLlm({
    required String apiKey,
    required String provider,
    required String model,
    required String baseUrl,
    String prompt = "Reply with OK",
    double timeoutSeconds = 30,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/llm/probe");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          "api_key": apiKey,
          "provider": provider,
          "model": model,
          "base_url": baseUrl,
          "prompt": prompt,
          "timeout_s": timeoutSeconds,
        }),
        timeout: const Duration(seconds: 45),
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "probeLlm");
    }
    return null;
  }

  Future<Map<String, dynamic>?> getExecutionCheckpoint(String runId) async {
    try {
      final uri = Uri.parse("$_base/api/executions/$runId/checkpoint");
      final resp = await _http.get(uri, headers: _authHeaders, timeout: timeout);
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        return Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "getExecutionCheckpoint");
    }
    return null;
  }

  Future<String?> resumeExecution({
    required String runId,
    String? apiKey,
    String? provider,
    String? model,
    String? baseUrl,
    String? workspace,
    String? task,
    int? priority,
    int? maxTokenBudget,
    double? maxCostBudget,
    bool? checkpointEnabled,
    bool? smokeCheckEnabled,
    int? smokeReworkBudget,
    Map<String, dynamic>? roleModelOverrides,
    String? resumeStage,
  }) async {
    try {
      final uri = Uri.parse("$_base/api/executions/$runId/resume");
      final resp = await _http.post(
        uri,
        headers: _jsonHeaders,
        body: jsonEncode({
          if (apiKey != null && apiKey.trim().isNotEmpty) "api_key": apiKey.trim(),
          if (provider != null && provider.trim().isNotEmpty) "provider": provider.trim(),
          if (model != null && model.trim().isNotEmpty) "model": model.trim(),
          if (baseUrl != null && baseUrl.trim().isNotEmpty) "base_url": baseUrl.trim(),
          if (workspace != null && workspace.trim().isNotEmpty) "workspace": workspace.trim(),
          if (task != null && task.trim().isNotEmpty) "task": task.trim(),
          if (priority != null) "priority": priority,
          if (maxTokenBudget != null) "max_token_budget": maxTokenBudget,
          if (maxCostBudget != null) "max_cost_budget": maxCostBudget,
          if (checkpointEnabled != null) "checkpoint_enabled": checkpointEnabled,
          if (smokeCheckEnabled != null) "smoke_check_enabled": smokeCheckEnabled,
          if (smokeReworkBudget != null) "smoke_rework_budget": smokeReworkBudget,
          if (roleModelOverrides != null && roleModelOverrides.isNotEmpty) "role_model_overrides": roleModelOverrides,
          if (resumeStage != null && resumeStage.trim().isNotEmpty) "resume_stage": resumeStage.trim(),
        }),
        timeout: timeout,
      );
      if (resp.statusCode >= 200 && resp.statusCode < 300) {
        final json = Map<String, dynamic>.from(jsonDecode(resp.body) as Map);
        if (json["ok"] == true) {
          return json["run_id"]?.toString();
        }
      }
    } catch (e) {
      PerformanceMonitor.instance.recordError(e, StackTrace.current, context: "resumeExecution");
    }
    return null;
  }
}

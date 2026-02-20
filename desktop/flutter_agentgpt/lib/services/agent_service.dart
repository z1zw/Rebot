import "dart:async";
import "dart:convert";

import "package:http/http.dart" as http;

import "sse_service.dart";

class AgentRunStream {
  AgentRunStream({
    required this.runId,
    required this.stream,
    required this.cancel,
  });

  final String runId;
  final Stream<SSEEvent> stream;
  final Future<void> Function() cancel;
}

class AgentService {
  AgentService({SSEService? sseService}) : _sseService = sseService ?? SSEService();

  final SSEService _sseService;

  Future<http.Response> _postWithRetry(
    Uri uri, {
    required Map<String, String> headers,
    required String body,
    int maxAttempts = 3,
  }) async {
    Object? lastError;
    for (int attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await http
            .post(uri, headers: headers, body: body)
            .timeout(const Duration(seconds: 60));
      } on TimeoutException catch (e) {
        lastError = e;
      } on http.ClientException catch (e) {
        lastError = e;
      }
      if (attempt < maxAttempts) {
        await Future.delayed(Duration(milliseconds: 400 * attempt));
      }
    }
    throw Exception("Run create request failed after $maxAttempts attempts: $lastError");
  }

  Future<AgentRunStream> streamRun(
    String task, {
    required String baseUrl,
    required String workspace,
    String? projectId,
    String? projectType,
    String? framework,
    required String apiKey,
    required String provider,
    required String model,
    required String llmBaseUrl,
    int? modelMaxConcurrency,
    String? autogptAgentId,
    bool autogptWorkflowEnabled = false,
    String? serverApiKey,
    int? priority,
    int? maxTokenBudget,
    double? maxCostBudget,
    Map<String, dynamic>? roleModelOverrides,
    bool checkpointEnabled = true,
    bool smokeCheckEnabled = true,
    int smokeReworkBudget = 1,
  }) async {
    final base = baseUrl.replaceAll(RegExp(r"/+$"), "");
    final runUri = (projectId != null && projectId.trim().isNotEmpty)
        ? Uri.parse("$base/api/projects/${projectId.trim()}/run")
        : Uri.parse("$base/api/run");
    final authHeaders = <String, String>{
      "Content-Type": "application/json",
      if ((serverApiKey ?? "").trim().isNotEmpty) "X-API-Key": serverApiKey!.trim(),
    };
    final runResp = await _postWithRetry(
      runUri,
      headers: authHeaders,
      body: jsonEncode({
        "task": task,
        if (projectId != null && projectId.trim().isNotEmpty) "project_id": projectId.trim(),
        if (projectType != null && projectType.trim().isNotEmpty) "project_type": projectType.trim(),
        if (framework != null && framework.trim().isNotEmpty) "framework": framework.trim(),
        "workspace": workspace,
        "provider": provider,
        "model": model,
        "base_url": llmBaseUrl,
        "api_key": apiKey,
        if (autogptAgentId != null && autogptAgentId.trim().isNotEmpty) "autogpt_agent_id": autogptAgentId.trim(),
        if (autogptWorkflowEnabled) "autogpt_workflow_enabled": true,
        if (modelMaxConcurrency != null) "model_max_concurrency": modelMaxConcurrency,
        if (priority != null) "priority": priority,
        if (maxTokenBudget != null) "max_token_budget": maxTokenBudget,
        if (maxCostBudget != null) "max_cost_budget": maxCostBudget,
        if (roleModelOverrides != null && roleModelOverrides.isNotEmpty) "role_model_overrides": roleModelOverrides,
        "checkpoint_enabled": checkpointEnabled,
        "smoke_check_enabled": smokeCheckEnabled,
        "smoke_rework_budget": smokeReworkBudget,
      }),
    );

    if (runResp.statusCode < 200 || runResp.statusCode >= 300) {
      throw Exception("Run create failed (${runResp.statusCode}): ${runResp.body}");
    }

    final decoded = jsonDecode(runResp.body);
    if (decoded is! Map<String, dynamic>) {
      throw Exception("Invalid run response payload");
    }
    final runId = (decoded["run_id"] ?? "").toString();
    if (runId.isEmpty) {
      throw Exception("Missing run_id in run response");
    }

    final sse = _sseService.connect(
      "$base/api/run/$runId/stream",
      headers: {
        if ((serverApiKey ?? "").trim().isNotEmpty) "X-API-Key": serverApiKey!.trim(),
      },
    );
    return AgentRunStream(
      runId: runId,
      stream: sse.stream,
      cancel: sse.cancel,
    );
  }
}

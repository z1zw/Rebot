import "package:flutter_test/flutter_test.dart";
import "package:rebot_agentgpt/services/api_service.dart";

void main() {
  group("ExecutionRecord", () {
    test("fromJson parses correctly", () {
      final json = {
        "run_id": "abc123",
        "status": "running",
        "stage": "coding",
        "progress": "50%",
        "metrics": {"tokens": 100},
        "created_at": "2026-01-01T00:00:00Z",
      };
      final record = ExecutionRecord.fromJson(json);
      expect(record.runId, "abc123");
      expect(record.status, "running");
      expect(record.stage, "coding");
      expect(record.progress, "50%");
      expect(record.metrics["tokens"], 100);
      expect(record.createdAt, isNotNull);
    });

    test("fromJson handles missing fields", () {
      final record = ExecutionRecord.fromJson({});
      expect(record.runId, "");
      expect(record.status, "unknown");
      expect(record.stage, "");
    });
  });

  group("DevServerInfo", () {
    test("fromJson parses correctly", () {
      final info = DevServerInfo.fromJson({
        "url": "http://localhost:3000",
        "command": "npm start",
        "port": 3000,
        "pid": 1234,
      });
      expect(info.url, "http://localhost:3000");
      expect(info.port, 3000);
      expect(info.pid, 1234);
    });
  });

  group("AutoGPTAgent", () {
    test("fromJson parses correctly", () {
      final agent = AutoGPTAgent.fromJson({
        "agent_id": "a1",
        "name": "Coder",
        "description": "Writes code",
        "source_path": "/agents/coder",
      });
      expect(agent.agentId, "a1");
      expect(agent.name, "Coder");
    });
  });

  group("WorkflowAnalysis", () {
    test("fromJson parses correctly", () {
      final analysis = WorkflowAnalysis.fromJson({
        "agent_id": "a1",
        "name": "Test",
        "node_count": 5,
        "edge_count": 4,
        "levels": 3,
        "inferred_files": ["main.dart", "app.dart"],
        "summary": "test summary",
      });
      expect(analysis.nodeCount, 5);
      expect(analysis.edgeCount, 4);
      expect(analysis.inferredFiles.length, 2);
    });
  });

  group("WorkflowSpec", () {
    test("toJson serializes correctly", () {
      final spec = WorkflowSpec(
        nodes: [
          WorkflowNode(id: "n1", type: "code", data: {"lang": "dart"}),
        ],
        edges: [
          WorkflowEdge(source: "n1", target: "n2"),
        ],
      );
      final json = spec.toJson();
      expect(json["nodes"], isA<List>());
      expect(json["edges"], isA<List>());
      expect((json["nodes"] as List).first["id"], "n1");
    });
  });

  group("SecurityTestResult", () {
    test("fromJson with run_id sets started true", () {
      final result = SecurityTestResult.fromJson({"run_id": "r1"});
      expect(result.started, true);
      expect(result.runId, "r1");
    });

    test("fromJson without run_id sets started false", () {
      final result = SecurityTestResult.fromJson({});
      expect(result.started, false);
    });
  });

  group("EmulatorStatus", () {
    test("fromJson parses correctly", () {
      final status = EmulatorStatus.fromJson({
        "running": true,
        "device": "Pixel 7",
        "mirror_active": true,
      });
      expect(status.running, true);
      expect(status.device, "Pixel 7");
      expect(status.mirrorActive, true);
    });
  });
}

import "dart:async";
import "dart:convert";

import "package:http/http.dart" as http;

class SSEEvent {
  const SSEEvent({
    required this.event,
    required this.rawData,
    required this.data,
  });

  final String event;
  final String rawData;
  final Map<String, dynamic> data;
}

class SSESubscription {
  SSESubscription({
    required this.stream,
    required Future<void> Function() onCancel,
  }) : _onCancel = onCancel;

  final Stream<SSEEvent> stream;
  final Future<void> Function() _onCancel;

  Future<void> cancel() => _onCancel();
}

class SSEService {
  SSESubscription connect(
    String url, {
    Map<String, String>? queryParams,
    Map<String, String>? headers,
  }) {
    final controller = StreamController<SSEEvent>();
    final client = http.Client();
    var closed = false;

    Future<void> closeAll() async {
      if (closed) return;
      closed = true;
      client.close();
      await controller.close();
    }

    () async {
      try {
        final uri = Uri.parse(url).replace(
          queryParameters: {
            ...Uri.parse(url).queryParameters,
            ...?queryParams,
          },
        );
        final req = http.Request("GET", uri);
        req.headers.addAll({
          "Accept": "text/event-stream",
          "Cache-Control": "no-cache",
          "Connection": "keep-alive",
          ...?headers,
        });

        final resp = await client.send(req);
        if (resp.statusCode < 200 || resp.statusCode >= 300) {
          controller.addError(
            Exception("SSE connect failed (${resp.statusCode})"),
          );
          await closeAll();
          return;
        }

        var buffer = "";
        await for (final chunk in resp.stream.transform(utf8.decoder)) {
          if (closed) break;
          buffer += chunk.replaceAll("\r\n", "\n");
          while (buffer.contains("\n\n")) {
            final idx = buffer.indexOf("\n\n");
            final raw = buffer.substring(0, idx).trim();
            buffer = buffer.substring(idx + 2);
            if (raw.isEmpty) continue;
            final event = _parseSSE(raw);
            if (event != null) controller.add(event);
          }
        }
      } catch (e, st) {
        if (!closed) {
          controller.addError(e, st);
        }
      } finally {
        await closeAll();
      }
    }();

    return SSESubscription(stream: controller.stream, onCancel: closeAll);
  }

  SSEEvent? _parseSSE(String raw) {
    String eventName = "message";
    final dataLines = <String>[];
    final lines = raw.split("\n");
    for (final line in lines) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("event:")) {
        eventName = line.substring(6).trim();
        continue;
      }
      if (line.startsWith("data:")) {
        dataLines.add(line.substring(5).trim());
      }
    }
    final rawData = dataLines.join("\n");
    Map<String, dynamic> data = <String, dynamic>{};
    if (rawData.isNotEmpty) {
      try {
        final decoded = jsonDecode(rawData);
        if (decoded is Map<String, dynamic>) {
          data = decoded;
        } else {
          data = {"value": decoded};
        }
      } catch (_) {
        data = {"text": rawData};
      }
    }
    return SSEEvent(event: eventName, rawData: rawData, data: data);
  }
}


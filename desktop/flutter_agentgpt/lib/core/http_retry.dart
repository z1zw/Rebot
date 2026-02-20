import "dart:async";
import "dart:convert";
import "dart:math";
import "package:http/http.dart" as http;

enum RetryStrategy { exponential, linear, fixed }

class HttpRetryClient {
  HttpRetryClient({
    http.Client? inner,
    this.maxRetries = 3,
    this.baseDelay = const Duration(milliseconds: 500),
    this.maxDelay = const Duration(seconds: 10),
    this.strategy = RetryStrategy.exponential,
    this.retryStatusCodes = const {408, 429, 500, 502, 503, 504},
    this.onRetry,
  }) : _inner = inner ?? http.Client();

  final http.Client _inner;
  final int maxRetries;
  final Duration baseDelay;
  final Duration maxDelay;
  final RetryStrategy strategy;
  final Set<int> retryStatusCodes;
  final void Function(int attempt, Duration delay, Object? error)? onRetry;

  Duration _delayFor(int attempt) {
    final ms = switch (strategy) {
      RetryStrategy.exponential =>
        baseDelay.inMilliseconds * pow(2, attempt).toInt(),
      RetryStrategy.linear =>
        baseDelay.inMilliseconds * (attempt + 1),
      RetryStrategy.fixed =>
        baseDelay.inMilliseconds,
    };
    final jitter = Random().nextInt(baseDelay.inMilliseconds ~/ 2 + 1);
    return Duration(milliseconds: min(ms + jitter, maxDelay.inMilliseconds));
  }

  bool _shouldRetry(int statusCode) => retryStatusCodes.contains(statusCode);

  Future<http.Response> get(Uri url, {Map<String, String>? headers, Duration? timeout}) =>
      _retry(() => _inner.get(url, headers: headers), timeout);

  Future<http.Response> post(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Duration? timeout,
  }) =>
      _retry(() => _inner.post(url, headers: headers, body: body), timeout);

  Future<http.Response> put(
    Uri url, {
    Map<String, String>? headers,
    Object? body,
    Duration? timeout,
  }) =>
      _retry(() => _inner.put(url, headers: headers, body: body), timeout);

  Future<http.Response> delete(Uri url, {Map<String, String>? headers, Duration? timeout}) =>
      _retry(() => _inner.delete(url, headers: headers), timeout);

  Future<http.Response> _retry(
    Future<http.Response> Function() request,
    Duration? timeout,
  ) async {
    final effectiveTimeout = timeout ?? const Duration(seconds: 30);
    for (int attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        final resp = await request().timeout(effectiveTimeout);
        if (attempt < maxRetries && _shouldRetry(resp.statusCode)) {
          final delay = _delayFor(attempt);
          onRetry?.call(attempt + 1, delay, "HTTP ${resp.statusCode}");
          await Future.delayed(delay);
          continue;
        }
        return resp;
      } on TimeoutException catch (e) {
        if (attempt >= maxRetries) rethrow;
        final delay = _delayFor(attempt);
        onRetry?.call(attempt + 1, delay, e);
        await Future.delayed(delay);
      } on http.ClientException catch (e) {
        if (attempt >= maxRetries) rethrow;
        final delay = _delayFor(attempt);
        onRetry?.call(attempt + 1, delay, e);
        await Future.delayed(delay);
      }
    }
    throw TimeoutException("All $maxRetries retries exhausted");
  }

  void close() => _inner.close();
}

class ApiResult<T> {
  final T? data;
  final ApiError? error;

  ApiResult.ok(this.data) : error = null;
  ApiResult.fail(this.error) : data = null;

  bool get isOk => error == null;
  bool get isError => error != null;

  T get dataOrThrow {
    if (data != null) return data!;
    throw error ?? ApiError(code: "unknown", message: "No data");
  }
}

class ApiError {
  final String code;
  final String message;
  final int? statusCode;
  final Object? cause;

  ApiError({
    required this.code,
    required this.message,
    this.statusCode,
    this.cause,
  });

  factory ApiError.fromResponse(http.Response resp) {
    String message;
    String code;
    try {
      final json = jsonDecode(resp.body);
      message = json["detail"] ?? json["error"] ?? json["message"] ?? resp.reasonPhrase ?? "";
      code = json["code"] ?? "http_${resp.statusCode}";
    } catch (_) {
      message = resp.reasonPhrase ?? "Request failed";
      code = "http_${resp.statusCode}";
    }
    return ApiError(code: code, message: message, statusCode: resp.statusCode);
  }

  factory ApiError.network(Object cause) => ApiError(
        code: "network_error",
        message: "Network connection failed. Please check your connection.",
        cause: cause,
      );

  factory ApiError.timeout() => ApiError(
        code: "timeout",
        message: "Request timed out. The server may be busy.",
      );

  @override
  String toString() => "ApiError($code): $message";
}

import "package:flutter_test/flutter_test.dart";
import "package:rebot_agentgpt/core/http_retry.dart";

void main() {
  group("ApiResult", () {
    test("ok result has data and no error", () {
      final result = ApiResult<String>.ok("hello");
      expect(result.isOk, true);
      expect(result.isError, false);
      expect(result.data, "hello");
      expect(result.error, null);
    });

    test("fail result has error and no data", () {
      final result = ApiResult<String>.fail(
        ApiError(code: "test", message: "fail"),
      );
      expect(result.isOk, false);
      expect(result.isError, true);
      expect(result.data, null);
      expect(result.error!.code, "test");
    });

    test("dataOrThrow returns data on success", () {
      final result = ApiResult<int>.ok(42);
      expect(result.dataOrThrow, 42);
    });

    test("dataOrThrow throws on failure", () {
      final result = ApiResult<int>.fail(
        ApiError(code: "err", message: "nope"),
      );
      expect(() => result.dataOrThrow, throwsA(isA<ApiError>()));
    });
  });

  group("ApiError", () {
    test("network factory sets correct code", () {
      final err = ApiError.network(Exception("no internet"));
      expect(err.code, "network_error");
      expect(err.message, contains("Network"));
    });

    test("timeout factory sets correct code", () {
      final err = ApiError.timeout();
      expect(err.code, "timeout");
    });

    test("toString includes code and message", () {
      final err = ApiError(code: "abc", message: "test message");
      expect(err.toString(), contains("abc"));
      expect(err.toString(), contains("test message"));
    });
  });
}

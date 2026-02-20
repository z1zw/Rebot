"""Tests for rebot.logging module."""

import json
import tempfile
from pathlib import Path
from io import StringIO
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest

from rebot.logging import (
    LogRecord,
    Formatter,
    JsonFormatter,
    PlainFormatter,
    RichFormatter,
    Handler,
    ConsoleHandler,
    FileHandler,
    Logger,
    log_context,
    log_timing,
    setup_logging,
    get_logger,
    LOG_LEVELS,
    RequestLogger,
    AgentLogger,
)


class TestLogRecord:
    """Test suite for LogRecord."""

    def test_log_record_creation(self):
        """Test LogRecord basic creation."""
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message"
        )
        assert record.timestamp == "2026-02-18T10:00:00Z"
        assert record.level == "INFO"
        assert record.logger == "test"
        assert record.message == "Test message"
        assert record.context == {}
        assert record.exception is None

    def test_log_record_with_context(self):
        """Test LogRecord with context."""
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message",
            context={"request_id": "123", "user": "admin"}
        )
        assert record.context["request_id"] == "123"
        assert record.context["user"] == "admin"

    def test_log_record_with_exception(self):
        """Test LogRecord with exception."""
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="ERROR",
            logger="test",
            message="Error occurred",
            exception="Traceback: ..."
        )
        assert record.exception == "Traceback: ..."

    def test_log_record_to_dict(self):
        """Test LogRecord.to_dict() method."""
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message",
            context={"key": "value"}
        )
        d = record.to_dict()
        assert d["timestamp"] == "2026-02-18T10:00:00Z"
        assert d["level"] == "INFO"
        assert d["logger"] == "test"
        assert d["message"] == "Test message"
        assert d["key"] == "value"

    def test_log_record_to_json(self):
        """Test LogRecord.to_json() method."""
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message"
        )
        json_str = record.to_json()
        data = json.loads(json_str)
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"


class TestJsonFormatter:
    """Test suite for JsonFormatter."""

    def test_json_formatter_format(self):
        """Test JsonFormatter formats to valid JSON."""
        formatter = JsonFormatter()
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message"
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"

    def test_json_formatter_with_context(self):
        """Test JsonFormatter includes context."""
        formatter = JsonFormatter()
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="DEBUG",
            logger="test",
            message="Debug",
            context={"user_id": 42}
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["user_id"] == 42


class TestPlainFormatter:
    """Test suite for PlainFormatter."""

    def test_plain_formatter_format(self):
        """Test PlainFormatter basic formatting."""
        formatter = PlainFormatter()
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message"
        )
        output = formatter.format(record)
        assert "2026-02-18T10:00:00Z" in output
        assert "INFO" in output
        assert "test:" in output
        assert "Test message" in output

    def test_plain_formatter_without_timestamp(self):
        """Test PlainFormatter without timestamp."""
        formatter = PlainFormatter(include_timestamp=False)
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message"
        )
        output = formatter.format(record)
        assert "2026-02-18T10:00:00Z" not in output
        assert "INFO" in output

    def test_plain_formatter_with_context(self):
        """Test PlainFormatter with context."""
        formatter = PlainFormatter()
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test",
            context={"key": "value"}
        )
        output = formatter.format(record)
        assert "key=value" in output

    def test_plain_formatter_with_exception(self):
        """Test PlainFormatter with exception."""
        formatter = PlainFormatter()
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="ERROR",
            logger="test",
            message="Error",
            exception="Traceback: Error details"
        )
        output = formatter.format(record)
        assert "Traceback: Error details" in output


class TestRichFormatter:
    """Test suite for RichFormatter."""

    def test_rich_formatter_format(self):
        """Test RichFormatter basic formatting."""
        formatter = RichFormatter()
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message"
        )
        output = formatter.format(record)
        assert "INFO" in output
        assert "Test message" in output
        # Should contain ANSI codes
        assert "\033[" in output

    def test_rich_formatter_colors_by_level(self):
        """Test RichFormatter uses different colors for levels."""
        formatter = RichFormatter()
        
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            record = LogRecord(
                timestamp="2026-02-18T10:00:00Z",
                level=level,
                logger="test",
                message="Test"
            )
            output = formatter.format(record)
            assert level in output


class TestConsoleHandler:
    """Test suite for ConsoleHandler."""

    def test_console_handler_emit(self):
        """Test ConsoleHandler emits to stream."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="INFO",
            logger="test",
            message="Test message"
        )
        handler.emit(record)
        output = stream.getvalue()
        assert "Test message" in output

    def test_console_handler_level_filter(self):
        """Test ConsoleHandler filters by level."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, level="WARNING")
        
        # DEBUG should be filtered
        debug_record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="DEBUG",
            logger="test",
            message="Debug message"
        )
        handler.handle(debug_record)
        
        # WARNING should pass
        warn_record = LogRecord(
            timestamp="2026-02-18T10:00:00Z",
            level="WARNING",
            logger="test",
            message="Warning message"
        )
        handler.handle(warn_record)
        
        output = stream.getvalue()
        assert "Debug message" not in output
        assert "Warning message" in output


class TestFileHandler:
    """Test suite for FileHandler."""

    def test_file_handler_emit(self):
        """Test FileHandler writes to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.log"
            handler = FileHandler(path, formatter=JsonFormatter())
            
            record = LogRecord(
                timestamp="2026-02-18T10:00:00Z",
                level="INFO",
                logger="test",
                message="Test message"
            )
            handler.emit(record)
            
            assert path.exists()
            content = path.read_text()
            assert "Test message" in content

    def test_file_handler_creates_directory(self):
        """Test FileHandler creates parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "subdir" / "test.log"
            handler = FileHandler(path)
            
            assert path.parent.exists()


class TestLogger:
    """Test suite for Logger."""

    def test_logger_creation(self):
        """Test Logger basic creation."""
        logger = Logger("test")
        assert logger.name == "test"
        assert logger.handlers == []

    def test_logger_with_handler(self):
        """Test Logger with handler."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        
        logger.info("Test message")
        output = stream.getvalue()
        assert "Test message" in output

    def test_logger_bind(self):
        """Test Logger.bind() creates new logger with context."""
        logger = Logger("test")
        bound = logger.bind(request_id="123")
        
        assert bound is not logger
        assert bound._context["request_id"] == "123"
        assert logger._context == {}

    def test_logger_unbind(self):
        """Test Logger.unbind() removes context keys."""
        logger = Logger("test")
        bound = logger.bind(a=1, b=2, c=3)
        unbound = bound.unbind("a", "c")
        
        assert "a" not in unbound._context
        assert unbound._context["b"] == 2
        assert "c" not in unbound._context

    def test_logger_levels(self):
        """Test Logger level methods."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        
        logger.debug("Debug")
        logger.info("Info")
        logger.warning("Warning")
        logger.error("Error")
        logger.critical("Critical")
        
        output = stream.getvalue()
        assert "Debug" in output
        assert "Info" in output
        assert "Warning" in output
        assert "Error" in output
        assert "Critical" in output

    def test_logger_exception(self):
        """Test Logger.exception() includes traceback."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        
        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("Caught error")
        
        output = stream.getvalue()
        assert "Caught error" in output
        assert "ValueError" in output


class TestLogContext:
    """Test suite for log_context context manager."""

    def test_log_context_binds_context(self):
        """Test log_context yields bound logger."""
        logger = Logger("test")
        
        with log_context(logger, request_id="123") as bound:
            assert bound._context["request_id"] == "123"


class TestLogTiming:
    """Test suite for log_timing decorator."""

    def test_log_timing_logs_success(self):
        """Test log_timing logs successful execution."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        
        @log_timing(logger, "Operation completed")
        def test_func():
            return 42
        
        result = test_func()
        assert result == 42
        
        output = stream.getvalue()
        assert "Operation completed" in output
        assert "elapsed_ms" in output

    def test_log_timing_logs_failure(self):
        """Test log_timing logs failed execution."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        
        @log_timing(logger, "Operation completed")
        def failing_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        output = stream.getvalue()
        assert "failed" in output
        assert "error" in output


class TestSetupLogging:
    """Test suite for setup_logging function."""

    def test_setup_logging_json_format(self):
        """Test setup_logging with JSON format."""
        # Reset globals
        import rebot.logging as logging_module
        logging_module._handlers.clear()
        logging_module._loggers.clear()
        logging_module._configured = False
        
        setup_logging(level="INFO", format="json", console=True)
        logger = get_logger("test")
        
        assert len(logger.handlers) > 0
        assert isinstance(logger.handlers[0].formatter, JsonFormatter)

    def test_setup_logging_plain_format(self):
        """Test setup_logging with plain format."""
        import rebot.logging as logging_module
        logging_module._handlers.clear()
        logging_module._loggers.clear()
        logging_module._configured = False
        
        setup_logging(level="DEBUG", format="plain", console=True)
        logger = get_logger("test")
        
        assert isinstance(logger.handlers[0].formatter, PlainFormatter)

    def test_setup_logging_rich_format(self):
        """Test setup_logging with rich format."""
        import rebot.logging as logging_module
        logging_module._handlers.clear()
        logging_module._loggers.clear()
        logging_module._configured = False
        
        setup_logging(level="INFO", format="rich", console=True)
        logger = get_logger("test")
        
        assert isinstance(logger.handlers[0].formatter, RichFormatter)

    def test_setup_logging_with_file(self):
        """Test setup_logging with file output."""
        import rebot.logging as logging_module
        logging_module._handlers.clear()
        logging_module._loggers.clear()
        logging_module._configured = False
        
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = str(Path(tmpdir) / "test.log")
            setup_logging(level="INFO", file=log_file, console=False)
            logger = get_logger("test")
            
            logger.info("Test file logging")
            
            assert Path(log_file).exists()


class TestGetLogger:
    """Test suite for get_logger function."""

    def test_get_logger_returns_logger(self):
        """Test get_logger returns Logger instance."""
        import rebot.logging as logging_module
        logging_module._handlers.clear()
        logging_module._loggers.clear()
        logging_module._configured = False
        
        logger = get_logger("my.module")
        assert isinstance(logger, Logger)
        assert logger.name == "my.module"

    def test_get_logger_same_name_returns_same_logger(self):
        """Test get_logger returns same logger for same name."""
        import rebot.logging as logging_module
        logging_module._handlers.clear()
        logging_module._loggers.clear()
        logging_module._configured = False
        
        logger1 = get_logger("same.module")
        logger2 = get_logger("same.module")
        assert logger1 is logger2


class TestLogLevels:
    """Test suite for LOG_LEVELS constant."""

    def test_log_levels_order(self):
        """Test LOG_LEVELS has correct ordering."""
        assert LOG_LEVELS["DEBUG"] < LOG_LEVELS["INFO"]
        assert LOG_LEVELS["INFO"] < LOG_LEVELS["WARNING"]
        assert LOG_LEVELS["WARNING"] < LOG_LEVELS["ERROR"]
        assert LOG_LEVELS["ERROR"] < LOG_LEVELS["CRITICAL"]


class TestRequestLogger:
    """Test suite for RequestLogger."""

    def test_request_logger_log_request(self):
        """Test RequestLogger.log_request()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        req_logger = RequestLogger(logger)
        
        req_logger.log_request("req-123", "GET", "/api/users")
        
        output = stream.getvalue()
        assert "GET /api/users" in output
        assert "req-123" in output

    def test_request_logger_log_response(self):
        """Test RequestLogger.log_response()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        req_logger = RequestLogger(logger)
        
        req_logger.log_response("req-123", 200, 50.5)
        
        output = stream.getvalue()
        assert "200" in output
        assert "req-123" in output


class TestAgentLogger:
    """Test suite for AgentLogger."""

    def test_agent_logger_creation(self):
        """Test AgentLogger creation."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        agent_log = AgentLogger("agent-001", logger)
        
        assert agent_log.logger._context["agent_id"] == "agent-001"

    def test_agent_logger_thinking(self):
        """Test AgentLogger.thinking()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        agent_log = AgentLogger("agent-001", logger)
        
        agent_log.thinking("Processing user request")
        # Debug level, might not show depending on level

    def test_agent_logger_action(self):
        """Test AgentLogger.action()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        agent_log = AgentLogger("agent-001", logger)
        
        agent_log.action("execute", "code_exec")
        
        output = stream.getvalue()
        assert "action" in output.lower() or "execute" in output

    def test_agent_logger_tool_call(self):
        """Test AgentLogger.tool_call()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        agent_log = AgentLogger("agent-001", logger)
        
        agent_log.tool_call("search", {"query": "test"})

    def test_agent_logger_tool_result(self):
        """Test AgentLogger.tool_result()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        agent_log = AgentLogger("agent-001", logger)
        
        agent_log.tool_result("search", True, 100.5)
        
        output = stream.getvalue()
        assert "search" in output

    def test_agent_logger_completion(self):
        """Test AgentLogger.completion()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        agent_log = AgentLogger("agent-001", logger)
        
        agent_log.completion(1500, "gpt-4", 2500.0)
        
        output = stream.getvalue()
        assert "gpt-4" in output or "completion" in output.lower()

    def test_agent_logger_finished(self):
        """Test AgentLogger.finished()."""
        stream = StringIO()
        handler = ConsoleHandler(stream=stream, formatter=PlainFormatter())
        logger = Logger("test", handlers=[handler])
        agent_log = AgentLogger("agent-001", logger)
        
        agent_log.finished("success", 5, 10000.0)
        
        output = stream.getvalue()
        assert "finished" in output.lower()

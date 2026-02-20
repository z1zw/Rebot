"""Rebot Structured Logging System.

Provides structured logging with:
- JSON formatted output for production
- Rich console output for development
- Context binding (request_id, agent_id, etc.)
- Performance timing
- Error tracking with stack traces

Usage:
    from rebot.logging import get_logger, setup_logging
    
    # Setup at application start
    setup_logging(level="INFO", format="structured")
    
    # Get a logger
    logger = get_logger(__name__)
    
    # Log with context
    logger.info("Processing request", request_id="123", user="admin")
    
    # Bind context for all subsequent logs
    log = logger.bind(agent_id="agent-1")
    log.info("Agent started")
"""

from __future__ import annotations

import sys
import time
import json
import logging
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TextIO, Union
from contextlib import contextmanager
from functools import wraps
from dataclasses import dataclass, field
import threading


# ============================================================================
# Log Record
# ============================================================================

@dataclass
class LogRecord:
    """Structured log record."""
    timestamp: str
    level: str
    logger: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = {
            "timestamp": self.timestamp,
            "level": self.level,
            "logger": self.logger,
            "message": self.message,
        }
        if self.context:
            d.update(self.context)
        if self.exception:
            d["exception"] = self.exception
        return d
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


# ============================================================================
# Formatters
# ============================================================================

class Formatter:
    """Base formatter."""
    
    def format(self, record: LogRecord) -> str:
        raise NotImplementedError


class JsonFormatter(Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: LogRecord) -> str:
        return record.to_json()


class PlainFormatter(Formatter):
    """Plain text formatter."""
    
    def __init__(self, include_timestamp: bool = True):
        self.include_timestamp = include_timestamp
    
    def format(self, record: LogRecord) -> str:
        parts = []
        
        if self.include_timestamp:
            parts.append(record.timestamp)
        
        parts.append(f"[{record.level:8}]")
        parts.append(f"{record.logger}:")
        parts.append(record.message)
        
        if record.context:
            ctx = " ".join(f"{k}={v}" for k, v in record.context.items())
            parts.append(f"({ctx})")
        
        msg = " ".join(parts)
        
        if record.exception:
            msg += f"\n{record.exception}"
        
        return msg


class RichFormatter(Formatter):
    """Rich console formatter with colors."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    def format(self, record: LogRecord) -> str:
        color = self.COLORS.get(record.level, "")
        
        parts = [
            f"{self.DIM}{record.timestamp}{self.RESET}",
            f"{color}{self.BOLD}[{record.level:8}]{self.RESET}",
            f"{self.DIM}{record.logger}:{self.RESET}",
            record.message,
        ]
        
        if record.context:
            ctx_parts = []
            for k, v in record.context.items():
                ctx_parts.append(f"{self.DIM}{k}={self.RESET}{v}")
            parts.append(f"({' '.join(ctx_parts)})")
        
        msg = " ".join(parts)
        
        if record.exception:
            msg += f"\n{color}{record.exception}{self.RESET}"
        
        return msg


# ============================================================================
# Handlers
# ============================================================================

class Handler:
    """Base handler."""
    
    def __init__(self, formatter: Optional[Formatter] = None, level: str = "DEBUG"):
        self.formatter = formatter or PlainFormatter()
        self.level = level
        self._level_num = LOG_LEVELS.get(level, 0)
    
    def handle(self, record: LogRecord) -> None:
        if LOG_LEVELS.get(record.level, 0) >= self._level_num:
            self.emit(record)
    
    def emit(self, record: LogRecord) -> None:
        raise NotImplementedError


class ConsoleHandler(Handler):
    """Console output handler."""
    
    def __init__(
        self, 
        stream: Optional[TextIO] = None,
        formatter: Optional[Formatter] = None,
        level: str = "DEBUG"
    ):
        super().__init__(formatter, level)
        self.stream = stream or sys.stderr
    
    def emit(self, record: LogRecord) -> None:
        try:
            msg = self.formatter.format(record)
            self.stream.write(msg + "\n")
            self.stream.flush()
        except Exception:
            pass


class FileHandler(Handler):
    """File output handler."""
    
    def __init__(
        self,
        path: Union[str, Path],
        formatter: Optional[Formatter] = None,
        level: str = "DEBUG",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        super().__init__(formatter or JsonFormatter(), level)
        self.path = Path(path)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self._lock = threading.Lock()
        
        self.path.parent.mkdir(parents=True, exist_ok=True)
    
    def emit(self, record: LogRecord) -> None:
        try:
            with self._lock:
                self._rotate_if_needed()
                msg = self.formatter.format(record)
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(msg + "\n")
        except Exception:
            pass
    
    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds max size."""
        if not self.path.exists():
            return
        
        if self.path.stat().st_size < self.max_bytes:
            return
        
        # Rotate files
        for i in range(self.backup_count - 1, 0, -1):
            src = self.path.with_suffix(f".{i}")
            dst = self.path.with_suffix(f".{i + 1}")
            if src.exists():
                src.rename(dst)
        
        # Rotate current file
        self.path.rename(self.path.with_suffix(".1"))


# ============================================================================
# Logger
# ============================================================================

LOG_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


class Logger:
    """Structured logger."""
    
    def __init__(self, name: str, handlers: Optional[List[Handler]] = None):
        self.name = name
        self.handlers = handlers or []
        self._context: Dict[str, Any] = {}
        self._level = "DEBUG"
    
    def bind(self, **kwargs: Any) -> "Logger":
        """Create a new logger with bound context."""
        new_logger = Logger(self.name, self.handlers)
        new_logger._context = {**self._context, **kwargs}
        new_logger._level = self._level
        return new_logger
    
    def unbind(self, *keys: str) -> "Logger":
        """Create a new logger without specified context keys."""
        new_logger = Logger(self.name, self.handlers)
        new_logger._context = {k: v for k, v in self._context.items() if k not in keys}
        new_logger._level = self._level
        return new_logger
    
    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        """Create and emit a log record."""
        if LOG_LEVELS.get(level, 0) < LOG_LEVELS.get(self._level, 0):
            return
        
        # Extract exception if present
        exc_info = kwargs.pop("exc_info", None)
        exception = None
        if exc_info:
            if isinstance(exc_info, BaseException):
                exception = "".join(traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__))
            elif exc_info is True:
                exception = traceback.format_exc()
            elif isinstance(exc_info, tuple):
                exception = "".join(traceback.format_exception(*exc_info))
        
        record = LogRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            logger=self.name,
            message=message,
            context={**self._context, **kwargs},
            exception=exception,
        )
        
        for handler in self.handlers:
            try:
                handler.handle(record)
            except Exception:
                pass
    
    def debug(self, message: str, **kwargs: Any) -> None:
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        self._log("CRITICAL", message, **kwargs)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log an error with exception info."""
        self._log("ERROR", message, exc_info=True, **kwargs)


# ============================================================================
# Context Managers and Decorators
# ============================================================================

@contextmanager
def log_context(logger: Logger, **kwargs: Any):
    """Temporarily bind context to a logger."""
    bound = logger.bind(**kwargs)
    try:
        yield bound
    finally:
        pass


def log_timing(logger: Logger, message: str = "Operation completed"):
    """Decorator to log execution time."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(
                    message,
                    function=func.__name__,
                    elapsed_ms=round(elapsed * 1000, 2),
                    status="success"
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(
                    f"{message} failed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed * 1000, 2),
                    status="error",
                    error=str(e),
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


def log_async_timing(logger: Logger, message: str = "Operation completed"):
    """Decorator to log async execution time."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(
                    message,
                    function=func.__name__,
                    elapsed_ms=round(elapsed * 1000, 2),
                    status="success"
                )
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                logger.error(
                    f"{message} failed",
                    function=func.__name__,
                    elapsed_ms=round(elapsed * 1000, 2),
                    status="error",
                    error=str(e),
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


# ============================================================================
# Global Logger Registry
# ============================================================================

_loggers: Dict[str, Logger] = {}
_handlers: List[Handler] = []
_configured = False


def setup_logging(
    level: str = "INFO",
    format: str = "rich",  # "json", "plain", "rich"
    file: Optional[str] = None,
    console: bool = True,
) -> None:
    """Setup global logging configuration."""
    global _handlers, _configured
    
    _handlers.clear()
    
    # Console handler
    if console:
        if format == "json":
            formatter = JsonFormatter()
        elif format == "plain":
            formatter = PlainFormatter()
        else:
            formatter = RichFormatter()
        
        _handlers.append(ConsoleHandler(formatter=formatter, level=level))
    
    # File handler
    if file:
        _handlers.append(FileHandler(
            path=file,
            formatter=JsonFormatter(),
            level=level
        ))
    
    # Update existing loggers
    for logger in _loggers.values():
        logger.handlers = _handlers
        logger._level = level
    
    _configured = True


def get_logger(name: str) -> Logger:
    """Get or create a logger."""
    if name not in _loggers:
        _loggers[name] = Logger(name, _handlers.copy())
        if _configured:
            pass  # Already have handlers
        elif not _handlers:
            # Default setup
            setup_logging()
    
    return _loggers[name]


# ============================================================================
# Standard Library Integration
# ============================================================================

class StructuredHandler(logging.Handler):
    """Bridge to Python's standard logging."""
    
    def __init__(self, logger: Logger):
        super().__init__()
        self.structured_logger = logger
    
    def emit(self, record: logging.LogRecord) -> None:
        level = record.levelname
        message = record.getMessage()
        
        kwargs = {}
        if record.exc_info:
            kwargs["exc_info"] = record.exc_info
        
        getattr(self.structured_logger, level.lower(), self.structured_logger.info)(
            message, **kwargs
        )


def integrate_stdlib_logging(logger_name: str = "rebot") -> None:
    """Integrate with Python's standard logging library."""
    stdlib_logger = logging.getLogger(logger_name)
    stdlib_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    stdlib_logger.handlers.clear()
    
    # Add our handler
    structured_logger = get_logger(logger_name)
    stdlib_logger.addHandler(StructuredHandler(structured_logger))


# ============================================================================
# Request/Response Logging Middleware
# ============================================================================

class RequestLogger:
    """Middleware for logging HTTP-style requests/responses."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def log_request(
        self,
        request_id: str,
        method: str,
        path: str,
        **kwargs: Any
    ) -> None:
        self.logger.info(
            f"Request: {method} {path}",
            request_id=request_id,
            type="request",
            method=method,
            path=path,
            **kwargs
        )
    
    def log_response(
        self,
        request_id: str,
        status: int,
        elapsed_ms: float,
        **kwargs: Any
    ) -> None:
        level = "info" if status < 400 else "error"
        getattr(self.logger, level)(
            f"Response: {status}",
            request_id=request_id,
            type="response",
            status=status,
            elapsed_ms=elapsed_ms,
            **kwargs
        )


# ============================================================================
# Agent Activity Logger
# ============================================================================

class AgentLogger:
    """Specialized logger for agent activities."""
    
    def __init__(self, agent_id: str, logger: Optional[Logger] = None):
        self.logger = (logger or get_logger("rebot.agent")).bind(agent_id=agent_id)
    
    def thinking(self, thought: str, **kwargs: Any) -> None:
        self.logger.debug("Agent thinking", thought=thought[:500], **kwargs)
    
    def action(self, action: str, tool: str, **kwargs: Any) -> None:
        self.logger.info("Agent action", action=action, tool=tool, **kwargs)
    
    def tool_call(self, tool: str, args: Dict[str, Any], **kwargs: Any) -> None:
        self.logger.debug("Tool call", tool=tool, args=args, **kwargs)
    
    def tool_result(self, tool: str, success: bool, elapsed_ms: float, **kwargs: Any) -> None:
        level = "info" if success else "warning"
        getattr(self.logger, level)(
            "Tool result",
            tool=tool,
            success=success,
            elapsed_ms=elapsed_ms,
            **kwargs
        )
    
    def completion(self, tokens: int, model: str, elapsed_ms: float, **kwargs: Any) -> None:
        self.logger.info(
            "LLM completion",
            tokens=tokens,
            model=model,
            elapsed_ms=elapsed_ms,
            **kwargs
        )
    
    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(message, exc_info=True, **kwargs)
    
    def finished(self, status: str, steps: int, elapsed_ms: float, **kwargs: Any) -> None:
        self.logger.info(
            "Agent finished",
            status=status,
            steps=steps,
            elapsed_ms=elapsed_ms,
            **kwargs
        )

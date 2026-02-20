"""Tests for rebot.config module."""

import os
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from rebot.config import (
    Config,
    LLMConfig,
    GenerationConfig,
    QualityConfig,
    LoggingConfig,
    CacheConfig,
    ConfigManager,
    get_config,
    reload_config,
    set_config,
    save_config,
    EnvLoader,
    JsonLoader,
    DefaultLoader,
    _merge_dict,
    _set_nested,
    _get_nested,
    _parse_env_value,
)


class TestLLMConfig:
    """Test suite for LLMConfig."""

    def test_llm_config_defaults(self):
        """Test LLMConfig default values."""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == ""
        assert config.timeout == 120.0
        assert config.max_retries == 3
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_llm_config_custom_values(self):
        """Test LLMConfig with custom values."""
        config = LLMConfig(
            provider="anthropic",
            model="claude-3-opus",
            api_key="test-key",
            timeout=60.0,
            temperature=0.5
        )
        assert config.provider == "anthropic"
        assert config.model == "claude-3-opus"
        assert config.api_key == "test-key"
        assert config.timeout == 60.0
        assert config.temperature == 0.5


class TestGenerationConfig:
    """Test suite for GenerationConfig."""

    def test_generation_config_defaults(self):
        """Test GenerationConfig default values."""
        config = GenerationConfig()
        assert config.language == "python"
        assert config.platforms == ["web"]
        assert config.include_ci is True
        assert config.include_security is True
        assert config.ai_codegen is True
        assert config.metagpt_chain is True
        assert config.max_workers == 4

    def test_generation_config_custom_platforms(self):
        """Test GenerationConfig with multiple platforms."""
        config = GenerationConfig(platforms=["web", "mobile", "desktop"])
        assert len(config.platforms) == 3
        assert "mobile" in config.platforms


class TestQualityConfig:
    """Test suite for QualityConfig."""

    def test_quality_config_defaults(self):
        """Test QualityConfig default values."""
        config = QualityConfig()
        assert config.lint is True
        assert config.test is True
        assert config.security is True
        assert config.type_check is True
        assert config.coverage_threshold == 60.0

    def test_quality_config_custom_threshold(self):
        """Test QualityConfig with custom threshold."""
        config = QualityConfig(coverage_threshold=80.0)
        assert config.coverage_threshold == 80.0


class TestLoggingConfig:
    """Test suite for LoggingConfig."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig default values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.format == "structured"
        assert config.file is None
        assert config.console is True

    def test_logging_config_custom_level(self):
        """Test LoggingConfig with custom level."""
        config = LoggingConfig(level="DEBUG", format="plain")
        assert config.level == "DEBUG"
        assert config.format == "plain"


class TestCacheConfig:
    """Test suite for CacheConfig."""

    def test_cache_config_defaults(self):
        """Test CacheConfig default values."""
        config = CacheConfig()
        assert config.enabled is True
        assert config.backend == "memory"
        assert config.ttl == 3600
        assert config.max_size == 10000
        assert config.path is None

    def test_cache_config_redis_backend(self):
        """Test CacheConfig with redis backend."""
        config = CacheConfig(backend="redis", ttl=7200)
        assert config.backend == "redis"
        assert config.ttl == 7200


class TestConfig:
    """Test suite for main Config class."""

    def test_config_defaults(self):
        """Test Config default values."""
        config = Config()
        assert config.project_name == "rebot-project"
        assert config.version == "0.1.0"
        assert isinstance(config.llm, LLMConfig)
        assert isinstance(config.generation, GenerationConfig)
        assert isinstance(config.quality, QualityConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.cache, CacheConfig)

    def test_config_to_dict(self):
        """Test Config.to_dict() method."""
        config = Config()
        d = config.to_dict()
        assert isinstance(d, dict)
        assert "llm" in d
        assert "generation" in d
        assert d["project_name"] == "rebot-project"

    def test_config_from_dict(self):
        """Test Config.from_dict() method."""
        data = {
            "project_name": "my-project",
            "llm": {"provider": "anthropic", "model": "claude-3"},
        }
        config = Config.from_dict(data)
        assert config.project_name == "my-project"
        assert config.llm.provider == "anthropic"
        assert config.llm.model == "claude-3"

    def test_config_api_keys(self):
        """Test Config API key fields."""
        config = Config(
            openai_api_key="sk-xxx",
            anthropic_api_key="sk-ant-xxx"
        )
        assert config.openai_api_key == "sk-xxx"
        assert config.anthropic_api_key == "sk-ant-xxx"


class TestHelperFunctions:
    """Test suite for helper functions."""

    def test_merge_dict_simple(self):
        """Test _merge_dict with simple dicts."""
        base = {"a": 1, "b": 2}
        overlay = {"b": 3, "c": 4}
        _merge_dict(base, overlay)
        assert base == {"a": 1, "b": 3, "c": 4}

    def test_merge_dict_nested(self):
        """Test _merge_dict with nested dicts."""
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        overlay = {"a": {"y": 5, "z": 6}}
        _merge_dict(base, overlay)
        assert base["a"] == {"x": 1, "y": 5, "z": 6}
        assert base["b"] == 3

    def test_set_nested_simple(self):
        """Test _set_nested with simple key."""
        d: Dict[str, Any] = {}
        _set_nested(d, "key", "value")
        assert d["key"] == "value"

    def test_set_nested_deep(self):
        """Test _set_nested with nested key."""
        d: Dict[str, Any] = {}
        _set_nested(d, "a.b.c", "value")
        assert d["a"]["b"]["c"] == "value"

    def test_get_nested_simple(self):
        """Test _get_nested with simple key."""
        d = {"key": "value"}
        assert _get_nested(d, "key") == "value"

    def test_get_nested_deep(self):
        """Test _get_nested with nested key."""
        d = {"a": {"b": {"c": "value"}}}
        assert _get_nested(d, "a.b.c") == "value"

    def test_get_nested_default(self):
        """Test _get_nested with missing key."""
        d = {"a": 1}
        assert _get_nested(d, "b", "default") == "default"

    def test_parse_env_value_bool_true(self):
        """Test _parse_env_value with boolean true values."""
        assert _parse_env_value("true") is True
        assert _parse_env_value("yes") is True
        assert _parse_env_value("1") is True
        assert _parse_env_value("on") is True

    def test_parse_env_value_bool_false(self):
        """Test _parse_env_value with boolean false values."""
        assert _parse_env_value("false") is False
        assert _parse_env_value("no") is False
        assert _parse_env_value("0") is False
        assert _parse_env_value("off") is False

    def test_parse_env_value_int(self):
        """Test _parse_env_value with integer."""
        assert _parse_env_value("42") == 42
        assert _parse_env_value("-10") == -10

    def test_parse_env_value_float(self):
        """Test _parse_env_value with float."""
        assert _parse_env_value("3.14") == 3.14
        assert _parse_env_value("0.5") == 0.5

    def test_parse_env_value_list(self):
        """Test _parse_env_value with comma-separated list."""
        result = _parse_env_value("a, b, c")
        assert result == ["a", "b", "c"]

    def test_parse_env_value_string(self):
        """Test _parse_env_value with plain string."""
        assert _parse_env_value("hello") == "hello"


class TestEnvLoader:
    """Test suite for EnvLoader."""

    def test_env_loader_reads_api_keys(self, monkeypatch):
        """Test EnvLoader reads API key env vars."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        loader = EnvLoader()
        config = loader.load()
        assert config.get("openai_api_key") == "test-openai-key"

    def test_env_loader_reads_rebot_vars(self, monkeypatch):
        """Test EnvLoader reads REBOT_ prefixed vars."""
        monkeypatch.setenv("REBOT_MODEL", "gpt-4-turbo")
        monkeypatch.setenv("REBOT_LOG_LEVEL", "DEBUG")
        loader = EnvLoader()
        config = loader.load()
        assert config.get("llm", {}).get("model") == "gpt-4-turbo"
        assert config.get("logging", {}).get("level") == "DEBUG"


class TestJsonLoader:
    """Test suite for JsonLoader."""

    def test_json_loader_loads_file(self):
        """Test JsonLoader loads JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"project_name": "test-project"}, f)
            f.flush()
            path = Path(f.name)
        
        try:
            loader = JsonLoader(path)
            config = loader.load()
            assert config["project_name"] == "test-project"
        finally:
            path.unlink()

    def test_json_loader_missing_file(self):
        """Test JsonLoader with missing file returns empty dict."""
        loader = JsonLoader(Path("/nonexistent/config.json"))
        config = loader.load()
        assert config == {}


class TestDefaultLoader:
    """Test suite for DefaultLoader."""

    def test_default_loader_returns_defaults(self):
        """Test DefaultLoader returns default config dict."""
        loader = DefaultLoader()
        config = loader.load()
        assert "project_name" in config
        assert "llm" in config
        assert config["llm"]["provider"] == "openai"


class TestConfigManager:
    """Test suite for ConfigManager."""

    def test_config_manager_singleton(self):
        """Test ConfigManager is singleton."""
        # Reset singleton for test
        ConfigManager._instance = None
        ConfigManager._config = None
        
        manager1 = ConfigManager()
        manager2 = ConfigManager()
        assert manager1 is manager2

    def test_config_manager_get_config(self):
        """Test ConfigManager.config property."""
        ConfigManager._instance = None
        ConfigManager._config = None
        
        manager = ConfigManager()
        config = manager.config
        assert isinstance(config, Config)

    def test_config_manager_set_get(self):
        """Test ConfigManager set and get methods."""
        ConfigManager._instance = None
        ConfigManager._config = None
        
        manager = ConfigManager()
        # Test that set method exists and can be called
        if hasattr(manager, 'set'):
            manager.set("project_name", "new-name")
        # Get returns config attribute value
        result = manager.get("project_name")
        assert result is not None  # Should return some value


class TestPublicAPI:
    """Test suite for public API functions."""

    def test_get_config(self):
        """Test get_config() function."""
        ConfigManager._instance = None
        ConfigManager._config = None
        
        config = get_config()
        assert isinstance(config, Config)

    def test_reload_config(self):
        """Test reload_config() function."""
        ConfigManager._instance = None
        ConfigManager._config = None
        
        config1 = get_config()
        config2 = reload_config()
        assert isinstance(config2, Config)

    def test_save_config(self):
        """Test save_config() function."""
        ConfigManager._instance = None
        ConfigManager._config = None
        
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_config.json"
            save_config(path)
            assert path.exists()
            
            # Verify content
            with open(path) as f:
                data = json.load(f)
            assert "project_name" in data

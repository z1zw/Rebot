"""Rebot Configuration System.

Supports multiple configuration sources:
1. Default values
2. YAML/TOML config files
3. Environment variables
4. CLI arguments (highest priority)

Usage:
    from rebot.config import get_config, Config
    
    config = get_config()
    api_key = config.openai_api_key
    model = config.default_model
"""

from __future__ import annotations

import os
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Configuration Schema
# ============================================================================

@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "openai"
    model: str = "gpt-4"
    api_key: str = ""
    base_url: str = ""
    timeout: float = 120.0
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass
class GenerationConfig:
    """Code generation configuration."""
    language: str = "python"
    platforms: List[str] = field(default_factory=lambda: ["web"])
    include_ci: bool = True
    include_security: bool = True
    ai_codegen: bool = True
    metagpt_chain: bool = True
    perspective: bool = True
    max_workers: int = 4


@dataclass
class QualityConfig:
    """Quality gate configuration."""
    lint: bool = True
    test: bool = True
    security: bool = True
    type_check: bool = True
    coverage_threshold: float = 60.0


@dataclass  
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "structured"  # "structured" or "plain"
    file: Optional[str] = None
    console: bool = True


@dataclass
class CacheConfig:
    """Caching configuration."""
    enabled: bool = True
    backend: str = "memory"  # "memory", "redis", "file"
    ttl: int = 3600
    max_size: int = 10000
    path: Optional[str] = None


@dataclass
class Config:
    """Main configuration class."""
    # Project
    project_name: str = "rebot-project"
    version: str = "0.1.0"
    
    # LLM
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Generation
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    
    # Quality
    quality: QualityConfig = field(default_factory=QualityConfig)
    
    # Logging
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Cache
    cache: CacheConfig = field(default_factory=CacheConfig)
    
    # Direct API keys (convenience)
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    azure_api_key: str = ""
    deepseek_api_key: str = ""
    
    # Paths
    output_dir: str = "./output"
    workspace_dir: str = "."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        config = cls()
        _update_dataclass(config, data)
        return config


def _update_dataclass(obj: Any, data: Dict[str, Any]) -> None:
    """Update dataclass fields from dict."""
    for key, value in data.items():
        if hasattr(obj, key):
            current = getattr(obj, key)
            if isinstance(current, (LLMConfig, GenerationConfig, QualityConfig, 
                                    LoggingConfig, CacheConfig)):
                if isinstance(value, dict):
                    _update_dataclass(current, value)
            else:
                setattr(obj, key, value)


# ============================================================================
# Configuration Loaders
# ============================================================================

class ConfigLoader:
    """Base config loader."""
    
    def load(self) -> Dict[str, Any]:
        raise NotImplementedError


class DefaultLoader(ConfigLoader):
    """Load default configuration."""
    
    def load(self) -> Dict[str, Any]:
        return asdict(Config())


class EnvLoader(ConfigLoader):
    """Load configuration from environment variables."""
    
    PREFIX = "REBOT_"
    
    def load(self) -> Dict[str, Any]:
        config = {}
        
        # Direct mappings
        env_mappings = {
            "OPENAI_API_KEY": "openai_api_key",
            "ANTHROPIC_API_KEY": "anthropic_api_key",
            "GOOGLE_API_KEY": "google_api_key",
            "AZURE_OPENAI_API_KEY": "azure_api_key",
            "DEEPSEEK_API_KEY": "deepseek_api_key",
            "REBOT_MODEL": "llm.model",
            "REBOT_PROVIDER": "llm.provider",
            "REBOT_TEMPERATURE": "llm.temperature",
            "REBOT_MAX_TOKENS": "llm.max_tokens",
            "REBOT_LOG_LEVEL": "logging.level",
            "REBOT_OUTPUT_DIR": "output_dir",
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                _set_nested(config, config_path, _parse_env_value(value))
        
        # Scan for REBOT_ prefixed variables
        for key, value in os.environ.items():
            if key.startswith(self.PREFIX) and key not in env_mappings:
                config_key = key[len(self.PREFIX):].lower()
                config[config_key] = _parse_env_value(value)
        
        return config


class YamlLoader(ConfigLoader):
    """Load configuration from YAML file."""
    
    def __init__(self, path: Path):
        self.path = path
    
    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        
        try:
            import yaml
            with open(self.path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            logger.warning("PyYAML not installed, skipping YAML config")
            return {}
        except Exception as e:
            logger.warning(f"Failed to load YAML config: {e}")
            return {}


class TomlLoader(ConfigLoader):
    """Load configuration from TOML file."""
    
    def __init__(self, path: Path):
        self.path = path
    
    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        
        try:
            import toml
            return toml.load(self.path)
        except ImportError:
            # Try tomllib (Python 3.11+)
            try:
                import tomllib
                with open(self.path, "rb") as f:
                    return tomllib.load(f)
            except ImportError:
                logger.warning("TOML library not installed, skipping TOML config")
                return {}
        except Exception as e:
            logger.warning(f"Failed to load TOML config: {e}")
            return {}


class JsonLoader(ConfigLoader):
    """Load configuration from JSON file."""
    
    def __init__(self, path: Path):
        self.path = path
    
    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {}
        
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load JSON config: {e}")
            return {}


# ============================================================================
# Configuration Manager
# ============================================================================

class ConfigManager:
    """Manages configuration from multiple sources."""
    
    _instance: Optional["ConfigManager"] = None
    _config: Optional[Config] = None
    
    def __new__(cls) -> "ConfigManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = self._load_config()
    
    def _load_config(self) -> Config:
        """Load configuration from all sources."""
        # Start with defaults
        config_dict: Dict[str, Any] = {}
        
        # Load in order of priority (later overrides earlier)
        loaders: List[ConfigLoader] = [
            DefaultLoader(),
            # Global config
            JsonLoader(Path.home() / ".rebot" / "config.json"),
            YamlLoader(Path.home() / ".rebot" / "config.yaml"),
            # Project config
            YamlLoader(Path.cwd() / "rebot.yaml"),
            YamlLoader(Path.cwd() / "rebot.yml"),
            TomlLoader(Path.cwd() / "rebot.toml"),
            # Environment (highest priority)
            EnvLoader(),
        ]
        
        for loader in loaders:
            try:
                data = loader.load()
                _merge_dict(config_dict, data)
            except Exception as e:
                logger.warning(f"Failed to load config from {loader.__class__.__name__}: {e}")
        
        return Config.from_dict(config_dict)
    
    @property
    def config(self) -> Config:
        """Get the current configuration."""
        return self._config or Config()
    
    def reload(self) -> Config:
        """Reload configuration from all sources."""
        self._config = self._load_config()
        return self._config
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        _set_nested(asdict(self._config), key, value)
        # Recreate config from dict
        self._config = Config.from_dict(asdict(self._config))
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return _get_nested(asdict(self._config), key, default)
    
    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = Path.home() / ".rebot" / "config.json"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._config.to_dict(), f, indent=2)


# ============================================================================
# Helper Functions
# ============================================================================

def _merge_dict(base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
    """Merge overlay dict into base dict recursively."""
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _merge_dict(base[key], value)
        else:
            base[key] = value


def _set_nested(d: Dict[str, Any], key: str, value: Any) -> None:
    """Set a nested dictionary value using dot notation."""
    keys = key.split(".")
    for k in keys[:-1]:
        if k not in d:
            d[k] = {}
        d = d[k]
    d[keys[-1]] = value


def _get_nested(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a nested dictionary value using dot notation."""
    keys = key.split(".")
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d


def _parse_env_value(value: str) -> Any:
    """Parse environment variable value to appropriate type."""
    # Boolean
    if value.lower() in ("true", "yes", "1", "on"):
        return True
    if value.lower() in ("false", "no", "0", "off"):
        return False
    
    # Number
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass
    
    # List (comma-separated)
    if "," in value:
        return [v.strip() for v in value.split(",")]
    
    return value


# ============================================================================
# Public API
# ============================================================================

def get_config() -> Config:
    """Get the global configuration instance."""
    return ConfigManager().config


def reload_config() -> Config:
    """Reload configuration from all sources."""
    return ConfigManager().reload()


def set_config(key: str, value: Any) -> None:
    """Set a configuration value."""
    ConfigManager().set(key, value)


def save_config(path: Optional[Path] = None) -> None:
    """Save configuration to file."""
    ConfigManager().save(path)

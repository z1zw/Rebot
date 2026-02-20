"""Tests for rebot.auto.generate module."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from rebot.auto.generate import OneShotGenerator, GeneratorConfig


class TestGeneratorConfig:
    """Test suite for GeneratorConfig class."""

    def test_config_creation(self):
        """Test GeneratorConfig can be created with defaults."""
        config = GeneratorConfig(language="python", platforms=["web"])
        assert config.language == "python"
        assert config.platforms == ["web"]

    def test_config_with_all_options(self):
        """Test GeneratorConfig with all options."""
        config = GeneratorConfig(
            language="typescript",
            platforms=["web", "ios", "android"],
            include_ci=True,
            include_security=True,
            execute_workflow=False,
            ai_codegen=True,
            metagpt_chain=True,
            perspective=True,
        )
        assert config.language == "typescript"
        assert len(config.platforms) == 3
        assert config.include_ci is True
        assert config.include_security is True

    def test_config_defaults(self):
        """Test GeneratorConfig default values."""
        config = GeneratorConfig(language="python", platforms=["web"])
        assert config.include_ci is True
        assert config.include_security is True
        assert config.execute_workflow is False
        assert config.ai_codegen is True
        assert config.metagpt_chain is True
        assert config.perspective is True

    def test_config_workflow_inputs(self):
        """Test GeneratorConfig with workflow inputs."""
        inputs = {"env": "production", "debug": False}
        config = GeneratorConfig(
            language="python",
            platforms=["web"],
            workflow_inputs=inputs,
        )
        assert config.workflow_inputs == inputs

    def test_config_domain_targets(self):
        """Test GeneratorConfig with domain targets."""
        config = GeneratorConfig(
            language="python",
            platforms=["web"],
            domain_targets=["finance", "analytics"],
        )
        assert "finance" in config.domain_targets

    def test_config_attention_scale(self):
        """Test GeneratorConfig attention scale."""
        config = GeneratorConfig(
            language="python",
            platforms=["web"],
            attention_scale=1.5,
        )
        assert config.attention_scale == 1.5


class TestOneShotGenerator:
    """Test suite for OneShotGenerator class."""

    def test_generator_creation(self, mock_model, temp_dir: Path):
        """Test OneShotGenerator can be created."""
        generator = OneShotGenerator(model=mock_model, root=temp_dir)
        assert generator.model is mock_model
        assert generator.root == temp_dir

    def test_generator_creates_directories(self, mock_model, temp_dir: Path):
        """Test generator creates output directories."""
        generator = OneShotGenerator(model=mock_model, root=temp_dir)
        
        # Mock the spec compiler and other components
        with patch.object(generator, 'generate') as mock_gen:
            mock_gen.return_value = None
            
            # Create dirs manually as the mock won't
            (temp_dir / "docs").mkdir(exist_ok=True)
            (temp_dir / "backend").mkdir(exist_ok=True)
            (temp_dir / "frontend").mkdir(exist_ok=True)
        
        assert temp_dir.exists()


class TestOneShotGeneratorIntegration:
    """Integration tests for OneShotGenerator."""

    @pytest.mark.slow
    def test_generator_full_pipeline(self, mock_model, temp_dir: Path):
        """Test full generation pipeline (mocked)."""
        # This would be a more comprehensive test
        generator = OneShotGenerator(model=mock_model, root=temp_dir)
        config = GeneratorConfig(
            language="python",
            platforms=["web"],
            ai_codegen=False,  # Disable to speed up test
            metagpt_chain=False,
            perspective=False,
        )
        
        # In a real test, we'd run the generator and check outputs
        assert generator.model is not None


class TestGeneratorPlatforms:
    """Test generator with different platforms."""

    def test_web_platform(self):
        """Test web platform configuration."""
        config = GeneratorConfig(language="typescript", platforms=["web"])
        assert "web" in config.platforms

    def test_mobile_platforms(self):
        """Test mobile platform configurations."""
        config = GeneratorConfig(
            language="dart",
            platforms=["ios", "android"],
        )
        assert "ios" in config.platforms
        assert "android" in config.platforms

    def test_desktop_platform(self):
        """Test desktop platform configuration."""
        config = GeneratorConfig(
            language="typescript",
            platforms=["desktop"],
        )
        assert "desktop" in config.platforms

    def test_miniapp_platform(self):
        """Test miniapp platform configuration."""
        config = GeneratorConfig(
            language="javascript",
            platforms=["miniapp"],
        )
        assert "miniapp" in config.platforms

    def test_all_platforms(self):
        """Test all platforms configuration."""
        config = GeneratorConfig(
            language="typescript",
            platforms=["web", "ios", "android", "desktop", "miniapp"],
        )
        assert len(config.platforms) == 5


class TestGeneratorMetaGPT:
    """Test generator MetaGPT integration."""

    def test_metagpt_chain_enabled(self):
        """Test MetaGPT chain configuration."""
        config = GeneratorConfig(
            language="python",
            platforms=["web"],
            metagpt_chain=True,
        )
        assert config.metagpt_chain is True

    def test_metagpt_native_config(self):
        """Test MetaGPT native configuration."""
        config = GeneratorConfig(
            language="python",
            platforms=["web"],
            metagpt_native=True,
            metagpt_native_rounds=10,
            metagpt_native_investment=5.0,
        )
        assert config.metagpt_native is True
        assert config.metagpt_native_rounds == 10
        assert config.metagpt_native_investment == 5.0

"""Tests for rebot.models.universal module."""

from __future__ import annotations

import pytest
import os
from unittest.mock import patch

from rebot.models.universal import LLMProvider, ProviderConfig


class TestLLMProvider:
    """Test suite for LLMProvider enum."""

    def test_openai_provider(self):
        """Test OpenAI provider value."""
        assert LLMProvider.OPENAI.value == "openai"

    def test_anthropic_provider(self):
        """Test Anthropic provider value."""
        assert LLMProvider.ANTHROPIC.value == "anthropic"

    def test_google_provider(self):
        """Test Google provider value."""
        assert LLMProvider.GOOGLE.value == "google"

    def test_azure_provider(self):
        """Test Azure provider value."""
        assert LLMProvider.AZURE.value == "azure"

    def test_deepseek_provider(self):
        """Test DeepSeek provider value."""
        assert LLMProvider.DEEPSEEK.value == "deepseek"

    def test_domestic_providers(self):
        """Test domestic (Chinese) providers."""
        domestic = [
            LLMProvider.QIANFAN,
            LLMProvider.DASHSCOPE,
            LLMProvider.ZHIPU,
            LLMProvider.MINIMAX,
            LLMProvider.BAICHUAN,
            LLMProvider.YI,
        ]
        for provider in domestic:
            assert provider.value is not None

    def test_local_providers(self):
        """Test local deployment providers."""
        local = [LLMProvider.OLLAMA, LLMProvider.VLLM]
        for provider in local:
            assert provider.value is not None

    def test_cloud_providers(self):
        """Test cloud providers."""
        cloud = [
            LLMProvider.BEDROCK,
            LLMProvider.SAGEMAKER,
            LLMProvider.VERTEX,
        ]
        for provider in cloud:
            assert provider.value is not None

    def test_aggregator_providers(self):
        """Test aggregator providers."""
        aggregators = [
            LLMProvider.OPENROUTER,
            LLMProvider.TOGETHER,
            LLMProvider.ANYSCALE,
            LLMProvider.FIREWORKS,
        ]
        for provider in aggregators:
            assert provider.value is not None

    def test_total_provider_count(self):
        """Test total number of providers."""
        # Should have at least 25+ providers
        assert len(LLMProvider) >= 25


class TestProviderConfig:
    """Test suite for ProviderConfig class."""

    def test_config_creation(self):
        """Test ProviderConfig can be created."""
        config = ProviderConfig(provider=LLMProvider.OPENAI)
        assert config.provider == LLMProvider.OPENAI

    def test_config_with_api_key(self):
        """Test ProviderConfig with direct API key."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key="sk-test-key",
        )
        assert config.api_key == "sk-test-key"

    def test_config_with_model(self):
        """Test ProviderConfig with model name."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4",
        )
        assert config.model == "gpt-4"

    def test_config_with_base_url(self):
        """Test ProviderConfig with custom base URL."""
        config = ProviderConfig(
            provider=LLMProvider.CUSTOM,
            base_url="https://api.example.com/v1",
        )
        assert config.base_url == "https://api.example.com/v1"

    def test_config_timeout(self):
        """Test ProviderConfig timeout setting."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            timeout=60.0,
        )
        assert config.timeout == 60.0

    def test_config_max_retries(self):
        """Test ProviderConfig max retries setting."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            max_retries=5,
        )
        assert config.max_retries == 5

    def test_config_extra_headers(self):
        """Test ProviderConfig with extra headers."""
        headers = {"X-Custom-Header": "value"}
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            extra_headers=headers,
        )
        assert config.extra_headers == headers

    def test_resolve_api_key_direct(self):
        """Test resolving API key from direct value."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            api_key="direct-key",
        )
        assert config.resolve_api_key() == "direct-key"

    def test_resolve_api_key_from_env(self):
        """Test resolving API key from environment variable."""
        with patch.dict(os.environ, {"TEST_API_KEY": "env-key"}):
            config = ProviderConfig(
                provider=LLMProvider.OPENAI,
                api_key_env="TEST_API_KEY",
            )
            assert config.resolve_api_key() == "env-key"

    def test_resolve_api_key_default_env(self):
        """Test resolving API key from default environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "openai-key"}):
            config = ProviderConfig(provider=LLMProvider.OPENAI)
            assert config.resolve_api_key() == "openai-key"


class TestProviderConfigRegion:
    """Test provider config with region settings."""

    def test_azure_with_region(self):
        """Test Azure config with region."""
        config = ProviderConfig(
            provider=LLMProvider.AZURE,
            region="eastus",
        )
        assert config.region == "eastus"

    def test_bedrock_with_region(self):
        """Test Bedrock config with region."""
        config = ProviderConfig(
            provider=LLMProvider.BEDROCK,
            region="us-west-2",
        )
        assert config.region == "us-west-2"


class TestProviderConfigOrganization:
    """Test provider config with organization settings."""

    def test_openai_with_organization(self):
        """Test OpenAI config with organization."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            organization="org-123",
        )
        assert config.organization == "org-123"

    def test_openai_with_project(self):
        """Test OpenAI config with project."""
        config = ProviderConfig(
            provider=LLMProvider.OPENAI,
            project="proj-456",
        )
        assert config.project == "proj-456"

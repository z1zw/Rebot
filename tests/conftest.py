"""Pytest configuration and shared fixtures for Rebot tests."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Iterator, List, Optional, Sequence
from unittest.mock import MagicMock, AsyncMock

import pytest

# Add rebot to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rebot.core.messages import Message
from rebot.models.base import ChatModel
from rebot.tools.base import BaseTool


# ============================================================================
# Mock Models
# ============================================================================

@dataclass
class MockMessage:
    """Mock message for testing."""
    role: str = "assistant"
    content: str = "Mock response"
    tool_calls: List[Any] = field(default_factory=list)


class MockChatModel(ChatModel):
    """Mock chat model for testing without API calls."""
    
    def __init__(
        self,
        responses: Optional[List[str]] = None,
        tool_responses: Optional[List[List[Any]]] = None,
    ):
        self.responses = responses or ["Mock response"]
        self.tool_responses = tool_responses or []
        self.call_count = 0
        self.last_messages: List[Message] = []
        self.last_tools: List[BaseTool] = []
    
    def invoke(
        self,
        messages: Sequence[Message],
        tools: Sequence[BaseTool] = (),
        **kwargs: Any,
    ) -> Message:
        self.last_messages = list(messages)
        self.last_tools = list(tools)
        
        response_idx = min(self.call_count, len(self.responses) - 1)
        content = self.responses[response_idx]
        
        tool_calls = []
        if self.tool_responses and self.call_count < len(self.tool_responses):
            tool_calls = self.tool_responses[self.call_count]
        
        self.call_count += 1
        
        return Message(role="assistant", content=content, tool_calls=tool_calls)
    
    async def ainvoke(
        self,
        messages: Sequence[Message],
        tools: Sequence[BaseTool] = (),
        **kwargs: Any,
    ) -> Message:
        return self.invoke(messages, tools, **kwargs)
    
    def stream(
        self,
        messages: Sequence[Message],
        tools: Sequence[BaseTool] = (),
        **kwargs: Any,
    ) -> Iterator[str]:
        response = self.invoke(messages, tools, **kwargs)
        for char in response.content:
            yield char
    
    async def astream(
        self,
        messages: Sequence[Message],
        tools: Sequence[BaseTool] = (),
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        response = self.invoke(messages, tools, **kwargs)
        for char in response.content:
            yield char


class MockToolModel(MockChatModel):
    """Mock model that returns tool calls."""
    
    def __init__(self, tool_name: str = "test_tool", tool_args: dict = None):
        super().__init__()
        self.tool_name = tool_name
        self.tool_args = tool_args or {}
    
    def invoke(
        self,
        messages: Sequence[Message],
        tools: Sequence[BaseTool] = (),
        **kwargs: Any,
    ) -> Message:
        self.last_messages = list(messages)
        self.last_tools = list(tools)
        self.call_count += 1
        
        # Return tool call on first invocation, then final response
        if self.call_count == 1:
            return Message(
                role="assistant",
                content="",
                tool_calls=[{
                    "id": f"call_{self.call_count}",
                    "type": "function",
                    "function": {
                        "name": self.tool_name,
                        "arguments": str(self.tool_args),
                    }
                }]
            )
        return Message(role="assistant", content="Task completed")


# ============================================================================
# Mock Tools
# ============================================================================

class MockTool(BaseTool):
    """Mock tool for testing."""
    
    name: str = "mock_tool"
    description: str = "A mock tool for testing"
    
    def __init__(self, name: str = "mock_tool", return_value: str = "Tool executed"):
        self.name = name
        self.description = f"Mock tool: {name}"
        self.return_value = return_value
        self.call_count = 0
        self.last_args: dict = {}
    
    def run(self, **kwargs: Any) -> str:
        self.call_count += 1
        self.last_args = kwargs
        return self.return_value
    
    async def arun(self, **kwargs: Any) -> str:
        return self.run(**kwargs)
    
    def get_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_model() -> MockChatModel:
    """Create a mock chat model."""
    return MockChatModel()


@pytest.fixture
def mock_model_with_responses() -> callable:
    """Factory fixture for creating mock models with specific responses."""
    def _create(responses: List[str]) -> MockChatModel:
        return MockChatModel(responses=responses)
    return _create


@pytest.fixture
def mock_tool() -> MockTool:
    """Create a mock tool."""
    return MockTool()


@pytest.fixture
def mock_tool_factory() -> callable:
    """Factory fixture for creating mock tools."""
    def _create(name: str = "test_tool", return_value: str = "OK") -> MockTool:
        return MockTool(name=name, return_value=return_value)
    return _create


@pytest.fixture
def sample_messages() -> List[Message]:
    """Create sample messages for testing."""
    return [
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Hello, how are you?"),
    ]


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for file operations."""
    return tmp_path


@pytest.fixture
def sample_code() -> str:
    """Sample Python code for testing code-related features."""
    return '''
def hello_world():
    """Print hello world."""
    print("Hello, World!")

class Calculator:
    """Simple calculator class."""
    
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def subtract(self, a: int, b: int) -> int:
        return a - b
'''


@pytest.fixture
def sample_spec() -> dict:
    """Sample specification for testing generation features."""
    return {
        "product": "Test App",
        "features": ["feature1", "feature2"],
        "goals": ["goal1"],
        "tech_stack": ["Python", "FastAPI"],
    }


# ============================================================================
# Async Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Environment Setup
# ============================================================================

@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("REBOT_TEST_MODE", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")


# ============================================================================
# Markers
# ============================================================================

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "requires_api: marks tests that require real API keys")


# ============================================================================
# Helper Functions
# ============================================================================

def assert_messages_equal(actual: List[Message], expected: List[Message]) -> None:
    """Assert two message lists are equal."""
    assert len(actual) == len(expected), f"Message count mismatch: {len(actual)} vs {len(expected)}"
    for i, (a, e) in enumerate(zip(actual, expected)):
        assert a.role == e.role, f"Role mismatch at index {i}: {a.role} vs {e.role}"
        assert a.content == e.content, f"Content mismatch at index {i}"


def create_test_agent_state(messages: List[Message] = None, **kwargs):
    """Helper to create agent state for testing."""
    from rebot.agents.middleware import AgentState
    return AgentState(messages=messages or [], **kwargs)

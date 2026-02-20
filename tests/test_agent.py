"""Tests for rebot.agents.agent module."""

from __future__ import annotations

import pytest
from typing import List

from rebot.agents.agent import Agent
from rebot.agents.middleware import AgentState
from rebot.core.messages import Message

from conftest import MockChatModel, MockTool, create_test_agent_state


class TestAgent:
    """Test suite for Agent class."""

    def test_agent_creation(self, mock_model: MockChatModel):
        """Test agent can be created with minimal configuration."""
        agent = Agent(model=mock_model)
        assert agent.model is mock_model
        assert agent.tools == ()
        assert agent.middleware == ()

    def test_agent_with_tools(self, mock_model: MockChatModel, mock_tool: MockTool):
        """Test agent can be created with tools."""
        agent = Agent(model=mock_model, tools=[mock_tool])
        assert len(agent.tools) == 1
        assert agent.tools[0] is mock_tool

    def test_agent_run_simple(self, mock_model: MockChatModel):
        """Test simple agent run without tools."""
        mock_model.responses = ["Hello! I'm doing well."]
        agent = Agent(model=mock_model)
        
        state = create_test_agent_state(
            messages=[Message(role="user", content="Hello")]
        )
        
        result = agent.run(state, context=None)
        
        assert len(result.messages) > 1
        assert result.messages[-1].role == "assistant"
        assert mock_model.call_count == 1

    def test_agent_run_preserves_messages(self, mock_model: MockChatModel):
        """Test that agent preserves original messages."""
        agent = Agent(model=mock_model)
        
        original_messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="What's 2+2?"),
        ]
        state = create_test_agent_state(messages=original_messages.copy())
        
        result = agent.run(state, context=None)
        
        # Should have original messages plus response
        assert len(result.messages) >= len(original_messages)
        assert result.messages[0].content == "You are helpful."
        assert result.messages[1].content == "What's 2+2?"

    @pytest.mark.asyncio
    async def test_agent_run_async(self, mock_model: MockChatModel):
        """Test async agent run."""
        mock_model.responses = ["Async response"]
        agent = Agent(model=mock_model)
        
        state = create_test_agent_state(
            messages=[Message(role="user", content="Async test")]
        )
        
        result = await agent.run_async(state, context=None)
        
        assert len(result.messages) > 1
        assert "Async" in result.messages[-1].content or mock_model.call_count > 0


class TestAgentState:
    """Test suite for AgentState."""

    def test_agent_state_creation(self):
        """Test AgentState can be created."""
        state = AgentState(messages=[])
        assert state.messages == []
        # run_id is optional and defaults to None
        assert state.run_id is None

    def test_agent_state_with_messages(self, sample_messages: List[Message]):
        """Test AgentState preserves messages."""
        state = AgentState(messages=sample_messages)
        assert len(state.messages) == 2
        assert state.messages[0].role == "system"

    def test_agent_state_configurable(self):
        """Test AgentState configurable dict."""
        config = {"temperature": 0.7, "max_tokens": 100}
        state = AgentState(messages=[], configurable=config)
        assert state.configurable == config


class TestAgentWithMiddleware:
    """Test agent with middleware."""

    def test_agent_middleware_list(self, mock_model: MockChatModel):
        """Test agent accepts middleware list."""
        from rebot.agents.middleware import AgentMiddleware
        
        class TestMiddleware(AgentMiddleware):
            def before_agent(self, state, context):
                return None
        
        middleware = TestMiddleware()
        agent = Agent(model=mock_model, middleware=[middleware])
        
        assert len(agent.middleware) == 1


class TestAgentSchemas:
    """Test agent schema handling."""

    def test_agent_state_schema(self, mock_model: MockChatModel):
        """Test agent generates state schema."""
        agent = Agent(model=mock_model)
        assert agent.state_schema is not None

    def test_agent_input_schema(self, mock_model: MockChatModel):
        """Test agent generates input schema."""
        agent = Agent(model=mock_model)
        assert agent.input_schema is not None

    def test_agent_output_schema(self, mock_model: MockChatModel):
        """Test agent generates output schema."""
        agent = Agent(model=mock_model)
        assert agent.output_schema is not None

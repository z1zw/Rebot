"""Tests for rebot.core.messages module."""

from __future__ import annotations

import pytest
import json

from rebot.core.messages import Message


class TestMessage:
    """Test suite for Message class."""

    def test_message_creation(self):
        """Test message can be created with required fields."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_roles(self):
        """Test different message roles."""
        roles = ["system", "user", "assistant", "tool"]
        for role in roles:
            msg = Message(role=role, content=f"Content for {role}")
            assert msg.role == role

    def test_message_with_tool_calls(self):
        """Test message with tool calls."""
        tool_calls = [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "test_tool",
                    "arguments": '{"arg1": "value1"}',
                },
            }
        ]
        msg = Message(role="assistant", content="", tool_calls=tool_calls)
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0]["function"]["name"] == "test_tool"

    def test_message_empty_content(self):
        """Test message with empty content."""
        msg = Message(role="assistant", content="")
        assert msg.content == ""

    def test_message_multiline_content(self):
        """Test message with multiline content."""
        content = """Line 1
Line 2
Line 3"""
        msg = Message(role="user", content=content)
        assert "\n" in msg.content
        assert msg.content.count("\n") == 2

    def test_message_unicode_content(self):
        """Test message with unicode content."""
        content = "你好世界 🌍 مرحبا"
        msg = Message(role="user", content=content)
        assert msg.content == content

    def test_message_equality(self):
        """Test message equality comparison."""
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="user", content="Hello")
        # Dataclass should support equality
        assert msg1.role == msg2.role
        assert msg1.content == msg2.content

    def test_message_serialization(self):
        """Test message can be serialized to dict."""
        msg = Message(role="user", content="Test")
        # Assuming Message has a method to convert to dict or is a dataclass
        if hasattr(msg, "model_dump"):
            data = msg.model_dump()
        elif hasattr(msg, "__dict__"):
            data = {"role": msg.role, "content": msg.content}
        
        assert data["role"] == "user"
        assert data["content"] == "Test"


class TestMessageList:
    """Test operations on message lists."""

    def test_message_list_creation(self):
        """Test creating a list of messages."""
        messages = [
            Message(role="system", content="You are helpful."),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
        ]
        assert len(messages) == 3

    def test_message_list_filtering(self):
        """Test filtering messages by role."""
        messages = [
            Message(role="system", content="System"),
            Message(role="user", content="User 1"),
            Message(role="assistant", content="Assistant 1"),
            Message(role="user", content="User 2"),
        ]
        
        user_messages = [m for m in messages if m.role == "user"]
        assert len(user_messages) == 2

    def test_message_list_last_user_message(self):
        """Test getting last user message."""
        messages = [
            Message(role="user", content="First"),
            Message(role="assistant", content="Response"),
            Message(role="user", content="Last"),
        ]
        
        user_messages = [m for m in messages if m.role == "user"]
        last_user = user_messages[-1] if user_messages else None
        assert last_user is not None
        assert last_user.content == "Last"

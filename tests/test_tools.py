"""Tests for rebot.tools module."""

from __future__ import annotations

import pytest
from typing import Any

from rebot.tools.base import BaseTool
from conftest import MockTool


class TestBaseTool:
    """Test suite for BaseTool base class."""

    def test_mock_tool_creation(self):
        """Test tool can be created."""
        tool = MockTool(name="test", return_value="result")
        assert tool.name == "test"
        assert tool.return_value == "result"

    def test_mock_tool_run(self):
        """Test tool run method."""
        tool = MockTool(name="calc", return_value="42")
        result = tool.run(input="test")
        
        assert result == "42"
        assert tool.call_count == 1
        assert tool.last_args == {"input": "test"}

    @pytest.mark.asyncio
    async def test_mock_tool_arun(self):
        """Test tool async run method."""
        tool = MockTool(name="async_tool", return_value="async_result")
        result = await tool.arun(data="async_data")
        
        assert result == "async_result"
        assert tool.call_count == 1

    def test_mock_tool_schema(self):
        """Test tool schema generation."""
        tool = MockTool(name="schema_tool")
        schema = tool.get_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "schema_tool"
        assert "description" in schema["function"]

    def test_tool_multiple_calls(self):
        """Test tool tracks multiple calls."""
        tool = MockTool(name="multi", return_value="ok")
        
        tool.run(a=1)
        tool.run(b=2)
        tool.run(c=3)
        
        assert tool.call_count == 3
        assert tool.last_args == {"c": 3}


class TestToolSchemas:
    """Test tool schema generation."""

    def test_schema_structure(self):
        """Test schema has correct structure."""
        tool = MockTool(name="structured_tool")
        schema = tool.get_schema()
        
        assert "type" in schema
        assert "function" in schema
        assert "name" in schema["function"]
        assert "description" in schema["function"]
        assert "parameters" in schema["function"]

    def test_schema_parameters(self):
        """Test schema parameters structure."""
        tool = MockTool(name="param_tool")
        schema = tool.get_schema()
        
        params = schema["function"]["parameters"]
        assert params["type"] == "object"
        assert "properties" in params


class TestToolRegistry:
    """Test tool registry functionality."""

    def test_register_multiple_tools(self):
        """Test registering multiple tools."""
        tools = [
            MockTool(name="tool_1", return_value="r1"),
            MockTool(name="tool_2", return_value="r2"),
            MockTool(name="tool_3", return_value="r3"),
        ]
        
        registry = {t.name: t for t in tools}
        
        assert len(registry) == 3
        assert "tool_1" in registry
        assert "tool_2" in registry
        assert "tool_3" in registry

    def test_get_tool_by_name(self):
        """Test getting tool by name."""
        tools = [
            MockTool(name="search", return_value="found"),
            MockTool(name="calculate", return_value="42"),
        ]
        
        registry = {t.name: t for t in tools}
        
        calc_tool = registry.get("calculate")
        assert calc_tool is not None
        assert calc_tool.run() == "42"


class TestToolExecution:
    """Test tool execution scenarios."""

    def test_tool_with_dict_args(self):
        """Test tool with dictionary arguments."""
        tool = MockTool(name="dict_tool", return_value="ok")
        result = tool.run(**{"key1": "value1", "key2": "value2"})
        
        assert result == "ok"
        assert tool.last_args["key1"] == "value1"
        assert tool.last_args["key2"] == "value2"

    def test_tool_with_no_args(self):
        """Test tool with no arguments."""
        tool = MockTool(name="no_args", return_value="done")
        result = tool.run()
        
        assert result == "done"
        assert tool.last_args == {}

    def test_tool_return_types(self):
        """Test tool with different return types."""
        # String return
        str_tool = MockTool(name="str_tool", return_value="string result")
        assert isinstance(str_tool.run(), str)

    def test_tool_chain(self):
        """Test chaining multiple tools."""
        tools = [
            MockTool(name="step1", return_value="result1"),
            MockTool(name="step2", return_value="result2"),
            MockTool(name="step3", return_value="final"),
        ]
        
        results = []
        for tool in tools:
            result = tool.run(previous=results[-1] if results else None)
            results.append(result)
        
        assert len(results) == 3
        assert results[-1] == "final"

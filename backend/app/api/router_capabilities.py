from __future__ import annotations

from fastapi import APIRouter

from app.core.capabilities import (
    list_llm_providers,
    list_tool_capabilities,
    resource_policy,
)


router = APIRouter()


@router.get("/capabilities/providers")
async def capabilities_providers():
    providers = list_llm_providers()
    return {"providers": providers, "count": len(providers)}


@router.get("/capabilities/tools")
async def capabilities_tools():
    tools = list_tool_capabilities()
    return {"tools": tools, "count": len(tools)}


@router.get("/capabilities/resources")
async def capabilities_resources():
    return {"resources": resource_policy()}

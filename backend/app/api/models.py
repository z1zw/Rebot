from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ExecuteResponse(BaseModel):
    run_id: str


class DevServerResponse(BaseModel):
    url: str
    command: str
    port: int
    pid: int
    preview_health: dict[str, Any] | None = None


class FileListRequest(BaseModel):
    workspace: str
    max_depth: int = 3
    tree: bool = False


class FileReadRequest(BaseModel):
    workspace: str
    path: str


class FileWriteRequest(BaseModel):
    workspace: str
    path: str
    content: str


class FileDeleteRequest(BaseModel):
    workspace: str
    path: str


class FileRepairRequest(BaseModel):
    workspace: str
    max_depth: int = 8


class SecurityTestRequest(BaseModel):
    target_url: str
    tools: list[str] = ["zap"]


class DevServerStartRequest(BaseModel):
    workspace: str
    framework: str
    project_type: str | None = None
    port: int | None = None
    command: str | None = None


class DevServerStopRequest(BaseModel):
    workspace: str
    framework: str
    project_type: str | None = None


class DevServerStatusRequest(BaseModel):
    workspace: str
    framework: str
    project_type: str | None = None


class DevServerRestartRequest(BaseModel):
    workspace: str
    framework: str
    project_type: str | None = None
    port: int | None = None
    command: str | None = None


class DevServerLogsRequest(BaseModel):
    workspace: str
    framework: str
    lines: int = 200


class EmulatorStartRequest(BaseModel):
    avd: str | None = None


class EmulatorStopRequest(BaseModel):
    pass


class ASTIndexRequest(BaseModel):
    workspace: str
    max_files: int = 300
    max_file_bytes: int = 512000
    include_references: bool = True


class ASTSymbolRefsRequest(BaseModel):
    workspace: str
    symbol: str
    max_files: int = 300
    max_file_bytes: int = 512000
    include_definitions: bool = True

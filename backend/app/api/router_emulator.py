from __future__ import annotations

from fastapi import APIRouter

from app.api.models import EmulatorStartRequest, EmulatorStopRequest
from app.core.emulator import EmulatorManager


router = APIRouter()


@router.post("/emulator/start")
async def start_emulator(req: EmulatorStartRequest):
    info = EmulatorManager.start(avd=req.avd)
    return {"avd": info.avd, "pid": info.pid}


@router.post("/emulator/stop")
async def stop_emulator(_: EmulatorStopRequest):
    return {"stopped": EmulatorManager.stop()}


@router.get("/emulator/status")
async def emulator_status():
    return EmulatorManager.status()


@router.post("/emulator/mirror/start")
async def emulator_mirror_start():
    status = EmulatorManager.status()
    device = status.get("device")
    ok = EmulatorManager.start_mirror(device=device)
    return {"started": ok, "device": device}


@router.post("/emulator/mirror/stop")
async def emulator_mirror_stop():
    return {"stopped": EmulatorManager.stop_mirror()}


@router.get("/emulator/devices")
async def emulator_devices():
    """List connected ADB devices and available AVDs."""
    devices = EmulatorManager.list_devices()
    avds = EmulatorManager.list_avds()
    return {
        "devices": devices,
        "avds": avds,
        "count": len(devices),
    }

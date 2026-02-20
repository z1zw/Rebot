from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import subprocess
import time

from app.core.process_sandbox import popen_checked, run_checked


@dataclass
class EmulatorInfo:
    avd: str
    started_at: float
    pid: int


class EmulatorManager:
    _proc: subprocess.Popen | None = None
    _info: EmulatorInfo | None = None
    _mirror_proc: subprocess.Popen | None = None

    @classmethod
    def _sdk_root(cls) -> Path:
        sdk = os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")
        if not sdk:
            # default Windows path
            fallback = Path.home() / "AppData" / "Local" / "Android" / "Sdk"
            if fallback.exists():
                return fallback
            raise RuntimeError("ANDROID_HOME not set")
        return Path(sdk)

    @classmethod
    def _adb_path(cls) -> Path:
        return cls._sdk_root() / "platform-tools" / "adb.exe"

    @classmethod
    def _emulator_path(cls) -> Path:
        return cls._sdk_root() / "emulator" / "emulator.exe"

    @classmethod
    def _avd_name(cls) -> str:
        return os.getenv("ANDROID_AVD_NAME", "RebotPixel")

    @classmethod
    def start(cls, *, avd: str | None = None) -> EmulatorInfo:
        if cls._proc and cls._proc.poll() is None:
            return cls._info  # type: ignore[return-value]
        avd_name = avd or cls._avd_name()
        emulator = cls._emulator_path()
        if not emulator.exists():
            raise RuntimeError("emulator.exe not found")
        proc = popen_checked(
            [str(emulator), "-avd", avd_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
        cls._proc = proc
        cls._info = EmulatorInfo(avd=avd_name, started_at=time.time(), pid=proc.pid)
        return cls._info

    @classmethod
    def stop(cls) -> bool:
        adb = cls._adb_path()
        if adb.exists():
            run_checked(
                [str(adb), "emu", "kill"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        if cls._proc and cls._proc.poll() is None:
            cls._proc.terminate()
        cls._proc = None
        cls._info = None
        return True

    @classmethod
    def status(cls) -> dict[str, Any]:
        adb = cls._adb_path()
        running = False
        device = None
        if adb.exists():
            completed = run_checked(
                [str(adb), "devices"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in completed.stdout.splitlines():
                if line.startswith("emulator-") and "device" in line:
                    running = True
                    device = line.split()[0]
                    break
        return {
            "running": running,
            "device": device,
            "avd": cls._info.avd if cls._info else cls._avd_name(),
            "pid": cls._info.pid if cls._info else None,
            "mirror_running": cls._mirror_proc is not None and cls._mirror_proc.poll() is None,
        }

    @classmethod
    def start_mirror(cls, *, device: str | None = None) -> bool:
        if cls._mirror_proc and cls._mirror_proc.poll() is None:
            return True
        cmd = ["scrcpy", "--window-title", "Rebot Android Mirror", "--always-on-top"]
        if device:
            cmd.extend(["-s", device])
        try:
            cls._mirror_proc = popen_checked(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except FileNotFoundError:
            return False

    @classmethod
    def stop_mirror(cls) -> bool:
        if cls._mirror_proc and cls._mirror_proc.poll() is None:
            cls._mirror_proc.terminate()
        cls._mirror_proc = None
        return True

    @classmethod
    def list_devices(cls) -> list[dict[str, Any]]:
        """List all connected ADB devices with their status."""
        adb = cls._adb_path()
        devices: list[dict[str, Any]] = []
        if not adb.exists():
            return devices
        
        try:
            completed = run_checked(
                [str(adb), "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in completed.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("List of devices"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    status = parts[1]
                    model = ""
                    product = ""
                    for p in parts[2:]:
                        if p.startswith("model:"):
                            model = p.split(":", 1)[1]
                        elif p.startswith("product:"):
                            product = p.split(":", 1)[1]
                    devices.append({
                        "device_id": device_id,
                        "status": status,
                        "model": model,
                        "product": product,
                        "is_emulator": device_id.startswith("emulator-"),
                    })
        except Exception:
            pass
        
        return devices

    @classmethod
    def list_avds(cls) -> list[str]:
        """List available Android Virtual Devices."""
        emulator = cls._emulator_path()
        avds: list[str] = []
        if not emulator.exists():
            return avds
        
        try:
            completed = run_checked(
                [str(emulator), "-list-avds"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in completed.stdout.splitlines():
                line = line.strip()
                if line:
                    avds.append(line)
        except Exception:
            pass
        
        return avds

from __future__ import annotations

from app.core.settings import settings


class ClamAVScanner:
    def __init__(self) -> None:
        self._client = None
        if settings.clamav_host:
            try:
                import pyclamd

                self._client = pyclamd.ClamdNetworkSocket(
                    settings.clamav_host, settings.clamav_port or 3310
                )
            except Exception:
                self._client = None

    def scan_bytes(self, data: bytes) -> bool:
        if not self._client:
            return True
        result = self._client.scan_stream(data)
        return result is None


clamav = ClamAVScanner()

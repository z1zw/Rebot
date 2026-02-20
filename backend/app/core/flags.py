from __future__ import annotations

from app.core.settings import settings


class FeatureFlags:
    def __init__(self) -> None:
        self._client = None
        if settings.launchdarkly_sdk_key:
            import ldclient

            ldclient.set_sdk_key(settings.launchdarkly_sdk_key)
            self._client = ldclient.get()

    def enabled(self, key: str, user_key: str = "anonymous", default: bool = False) -> bool:
        if not self._client:
            return default
        user = {"key": user_key}
        return self._client.variation(key, user, default)


flags = FeatureFlags()

from __future__ import annotations

from piphi_runtime_kit_python import RuntimeConfig
from pydantic import Field, field_validator


class DeviceConfig(RuntimeConfig):
    host: str
    alias: str | None = None
    poll_interval_seconds: int = Field(default=10, ge=5, le=300)

    @field_validator("host")
    @classmethod
    def validate_host(cls, value: str) -> str:
        host = value.strip()
        if not host or "://" in host or "/" in host:
            raise ValueError("host must be a hostname or IP address without a URL scheme")
        return host

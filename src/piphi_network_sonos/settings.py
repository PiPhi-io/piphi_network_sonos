from __future__ import annotations

import os
from importlib.metadata import version

INTEGRATION_ID = "piphi-network-sonos"
INTEGRATION_NAME = "Sonos"
INTEGRATION_VERSION = version("piphi-network-sonos")
PROJECT_KIND = "integration"
PROJECT_PRESET = "actuator-device"
PROJECT_DOMAIN = "local-device"
DEFAULT_PORT = 8090


def runtime_port() -> int:
    raw_port = os.getenv("PORT", str(DEFAULT_PORT))
    try:
        return int(raw_port)
    except ValueError:
        return DEFAULT_PORT

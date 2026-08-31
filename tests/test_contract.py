from __future__ import annotations

from piphi_network_sonos.contract import COMMANDS, REQUIRED_ENDPOINTS
from piphi_network_sonos.main import app
import json
from pathlib import Path

from piphi_network_sonos.contract import CAPABILITIES
from piphi_network_sonos.settings import INTEGRATION_VERSION


def test_runtime_implements_contract_routes() -> None:
    routes = set(app.openapi()["paths"])
    for path in [
        "/health",
        "/diagnostics",
        "/discover",
        "/config",
        "/config/sync",
        "/deconfigure",
        "/deconfigure/{config_id}",
        "/ui-config",
        "/entities",
        "/state",
        "/contract",
        "/events",
        "/events/device/{config_id}/example",
        "/telemetry/example",
        "/telemetry/device/{config_id}/example",
        "/command",
    ]:
        assert path in routes

    assert REQUIRED_ENDPOINTS == ["health", "entities", "command", "config", "ui_config"]
    assert "refresh" in COMMANDS


def test_manifest_stays_in_sync_with_runtime_contract() -> None:
    manifest = json.loads((Path(__file__).parents[1] / "manifest.json").read_text())
    assert manifest["capabilities"] == CAPABILITIES
    assert manifest["commands"] == COMMANDS
    assert manifest["version"] == INTEGRATION_VERSION
    assert manifest["marketplace"]["governance"]["publication_status"] == "draft"

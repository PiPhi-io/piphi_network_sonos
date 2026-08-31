from __future__ import annotations

from fastapi import APIRouter
from piphi_runtime_kit_python import (
    IntegrationDiscoveryRequest,
    build_discovery_response,
    normalize_discovery_inputs,
)

from ..contract import CONFIG_SCHEMA
from ..sonos_client import discover_speakers

router = APIRouter(tags=["discovery"])


@router.post("/discover")
async def discover(payload: IntegrationDiscoveryRequest | None = None):
    inputs = normalize_discovery_inputs(payload.inputs if payload else None)
    timeout = max(1, min(int(inputs.get("timeout", 5)), 15))
    speakers = await discover_speakers(timeout=timeout, interface_addr=inputs.get("interface_addr"))
    return build_discovery_response([{
        "id": speaker.uid, "device_id": speaker.uid, "host": speaker.host,
        "alias": speaker.name, "name": speaker.name, "model_name": speaker.model_name,
        "household_id": speaker.household_id,
    } for speaker in speakers])


@router.get("/ui-config")
async def ui_config():
    return CONFIG_SCHEMA

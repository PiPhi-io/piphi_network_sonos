from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ..contract import FALLBACK_ENTITY
from ..state import capabilities, commands, registry

router = APIRouter(tags=["entities"])


@router.get("/entities")
async def entities() -> dict[str, Any]:
    entries = list(registry.entries.values())
    runtime_entities = [
        {
            "id": entry["device_id"],
            "name": entry.get("alias") or entry.get("device_info", {}).get("player_name") or "Sonos speaker",
            "config_id": entry["config_id"],
            "device_id": entry["device_id"],
            "entity_type": FALLBACK_ENTITY["entity_type"],
            "device_class": FALLBACK_ENTITY["device_class"],
            "metadata": {"host": entry.get("host"), **entry.get("device_info", {})},
            "capabilities": FALLBACK_ENTITY["capabilities"],
            "available_commands": FALLBACK_ENTITY["available_commands"],
            "dashboard": FALLBACK_ENTITY["dashboard"],
        }
        for entry in entries
    ] or [FALLBACK_ENTITY]
    return {"entities": runtime_entities, "capabilities": capabilities, "commands": commands}

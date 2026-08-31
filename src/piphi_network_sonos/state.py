from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException
from piphi_runtime_kit_python import (
    AutomationRegistry, SQLiteAutomationIdempotencyStore, build_local_event_record,
    build_runtime_identity, create_runtime_starter,
)

from .contract import CAPABILITIES, COMMANDS
from .schemas import DeviceConfig
from .service import SonosRuntimeService
from .settings import INTEGRATION_ID, INTEGRATION_NAME, INTEGRATION_VERSION

starter = create_runtime_starter(integration_id=INTEGRATION_ID, integration_name=INTEGRATION_NAME, version=INTEGRATION_VERSION)
runtime = starter.runtime
registry = starter.registry
telemetry = starter.telemetry_client
config_sync = starter.config_sync
automations = AutomationRegistry(idempotency_store=SQLiteAutomationIdempotencyStore(
    os.getenv("PIPHI_AUTOMATION_LEDGER_PATH", "./data/automation-actions.sqlite3")
))
service = SonosRuntimeService(registry=registry, runtime=runtime, telemetry=telemetry)
capabilities = CAPABILITIES
commands = COMMANDS


def make_entry(config: DeviceConfig) -> dict[str, Any]:
    identity = build_runtime_identity(config, integration_id=INTEGRATION_ID)
    return {**identity, "host": config.host, "alias": config.alias, "config": config.model_dump(mode="json")}


def append_runtime_event(event_type: str, device: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    event = build_local_event_record(event_type=event_type, device=device, payload=payload or {}, source=INTEGRATION_ID, severity="info")
    registry.append_event(event)
    return event


def get_entry_or_404(config_id: str) -> dict[str, Any]:
    entry = registry.get(config_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"unknown config_id={config_id}")
    return entry


async def apply_config(config: DeviceConfig) -> None:
    entry = make_entry(config)
    await service.configure(config, entry)
    append_runtime_event("runtime.config.applied", entry, {"host": config.host, "alias": config.alias})


async def remove_config(config_id: str) -> bool:
    entry = registry.get(config_id)
    removed = await service.remove(config_id)
    if removed and entry:
        append_runtime_event("runtime.config.removed", entry, {"host": entry.get("host"), "alias": entry.get("alias")})
    return removed


def _register_automation_actions() -> None:
    for command_name, command_definition in commands.items():
        async def handler(request, *, _command_name=command_name):
            target = request.target if isinstance(request.target, dict) else {}
            config_id = str(request.config_id or target.get("config_id") or request.device_id or "")
            result = await service.execute(config_id, _command_name, request.args)
            entry = get_entry_or_404(config_id)
            result["event"] = append_runtime_event("runtime.command.completed", entry, {"command": _command_name, "params": request.args})
            return result

        automations.action(command_name, label=str(command_definition.get("description") or command_name))(handler)


_register_automation_actions()

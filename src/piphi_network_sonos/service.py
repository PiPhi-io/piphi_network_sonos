from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from piphi_runtime_kit_python import schedule_telemetry_delivery

from .schemas import DeviceConfig
from .sonos_client import SoCoSpeakerClient, SonosClient
from .contract import CAPABILITIES


@dataclass(slots=True)
class ActiveSpeaker:
    config: DeviceConfig
    entry: dict[str, Any]
    client: SonosClient
    task: asyncio.Task[None] | None = None


class SonosRuntimeService:
    def __init__(self, *, registry, runtime, telemetry, client_factory: Callable[[str], SonosClient] = SoCoSpeakerClient):
        self.registry = registry
        self.runtime = runtime
        self.telemetry = telemetry
        self.client_factory = client_factory
        self._sessions: dict[str, ActiveSpeaker] = {}
        self._lock = asyncio.Lock()

    def set_client_factory(self, factory: Callable[[str], SonosClient]) -> None:
        self.client_factory = factory

    async def configure(self, config: DeviceConfig, entry: dict[str, Any]) -> None:
        config_id = str(entry["config_id"])
        async with self._lock:
            await self._remove_locked(config_id)
            session = ActiveSpeaker(config=config, entry=entry, client=self.client_factory(config.host))
            self._sessions[config_id] = session
            self.registry.set(config_id, entry)
            try:
                await self._refresh_session(session)
            except Exception as exc:
                self.registry.update_state(config_id, {
                    "connected": False, "host": config.host, "error": str(exc),
                }, device_id=str(entry["device_id"]))
            session.task = asyncio.create_task(self._poll(session), name=f"sonos-poll-{config_id}")

    async def remove(self, config_id: str) -> bool:
        async with self._lock:
            existed = config_id in self._sessions or self.registry.get(config_id) is not None
            await self._remove_locked(config_id)
            self.registry.remove(config_id)
            return existed

    async def _remove_locked(self, config_id: str) -> None:
        session = self._sessions.pop(config_id, None)
        if session and session.task and session.task is not asyncio.current_task():
            session.task.cancel()
            with suppress(asyncio.CancelledError):
                await session.task

    async def close(self) -> None:
        async with self._lock:
            for config_id in list(self._sessions):
                await self._remove_locked(config_id)

    async def refresh(self, config_id: str) -> dict[str, Any]:
        session = self._sessions.get(config_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"unknown config_id={config_id}")
        return await self._refresh_session(session)

    async def execute(self, config_id: str, command: str, params: dict[str, Any]) -> dict[str, Any]:
        session = self._sessions.get(config_id)
        if session is None:
            raise HTTPException(status_code=404, detail=f"unknown config_id={config_id}")
        try:
            await session.client.command(command, params)
            state = await self._refresh_session(session)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Sonos command failed: {exc}") from exc
        return {"command": command, "config_id": config_id, "device_id": session.entry["device_id"], "state": state}

    async def _poll(self, session: ActiveSpeaker) -> None:
        while self._sessions.get(str(session.entry["config_id"])) is session:
            await asyncio.sleep(session.config.poll_interval_seconds)
            try:
                await self._refresh_session(session)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.registry.update_state(str(session.entry["config_id"]), {
                    "connected": False, "host": session.config.host, "error": str(exc),
                }, device_id=str(session.entry["device_id"]))

    async def _refresh_session(self, session: ActiveSpeaker) -> dict[str, Any]:
        state = await session.client.snapshot()
        config_id = str(session.entry["config_id"])
        device_id = str(session.entry["device_id"])
        session.entry["device_info"] = {
            key: state.get(key) for key in ("uid", "player_name", "model_name", "serial_number", "software_version")
            if state.get(key) is not None
        }
        self.registry.update_state(config_id, state, device_id=device_id)
        metrics = {
            key: value for key, value in state.items()
            if CAPABILITIES.get(key, {}).get("kind") == "sensor" and isinstance(value, (bool, int, float, str))
        }
        schedule_telemetry_delivery(
            process_state=self.runtime.process_state, telemetry_client=self.telemetry,
            auth_context=self.runtime.auth, config_id=config_id, device_id=device_id,
            container_id=session.entry.get("container_id"), metrics=metrics,
            units={"volume_percent": "%", "position_seconds": "s", "duration_seconds": "s"},
        )
        return state

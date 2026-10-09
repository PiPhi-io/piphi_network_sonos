from __future__ import annotations

from typing import Any

import httpx
import pytest
from piphi_runtime_testkit_python import assert_entities_response, build_config_payload

from piphi_network_sonos.main import app
from piphi_network_sonos.state import registry, service


class FakeSpeaker:
    def __init__(self, _host: str):
        self.state = {"playback_state": "paused_playback", "volume_percent": 18, "muted": False}
        self.commands: list[tuple[str, dict[str, Any]]] = []

    async def snapshot(self) -> dict[str, Any]:
        return {
            "connected": True, "uid": "RINCON_0001", "player_name": "Living Room",
            "model_name": "Sonos One", "track_title": "A Song", "artist": "An Artist",
            "album": "An Album", "album_art_uri": "", "position_seconds": 30,
            "duration_seconds": 180, "group_id": "RINCON_GROUP:1", **self.state,
        }

    async def command(self, name: str, params: dict[str, Any]) -> None:
        self.commands.append((name, params))
        if name == "play":
            self.state["playback_state"] = "playing"
        if name == "set_volume":
            value = int(params["volume"])
            if not 0 <= value <= 100:
                raise ValueError("volume must be between 0 and 100")
            self.state["volume_percent"] = value
        if name == "play_media":
            self.state["playback_state"] = "playing"
            self.state["track_title"] = str(params.get("title") or "Library audio")


@pytest.mark.anyio
async def test_core_config_entities_state_and_commands_round_trip() -> None:
    created: list[FakeSpeaker] = []

    def factory(host: str) -> FakeSpeaker:
        speaker = FakeSpeaker(host)
        created.append(speaker)
        return speaker

    service.set_client_factory(factory)
    payload = build_config_payload(
        config_id="sonos-living-room", device_id="RINCON_0001",
        extra={"host": "192.0.2.10", "alias": "Living Room", "poll_interval_seconds": 300},
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://core-test") as client:
        response = await client.post("/config", json=payload)
        assert response.status_code == 200
        assert response.json()["config_id"] == "sonos-living-room"

        entities = (await client.get("/entities")).json()
        assert_entities_response(entities)
        [entity] = entities["entities"]
        assert entity["entity_type"] == "media_player"
        assert entity["dashboard"]["default_widget"] == "media-control"

        command = await client.post("/command", json={
            "contract_version": "automation.runtime.command.v1", "command": "set_volume",
            "target": {"config_id": "sonos-living-room", "device_id": "RINCON_0001"},
            "params": {"volume": 42}, "capability": "action.set_volume",
        })
        assert command.status_code == 200
        assert command.json()["state"]["volume_percent"] == 42

        media_command = await client.post("/command", json={
            "contract_version": "automation.runtime.command.v1", "command": "play_media",
            "target": {"config_id": "sonos-living-room", "device_id": "RINCON_0001"},
            "params": {
                "uri": "http://core.test/api/v2/media/library/stream/lib_track?expires=9999999999&signature=" + "a" * 64,
                "source": "piphi-library", "mime_type": "audio/mpeg", "title": "Library Track",
            },
            "capability": "action.play_media",
        })
        assert media_command.status_code == 200
        assert media_command.json()["state"]["track_title"] == "Library Track"

        state = (await client.get("/state")).json()
        assert state["state_snapshots"]["sonos-living-room"]["state"]["volume_percent"] == 42

    assert created[0].commands[0] == ("set_volume", {"volume": 42})
    assert created[0].commands[1][0] == "play_media"
    await service.close()
    registry.entries.clear()
    registry.state_snapshots.clear()


@pytest.mark.anyio
async def test_invalid_volume_is_rejected_without_hiding_vendor_error() -> None:
    speaker = FakeSpeaker("192.0.2.11")
    service.set_client_factory(lambda _host: speaker)
    payload = build_config_payload(config_id="sonos-office", extra={"host": "192.0.2.11", "poll_interval_seconds": 300})
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://core-test") as client:
        await client.post("/config", json=payload)
        response = await client.post("/command", json={
            "contract_version": "automation.runtime.command.v1", "command": "set_volume",
            "target": {"config_id": "sonos-office", "device_id": "sonos-office"},
            "params": {"volume": 120}, "capability": "action.set_volume",
        })
        assert response.status_code in {200, 422}
        body = response.json()
        assert "between 0 and 100" in str(body)
    await service.close()
    registry.entries.clear()
    registry.state_snapshots.clear()

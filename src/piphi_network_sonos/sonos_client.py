from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import parse_qs, urlsplit


def _seconds(value: Any) -> int:
    try:
        parts = [int(part) for part in str(value or "0").split(":")]
    except ValueError:
        return 0
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


def _validate_library_media_uri(params: dict[str, Any]) -> tuple[str, str]:
    if str(params.get("source") or "").strip() != "piphi-library":
        raise ValueError("play_media only accepts PiPhi Library streams")
    uri = str(params.get("uri") or "").strip()
    if not uri or len(uri) > 4096:
        raise ValueError("a valid PiPhi Library stream URI is required")
    parsed = urlsplit(uri)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
        or not re.search(r"/api/[^/]+/media/library/stream/[^/]+$", parsed.path)
    ):
        raise ValueError("a valid PiPhi Library stream URI is required")
    query = parse_qs(parsed.query)
    expires_values = query.get("expires", [])
    signatures = query.get("signature", [])
    try:
        expires_at = int(expires_values[0]) if len(expires_values) == 1 else 0
    except (TypeError, ValueError):
        expires_at = 0
    signature = signatures[0] if len(signatures) == 1 else ""
    now = int(time.time())
    if expires_at < now or expires_at > now + 3600:
        raise ValueError("PiPhi Library stream URI is expired")
    if not re.fullmatch(r"[0-9a-f]{64}", signature):
        raise ValueError("PiPhi Library stream URI signature is invalid")
    mime_type = str(params.get("mime_type") or "").strip().lower()
    if mime_type and not mime_type.startswith("audio/"):
        raise ValueError("play_media only supports audio content")
    title = str(params.get("title") or "").strip()[:512]
    return uri, title


@dataclass(frozen=True, slots=True)
class DiscoveredSpeaker:
    uid: str
    host: str
    name: str
    model_name: str | None = None
    household_id: str | None = None


class SonosClient(Protocol):
    async def snapshot(self) -> dict[str, Any]: ...
    async def command(self, name: str, params: dict[str, Any]) -> None: ...


class SoCoSpeakerClient:
    """Async boundary around SoCo's blocking local UPnP API."""

    def __init__(self, host: str):
        from soco import SoCo

        self._speaker = SoCo(host)

    async def snapshot(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._snapshot_sync)

    def _snapshot_sync(self) -> dict[str, Any]:
        speaker = self._speaker
        info = speaker.get_speaker_info()
        transport = speaker.get_current_transport_info()
        track = speaker.get_current_track_info()
        group = speaker.group
        art = track.get("album_art") or ""
        if art and art.startswith("/"):
            art = speaker.get_album_art_full_uri(art)
        return {
            "connected": True,
            "uid": speaker.uid,
            "player_name": speaker.player_name,
            "model_name": info.get("model_name"),
            "serial_number": info.get("serial_number"),
            "software_version": info.get("software_version"),
            "playback_state": str(transport.get("current_transport_state") or "UNKNOWN").lower(),
            "volume_percent": int(speaker.volume),
            "muted": bool(speaker.mute),
            "track_title": track.get("title") or "",
            "artist": track.get("artist") or "",
            "album": track.get("album") or "",
            "album_art_uri": art,
            "position_seconds": _seconds(track.get("position")),
            "duration_seconds": _seconds(track.get("duration")),
            "group_id": group.uid,
            "group_coordinator_uid": group.coordinator.uid,
            "is_coordinator": group.coordinator.uid == speaker.uid,
        }

    async def command(self, name: str, params: dict[str, Any]) -> None:
        await asyncio.to_thread(self._command_sync, name, params)

    def _command_sync(self, name: str, params: dict[str, Any]) -> None:
        speaker = self._speaker
        if name in {"play", "pause", "stop", "next", "previous"}:
            getattr(speaker, name)()
        elif name == "play_media":
            uri, title = _validate_library_media_uri(params)
            if title:
                speaker.play_uri(uri, title=title)
            else:
                speaker.play_uri(uri)
        elif name == "set_volume":
            volume = int(params.get("volume", params.get("value", -1)))
            if not 0 <= volume <= 100:
                raise ValueError("volume must be between 0 and 100")
            speaker.volume = volume
        elif name == "set_mute":
            value = params.get("muted", params.get("value"))
            if not isinstance(value, bool):
                raise ValueError("muted must be a boolean")
            speaker.mute = value
        elif name == "join_group":
            host = str(params.get("coordinator_host") or "").strip()
            if not host:
                raise ValueError("coordinator_host is required")
            from soco import SoCo
            speaker.join(SoCo(host))
        elif name == "leave_group":
            speaker.unjoin()
        elif name != "refresh":
            raise ValueError(f"unsupported Sonos command: {name}")


async def discover_speakers(*, timeout: int = 5, interface_addr: str | None = None) -> list[DiscoveredSpeaker]:
    def discover_sync() -> list[DiscoveredSpeaker]:
        from soco import discover

        speakers = discover(timeout=timeout, interface_addr=interface_addr) or set()
        result = []
        for speaker in speakers:
            info = speaker.get_speaker_info()
            result.append(DiscoveredSpeaker(
                uid=speaker.uid, host=speaker.ip_address, name=speaker.player_name,
                model_name=info.get("model_name"), household_id=getattr(speaker, "household_id", None),
            ))
        return sorted(result, key=lambda item: (item.name.lower(), item.uid))

    return await asyncio.to_thread(discover_sync)

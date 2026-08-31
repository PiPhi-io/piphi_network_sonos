from __future__ import annotations

from typing import Any

ENDPOINTS = {
    "health": "/health", "diagnostics": "/diagnostics", "discover": "/discover",
    "entities": "/entities", "state": "/state", "config": "/config",
    "config_sync": "/config/sync", "deconfigure": "/deconfigure",
    "ui_config": "/ui-config", "events": "/events", "command": "/command",
}
REQUIRED_ENDPOINTS = ["health", "entities", "command", "config", "ui_config"]

CAPABILITIES: dict[str, dict[str, Any]] = {
    "connected": {"kind": "sensor", "unit": "bool"},
    "playback_state": {"kind": "sensor", "unit": "state", "dashboard": {
        "allowed_widgets": ["media-control", "external-widget", "text"],
        "default_widget": "media-control", "recommended_widgets": ["external-widget"],
    }},
    "volume_percent": {"kind": "sensor", "unit": "%"},
    "muted": {"kind": "sensor", "unit": "bool"},
    "track_title": {"kind": "sensor", "unit": "text"},
    "artist": {"kind": "sensor", "unit": "text"},
    "album": {"kind": "sensor", "unit": "text"},
    "album_art_uri": {"kind": "sensor", "unit": "url"},
    "position_seconds": {"kind": "sensor", "unit": "s"},
    "duration_seconds": {"kind": "sensor", "unit": "s"},
    "group_id": {"kind": "sensor", "unit": "text"},
    **{name: {"kind": "action"} for name in (
        "refresh", "play", "pause", "stop", "next", "previous",
        "set_volume", "set_mute", "join_group", "leave_group",
    )},
}

COMMANDS: dict[str, dict[str, Any]] = {
    "refresh": {"description": "Refresh speaker state.", "timeout_ms": 10000},
    "play": {"description": "Resume playback.", "timeout_ms": 10000},
    "pause": {"description": "Pause playback.", "timeout_ms": 10000},
    "stop": {"description": "Stop playback.", "timeout_ms": 10000},
    "next": {"description": "Skip to the next queue item.", "timeout_ms": 10000},
    "previous": {"description": "Return to the previous queue item.", "timeout_ms": 10000},
    "set_volume": {"description": "Set volume from 0 to 100.", "timeout_ms": 10000},
    "set_mute": {"description": "Mute or unmute the speaker.", "timeout_ms": 10000},
    "join_group": {"description": "Join another Sonos coordinator by host.", "timeout_ms": 15000},
    "leave_group": {"description": "Leave the current Sonos group.", "timeout_ms": 15000},
}

CONFIG_SCHEMA: dict[str, Any] = {
    "schema": {
        "title": "Sonos speaker setup",
        "description": "Choose a discovered speaker or enter its local IP address. No Sonos cloud account is required.",
        "type": "object", "required": ["host"],
        "properties": {
            "host": {"type": "string", "title": "Speaker IP address or hostname"},
            "alias": {"type": "string", "title": "Display name"},
            "poll_interval_seconds": {"type": "integer", "title": "State refresh interval", "minimum": 5, "maximum": 300, "default": 10},
        },
    },
    "uiSchema": {"host": {"placeholder": "192.168.1.50"}, "alias": {"placeholder": "Living Room"}},
}

SPEAKER_CAPABILITIES = list(CAPABILITIES)
AVAILABLE_COMMANDS = [
    {"id": command_id, "label": definition["description"].rstrip("."), "kind": "action"}
    for command_id, definition in COMMANDS.items()
]
FALLBACK_ENTITY: dict[str, Any] = {
    "id": "sonos-speaker", "name": "Sonos speaker", "device_id": "sonos-speaker",
    "device_class": "speaker", "entity_type": "media_player",
    "capabilities": SPEAKER_CAPABILITIES, "available_commands": AVAILABLE_COMMANDS,
    "dashboard": {"allowed_widgets": ["media-control", "external-widget", "tile"], "default_widget": "media-control", "recommended_widgets": ["external-widget"]},
}

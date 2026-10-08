from __future__ import annotations

import time

import pytest

from piphi_network_sonos.sonos_client import (
    SoCoSpeakerClient,
    _seconds,
    _validate_library_media_uri,
)


def test_sonos_time_values_are_normalized_for_core() -> None:
    assert _seconds("01:02:03") == 3723
    assert _seconds("04:05") == 245
    assert _seconds("NOT_IMPLEMENTED") == 0


def test_command_validation_happens_before_sonos_mutation() -> None:
    class Speaker:
        volume = 25
        mute = False

    client = object.__new__(SoCoSpeakerClient)
    client._speaker = Speaker()

    with pytest.raises(ValueError, match="between 0 and 100"):
        client._command_sync("set_volume", {"volume": 101})
    with pytest.raises(ValueError, match="must be a boolean"):
        client._command_sync("set_mute", {"muted": "yes"})
    with pytest.raises(ValueError, match="coordinator_host is required"):
        client._command_sync("join_group", {})


def _signed_library_uri(*, expires: int | None = None, signature: str | None = None) -> str:
    return (
        "http://192.0.2.2:31419/api/v2/media/library/stream/lib_track"
        f"?expires={expires or int(time.time()) + 900}"
        f"&signature={signature or 'a' * 64}"
    )


def test_play_media_accepts_only_bounded_signed_library_audio_urls() -> None:
    uri = _signed_library_uri()
    assert _validate_library_media_uri(
        {
            "uri": uri,
            "source": "piphi-library",
            "mime_type": "audio/flac",
            "title": "Night Drive",
        }
    ) == (uri, "Night Drive")

    with pytest.raises(ValueError, match="only accepts PiPhi Library"):
        _validate_library_media_uri({"uri": uri, "source": "external"})
    with pytest.raises(ValueError, match="valid PiPhi Library"):
        _validate_library_media_uri(
            {
                "uri": "https://example.com/song.mp3",
                "source": "piphi-library",
            }
        )
    with pytest.raises(ValueError, match="expired"):
        _validate_library_media_uri(
            {
                "uri": _signed_library_uri(expires=int(time.time()) - 1),
                "source": "piphi-library",
            }
        )
    with pytest.raises(ValueError, match="only supports audio"):
        _validate_library_media_uri(
            {
                "uri": uri,
                "source": "piphi-library",
                "mime_type": "video/mp4",
            }
        )


def test_play_media_dispatches_to_soco_play_uri() -> None:
    calls: list[tuple[str, str]] = []

    class Speaker:
        def play_uri(self, uri: str, title: str = "") -> None:
            calls.append((uri, title))

    client = object.__new__(SoCoSpeakerClient)
    client._speaker = Speaker()
    uri = _signed_library_uri()
    client._command_sync(
        "play_media",
        {
            "uri": uri,
            "source": "piphi-library",
            "mime_type": "audio/mpeg",
            "title": "A Song",
        },
    )

    assert calls == [(uri, "A Song")]

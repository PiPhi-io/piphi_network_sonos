from __future__ import annotations

import pytest

from piphi_network_sonos.sonos_client import SoCoSpeakerClient, _seconds


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

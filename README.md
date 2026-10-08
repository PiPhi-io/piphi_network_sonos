# PiPhi Network Sonos

PiPhi runtime integration for discovering and controlling Sonos speakers on the local network. It uses [SoCo](https://github.com/SoCo/SoCo), requires no Sonos cloud account, and supports reachable Sonos S1 and S2 systems.

## Features

- SSDP discovery with stable Sonos `RINCON_*` IDs
- Playback, queue navigation, volume, mute, and group controls
- Track, album art, playback position, group, and connectivity state
- Poll-based telemetry without inbound UPnP callback ports
- Core contract, config-sync, automation command, and mock-device tests
- Sandboxed “Sonos now playing” dashboard widget with explicit command permissions
- Signed, short-lived PiPhi Media Library audio handoff through `play_media`

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
uvicorn piphi_network_sonos.main:app --host 0.0.0.0 --port 8090
```

Run the runtime on the same LAN/VLAN as the speakers. Docker uses host networking because SSDP multicast does not reliably traverse a normal container bridge. A known speaker IP can still be configured when multicast is filtered.

```bash
curl -X POST http://127.0.0.1:8090/discover -H 'content-type: application/json' -d '{"inputs":{"timeout":5}}'
```

## Widget

```bash
cd widgets/sonos-now-playing
npm install
npm run build
npm test
npm run conformance
```

See [docs/library-evaluation.md](docs/library-evaluation.md) for the library decision, network constraints, deferred features, and hardware qualification plan.

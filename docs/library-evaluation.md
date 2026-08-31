# Sonos library evaluation

Evaluated on 2026-08-31 for a local PiPhi Core runtime.

## Decision

Use Python [SoCo](https://github.com/SoCo/SoCo) `>=0.31.2,<0.32.0` behind an integration-owned async adapter. SoCo has the broader Sonos control surface, stable speaker identity and topology APIs, event support for future work, recent 2026 releases, and the same language as PiPhi's mature runtime SDK and testkit. The adapter runs blocking calls in worker threads, keeping FastAPI responsive and making vendor I/O replaceable in tests.

| Area | SoCo (Python) | `sonos` / node-sonos |
| --- | --- | --- |
| Latest observed release | 0.31.2, 2026-07-29 | 1.14.3, 2026-02-27 |
| License | MIT | MIT |
| Discovery | SSDP and optional directed/network-scan paths | Event and async SSDP discovery |
| Identity/topology | UID, household, coordinator, members | Host and `getAllGroups()` |
| Controls | Playback, queue, groups, alarms, EQ, inputs, library, favorites | Playback, queue, volume, groups, alarms, radio helpers |
| PiPhi fit | Python Runtime SDK/testkit; requires thread offload | Async JavaScript, narrower runtime surface |

Sources: [SoCo repository](https://github.com/SoCo/SoCo), [SoCo PyPI](https://pypi.org/project/soco/), [discovery API](https://docs.python-soco.com/en/latest/api/soco.discovery.html), [topology guide](https://docs.python-soco.com/en/latest/advanced/topology.html), [node-sonos package](https://www.npmjs.com/package/sonos), and [node-sonos repository](https://github.com/bencevans/node-sonos).

## Platform behavior and scope

- Both libraries use local IPv4 UPnP, not the Sonos cloud Control API.
- SSDP multicast motivates host networking; manual IP configuration is the fallback.
- Local control works offline, while selected music services may still require internet and their own Sonos authentication.
- SoCo warns that music-service browsing/authentication may break as Sonos changes service authentication. Version 0.1 controls the current speaker and queue without handling music-service credentials.
- Playback may be group/coordinator-sensitive. State includes group and coordinator identity.
- Although SoCo supports push subscriptions, they need an inbound listener and renewal lifecycle. Initial state sync polls for simpler, deterministic deployment.
- Recently powered-off devices may briefly remain in topology; runtime health is authoritative.

Version 0.1 reads connectivity, identity, playback, volume, mute, track metadata, progress, and grouping. It implements refresh, play, pause, stop, previous, next, volume, mute, join, and leave. Queue editing, favorites, alarms, timers, EQ, TV/line-in, library browsing, music-service search, snapshots, and push subscriptions are deferred.

## Verification

Automated tests cover manifest/contract drift, Core config payloads, entity metadata, state normalization, command dispatch, validation failures, and Widget SDK conformance through a fake `SonosClient`.

Before promoting registry governance beyond `draft/unverified`, test an S1 and S2 household; standalone, stereo, and grouped players; queue/radio/TV/idle sources; reboot, IP change, Wi-Fi loss, and coordinator changes; Core restart/config sync; and host-network discovery. Automated passing proves Core contract compatibility, not real-hardware qualification.

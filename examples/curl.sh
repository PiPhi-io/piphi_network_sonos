#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8090}"

curl -sS "$BASE_URL/health"
curl -sS "$BASE_URL/diagnostics"
curl -sS "$BASE_URL/ui-config"
curl -sS -X POST "$BASE_URL/discover" -H 'content-type: application/json' -d '{"inputs":{"timeout":5}}'
curl -sS -X POST "$BASE_URL/config" -H 'content-type: application/json' -d '{"id":"sonos-living-room","device_id":"RINCON_00000000000101400","host":"192.0.2.10","alias":"Living Room"}'
curl -sS "$BASE_URL/entities"
curl -sS -X POST "$BASE_URL/command" -H 'content-type: application/json' -d '{"contract_version":"automation.runtime.command.v1","command":"set_volume","target":{"config_id":"sonos-living-room","device_id":"RINCON_00000000000101400"},"params":{"volume":35},"capability":"action.set_volume","capability_requirements":["action.set_volume"]}'

import assert from "node:assert/strict";
import test from "node:test";
import manifest from "../widget.manifest.json" with { type: "json" };
import { validateWidgetManifest } from "piphi-network-widget-sdk/manifest";

test("widget manifest conforms to the PiPhi Widget SDK", () => {
  assert.deepEqual(validateWidgetManifest(manifest).filter((item) => item.severity === "error"), []);
});

test("control commands are explicitly permissioned", () => {
  assert.ok(manifest.security.permissions.includes("host.executeCommand"));
  for (const command of ["play", "pause", "set_volume", "set_mute"]) assert.ok(manifest.security.allowed_commands.includes(command));
});

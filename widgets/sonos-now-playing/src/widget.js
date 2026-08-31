import { getInjectedPiPhiWidgetHost } from "piphi-network-widget-sdk";

const host = getInjectedPiPhiWidgetHost();
const root = document.querySelector("#piphi-widget-root") || document.body;
const context = await host.getContext();
const settings = await host.getSettings();
const translatedTitle = await host.translate("widget.title");

root.innerHTML = `
  <style>
    :root { color-scheme: light dark; font: 14px/1.35 system-ui, sans-serif; }
    * { box-sizing: border-box; }
    main { min-height: 320px; padding: 18px; color: CanvasText; background: Canvas; }
    h2 { margin: 0 0 14px; font-size: 1rem; }
    .now { display: grid; grid-template-columns: 112px 1fr; gap: 16px; align-items: center; }
    .art { width: 112px; aspect-ratio: 1; border-radius: 16px; object-fit: cover; background: color-mix(in srgb, CanvasText 8%, Canvas); }
    .art[hidden] { display: none; }
    .track { min-width: 0; }
    .title, .artist, .album { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .title { font-size: 1.2rem; font-weight: 750; }
    .artist { margin-top: 4px; }
    .album, [role=status] { opacity: .65; }
    .progress { width: 100%; accent-color: #7657d6; }
    .times { display: flex; justify-content: space-between; font-variant-numeric: tabular-nums; font-size: .78rem; opacity: .65; }
    .controls { display: flex; justify-content: center; align-items: center; gap: 8px; margin: 18px 0; }
    button { min-width: 42px; min-height: 42px; border: 1px solid color-mix(in srgb, CanvasText 20%, transparent); border-radius: 999px; background: Canvas; color: CanvasText; cursor: pointer; }
    button:focus-visible, input:focus-visible { outline: 3px solid #7657d6; outline-offset: 2px; }
    button.primary { min-width: 52px; min-height: 52px; color: white; background: #7657d6; border: 0; }
    .volume { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 10px; }
    @media (max-width: 360px) { .now { grid-template-columns: 82px 1fr; } .art { width: 82px; } }
  </style>
  <main dir="${escapeHtml(context.localization?.direction || "ltr")}">
    <h2>${escapeHtml(String(settings.title || translatedTitle))}</h2>
    <section class="now" aria-live="polite">
      <img class="art" alt="" hidden>
      <div class="track"><div class="title">—</div><div class="artist">—</div><div class="album">—</div></div>
    </section>
    <input class="progress" type="range" min="0" max="1" value="0" disabled aria-label="Playback progress">
    <div class="times"><span class="position">0:00</span><span class="duration">0:00</span></div>
    <div class="controls" aria-label="Playback controls">
      <button data-command="previous" aria-label="Previous track">⏮</button>
      <button class="primary" data-command="play_pause" aria-label="Play">▶</button>
      <button data-command="next" aria-label="Next track">⏭</button>
      <button data-command="stop" aria-label="Stop">⏹</button>
    </div>
    <div class="volume"><button data-command="mute" aria-label="Mute">🔊</button><input class="volume-slider" type="range" min="0" max="100" value="0" aria-label="Volume"><output>0%</output></div>
    <p role="status">loading</p>
  </main>`;

let state = {};
const status = root.querySelector("[role=status]");
const playPause = root.querySelector('[data-command="play_pause"]');
const volume = root.querySelector(".volume-slider");

for (const button of root.querySelectorAll("button[data-command]")) {
  button.addEventListener("click", async () => {
    const token = button.dataset.command;
    const commandName = token === "play_pause" ? (state.playback_state === "playing" ? "pause" : "play") : token === "mute" ? "set_mute" : token;
    const args = token === "mute" ? { muted: !Boolean(state.muted) } : {};
    await runCommand(commandName, args);
  });
}
volume.addEventListener("change", () => runCommand("set_volume", { volume: Number(volume.value) }));

const stop = await host.subscribeState(
  { capabilityIds: ["playback_state", "volume_percent", "muted", "track_title", "artist", "album", "album_art_uri", "position_seconds", "duration_seconds"] },
  (event) => {
    status.textContent = event.status || event.kind;
    if (event.kind !== "snapshot" && event.kind !== "point") return;
    state = { ...state, ...extractState(event.data) };
    render();
  },
);
window.addEventListener("pagehide", stop, { once: true });
await host.ready({ height: 340 });

async function runCommand(commandName, args) {
  status.textContent = "working";
  try { await host.executeCommand({ commandName, args }); status.textContent = "live"; }
  catch (error) { status.textContent = error?.message || "Command failed"; }
}

function render() {
  root.querySelector(".title").textContent = state.track_title || "Nothing playing";
  root.querySelector(".artist").textContent = state.artist || "Sonos";
  root.querySelector(".album").textContent = state.album || "";
  const art = root.querySelector(".art");
  art.hidden = settings.show_album_art === false || !state.album_art_uri;
  if (!art.hidden) art.src = state.album_art_uri;
  const position = Number(state.position_seconds || 0), duration = Number(state.duration_seconds || 0);
  root.querySelector(".progress").max = String(Math.max(duration, 1));
  root.querySelector(".progress").value = String(Math.min(position, duration || 1));
  root.querySelector(".position").textContent = formatTime(position);
  root.querySelector(".duration").textContent = formatTime(duration);
  volume.value = String(Number(state.volume_percent || 0));
  root.querySelector("output").textContent = `${volume.value}%`;
  playPause.textContent = state.playback_state === "playing" ? "⏸" : "▶";
  playPause.setAttribute("aria-label", state.playback_state === "playing" ? "Pause" : "Play");
  root.querySelector('[data-command="mute"]').textContent = state.muted ? "🔇" : "🔊";
}

function extractState(data) { return data?.primaryState || data?.state || data?.value || data || {}; }
function formatTime(seconds) { const value = Math.max(0, Math.floor(Number(seconds) || 0)); return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`; }
function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character]); }

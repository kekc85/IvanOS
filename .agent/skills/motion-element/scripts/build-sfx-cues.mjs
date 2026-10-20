/**
 * build-sfx-cues.mjs v2 — слоёный (compound) аудио-инжект для motion-element.
 *
 * Каждое размеченное событие data-sfx="<eventName>" data-sfx-at="<label>" разворачивается в
 * НЕСКОЛЬКО <audio>-слоёв по рецепту из sfx-map.json (v2), вместо одного файла на тег.
 * Для каждого слоя берётся ВАРИАЦИЯ из пула категории (round-robin, без немедленного повтора),
 * применяется offset_ms (data-start = atSeconds + (lead_in + offset + humanize)/1000),
 * gain_db→linear (data-volume), детерминированный humanize (сид от индекса, без Math.random).
 *
 * Нативный мультитрек HyperFrames микширует все слои в один рендер.
 *
 * Usage:
 *   node build-sfx-cues.mjs inject <index.html> <cues.json> [sfx-map.json] [manifest.json] [sfxDirRel]
 *     cues.json = [{event, atSeconds, step?, isFinal?}]  (event = имя compound-события)
 *   Без аргументов экспортирует чистые функции для unit-теста.
 */
import { readFileSync, writeFileSync } from "node:fs";

const db2lin = (db) => Math.pow(10, db / 20);

// детерминированный round-robin по категории
function makeRotator(manifest) {
  const idx = {};
  return (cat) => {
    const pool = (manifest.categories || {})[cat];
    if (!pool || !pool.length) return null;
    const i = (idx[cat] = (idx[cat] ?? -1) + 1) % pool.length;
    return `${cat}/${pool[i]}`;
  };
}

// детерминированный humanize: маленький джиттер от seed (индекс слоя/события)
function humanize(seed, h) {
  const r = (n) => {
    const x = Math.sin(seed * 12.9898 + n * 78.233) * 43758.5453;
    return (x - Math.floor(x)) * 2 - 1; // [-1,1], детерминированно
  };
  return {
    timing_ms: r(1) * (h?.timing_ms ?? 0),
    gain_db: r(2) * (h?.gain_db ?? 0),
  };
}

/** Разворачивает cue-list событий в плоский список аудио-слоёв. */
export function resolveLayers(cues, map, manifest) {
  const rotate = makeRotator(manifest);
  const g = map.global || {};
  const leadIn = (g.lead_in_ms ?? 0) / 1000;
  const out = [];
  let seed = 0;
  for (const cue of cues) {
    const ev = (map.events || {})[cue.event];
    if (!ev) continue;
    let layers = ev.layers;
    if (ev.per_step || ev.final_step) layers = cue.isFinal ? ev.final_step : ev.per_step;
    if (!layers) continue;
    for (const L of layers) {
      const file = rotate(L.cat);
      if (!file) continue;
      const hz = humanize(seed++, g.humanize);
      const at = cue.atSeconds + leadIn + (L.offset_ms ?? 0) / 1000 + hz.timing_ms / 1000;
      const gain = db2lin((L.gain_db ?? 0) + hz.gain_db);
      out.push({ file, atSeconds: Math.max(0, +at.toFixed(3)), gain: +Math.min(1, gain).toFixed(3) });
    }
  }
  return out.sort((a, b) => a.atSeconds - b.atSeconds);
}

/** <audio> на каждый слой, каждый на своём track-index (overlaps free). sfxDirRel = префикс пути к файлам. */
export function injectAudioTags(html, layers, sfxDirRel = "sfx", startTrackIndex = 30) {
  let idx = startTrackIndex;
  const tags = layers
    .map((c) =>
      `<audio src="${sfxDirRel}/${c.file}" data-start="${c.atSeconds.toFixed(3)}" ` +
      `data-track-index="${idx++}" data-volume="${c.gain}"></audio>`)
    .join("\n");
  return html.includes("</body>") ? html.replace("</body>", `${tags}\n</body>`) : html + "\n" + tags;
}

if (process.argv[2] === "inject") {
  const [, , htmlPath, cuesPath, mapPath, manifestPath, sfxDir] = process.argv;
  const html = readFileSync(htmlPath, "utf8");
  const cues = JSON.parse(readFileSync(cuesPath, "utf8"));
  const map = JSON.parse(readFileSync(mapPath || new URL("../config/sfx-map.json", import.meta.url)));
  const manifest = JSON.parse(readFileSync(manifestPath || map.library_manifest));
  const layers = resolveLayers(cues, map, manifest);
  writeFileSync(htmlPath, injectAudioTags(html, layers, sfxDir || "sfx"));
  console.log(`resolved ${cues.length} events → ${layers.length} audio layers injected into ${htmlPath}`);
}
# Workflow — от брифа до оверлея

Стек: HyperFrames (HTML + GSAP timeline), рендер через headless Chrome + FFmpeg. Локально, $0. Все пути абсолютные. Output runtime: `~/.business/growth/motion-elements/<date>-<slug>/`.

## Phase 0 — Brief capture
1. Принять текст/надиктовку автора («сделай тикер MRR с 0 до 9700», «нарисуй маркером кружок-стрелку»).
2. Классифицировать в `template_id`: `python3 scripts/classify-brief.py "<бриф>"` → топ-кандидат + confidence. Низкая уверенность → переспросить ОДНОЙ фразой, какой из 2 ближайших.
3. Извлечь params (текст, числа, цвета, логотипы, длительность, output-mode, язык).

## Phase 1 — Context-gap gate (HARD)
Если в брифе нет реального контента, который нельзя выдумывать:
- ticker/odometer/count-up → точное число и валюта/суффикс;
- comment-pop / chat-bubbles → реальные реплики (не плейсхолдер);
- ui-comparison-bar → реальные инструменты + логотипы;
- kinetic-caption → точный текст хука.
→ СТОП. Нумерованный список «нужно от тебя», ждать. Не выдумывать, не округлять, не ставить плейсхолдер в финал. `_shared/context-gap-gate.md`,.

## Phase 2 — Author composition
1. `cd ~/.business/growth/motion-elements/ && npx hyperframes init <date>-<slug>`.
2. Скопировать `templates/<template_id>/index.html` + `params.json` в проект, подставить params (текст/числа/цвета/логотипы).
3. Канвас 1080×1920 (9:16). Watermark `<твой-хэндл>` bottom-right включён по умолчанию (`--no-watermark` чтобы снять).
4. Если есть озвучка для kinetic-caption: `npx hyperframes tts "<скрипт>" --voice <v> --output vo.wav` → `npx hyperframes transcribe vo.wav` → timestamps по словам в композицию.

## Phase 2.5 — Sound design (HARD если `--with-audio`, default ON; skip при `--mute`)
Полные шаги, схема `sfx-map.json`, FFmpeg-рецепты дакинга/мастеринга, бит-синк — `prompts/03-audio.md`.
Кратко: разметить `data-sfx` на элементах-триггерах + GSAP-label на акцентном твине → `node scripts/build-sfx-cues.mjs` собирает cue-list по `tl.labels` → инжектит `<audio data-start data-track-index>` на каждый cue → музыка-бед (`afade`) + при нужде дакинг (`sidechaincompress`) и мастер (`loudnorm I=-14`).

## Phase 3 — Lint + inspect (HARD до рендера)
- `npx hyperframes lint --json` → ноль errors (missing `data-composition-id`, overlap треков, незарегистрированные timelines).
- `npx hyperframes inspect --json` → текст не вылезает за safe-zone/контейнеры, ноль errors. Warnings — ревью.
- **Determinism grep:** `grep -nE "Math\.random|setInterval|Date\.now" index.html` → пусто. Иначе рендер ≠ превью, FAIL.

## Phase 4 — Render
`npx hyperframes render` → MP4 1080×1920.

## Phase 5 — Output mode (по params `_out`)
- `solid` — MP4 на цветном ключ-фоне (для chroma-key в редакторе).
- `transparent` — рендер на solid key-фон → `npx hyperframes remove-background <mp4>` (u2net) → ProRes 4444 MOV или VP9 WebM с альфой для прямой накладки.
- `composite` — наложить элемент на присланную автором съёмку вторым `<video>`-треком прямо в HF.
- `recolor` — перегенерить с другим `accent_color`/`theme` из тех же params (вариант под бренд-палитру).

## Phase 6 — Flat output
Одна папка, без подпапок, префиксы в имени:
`<slug>.mov` (или `.mp4`/`.webm`) · `<slug>-preview.mp4` · `<slug>-muted.mp4` (немой вариант) · `<slug>-params.json` · `<slug>-README.txt` (как дропнуть + output-mode). Путь в чат.

## Phase 7 — Drop hint
Одной строкой: overlay-трек / blend-mode / длительность; элемент seek-safe (ретаймится). Если `transparent` — «клади прямо поверх, фон прозрачный». Если `solid` — «ключи по фону #RRGGBB».

## Gates перед выдачей (Evidence)
Каждый gate из SKILL.md «Quality gates» закрыть с доказательством: цитата lint/inspect JSON, grep determinism пуст, число сверено с источником, рендер просмотрен.. Синк звука оценивать на playback, не на статичных кадрах.
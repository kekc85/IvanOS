---
name: motion-element
version: "1.0"
created: 2026-06-01
last_reviewed: 2026-06-01
description: Делает ОДИН motion-графический элемент-оверлей для рилз из описания (RU/EN) — прозрачный MOV/WebM или MP4 на движке HyperFrames, локально, $0, без After Effects и платного CapCut, со звуком синхронно с движением. Триггеры: "сделай моушн-элемент/оверлей для рилза", "анимированный тикер/счётчик", "всплывающие комменты поверх видео", "печатающийся терминал", "before/after для рилза", "kinetic-подписи", /motion-element, /element, "make a motion overlay", "transparent overlay for my reel".
metadata:
  artifact_type: mixed
  user: personal
  engine: hyperframes
  cost: "$0"
---

# motion-element — один motion-графический оверлей из текста

Описал словами один графический элемент → получил готовый клип для накладки в монтаж рилза. На движке HyperFrames (HTML + GSAP timeline, рендер через headless Chrome + FFmpeg). Локально, бесплатно, без After Effects и без платного CapCut.

## Когда применять

Триггеры:
- `/motion-element`, `/element`
- «сделай моушн-элемент», «сделай оверлей для рилза», «нужна анимированная плашка/тикер/счётчик»
- «всплывающие комменты поверх видео», «печатающийся терминал», «counter с 0 до N»
- «kinetic-подписи под озвучку», «before/after для рилза», «нарисуй маркером кружок/стрелку на видео», «сделай прозрачную графику»
- EN: «make a motion overlay», «animated counter/ticker», «kinetic caption element», «transparent MOV overlay for my reel», «typing terminal clip», «before/after wipe»

## Граница ответственности (один источник истины)

| Нужно | Скилл |
|---|---|
| ОДИН графический элемент-оверлей из текста, для накладки на свою съёмку | **motion-element** (этот) |
| Целый ролик из чужого рилза (URL/ингест) в голосе автора | `produce-reel` / `replicate-reel` |
| План motion по сегментам ингеста (не рендер) | `motion-storyboard` |
| Низкоуровневый движок (CLI, TTS, bg-removal, блоки) | `hyperframes` / `-cli` / `-media` / `-registry` |
| Замена нижнего B-roll в готовом сплите | `broll-swap` |

**Линия раздела одной фразой:** есть исходный рилз → `ingest/replicate/produce`. Нужен один новый графический кусок поверх своей съёмки → `motion-element`. Движок не дублируем — этот скилл тонкая обёртка-оркестрация поверх `hyperframes` + `gsap` + `hyperframes-media`.

## Workflow (детали — `prompts/01-workflow.md`)

0. **Brief capture** — принять текст/надиктовку, классифицировать в `template_id` (`scripts/classify-brief.py`), извлечь params.
1. **Context-gap gate (HARD)** — нет реальных цифр/текста/кейса/логотипов → СТОП, нумерованный список «нужно от тебя», ждать. Не выдумывать числа/цитаты. `_shared/context-gap-gate.md`,.
2. **Author composition** — `npx hyperframes init`, скопировать `templates/<id>/`, подставить params; озвучка → `hyperframes tts` → `transcribe` → timestamps для kinetic-caption.
2.5 **Sound design (HARD если `--with-audio`)** — разметить события `data-sfx`, собрать cue-list по GSAP-labels, подложить музыку, дакинг/мастеринг. Детали — `prompts/03-audio.md`.
3. **Lint + inspect (HARD до рендера)** — `npx hyperframes lint --json` + `inspect --json` → ноль errors.
4. **Render** — `npx hyperframes render`, канвас 1080×1920 (9:16).
5. **Output mode** — `solid` (MP4 на ключ-фоне) / `transparent` (→ `remove-background` → ProRes 4444 MOV или VP9 WebM с альфой) / `composite` (наложить на присланную съёмку) / `recolor` (та же params, другой accent под бренд).
6. **Flat output** — всё одной папкой без подпапок: `<slug>.mov`/`.mp4`/`.webm` + `-preview.mp4` + `-muted` вариант + `params.json` + `README.txt`. Путь в чат.
7. **Drop hint** — одной строкой куда положить в монтаж (трек, blend, длительность), что элемент seek-safe (ретаймится).

## Template library v1.0 (детали — `prompts/02-templates.md`)

Каждый шаблон = HyperFrames-композиция `templates/<id>/index.html` + `params.json`. Seek-driven, без RNG.

`comment-pop` · `count-up-ticker` · `code-terminal` · `before-after-wipe` · `kinetic-caption` · `ui-comparison-bar` · `chat-bubbles` · `scribble-callout` · `screen-zoom-punch` · `price-odometer`

Статус сборки шаблонов — `prompts/02-templates.md` (раздел «Build status»). Новый шаблон = новая папка `templates/<id>/` без правки движка.

## Звук синхронно с движением (детали — `prompts/03-audio.md`)

Главный рычаг: GSAP-timeline уже знает точную секунду каждого события → build-скрипт выдаёт детерминированный SFX cue-list, звук попадает кадр-в-кадр, а не на глаз в CapCut.
- **СЛОЁНЫЙ звук (v2), не 1 файл на тег.** Событие = compound из 3-6 слоёв в трёх полосах (transient/body/texture): whoosh-переход = air-sweep + sub + crack + tail; reveal = riser → impact + crack + sub-drop + tail. Рецепты и стандарты — `knowledge/sound-design-standards.md` (12 рецептов, энергия под движение, sidechain). Схема — `config/sfx-map.json` v2 (compound-события + пулы вариаций по категориям).
- **Реальная библиотека 272 звука** `~/.business/assets/sfx-library/sorted/` (+ `manifest.json`): Kenney CC0 + Sonniss GDC (whoosh) + designed-склейки. $0, без ключей, коммерчески чисто. Пополнение/таксономия — `knowledge/free-audio-sources.md`, добор `scripts/make-starter-sfx.sh` (синтетика-fallback).
- **Движок инжекта** `scripts/build-sfx-cues.mjs` (v2): событие → N аудио-слоёв, round-robin вариации из пула (без повтора), offset_ms, gain_db→linear, детерминированный humanize (микро-джиттер питча/тайминга = human feel).
- **Нативно в HF:** мультитрек `<audio data-start data-track-index data-volume>` микшируется в один рендер (проверено: 30 слоёв в одном рендере); per-frame band-реактивность (`extract-audio-data.py`).
- **FFmpeg-постшаг:** фейды (`afade`), сайдчейн-дакинг музыки под голос/SFX (`sidechaincompress`), мастер-громкость (`loudnorm I=-14`).
- **Бит-онсеты:** librosa (`beat_track`/`onset_detect`) — акценты движения и SFX на одной сетке.
- Флаги: `--with-audio` (default для рилз) / `--mute` (немой вариант для редактора со своим звуком).

## Quality gates (проверяемые)

1. **9:16 safe-zone** — top/bottom 130px, left/right 80px; `inspect` ловит вылет.
2. **Watermark `<твой-хэндл>`** — bottom-right по умолчанию; флаг `--no-watermark`, если кладётся на свой кадр с вотермаркой.
3. **Lint + inspect ДО render** — оба `--json`, ноль errors = gate.
4. **Determinism gate** — grep композиции на `Math.random` / `setInterval` / `Date.now` в анимации → FAIL (рендер не совпадёт с превью).
5. **Number/fact gate** — все числа в ticker/odometer/stats сверены с источником автора, не выдуманы.
6. **Audio gates** — loudness ≈ −14 LUFS, дакинг под голос/SFX, не «вошить» каждый стык, звук читается и без звука (sound-off), лицензия чистая, тайминг pre-baked.
7. **Humaniser — УСЛОВНО** — `Skill('humaniser')` ТОЛЬКО если on-screen текст = audience-facing копи (хук kinetic-caption, реплики comment-pop/chat-bubbles, CTA). НЕ для чистых данных (числа, логотипы, код) ( — исключение для data/metadata).
8. **Visual + audio review каждого рендера** — посмотреть отрендеренный клип (или hero-frames через `inspect`) ДО выдачи: язык/контент/порядок/вотермарка/safe-zone/синк звука (— для оценки синка нужен playback, не только кадры).

## Anti-patterns

- Не генерировать целый ролик — это `produce-reel`. Здесь один атомарный элемент.
- Не дублировать движок HyperFrames внутри скилла — звать его CLI/скиллы.
- Не `Math.random`/`setInterval` в анимации (рендер ≠ превью). Сиды позиций — в разметку.
- Не звать `audio.play()` из GSAP — плейбэком владеет фреймворк, GSAP только анимирует визуал.
- Не выдумывать числа/комменты/логотипы — context-gap gate.
- Не отчитываться «готово N/N» без просмотра рендера ().

## Memory cross-refs

 · · · · · · · ·

## Параллельные скиллы

`produce-reel` (целый ролик из источника) · `hyperframes` (движок) · `broll-swap` (замена B-roll) · `carousel` (статичные слайды). Этот — единственный про «один анимированный элемент-оверлей из текста».
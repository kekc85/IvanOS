---
name: ui-record
description: Записать UI-моушн-клип реального софта (web-сайта или CLI-терминала) для использования как b-roll в контент-фабрике автора. Headless Chromium через Playwright recordVideo + ffmpeg → mp4 1080×1920 30fps с реальным cursor motion, scroll, typing. Триггерится на "запиши UI", "сделай b-roll сайта", "запиши терминал", "/ui-record <scenario>", "нужен клип <site>", или когда замысел требует показать как работает конкретный сервис/CLI без manual recording и без AI-генерации.
allowed-tools: Bash, Read, Write, Edit
version: "1.0"
created: 2026-05-25
last_reviewed: 2026-05-25
review_deps_every: 3 months
---

> ⚠️ В ПАКЕТ НЕ ВХОДЯТ: `record.mjs`. Команды с этими именами даны как ОПИСАНИЕ: инструмент либо приходит из внешнего пакета, который ставится отдельно, либо собирается на твоём проекте по этой же инструкции. Внутри поставки такого файла нет

# UI Record - сценарий → motion mp4

Автоматическая запись реального UI с motion (cursor, scroll, typing) для использования b-roll в финальных reels. Никаких credits, никаких ручных записей. Один инструмент для веба и для CLI.

## Когда триггерить

- автор говорит «запиши UI сайта X», «сделай терминальный клип», «нужен b-roll для motion.dev»
- В replicate-reel требуется b-roll сегмент с UI motion
- Любой раз когда нужно UI proof и source video автора не подходит
- Прямой вызов: `/ui-record <scenario-name>`

НЕ триггерить если:
- Нужна голая фото/png — это не motion
- Нужно показать конкретного автора в кадре (нет — мы показываем UI его инструмента)
- Сайт требует логин — сначала записать flow, либо использовать local mock

## Расположение

Пакет `content-factory` в поставку НЕ входит (см. предупреждение выше). Путь к нему
ты задаёшь сам одним из двух способов, и `scripts/record.sh` проверяет их в этом
порядке:

1. переменная окружения `CONTENT_FACTORY_DIR=/путь/к/content-factory`
2. каталог `tools/ui-record/` рядом со скриптом (если ты собрал recorder у себя)

Ниже `<CF>` означает выбранный путь. Внутри он устроен так:

```
<CF>/tools/ui-record/
├── record.mjs              ← Playwright recorder
├── terminal.html           ← fake terminal page (xterm-style)
├── scenarios/              ← JSON-сценарии per tool (commit-able)
│   ├── claude-code-install.json
│   ├── claude-code-build.json
│   ├── motion-dev.json
│   └── ...
└── library/                ← output mp4 cache
    └── *.mp4
```

## Запуск

Из каталога `<CF>` (см. «Расположение» выше):

```bash
node tools/ui-record/record.mjs \
  --scenario <name-or-path> \
  --out tools/ui-record/library/<name>.mp4
```

- `--scenario` — имя файла из `scenarios/` (без расширения) ИЛИ абсолютный путь к JSON
- `--out` — куда писать финальный mp4 (всегда H.264, 1080×1920, 30fps)

Время записи: ~30-60 сек на клип (Playwright launch + actions + ffmpeg convert).

## Формат сценария

### Web (запись реального сайта)

```json
{
  "name": "motion-dev",
  "kind": "web",
  "url": "https://motion.dev/",
  "viewport": {"width": 1080, "height": 1920},
  "duration_sec": 7,
  "wait_for_selector": "body",
  "actions": [
    {"at": 0.8, "type": "mouse_move", "to": [540, 1000]},
    {"at": 2.0, "type": "scroll", "by": [0, 600]},
    {"at": 3.5, "type": "mouse_move", "to": [320, 1200]},
    {"at": 4.2, "type": "click", "selector": ".cta-button"},
    {"at": 5.0, "type": "type", "selector": "input[type=email]", "text": "hi@example.com"},
    {"at": 6.0, "type": "highlight", "selector": ".feature-card"}
  ]
}
```

Поддерживаемые action types:
- `mouse_move` — `to: [x, y]` плавное перемещение курсора (cubic-bezier ease-out, Screen Studio-style)
- `click` — `selector` или `to` (с анимированным pulse-ring). Опции:
  - `zoom: true` — auto-zoom-in to click point (CSS transform на documentElement, 300ms cubic-bezier)
  - `zoom_scale: 1.6` — degree of zoom (default 1.6, range 1.3-2.2)
  - `zoom_hold_ms: 600` — сколько держать zoom после click до zoom-out (default 600)
  - `zoom_out: false` — оставить zoom активным (для chain нескольких clicks в одной zone)
- `scroll` — `by: [dx, dy]` плавный скролл
- `type` — `selector` + `text` (jittered keyboard timing 30-90ms)
- `highlight` — `selector`, обводит элемент рамкой и скроллит в центр
- `wait` — pure timing anchor

## Cursor polish features (новое 2026-05-28)

Закрывают gap с Screen Studio / CursorClip без покупки лицензии.

### Cursor smoothing (по умолчанию ON)

`smoothMouseMove` использует **cubic-bezier ease-out** (`1 - (1-t)^3`) — соответствует Screen Studio signature smooth glide. Раньше был симметричный ease-in-out, теперь курсор замедляется к концу = ощущение точного приземления.

### Auto-zoom-on-click

Включается двумя способами:

**Глобально на сценарий** — все click actions получат auto-zoom:

```json
{
  "kind": "web",
  "url": "https://example.com",
  "auto_zoom_on_click": true,
  "zoom_scale": 1.6,
  "zoom_hold_ms": 600,
  "actions": [...]
}
```

**Per-action override** — конкретные clicks с zoom (или без, если глобально включено):

```json
{
  "type": "click",
  "selector": ".cta-button",
  "zoom": true,
  "zoom_scale": 1.8,
  "zoom_hold_ms": 800
}
```

Чтобы chain последовательные clicks в одной zone без zoom-out между ними — `zoom_out: false` на промежуточных:

```json
{"type": "click", "selector": ".step-1", "zoom": true, "zoom_out": false},
{"type": "click", "selector": ".step-2", "zoom": true, "zoom_out": false},
{"type": "click", "selector": ".confirm", "zoom": true}
```

**Tech detail.** Zoom через CSS transform на `document.documentElement` — vector-rendered в Chromium до Playwright recordVideo capture. Качество выше чем ffmpeg post-process upscale (потому что rendering происходит в browser до raster encoding).

### Когда применять auto-zoom

- ✅ Click на CTA / Save / Submit — focus viewer attention
- ✅ Click на small UI element (typing area / chevron / dropdown trigger)
- ✅ Click на key step of demo workflow
- ❌ НЕ применять на каждый click подряд (становится disorienting)
- ❌ НЕ применять если viewer должен видеть big picture (overview shots)
- Cap: max 2-3 auto-zoom moments на 30-сек clip

### Terminal (CLI demo через локальный xterm.html)

```json
{
  "name": "claude-code-install",
  "kind": "terminal",
  "viewport": {"width": 1080, "height": 1920},
  "duration_sec": 6,
  "terminal": {
    "title": "~/projects/agency-site",
    "cwd": "~/projects",
    "commands": [
      {
        "kind": "command",
        "text": "npm install -g @anthropic-ai/claude-code",
        "before_ms": 300,
        "speed": 32,
        "after_ms": 250,
        "output": [
          {"text": "added 24 packages in 3s", "style": "ok", "delay_ms": 600}
        ]
      },
      {
        "kind": "command",
        "text": "claude",
        "before_ms": 200,
        "output": [
          {"text": "Claude Code v0.7.2 — ready", "style": "ok", "delay_ms": 200},
          {"text": "Type your prompt and hit Enter.", "style": "out", "delay_ms": 150}
        ]
      }
    ]
  }
}
```

Output styles: `out` (grey), `ok` (green), `warn` (yellow), `err` (red).

## Synthetic UI mock pipeline (новое 2026-05-28)

Когда нужен **UI которого не существует в реальном софте** (концепт продукта / иллюстрация workflow / hypothetical interface) - не покупать Magic Patterns / v0 subscription, а собрать своими руками через тот же стек:

### Подход

1. **Сгенерить mock через Claude Code** (vibe-coding):
   - Запросить у Claude HTML + Tailwind + Framer Motion компонент типа "Settings dashboard для AI agent app с 4 toggles и save button"
   - Сохранить в `<CF>/tools/ui-record/mocks/<name>.html`

2. **Запустить локально** (или просто открыть HTML):
   - Для статичного mock - просто `file://` URL в Playwright достаточно
   - Для interactive React/Next mock - `npm run dev` на random port, передать URL в scenario

3. **Записать через ui-record** с реальным cursor motion и опционально auto-zoom-on-click:
   ```json
   {
     "name": "agent-settings-mock",
     "kind": "web",
     "url": "file:///абсолютный/путь/к/mocks/agent-settings.html",
     "viewport": {"width": 1080, "height": 1920},
     "duration_sec": 8,
     "auto_zoom_on_click": true,
     "zoom_scale": 1.7,
     "actions": [
       {"at": 1.0, "type": "mouse_move", "to": [540, 800]},
       {"at": 2.0, "type": "click", "selector": ".toggle-notifications"},
       {"at": 3.5, "type": "click", "selector": ".toggle-autosync"},
       {"at": 5.0, "type": "click", "selector": ".save-button", "zoom_scale": 2.0}
     ]
   }
   ```

### Преимущества vs v0.dev / Magic Patterns / Lovable

- **$0 cost** — нет subscription, Claude Code локально + ui-record локально
- **Pixel-exact control** — что закодили = то и записали
- **Reproducible** — HTML коммитится в repo, mock переиспользуется
- **Same toolchain** — никаких новых dependencies vs существующего стека

### Когда применять / не применять

**Применять.** Concept UI / hypothetical product / illustration of workflow that doesn't exist yet.

**Не применять.** Реальный workflow в существующем софте (Claude Code / Cursor / n8n / Lovable / etc) - тогда записывать реальное.

## Workflow

1. **Берёшь новый ингест** → читаешь transcript → определяешь какие UI-моменты упоминаются.
2. **Для каждого UI-момента** — либо существующий сценарий из `scenarios/`, либо пишешь новый JSON (~15 строк).
3. **Записываешь клипы**:
   ```bash
   node tools/ui-record/record.mjs --scenario X --out tools/ui-record/library/X.mp4
   ```
4. **Vision-verify**: вытащи 4-6 кадров через ffmpeg, прочитай через Read, убедись что motion есть и нет дефектов:
   ```bash
   for t in 1.0 3.0 5.0 7.0; do
     ffmpeg -y -ss "$t" -i clip.mp4 -vframes 1 -vf "scale=540:960" "frame_$t.jpg"
   done
   ```
5. **Используй mp4 как `src` в `broll_segments`** spec.json для `Replica.tsx`.

## Self-verification (обязательно перед "готово")

После записи каждого клипа:

1. ffprobe — проверить `width=1080`, `height=1920`, `r_frame_rate=30/1`, `codec_name=h264`, `duration` ≈ ожидаемой.
2. Vision-check 4+ кадров: motion есть (разница между кадрами видна), курсор виден, текст не обрезан справа, никаких cookie-баннеров.
3. Если дефект — править scenario (короче команды для wrap, меньше шрифт, другой селектор) и перезаписать.

НЕ показывать автору клип без vision-verify. Прецедент 2026-05-23 — 4 неудачных подхода подряд именно из-за partial demos без проверки.

## Что записывается надёжно

- Все publicly-accessible landing сайты с responsive дизайном (motion.dev, anthropic.com, claude.com)
- Локальные dev серверы (`http://localhost:3000`)
- CLI-демонстрации через terminal.html (любые команды + outputs)

## Что записывается плохо (workaround)

- Сайты которые блокируют headless или показывают cookie-walls → инжектится `killBanners()`, но если сайт делает heavy bot-detect — собрать local mock HTML с тем же содержимым.
- Сайты не адаптированные под portrait 1080×1920 (например 21st.dev отдаёт пустой экран) → fallback: desktop viewport 1280×800 + ffmpeg pad в портрет, либо local mock.
- Сайты за логином → flow с `actions[].type=type/click` для авторизации, либо local mock.

## Что НЕ делать

- НЕ накладывать source video автора и не использовать его для b-roll
- НЕ генерировать UI через credit-based сервисы (Higgsfield/Kling/Sora)
- НЕ записывать вручную через QuickTime/OBS
- НЕ использовать static PNG скриншоты вместо motion mp4 (автор явно: «UI proof = video с motion»)
- НЕ показывать клип автору без vision-verify

## Интеграция с рендер-узлом (replicate-viral, ранее replicate-reel) / Replica.tsx

> ПРИМЕЧАНИЕ 2026-06-10: рендер-узел = `replicate-viral` Фаза 6 (`replicate-reel` [DEPRECATED]). Replica.tsx и b-roll сегменты используются им же.


В `<CF>/src/compositions/Replica.tsx` есть universal composition. Spec.json указывает `broll_segments`:

```json
{
  "duration_sec": 30,
  "broll_segments": [
    {"from_sec": 0,  "to_sec": 7,  "src": "/tools/ui-record/library/claude-code-install.mp4"},
    {"from_sec": 7,  "to_sec": 15, "src": "/tools/ui-record/library/claude-code-build.mp4"},
    {"from_sec": 15, "to_sec": 22, "src": "/tools/ui-record/library/motion-dev.mp4"}
  ],
  "caption_phrases": [
    {"text": "Я собрал сайт на 10 тысяч долларов", "start_sec": 0, "end_sec": 3},
    {"text": "Одной строкой кода Claude", "start_sec": 3, "end_sec": 6}
  ],
  "avatar_marker_text": "видео аватара ивана",
  "watermark_text": "<твой-хэндл>"
}
```

Render:
```bash
cd "$CONTENT_FACTORY_DIR"   # или путь, который ты выбрал в «Расположении»
npx remotion render Replica out.mp4 --props=specs/2026-05-25-myreel.json
```

ВАЖНО: композиция Replica на 2026-05-25 написана но НЕ wired в `src/Root.tsx`. Чтобы её активировать — добавь импорт `{Replica, replicaSchema, replicaDefaultProps}` и `<Composition id="Replica" ... />` в Root.tsx. Это намеренно отложено до next session где будет full end-to-end.
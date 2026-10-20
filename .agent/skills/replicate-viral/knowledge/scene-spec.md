# scene-spec — декларативная сцена для Opus (AC1 «тропинки для Opus»)

**Философия: модель решает ЧТО, скрипт решает КАК.**
Слабая модель (Opus) НЕ верстает CSS/тайминги руками — она описывает сцену коротким
JSON-выбором из enum-меню канона. `scene-assemble.py` детерминированно собирает
готовый `index.html` из валидированных сниппетов библиотеки `motion-blocks`. Это закрывает
корневой провал Opus: «160/175 строк сцены = магические числа на глаз».

## Поток
```
spec.json  →  scene-assemble.py  →  <out>/index.html (+ blocks/ + assets/)
              (валидация → сборка → preflight → [--render: render + полный аудит])
```

```bash
# валидация + сборка + preflight (0 рендеров)
python3 scene-assemble.py scene.spec.json -o /tmp/scene-x

# + рендер + полный scene-audit по mp4
python3 scene-assemble.py scene.spec.json -o /tmp/scene-x --render
# сцена без лица по дизайну (full-screen UI):
python3 scene-assemble.py scene.spec.json -o /tmp/scene-x --render --no-face-expected
```

## Формат спеки (схема `scene-spec.schema.json`)
```jsonc
{
  "scene_id": "my-scene",          // [a-z0-9_-], id композиции и файла
  "duration": 5,                   // 0.5..60 сек
  "background": "grid-floor",      // enum: dark | cream | grid-floor | black | near-black
  "layers": [                      // снизу вверх; z = порядок наложения (больше = выше)
    { "block": "K3-overlap-card-avatar", "z": 1, "params": { ... } },
    { "block": "J5-word-stream-whisper-sync", "z": 5, "font_role": "impact", "params": { ... } }
  ],
  "sfx": [                         // ≤12; плотность 1/1.5с (валидатор предупреждает)
    { "t": 0.15, "category": "whoosh", "volume": 0.16 }
  ],
  "audio": { "vo_src": "vo.wav", "music_src": "bg.mp3" },   // опц.
  "overrides": [                   // отступление от меню/дефолта = ОБЯЗАН нести why
    { "field": "layers[0].block", "value": "K3-...", "why": "..." }
  ],
  "beats": [                       // ОПЦ. побитная монтаж-структура (skeleton binding)
    { "layout": "full-head", "t0": 0, "t1": 2, "block": "O6-..." },
    { "layout": "full-ui",   "t0": 2, "t1": 4 }
  ]
}
```

## beats[] — montage skeleton binding (Ф2)
`beats[]` (опц.) кодирует ПОБИТНУЮ монтаж-структуру сцены, чтобы реплика воспроизводила
монтаж эталона, а не съезжала в монотонную говорящую голову. Каждый бит:
`{ layout (обяз., enum), t0, t1 (сек, опц.), block (ссылка на блок, опц.) }`.
**layout-enum:** `full-demo` · `split` · `full-ui` · `full-head` · `anchor-rotate`
(`full-head` = говорящая голова на весь кадр).

**Принуждение.** Если рядом со спекой (`dirname(spec)/scene-skeleton.json`), в out-dir,
или по `--skeleton <path>` есть `scene-skeleton.json` (вывод `skeleton-derive.py`) —
`scene-assemble.py` ПРОВЕРЯЕТ, что `beats[]` воспроизводят скелет, и при несовпадении
**reject (exit 2), не собирает**:
- число битов спеки == `n_beats` скелета;
- `layout` каждого бита спеки == layout соответствующего бита скелета (по порядку);
- длительность бита спеки (`t1-t0`) ≤ длительности бита скелета (+0.05с);
- avatar full-screen (`layout==full-head` ИЛИ `block` = full-screen аватар-блок, напр. `O6`)
  допустим ТОЛЬКО на битах, где у скелета `avatar_role∈{bookend,anchor}`; на `absent`-битах
  full-head ЗАПРЕЩЁН (анти-монотонность: где у эталона контент — нельзя ставить лицо).

**Backward-compat.** НЕТ `scene-skeleton.json` нигде → принуждение выключено, спека без
`beats[]` валидна по-старому. ЕСТЬ скелет, но в спеке нет `beats[]` → reject с подсказкой
«спека должна содержать beats[] по скелету».

```bash
# принуждение скелета (явный путь); иначе ищется рядом со спекой / в out-dir
python3 scene-assemble.py scene.spec.json -o /tmp/scene-x --skeleton /path/scene-skeleton.json
```

## Меню enum
**Блоки** (`layers[].block`) — только параметрические (slots/variables в meta.json):
`E5-perspective-grid-floor`, `K3-overlap-card-avatar`, `O6-avatar-feathered-fill`,
`A18-title-strap-caps`, `F5-ai-model-icon-row`, `G24-repo-file-list`, `G25-readme-card`,
`G26-glow-frame-highlight`, `G27-command-input-typeon`, `J5-word-stream-whisper-sync`.
Параметры (`params`) каждого блока = ключи из его `meta.json` (`variables` ИЛИ `slots`).
Неизвестный ключ → ошибка валидатора с перечнем допустимых.

**font_role** (канон-шрифты): `impact` (→ассемблер инлайнит oswald.css, condensed-display) ·
`sans-strap` · `serif-italic` · `mono` · `none`.

**background**: `dark/near-black` `#060608` · `black` `#000` · `cream` `#FAF6EF` (бренд автора) ·
`grid-floor` `#060608` (фон под слой-блок E5/K3). grid-floor/stage сам рисует блок-слой.

**captions.style**: `word-stream-whisper` · `mono-caps-chip` · `serif-italic-pop`.
**sfx.category** (из `sfx/mapping.md`, событие→звук): `whoosh` (смена сцены) · `click`/`pop`
(появление UI/буллета) · `ui` (тоггл/скролл) · `ding` (готовый результат) · `riser`
(нарастание перед панчем) · `keyboard` (печать) · `negative` (ошибка/«было-сломано» в before/after,
редко, только соло). Громкость 0.14–0.18 = −18dB под голос. Длинные designed-звуки
(`ding-05/06`, `riser-04`, `negative-01`) — только соло в паузе речи, не подкладкой.

## Акцент-цвет (канон)
Бренд-золото автора `#E0A53D` (тёплый) ИЛИ жёлтый хайлайт на цифрах/деньгах/ключевых словах.
Ядовито-лайм ЗАПРЕЩЁН (анти-образец theaiscaler). gold:true на слове captions = акцент.

## override с why (анти-шаблонность)
Дефолт = меню. Любое отступление (другой блок/цвет/гео вне дефолта) кладётся в `overrides`
с обязательным `why` — это осознанное решение СИЛЬНОЙ модели, а не дрейф. Валидатор
блокирует override без why.

## Как ассемблер собирает (детерминизм)
1. **Валидация спеки** — jsonschema если стоит, иначе ручная (обязательные/enum) + ВСЕГДА
   доменная: блок существует · param ∈ variables∪slots блока · видео-слот ffprobe аспект/
   длительность против требований (K3 ждёт avatar 720×1280 head-and-shoulders).
2. **Трансформ блока в sub-comp** — каждый блок → `<template>`-обёрнутый sub-comp HyperFrames
   с уникальным `composition-id`; переменные ЗАПЕКАЮТСЯ в build-time (defaults блока + params
   слоя заменяют `getVariables()` константой — без runtime-vars, полный детерминизм); media
   `src` → root-относительный `blocks/<cid>/<file>`; слот-файлы копируются под дефолтным именем.
3. **Сборка root** — слои по z как nested compositions (`data-composition-src`), SFX = отдельные
   `<audio id data-start data-volume>`, инлайн oswald.css при `font_role:impact`.
4. **Авто-аудит** — preflight (0 рендеров) на ПЛОСКОМ `*.audit-html` (root + развёрнутые sub-comp,
   чтобы B/M-оси видели реальную разметку), при `--render` — npx render + полный scene-audit по mp4.

Одинаковая спека → байт-в-байт одинаковый HTML (сорт ключей, без дат/рандома).

## Семьи раскладок и scene-audit (профили семей, Ф5a)
`scene-audit.py` исторически откалиброван на **talking-head split** (G0DM0D3: верх-скриншот /
низ-аватар, 2 слота). Оси `A2` (подбородок в обрезке), `M` (сплит-с-0), `K` (тёмные бары),
`B15` (2-слот-split), `B12` (currentTime lip-sync) — про ЭТУ семью.

**Overlap-card семья** (K3 / эталон DUqeScpDAHW, назначен автором планкой) — другая раскладка:
тёмная кинематографичная сцена-пол, аватар bottom-pinned с НАМЕРЕННЫМ кропом подбородка,
голова «вылезает» над карточкой. Эта семья ШТАТНО трипает 5 split-осей выше — это НЕ дефект
сборки и НЕ повод ослаблять аудит. Оси, валидные для overlap-card (проходят на эталоне):
`A headroom` (270px) · `J text∩face` · `K2 caption∩UI` · `F` (с обводкой) · `B3/B4` (Oswald
премиум) · `B5` (обводка) · `B9` (бренд-золото). Для overlap-card СУДИТЬ по ним + vision-слой
(финальный глаз на читаемость/реализм — единственный недетерминируемый класс).

Не «чинить» split-оси под overlap-card подгонкой аудита — это разные семьи; критик-человек/
сильная модель смотрит профильные оси семьи + кадр.

### Машинное принуждение (Ф5a — закрыт зазор «оси = суждение оператора»)
`scene-audit.py --family talking-head-split|overlap-card` (default `talking-head-split` —
полная обратная совместимость). Профиль = декларативная таблица `FAMILY_PROFILES` В КОДЕ:
для `overlap-card` оси `A2/M/K/B12/B15` переведены в **WARN-only** «вне профиля семьи» (печатаются,
НЕ валят exit 2); профильные оси (`A headroom · J · K2 · F · B3/B4/B5/B9 · G · H · I` и т.д.)
остаются **hard-FAIL**. Проверки НЕ удалены — изменён только режим вердикта. Аудит печатает
активный профиль и какие оси переведены в WARN (прозрачность).

Спека несёт `"family": "overlap-card"` (опц. поле схемы, default `talking-head-split`);
`scene-assemble.py --render` прокидывает его в авто-аудит. Эталон `examples/etalon-overlap.spec.json`
объявляет `family: overlap-card` и проходит авто-аудит PASS.

### golden-run.sh — регрессия-якорь скилла
`scripts/golden-run.sh [--update-baseline]` гонять ПОСЛЕ ЛЮБОЙ правки скилла / сниппетов /
аудитора — ловит деградацию ДО автора. Проверяет: (1) детерминизм сборки (md5 HTML против
baseline), (2) аудит overlap-card PASS, (3) покадровую регрессию рендера (5 кадров: mean-abs-diff
и SSIM против baseline-PNG, порог = шум кодека×3). Baseline в `scripts/golden/`
(md5 + 5 PNG + metadata с порогами). Калибровка порогов: шум кодека между
идентичными рендерами max mean-abs-diff≈0.56 / min SSIM≈0.993 → пороги 1.7 / 0.978.

---
name: omni-flash
description: Drive Google Flow (Gemini Omni Flash) over the browser to restyle / "оживить" a talking-head clip - add motion-design graphic inserts and kinetic captions synced to speech, or fully restyle the segment. Used as the stylized-montage layer of the reel pipeline. Triggers - "прогони через Omni Flash", "оживи говорящий сегмент", "стилизуй клип в Omni", "/omni-flash <clip>", or when the reel pipeline needs the talking-segment styling + subtitle layer.
---

# omni-flash — вождение Gemini Omni Flash (Google Flow)

Я сам вожу Google Flow через браузер (CDP) на ТВОЁМ залогиненном аккаунте, без ручных кликов: гружу говорящий клип, шлю промт на стилизацию/оживляж + кинетические субтитры, жду рендер, забираю output, проверяю и отдаю ссылкой.

## Место в пайплайне (карта ролей, НЕ путать)

| Слой | Инструмент | Что делает |
|---|---|---|
| Говорящий якорь | HeyGen Avatar V5 | фотореалистичный говорящий двойник (твой аватар, сырьё) |
| **Стилизация говорящих сегментов + субтитры** | **omni-flash (этот скилл)** | берёт говорящий клип → оживляж + кинетик-сабы в такт речи |
| Реальный UI сервиса (GitHub-репо и т.п.) | hyperframes | реальный скринкаст, без AI-перерисовки |
| Абстрактные/нарисованные вставки | Higgsfield + `motion-design-prompter` | статичный дизайн → анимир-клип |
| Финальная сборка | hyperframes/ffmpeg | склейка слоёв, 9:16, водяной знак |


## Два режима

- **clean** - лицо остаётся фотореалистичным, Omni добавляет только графику + кинетические акцент-слова + субтитры ВОКРУГ, не трогая лицо. Дефолт для брендового talking-head.
- **energy** - полный рестайл сегмента (paper-cutout / коллаж / stop-motion) для хук-моментов. Лицо стилизуется намеренно.

Субтитры и кинетический текст в обоих режимах промтом держим ВНЕ зоны лица (верхняя/нижняя треть) - это закрывает старую боль hyperframes «текст на лице/лбу».

## Доступ (BYOA — на аккаунте УЧЕНИКА)

- Сёрфейс: **Google Flow** (`labs.google/flow`), нужен тариф Google AI Pro/Ultra на ТВОЁМ Google-аккаунте.
- Работаем через ТВОЙ залогиненный Chrome по CDP. Скилл НИКОГДА не запускает и не закрывает Chrome - только `connect_over_cdp` к порту 9222 и работа в `contexts[0]` (чья сессия в браузере, на той и рендерим). CDP-порт аккаунт-агностичен, аккаунт берётся из ТВОЕЙ залогиненной вкладки Flow.

## Workflow

### Шаг 0 — BYOA-гейт Google Flow (на старте, до probe/run)
Канон: `_shared/bring-your-own-account.md`. Сервис работает на аккаунте УЧЕНИКА, не автора.
```bash
python3 ~/.claude/skills/_shared/bin/account.py status google_flow
```
- `connected` → дальше Шаг 1.
- `missing` → показать онбординг, СТОП, дождаться пока ученик поднимет СВОЙ залогиненный Chrome и войдёт в СВОЙ Google Flow:
  ```bash
  python3 ~/.claude/skills/_shared/bin/account.py onboard google_flow
  ```
  Ученик: поднял Chrome `--remote-debugging-port=9222` (профиль `~/.chrome-cdp-profile`), вошёл в СВОЙ Google, открыл Flow. Затем фиксируем подключение:
  ```bash
  python3 ~/.claude/skills/_shared/bin/account.py set google_flow.connected true
  ```
Проверка живости CDP перед probe/run:
```bash
curl -s --max-time 3 http://localhost:9222/json/version
```
Если CDP не отвечает → сбросить и снова провести ученика по онбордингу (СВОЙ Chrome не поднят). Дальше скилл работает на ЕГО сессии.

### Шаг 1 — probe (ОДИН раз на новый UI Flow, до первого run)
Снять живые селекторы Flow (UI меняется, вслепую не хардкодим):
```bash
~/.business/scripts/auto-uniqualize/python3 scripts/omni_driver.py probe
```
Из вывода (`file_inputs` / `editors` / `buttons` / `videos`) + `probe-flow.png` заполнить `config.json → selectors`. Это и есть момент истины: убедиться, что Omni Flash доступен в аккаунте и принимает video-to-video.

### Шаг 2 — собрать промт
```bash
scripts/build_prompt.py --mode clean --spoken "<дословный текст речи>" --style "<бриф графики>" > /tmp/omni_prompt.txt
# energy:
scripts/build_prompt.py --mode energy --spoken "<текст>" --style "<тема рестайла>" > /tmp/omni_prompt.txt
```

### Шаг 3 — run (загрузка → промт → submit → poll → download)
```bash
~/.business/scripts/auto-uniqualize/python3 scripts/omni_driver.py run \
  --clip <clip.mp4> --prompt-file /tmp/omni_prompt.txt --out <out.mp4>
```
Драйвер трекает СВОЙ baseline (не «новейшее»), ловит rate-limit/quota и останавливается, не долбит.

### Шаг 4 — машинная верификация (гейт перед выдачей)
```bash
scripts/verify_output.py --src <clip.mp4> --out <out.mp4>
```
FAIL по растяжению / пропаже аудио / расхождению длительности = НЕ отдаём, чиним промт/режим.

### Шаг 5 — доставка
Только HTTP-URL через localhost (как в `~/.claude/skills/website/scripts/show-screen.py`), не файловый путь:
```bash
python3 -m http.server <port> --bind 127.0.0.1   # в папке с out.mp4, в фоне
# отдать голый http://localhost:<port>/out.mp4
```

## Fallback (если CDP хрупит / селекторы съехали)
Отдаю готовый промт (`/tmp/omni_prompt.txt`) + клип, ученик рендерит 1 кликом в UI своего Flow и кладёт результат в условленную папку - скилл подхватывает файл с Шага 4 (верификация + доставка). Паттерн как в `replicate-viral/knowledge/heygen-browser.md`.

## Anti-patterns
- ❌ launch_persistent_context / новый профиль / запуск-закрытие Chrome. Только connect_over_cdp к уже поднятому залогиненному Chrome ученика.
- ❌ Хватать «новейшее завершённое» сразу после submit (stale). Только рост СВОЕГО baseline.
- ❌ Отдавать без `verify_output.py` (растяжение/без аудио).
- ❌ Файловый путь в выдаче. Только localhost-URL.
- ❌ Прогонять через Omni реальный UI-скринкаст или абстрактные вставки - это hyperframes/Higgsfield.
- ❌ Долбить при rate-limit. Стоп, ждать сброс (как с image-лимитом Custom GPT).

## Файлы
- `scripts/build_prompt.py` - 5-частный промт (Goal/Input role/Scene/Motion/Constraints), режимы clean/energy
- `scripts/omni_driver.py` - CDP-драйвер: `probe` (снять селекторы) | `run` (загрузка→промт→poll→download)
- `scripts/verify_output.py` - ffprobe-гейт: без растяжения / аудио на месте / длительность
- `config.json` - cdp_url, flow_url, таймауты, selectors (заполнить из probe)
- venv: `~/.business/scripts/auto-uniqualize/.venv`

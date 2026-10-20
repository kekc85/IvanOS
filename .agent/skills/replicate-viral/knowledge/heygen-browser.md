# HeyGen Avatar V через браузер (CDP)

Контекст: HeyGen API-квота = 0 (UI-подписка ≠ API-кредиты, проверено — `remaining_quota:0`, только free credits). Поэтому Avatar V создаём/рендерим через залогиненный Chrome по CDP, не через API.

## Почему копия профиля

Chrome 136+ блокирует `--remote-debugging-port` на ОСНОВНОМ профиле (защита). Обход — полная копия профиля в отдельную папку.

> **OS-заметка (этот блок написан под macOS).** Команды ниже — Mac-специфичные (`/Applications/...`, `~/Library/Application Support/Google/Chrome`, `pkill`). На **Windows** профиль лежит в `%LOCALAPPDATA%\Google\Chrome\User Data`, бинарь — `%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe` (или `C:\Program Files\Google\Chrome\Application\chrome.exe`); запуск: `chrome.exe --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.chrome-cdp-profile"`. На **Linux** — `~/.config/google-chrome`, бинарь `google-chrome`/`chromium`. Это персонально-аккаунтный шаг (свой Chrome + свой HeyGen, BYOA — см. `_shared/bring-your-own-account.md`), а не кросс-платформенный авто-флоу — проще всего fallback: ученик рендерит Portrait в СВОЁМ кабинете HeyGen за 1 клик (вставляет наш скрипт+аудио своим аватаром).

```bash
SRC="$HOME/Library/Application Support/Google/Chrome"
DST="$HOME/.chrome-cdp-profile"
pkill -9 -f "Google Chrome"; sleep 3
rm -rf "$DST"; mkdir -p "$DST"
cp -f "$SRC/Local State" "$DST/Local State"
rsync -a --exclude 'Cache' --exclude 'Code Cache' --exclude 'GPUCache' \
  --exclude 'Service Worker/CacheStorage' "$SRC/Default/" "$DST/Default/"
nohup "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 --user-data-dir="$DST" --profile-directory=Default \
  --no-first-run --no-default-browser-check >/tmp/chrome-cdp.log 2>&1 &
sleep 5; curl -s http://localhost:9222/json/version   # проверка CDP up
```

Полная копия профиля переносит логины (HeyGen, Google, IG). Выборочный копир кук — НЕ переносит сессию (HeyGen держит токен в localStorage/IndexedDB, не только cookies).

## Подключение Playwright (Chrome 149 quirk)

`connectOverCDP` падает с "Browser context management is not supported" если создавать `newPage()` сразу. Обход — переиспользовать существующую вкладку:

```js
import { chromium } from 'playwright-core';
const b = await chromium.connectOverCDP('http://localhost:9222');
const ctx = b.contexts()[0];
const page = ctx.pages()[0] || await ctx.newPage();   // existing page first
```

playwright-core ставится локально: `cd /tmp/cdp-run && npm i playwright-core`.

## Avatar V flow

В HeyGen «Create a new avatar» две карточки:
- **Clone a real person (Avatar V)** — вход ВИДЕО-footage (моторика). Лицо/сцена.
- **Create a virtual character** — вход фото (generic motion).

🔴🔴 Формат рендера: **ШИРОКИЙ Landscape 16:9 (≈3440×1920), НЕ Portrait** (SKILL.md ЗАКОН 5, прецедент Headroom по решению автора). HeyGen в нативном портрете 9:16 кладёт аватар систематически правее центра (замерено: +194px / +18.0% от центра; разброс по кадрам 14px = это не рандом, а как HeyGen компонует портрет → «неровно», слив кредитов на ре-рендеры). В широком кадре аватар у HeyGen по центру → кропим РОВНУЮ портретную колонку 1080×1920 ЛОКАЛЬНО: `python3 scripts/twin-frame.py <wide.mp4> --out <portrait.mp4>` (медиана лица по ВСЕМ кадрам, +0.6%). Эта колонка универсальна: full-screen целиком + кроп в нижнюю панель сплита. **Ре-рендер ради кадрирования ЗАПРЕЩЁН** (портрет всегда смещён, кредиты впустую) — «неровно» лечится локальным ре-кропом, не HeyGen.

## APPLY CUSTOM MOTION — НЕ использовать (тест по решению автора)

Поле `APPLY CUSTOM MOTION (BETA)` в Avatar Shots на движении **разваливает аватар** (лицо плывёт, зубы неестественные) — оставлять ПУСТЫМ. Динамику спикера держим нативной моторикой аватара + монтажом (SKILL.md Фаза 6, канон D1 — движение несут B-roll/cuts, не голова). Кнопка `Motion` (пресет) — пробовать осторожно; кастомное текстовое поле — нет.

**Загрузка лука принимает ВИДЕО (MP4/MOV/WebM), не только фото** (экран «Add more looks»). Открытый тест: оживить Higgsfield-кадр в короткий MP4 и залить как видео-лук — движение запечённое, может держать лицо лучше, чем выдуманный custom motion. Также «Add a scene element» = до 3 рефов на продукты/объекты/одежду поверх стабильного Mix-аватара.

## Лук спикера (как завести фото как аватар)

Можно создать аватар ИЗ фото: Avatar Shots → создать аватар из фото → URL получает `?avatarCreated=true`, фото становится look в `Presenter (Avatar V)`. 🔴 **НО (вердикт по решению автора, SKILL.md Фаза 4.5): вау-СЦЕНУ из Higgsfield в аватар НЕ запекать** — на движении лицо ломается (мультяшность/зубы). Спикер = СТАБИЛЬНЫЙ подкаст-лук (реалистичный Avatar V / Mix реального лица). Higgsfield вау-кадры идут СТАТИЧНЫМИ вставками в монтаж (Фаза 6), не в говорящую голову.

## Fallback (если CDP нестабилен)

CDP-автоматизация HeyGen хрупкая (UI меняется, рендеры ждать). Надёжный fallback: дать УЧЕНИКУ адаптированный скрипт + аудио (OmniVoice), он рендерит Portrait в СВОЁМ кабинете HeyGen за 1 клик (своим аватаром из `accounts.json`) и выносит MP4. Скилл подхватывает файл и идёт в Фазу 5. Не блокироваться на CDP — результат важнее автоматизации.

## IG cookies для ingest за login wall

Экспорт кук из CDP-сессии в Netscape для yt-dlp:
```js
const cks = await ctx.cookies('https://www.instagram.com');
// → Netscape формат → /tmp/ig-cookies.txt
```
```bash
yt-dlp --cookies /tmp/ig-cookies.txt --print "%(upload_date)s\t%(view_count)s\t%(like_count)s" --skip-download "<reel_url>"
```
Внимание: `timeout` отсутствует на macOS — не оборачивать yt-dlp в него (команда паднет). Использовать `--socket-timeout N`.
## 🔴🔴 Chrome 149 — playwright connectOverCDP ПАДАЕТ. Дефолт = СЫРОЙ CDP (0.0, валидировано «выглядит идеально»)

Прецедент reel-DYkcu5AP6nD: `chromium.connectOverCDP('http://localhost:9222')` падает на Chrome 149 с `Protocol error (Browser.setDownloadBehavior): Browser context management is not supported` — playwright дёргает browser-level вызов, которого в Chrome 149 нет. Это перекрывает раздел «Подключение Playwright» выше.

**Рабочий дефолт — минимальный сырой CDP-клиент** (`scripts/cdp.mjs`, Node 22+ global WebSocket, минует browser-level вызовы):
```js
import { CDP, pageWs } from '<skill>/scripts/cdp.mjs';
const { ws } = await pageWs(t=>t.type==='page' && t.url.includes('heygen.com'));
const c=new CDP(ws); await c.connect();
await c.send('Page.enable'); await c.send('Runtime.enable');
await c.evaluate(`location.href`);            // Runtime.evaluate
await c.screenshot('/tmp/x.png');             // Page.captureScreenshot
// клики: Runtime.evaluate el.click() ИЛИ Input.dispatchMouseEvent по getBoundingClientRect center
```
Создать вкладку если 0 page-таргетов: 🔴 **в Chrome 149 `/json/new` ОТКЛЮЧЁН (curl возвращает не-JSON, вкладка не создаётся; прецедент по решению автора).** Создавать через browser-level CDP `Target.createTarget`: взять `webSocketDebuggerUrl` из `/json/version`, `new CDP(bws)`, `await bc.send('Target.createTarget',{url:'https://app.heygen.com/home'})` → по `targetId` найти page-таргет в `/json` и подключиться к его ws. Боевой образец — `~/<твоя рабочая папка ролика>/heygen-full.mjs`. 🔴 **HeyGen-вкладка тяжёлая — RAM-watchdog может убить её между ходами**, поэтому весь флоу «Script to Video → fill → continue → Submit» гнать В ОДНОМ node-процессе (не разбивать на несколько вызовов, иначе вкладка исчезает = `no matching tab`). `curl -X PUT "http://localhost:9222/json/new?..."` оставлен как легаси (на старых Chrome).
Высокий вьюпорт (модалки/кнопки не уходят под сгиб): `Browser.getWindowForTarget` → `Browser.setWindowBounds {width:1600,height:1200}`.

## 🔴🔴 КОРРЕКЦИЯ по решению автора (прецедент GODMOD3, ~100 раундов в тупике) — РЕНДЕР = create-v4 DIRECT, НЕ агентный Video Agent

> Корень потери времени: агентный «Video Agent» (Script-to-Video) на низком балансе НЕ РЕНДЕРИТ - крутит план, пишет в прозе «applying blueprint / credit-related setback / Completed Ns», но `<video>` не отдаёт; легко принять его прозу за hard credit-блок и ложно заключить «нет кредитов» (автор: «дурак, там всё было» - 20 кредитов ХВАТАЛО). 

**ДЕФОЛТ рендера двойника = ПРЯМОЙ редактор `app.heygen.com/create-v4/draft?vt=l&panel=scene`** (Avatar IV; твой аватар и голос (их выбираешь сам в редакторе)):
1. Создать СВЕЖИЙ черновик (Target.createTarget на URL выше). Закрыть модалку Brand Systems (Escape).
2. Залить скрипт в поле Script: `Input.insertText` в сфокусированный contenteditable (НЕ `textContent` - редактор Lexical, прямой textContent игнорится и сцена остаётся «No script»). Скрипт одной строкой (без \n, иначе плодит сцены).
3. Верхняя кнопка `Generate` → модалка «Generate Video» (Resolution 1080p / Format MP4 / Watermark Off) → `Submit`.
4. Рендер идёт server-side, проект появляется в Projects; видео на `/videos/<id>` (id = id черновика). Прямую S3-ссылку (`resourceN.heygen.ai/video/transcode/<id>/<tok>/1920x1080_nocap.mp4`) брать **Network-перехватом** (Network.enable + ловить responseReceived с `heygen-resources|amazonaws|.mp4` в первые секунды загрузки страницы /videos, ДО OOM).
5. Кадрировать локально (twin-frame / swap-panel по лицу) - ЗАКОН 5.

🔴 **create-v4 / AI Studio OOM-роняет ВСЕ вкладки (включая ЖИВЫЕ вкладки автора в его браузере) через ~2-3 CDP-взаимодействия на RAM-узкой машине.** Поэтому: fill+Generate+Submit ОДНИМ быстрым проходом, после Submit вкладку закрыть и поллить server-side, НЕ держать редактор открытым, НЕ делать 3+ взаимодействия подряд. Меньше открытых вкладок = больше шанс пережить.

🔴 **Кредит-блок определять РЕАЛЬНЫМ балансом** (settings → Usage & History «X remaining») + пробой стандартного рендера, НЕ текстом-прозой агента.

Агентный «Script to Video» Video Agent ниже - LEGACY/бэкап (на достаточном балансе может работать), но НЕ дефолт. ⬇️

**[LEGACY] Флоу рендера через «Script to Video» (агентный Video Agent), НЕ AI Studio.** Тяжёлый canvas-редактор AI Studio на RAM-узкой машине OOM-крашит ВСЕ вкладки. Агентный флоу рендерит server-side:
1. home → клик карточку `Script to Video` (реальным mouse-click по координатам центра, React).
2. Вставить скрипт в `[role=dialog] textarea` (native value setter + `input` event), `Continue`.
3. На шаге 2 выбрать аватар+голос УЧЕНИКА — имена читать из `accounts.json` (`heygen.avatar_name` / `heygen.voice_name`, helper `account.py get heygen.avatar_name`), НЕ хардкод автора курса. Если в кабинете ученика они уже дефолтны из прошлой сессии — оставить, иначе выбрать его аватар/голос по имени. Опц. `Instructions` = «чистая говорящая голова, ШИРОКИЙ ландшафт 16:9, аватар точно по центру, без b-roll/субтитров/музыки (НЕ портрет 9:16, ЗАКОН 5)».
4. `Continue` → композер «Say it with video» → `Submit` (aria-label, ~правый низ) → создаётся `/video-agent/<id>`, статус 0→100% server-side.
5. **Скачать БЕЗ кнопки Download:** видео-агент держит сцены отдельными mp4 на `heygen-resources-prod.s3-...amazonaws.com` (presigned, ~7 дней). Достать `document.querySelectorAll('video')` → `.src` (http, не blob) → `curl` каждую → `ffmpeg concat` = полный talking-head. Аудио = НАТИВНОЕ 48к (не whisper-16к).
   - ✅ Это нужный режим (ЗАКОН 5): просим ШИРОКИЙ ландшафт 16:9 (НЕ портрет), агент рендерит ~3440x1920 с аватаром по центру → кропим РОВНУЮ портретную колонку 1080x1920 ЛОКАЛЬНО `scripts/twin-frame.py` (медиана лица YuNet по ВСЕМ кадрам, не 1-3 сэмпла = нет дрейфа). НЕ просить портрет 9:16 — нативный портрет HeyGen смещён +18% вправо. Финал → `scripts/twin-centering-check.py` PASS.
   - ⚠️ S3-ссылки presigned ~7 дней — качать в ту же сессию, не откладывать.

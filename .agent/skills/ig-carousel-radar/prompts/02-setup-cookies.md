# One-time setup: IG cookies + seed lists

> 🔒 **BYOA (bring-your-own-account):** cookies = ТВОЯ IG-сессия, не автора курса. Сначала
> `python3 ~/.claude/skills/_shared/bin/account.py status instagram`; если `missing` →
> `account.py onboard instagram`, затем headed-login ниже. Канон — `_shared/bring-your-own-account.md`.

**Default flow:** auto-bootstrap. Запусти `python3 scripts/radar.py` - skill сам вызовет `scripts/setup.py` если cookies / seeds отсутствуют.

`setup.py` делает 3 шага:
1. Bootstrap seed YAML files если missing (watchlist + hashtags с дефолтными значениями)
2. Headed Chromium login - открывает IG login UI, ученик логинится руками в СВОЙ IG (вкл. 2FA), script ждёт landing на feed → сохраняет ЕГО cookies автоматически в `~/.business/processes/.ig-cookies.json` с chmod 600
3. Dry-run validation (1 sample per mode)

После - `radar.py` запускается нормально.

**Re-run setup** при cookie expiry (~90 дней) или major IG account change: `rm ~/.business/processes/.ig-cookies.json && python3 scripts/setup.py`.

---

## Manual fallback (если auto-setup не сработал)

Делается один раз. Re-run при cookie expiry (~90 дней) или major IG account change.

## 1. IG cookie export

**Зачем:** IG headless требует logged-in session. Cookies = auth credential.

**Шаги:**

1. Открой Chrome (или любой Chromium браузер)
2. Залогинься в `https://instagram.com` в СВОЙ аккаунт
3. Установи extension [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) (если ещё нет)
4. На странице instagram.com → клик extension icon
5. Бутон "Export" (правый верх) → формат "JSON"
6. Скопируй JSON → сохрани в файл:

```bash
mkdir -p ~/.business/processes
# Вставь JSON через VS Code или nano:
code ~/.business/processes/.ig-cookies.json
# или
nano ~/.business/processes/.ig-cookies.json

# Защити permissions
chmod 600 ~/.business/processes/.ig-cookies.json
```

7. Проверь что файл валидный JSON и не пустой:

```bash
python3 -c "import json; d=json.load(open(@'~/.business/processes/.ig-cookies.json'.replace('@','').replace('~', __import__('os').path.expanduser('~')))); print(f'cookies loaded: {len(d)}')"
```

Должно быть `cookies loaded: 15+` (IG ставит много cookies).

**Security:** cookies даёт ПОЛНЫЙ доступ к ТВОЕМУ IG account. Файл chmod 600 + НЕ commit в git + .gitignore. Папка `.business/` уже в gitignore по умолчанию. Это твоя сессия, в дистрибутив её куки не попадают.

## 2. Watchlist seed (~/.business/growth/watchlist-en.yml)

**Зачем:** Mode B sweep по конкретным handles. Твоя курация решает топик-релевантность.

```bash
mkdir -p ~/.business/growth
code ~/.business/growth/watchlist-en.yml
```

Шаблон:

```yaml
# автор - IG watchlist EN
# Конкуренты + reference creators в vibemarketing / vibecoding / AI tools / solopreneur
# Update quarterly (Q1 / Q2 / Q3 / Q4)

handles:
  # Reference creators (авторские alpha refs)
  - rileybrown_ai
  - sabrina.ramonov
  - heatherbcooper

  # Solopreneur / indie hackers
  - levelsio
  - greg.isenberg
  - marc_louvion

  # Add 10-20 total. Прочитай ~/.business/marketing/competitors.md
  # перед добавлением - не дублировать research
```

**Source-of-truth check** per:
- Перед добавлением handle → grep `~/.business/marketing/competitors.md` есть ли он там
- Если есть - copy с тем же контекстом (роль, ниша)
- Если нет - добавить и в competitors.md ОДНОВРЕМЕННО

## 3. Hashtags seed (~/.business/growth/hashtags-en.yml)

**Зачем:** Mode C sweep по тегам. Discovery новых creators которые не в watchlist.

```bash
code ~/.business/growth/hashtags-en.yml
```

Шаблон:

```yaml
# автор - IG hashtags EN
# 5-10 tags максимум. Узкая ниша лучше широкой.

tags:
  - vibecoding
  - vibemarketing
  - aitools
  - claudecode
  - aimarketing
  - indiehacker
  - solopreneur
  - aiautomation
```

**Anti-pattern:** не клади generic tags типа `#marketing` / `#business` - там 100K posts/day, noise > signal.

## 4. First run (dry verification)

```bash
cd ~/.claude/skills/ig-carousel-radar
python3 scripts/radar.py --dry-run
```

Если `.venv/` отсутствует (свежий clone skill) - bootstrap:

```bash
cd ~/.claude/skills/ig-carousel-radar
python3 -m venv .venv
pip install playwright pyyaml
python3 -m playwright install chromium
```

`--dry-run` mode: запустит auth check + 1 scroll feed + 1 watchlist handle + 1 hashtag → проверит парсинг работает, без полного прогона.

Должно вывести что-то вроде:

```
[OK] cookies loaded (15 entries, age 0d)
[OK] watchlist: 6 handles
[OK] hashtags: 8 tags
[OK] feed mode: 3 carousels found in 1 scroll
[OK] watchlist mode: 2 carousels found in 1 profile
[OK] hashtag mode: 5 carousels found in 1 tag
[OK] auth healthy, all 3 modes functional
[DRY-RUN] skipping filter+digest write
```

Если ошибка - см. `prompts/01-run-radar.md` секция "Error handling".

## 5. Real first run

```bash
python3 scripts/radar.py
```

Полный прогон. Может занять 5-15 минут (зависит от config volumes).

После - `prompts/03-tune-thresholds.md` (по результату первого digest tune COMMENTS_THRESHOLD).

## 6. (Optional) Cron schedule

Через `schedule` skill:

```
/schedule create ig-carousel-radar
cron: 0 8 * * *  (every day 08:00)
action: cd ~/.claude/skills/ig-carousel-radar && python3 scripts/radar.py
```

Или через `loop` для интерактивного recurring.
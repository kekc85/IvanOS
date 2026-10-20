# Фаза 03: делегировать скрипт скиллу video + outcome-гейт + humaniser

Цель: получить скрипт в голосе автора не переписывая скриптинг руками (его движок - скилл `video`, mode Replication). Скилл-оркестратор ВЫЗЫВАЕТ `video`, забирает скрипт + chapter map + headline + outro, и накрывает финальными гейтами: outcome-language, mastery-линза, humaniser. CTA - по роли из фазы 00

## Вход

`$PROJECT_DIR` + `$INGEST_DIR` + `VIDEO_ID` из фазы 02 (папка в `~/.business/growth/ingest/` готова, card.md принят). Роль из фазы 00 (`project.json`)

## Шаги

1. **Засечь метку времени В ФАЙЛ (переживает между bash-вызовами), затем делегировать скрипт скиллу `video`:** `date +%s > "$PROJECT_DIR/.before"`, потом `Skill('video')` с аргументом `replicate <VIDEO_ID> --length long-10-60min`. video сам резолвит id через `ls ~/.business/growth/ingest/`, читает card.md ОТТУДА (Mode C, 01c) и пишет скрипт в голосе автора со своим voice+humaniser-стеком. Тир long-10-60min помечен у video как experimental v1.0 - если скрипт выйдет слабым по удержанию, добрать mastery-линзой (шаг 3) поверх, а не переписывать вручную

2. **Забрать скрипт от video и СОХРАНИТЬ в проект.** video пишет скрипт в СВОЙ архив `~/.business/growth/scripts/<date>-<slug>.md` (slug = первые 4 слова заголовка video) + отдаёт путь/текст в чат. Скопировать его в `$PROJECT_DIR/script.md` (единый якорь, чтобы фаза 04 читала из известного места). Чтобы НЕ взять чужой свежий .md - засечь метку ДО вызова video и брать файл новее её (а не слепой `head -1`):
   ```bash
   BEFORE=$(cat "$PROJECT_DIR/.before")   # метка из шага 1 (в файле, пережила между вызовами)
   SRC=$(find ~/.business/growth/scripts -name '*.md' -newermt "@$BEFORE" 2>/dev/null | head -1)
   [ -z "$SRC" ] && SRC=$(ls -t ~/.business/growth/scripts/*.md | head -1)  # fallback
   cp "$SRC" "$PROJECT_DIR/script.md"
   jq --arg s "$PROJECT_DIR/script.md" '.script_path=$s' \
      "$PROJECT_DIR/project.json" > "$PROJECT_DIR/.pj" && mv "$PROJECT_DIR/.pj" "$PROJECT_DIR/project.json"
   ```
   Если video явно назвал путь архива в чате - взять его напрямую (надёжнее find). `chapter_map` (главы 5-9) video отдаёт в handoff-brief текстом (для long-tier production = manual, отдельного объекта нет) - извлечь главы и дописать в `$PROJECT_DIR/script.md` секцией `## Главы` (5-9 строк), опора storyboard (фаза 04). Проверить: число глав в коридоре 5-9

3. **Mastery-линза** (по `knowledge/mastery-application.md`, регламент `mastery/PROTOCOL.md`): прогнать скрипт через мастеров удержания и сторителлинга (`virality-attention`: MrBeast / Thompson / Peretti · `storytelling`: McKee / Snyder · `public-speaking`: Chris Anderson). Каждый применённый метод - с цитатой мастера; нет цитаты = линза не применена (FAIL). Усилить хук и мини-хуки глав там, где удержание проседает. **Портируемость:** если папки `mastery/` нет (ученик без корпуса автора) - линза ОПЦИОНАЛЬНА, не блокирует фазу; опереться на `knowledge/mastery-application.md` (методы вшиты в скилл с цитатами) как минимальную базу

4. **Outcome-language-гейт** (жёсткий, финальная сверка поверх video). Грепнуть финальный скрипт на запрещённые слова в outcome-формулировках для ЦА:
   ```bash
   grep -nE "программир|MVP|SaaS|приложени|разработчик" "$PROJECT_DIR/script.md"
   ```
   В обещании результата зрителю этих слов быть НЕ должно - только «мини-продукт» / «цифровой продукт эксперта» (voice-profile канон). Совпадение в outcome для ЦА = переписать формулировку. Термины допустимы только когда речь про инструмент/процесс, не про результат зрителя

5. **CTA по роли** (закон №8, скилл роли НЕ смешивает):
   - **`acquisition`** → CTA = лид-магнит + код-слово в комменты
   - **`launch-lead-magnet`** → единственное действие = РЕГИСТРАЦИЯ, ноль код-слова и домашки
   acquisition-CTA в launch-ролике (и наоборот) = брак, проверить соответствие явно

6. **Humaniser финал + стиль хука/CTA автора** (`Skill('humaniser')`, формат-тройка): без нейроклише · без длинных тире (только дефис) · без точки в конце абзаца. Плюс позитивная сверка хука/CTA против стиля автора: хук = broad pattern-interrupt в кошелёк зрителя (не нишевые названия в 1-й строке), цифры простые человеческие, CTA склеивает оффер+лид-магнит+код-слово в ОДИН заход. Обязательный проход перед storyboard

## Выход

- `$PROJECT_DIR/script.md` - финальный скрипт в голосе автора (прошёл outcome-гейт + mastery + humaniser) + секция `## Главы` (5-9) + headline + outro + CTA под роль
- `script_path` записан в `project.json`

## Гейт

Дальше только когда: скрипт прошёл outcome-language-гейт (grep чистый в outcome-формулировках) + humaniser (формат-тройка) + mastery применена с цитатами; chapter map существует и в коридоре 5-9 глав; CTA соответствует роли. Нет улики прогона (вывод grep, отчёт линзы) = не заявлять «готово»

→ Дальше: `prompts/04-visual-storyboard.md`
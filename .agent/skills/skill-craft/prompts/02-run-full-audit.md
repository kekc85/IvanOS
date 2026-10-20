# Полный аудит скилла: алгоритм

Используется когда пользователь говорит "проверь скилл <имя>" или "/qa-skill <имя>".

## Шаг 0. Резолв имени скилла

```bash
SKILL_NAME="<имя>"
SKILL_PATH="/Users/$USER/.claude/skills/$SKILL_NAME"

# Проверить что существует
test -d "$SKILL_PATH" || echo "FAIL L1.0: папка скилла не существует"
```

## Шаг 1. L1 - Structural Integrity (детерминированно)

```bash
# 1.1. SKILL.md существует
test -f "$SKILL_PATH/SKILL.md" || echo "FAIL L1.1: нет SKILL.md"

# 1.2. YAML frontmatter валиден
python3 -c "
import re, yaml, sys
with open('$SKILL_PATH/SKILL.md') as f:
    content = f.read()
m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
if not m:
    print('FAIL L1.2: нет frontmatter')
    sys.exit(1)
try:
    fm = yaml.safe_load(m.group(1))
    assert 'name' in fm, 'нет поля name'
    assert 'description' in fm, 'нет поля description'
    assert fm['name'] == '$SKILL_NAME', f\"name='{fm['name']}' не совпадает с папкой '$SKILL_NAME'\"
    desc_len = len(fm['description'])
    if desc_len < 80:
        print(f'WARN L1.2: description слишком короткий ({desc_len} симв)')
    elif desc_len > 500:
        print(f'WARN L1.2: description слишком длинный ({desc_len} симв)')
    else:
        print('PASS L1.2: frontmatter корректный')
except Exception as e:
    print(f'FAIL L1.2: {e}')
"

# 1.3. Описание содержит триггерные фразы
grep -i 'когда срабатывать\|trigger\|используй когда\|use when\|use this when' "$SKILL_PATH/SKILL.md" > /dev/null \
  && echo "PASS L1.3: триггеры есть в SKILL.md" \
  || echo "WARN L1.3: явных триггеров в SKILL.md не найдено"

# 1.4. Структура папок (knowledge/, prompts/, examples/ - опционально)
for sub in knowledge prompts examples; do
  if [ -d "$SKILL_PATH/$sub" ]; then
    count=$(find "$SKILL_PATH/$sub" -name "*.md" | wc -l)
    echo "INFO L1.4: $sub/ - $count файлов"
  fi
done

# 1.5. Cross-references целы (v1.2: placeholder whitelist + контекст)
python3 << PYEOF
import os, re, glob
skill_path = '$SKILL_PATH'

# Placeholders которые НЕ нужно резолвить — типичные template-шаблоны.
PLACEHOLDER_PATTERNS = [
    r'^X\.md$',                # просто "X.md"
    r'^<[^>]+>\.md$',          # <skill>.md, <name>.md
    r'^\{[^}]+\}\.md$',        # {name}.md
    r'^.*<[^>]+>.*\.md$',      # audit-<skill>-<date>.md
    r'^.*X\.md$',              # knowledge/X.md, prompts/X.md
]

def is_placeholder(ref):
    return any(re.match(p, ref) for p in PLACEHOLDER_PATTERNS)

broken = []
placeholders_seen = 0
for md_file in glob.glob(f'{skill_path}/**/*.md', recursive=True):
    with open(md_file) as f:
        content = f.read()
    refs = re.findall(r'\`([\w\-/<>\{\}\.]+\.md)\`', content)
    for ref in refs:
        if ref.startswith('http'): continue
        if is_placeholder(ref):
            placeholders_seen += 1
            continue
        candidate = os.path.join(os.path.dirname(md_file), ref)
        if not os.path.exists(candidate):
            candidate2 = os.path.join(skill_path, ref)
            if not os.path.exists(candidate2):
                broken.append((md_file.replace(skill_path + '/', ''), ref))
if broken:
    print(f'WARN L1.5: битые cross-references ({len(broken)}), placeholders skipped: {placeholders_seen}:')
    for src, ref in broken[:5]:
        print(f'  {src} -> {ref}')
else:
    print(f'PASS L1.5: ссылки корректны (placeholders skipped: {placeholders_seen})')
PYEOF

# 1.6. Размеры файлов разумные
find "$SKILL_PATH" -name "*.md" -size +50k -exec echo "WARN L1.6: большой файл {}" \;
find "$SKILL_PATH" -name "*.md" -size -100c -exec echo "WARN L1.6: подозрительно маленький файл {}" \;
```

## Шаг 2. L2 - Content Quality (LLM-as-judge — ОБЯЗАТЕЛЬНО)

L2 НЕ ограничивается grep'ом. Семантическая оценка обязательна.

### 2.1. Deterministic checks (grep / regex)

```bash
# TODO/placeholder
grep -rn -i "TODO\|fixme\|\[заполнить\]\|\[fill\]\|\.\.\." $SKILL_PATH/ | head -10

# Em-dash (memory feedback-no-em-dash) — не в начале bullet
grep -n '—' $SKILL_PATH/SKILL.md | grep -v -E '^\s*[0-9]+:\s*[-*+]\s*—'

# Конкретные конкуренты (memory feedback-no-attacking-competitors)
grep -i 'аяз\|ayaz\|афонина\|smm school\|skillbox' $SKILL_PATH/

# Жаргон/англицизмы запрещённые (memory feedback-no-tech-jargon)
grep -i 'grand slam\|fast-action\|digital-twin\|фасилитация' $SKILL_PATH/
```

### 2.2. LLM-as-judge (АКТИВНО, не декларативно)

Прочитать SKILL.md + все prompts/*.md + все knowledge/*.md и явно оценить по критериям:

```markdown
You are auditing a Claude Code skill. Read the files and answer YES/NO with short reasoning:

1. **Полнота режимов**: каждый режим из SKILL.md имеет соответствующий prompt/knowledge файл с полной инструкцией? List missing.
2. **Семантическая логика workflow**: есть ли шаги которые «snapshot» вместо «active probe»? (например «проверить логи последние N строк» вместо «watch logs N минут»)
3. **Coverage edge cases для типа skill**: для TG-бот скилла — упомянуты ли permissions/bind mount, MIME discrimination, FSM state? Для frontend — loading/error/empty states? (См. `knowledge/bug-categories.md`)
4. **Достоверность фактов**: цифры, ставки, имена пакетов с версиями — реалистичные на момент создания?
5. **Актуальность**: даты разумные, есть ли «точки устаревания» (review_deps_every:)?
6. **Tone match user memories**: соответствует личным предпочтениям пользователя (читай memory feedback-* в `~/.claude/projects/<твой-проект>/memory/`)?
7. **Universal vs personal**: если skill universal — нет ли жёсткой привязки к автору? Если personal — явно ли это объявлено в description?

Output: список semantic findings с уровнем severity + почему.
```

### 2.3. Memory cross-check

Прочитать `~/.claude/projects/<твой-проект>/memory/MEMORY.md` index, найти все feedback-правила, проверить каждое в контексте skill:

```bash
# Список feedback правил

# Для каждого — Read и mental check соответствия
```

## Шаг 3. L3 - Trigger Engineering

1. **Извлечь триггеры из description:**
   ```python
   import yaml, re
   with open(f'{SKILL_PATH}/SKILL.md') as f:
       fm = yaml.safe_load(re.match(r'---\n(.*?)\n---', f.read(), re.DOTALL).group(1))
   desc = fm['description']
   ```
2. **Сгенерировать тестовый датасет:**
   - 10 положительных формулировок (должны запустить скилл)
   - 5 отрицательных (не должны)
3. **Проверить покрытие:**
   - Содержит ли description ключевые слова из положительных?
   - Достаточно ли он специфичен чтобы не сработать на отрицательные?
4. **Дискриминативность с другими скиллами:**
   - Прочитать descriptions других скиллов в namespace
   - Найти возможные overlaps

## Шаг 4. L4 - Workflow Coverage + Bug-category matrix

1. **Для каждого режима из SKILL.md:**
   - Прочитать соответствующий prompt-файл
   - Проверить что есть: вход, шаги, выход
   - Проверить error handling (что если что-то пошло не так)
   - Проверить hand-off points (когда нужен человек)

2. **Bug-category matrix (НОВОЕ v1.1):**
   - Прочитать `~/.claude/skills/qa-skill/knowledge/bug-categories.md`
   - Detect type of audited skill: TG-бот / Frontend / Backend / CLI / ETL / QA
   - Для каждой категории из matrix — проверить упомянута ли в skill workflow:
   ```bash
   # Пример для TG-бот skill
   for cat in 'permissions\|bind mount' 'MIME' 'rotation' 'subscription' 'rate limit' 'timeout' 'FSM'; do
       grep -i "$cat" $SKILL_PATH/SKILL.md > /dev/null && echo "  ✓ $cat" || echo "  ✗ $cat MISSING (применимо для TG-бот)"
   done
   ```
   - Каждая missing категория = important finding L4.

3. **Decision trees:**
   - Все if/then ветки имеют ответ для каждой ветки?

4. **Edge cases в prompts:**
   - Упомянуты ли empty inputs, конфликтные inputs, timeout-ы?

## Шаг 5. L5 - End-to-End Simulation (АКТИВНАЯ, не manual review)

Для каждого режима skill:

1. **Active dispatch simulation:**
   - Если skill имеет slash-command (например `/qa-process`) — мысленно (или в отдельной Claude-сессии) подать команду + типичный input
   - Зафиксировать: какие файлы Claude прочитает? Какие команды выполнит? Какой output?

2. **Real-world reference check:**
   - Прочитать `examples/track-record-<skill>.md` если есть
   - Если есть прежние применения — сравнить ожидаемый output с записанным

3. **Bug-hunt simulation:**
   - Сгенерировать «троянский» input: контент с проблемой которую skill должен поймать
   - Пройти по prompt'ам и оценить — поймает ли skill эту проблему?
   - Например для qa-process: «есть ли в skill чек-лист который ловит permissions bug на bind mount?»

4. **Output evaluation:**
   - Релевантен входу?
   - Полный (все expected поля)?
   - Без галлюцинаций (нет фактов которых нет в knowledge base)?
   - Tone match user memories?

## Шаг 6. L6 - Safety & Compliance

1. **Этические границы:**
   - Грэп по SKILL.md и prompts: есть ли упоминание отказов от malicious requests?
   - Есть ли upholding принципов (например для аудит-инструмента: "не для атаки на чужие сайты")?
2. **Privacy:**
   - Если работает с чувствительными данными - упомянуты ли требования к согласию?
3. **Дисклеймеры:**
   - Если скилл выдаёт material advice - есть ли дисклеймер?
4. **Prompt injection resistance:**
   - Если есть точки приёма user input - есть ли sanitization?

## Шаг 7. L7 - Maintenance

1. **Версионность:**
   - grep по датам ("2024", "2025", "2026") - помечены ли как точки устаревания?
2. **Documentation для обновлений:**
   - Указано ли куда смотреть когда нормы изменятся?
3. **Examples freshness:**
   - Когда последний раз обновлялись?

## Шаг 8. Формирование отчёта

Формат отчёта - см. ниже.

```markdown
# Аудит скилла: <name>
Дата: <YYYY-MM-DD>
Версия методологии: 1.0

## Сводка

| Уровень | Статус | Находок | Критичных |
|---|---|---|---|
| L1 Structural | ... | N | M |
| L2 Content | ... | ... | ... |
| ... | ... | ... | ... |

## Вердикт

[ ] ✅ READY TO PUBLISH
[ ] ⚠️ NEEDS FIXES
[ ] ❌ NOT READY
[ ] 🚨 DANGEROUS (есть FAIL на L6)

## Детальные находки

### L1.X. [Название]
- Что: ...
- Где: ...
- Как починить: ...
- Приоритет: critical / important / minor

## Action plan
1. ...
2. ...

## Recommendations beyond fixes
- ...
```

## Шаг 9. Сохранение отчёта

```bash
DATE=$(date +%Y-%m-%d)
mkdir -p $SKILL_PATH/../qa-skill/examples
cp /tmp/audit_report.md "$SKILL_PATH/../qa-skill/examples/audit-$SKILL_NAME-$DATE.md"
```

## Шаг 10. Опционально - фиксация найденных проблем

Если пользователь просит "найди и почини" - после выдачи отчёта переходим к исправлению критичных и важных находок.
# Формат итогового отчёта аудита

Используется после прогона `01-run-full-audit.md` для генерации reproducible markdown-отчёта.

## Файл назначения

```
~/.claude/skills/qa-skill/examples/audit-<skill_name>-<YYYY-MM-DD>[-vN].md
```

При повторном прогоне в тот же день — добавляется суффикс `-v2`, `-v3` и т.д.

## Шаблон

```markdown
# Аудит скилла: <name>
Дата: <YYYY-MM-DD>
Версия методологии: <qa-skill version>
Аудитор: Claude через `/qa-skill <name>`
Предыдущий отчёт (если есть): <link>

## Сводка

| Уровень | Статус | Critical | Important | Minor |
|---|---|---|---|---|
| L1 Structural | PASS/WARN/FAIL | N | N | N |
| L2 Content | ... | ... | ... | ... |
| L3 Trigger | ... | ... | ... | ... |
| L4 Workflow | ... | ... | ... | ... |
| L5 E2E | ... | ... | ... | ... |
| L6 Safety | ... | ... | ... | ... |
| L7 Maintenance | ... | ... | ... | ... |

## Вердикт

[ ] ✅ READY TO PUBLISH (все PASS, max WARN на L7)
[ ] ⚠️ NEEDS FIXES (WARN на L2-L6 или FAIL на L7)
[ ] ❌ NOT READY (FAIL на L1-L5)
[ ] 🚨 DANGEROUS (FAIL на L6)

## Что починено между прогонами (если v2+)

| Issue (audit vN) | Статус | Доказательство |
|---|---|---|
| L2.2 em-dash 22 раза | ✅ closed | grep -c '—' = 0 |
| ... | ... | ... |

## Детальные находки

### LX.Y - <Название>
- **Что:** описание проблемы одним предложением
- **Где:** файл:строка (если применимо)
- **Как починить:** конкретное действие или команда
- **Приоритет:** critical / important / minor
- **Категория** (для bug-categories.md): permissions / race / network / encoding / I/O / state-mgmt / semantic / etc

## Action plan

1. Critical: ... (block publish)
2. Important: ... (block release но не emergency)
3. Minor: ... (улучшение, не блокирует)

## Track record update

**Что aqa-skill поймал:** список реальных проблем
**Что aqa-skill пропустил** (если выявилось позже): добавить в `examples/track-record-<skill>.md` с описанием почему пропустил и как улучшить методологию

## Recommendations beyond fixes

- Стратегические улучшения
- Идеи для следующего ревью
- Когда следующий audit

## Метаурок (опц.)

Если аудит выявил что-то о самом qa-skill (gap в методологии, false positive в детекторах) — фиксируем здесь, обновляем `knowledge/methodology.md`.
```

## Критерии классификации находок

**Critical** — блокирует публикацию:
- FAIL на L1 (нет SKILL.md, невалидный frontmatter, битые ссылки)
- FAIL на L6 (Safety/Compliance issue)
- Нарушение явного user-memory правила (em-dash, attack on competitors, привязка к автору в universal skill)

**Important** — блокирует релиз, но не emergency:
- WARN на L1-L4
- Semantic gaps (логика workflow слабая хоть и грамматически OK)
- Missing categories из bug-coverage matrix

**Minor** — улучшение качества, не блокирует:
- WARN на L7
- False positive в детекторах (с обоснованием)
- Стилистические замечания

## Self-test handling

При прогоне qa-skill через сам себя — false positives возможны (см. SKILL.md «Примечание о self-test»). В отчёте явно отмечать какие находки являются self-test artifact, не реальной проблемой.
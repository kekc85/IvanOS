# Профиль площадки: ДЗЕН - ПЕРЕЕХАЛ

🔴 Этот файл больше не канон. по решению автора Дзен выделен в собственный движок `dzen-engine`:
у площадки другой закон дистрибуции (лента платит за дочитывания, а не за пользу), поэтому
общий конвейер площадок ему мал

**Правила, лимиты, эталоны и чек-лист Дзена:**

| Что | Где |
|---|---|
| Правила площадки, лимиты, санкции, чек-лист публикации | `~/.claude/skills/dzen-engine/knowledge/platform-rules.md` |
| Эталоны топов, паттерны, хуки, анти-паттерны | `~/.claude/skills/dzen-engine/knowledge/etalony-dzen.md` |
| Как писать под Дзен (формат, герой, хук, структура) | `~/.claude/skills/dzen-engine/knowledge/redaktura.md` |
| Порядок сайт → Дзен, разведение запросов | `~/.claude/skills/dzen-engine/knowledge/syndication-dzen.md` |
| Чекер лимитов | `~/.claude/skills/dzen-engine/tools/dzen-limits-check.py` |
| Контракт версий с SEO-движком | `~/.claude/skills/dzen-engine/CONTRACT.md` |

**Что делать при дзен-задаче:**

```bash
python3 ~/.claude/skills/dzen-engine/tools/sync-check.py --role consumer
```

затем `Skill('dzen-engine')`

Правки дзен-правил вносить ТОЛЬКО в `dzen-engine`. Копия правил в двух скиллах = рассинхрон
через месяц, поэтому здесь оставлен указатель, а не текст

Прежнее содержимое этого файла (профиль от в даты запуска.2026) целиком перенесено
в `dzen-engine/knowledge/platform-rules.md` без потери фактуры

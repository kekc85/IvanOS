# README.md template

Структура файла который генерируется в каждой output папке.

## Шаблон

```markdown
# Visual research: <query>

**Date:** YYYY-MM-DD
**Mode:** person / event / news
**Query:** <as user typed it>
**Disambiguated:** <person name + company/role | event name + year | topic + window>

## Summary

<1-2 предложения: что нашли, какой top recommendation для использования>

## Files

### <filename-1>.{png,jpg}
- **Source:** <full URL>
- **Author/Photographer:** <name if known>
- **License:** <PD / CC-BY / CC-BY-SA / Editorial use only / Press kit / UNKNOWN>
- **Date taken:** <YYYY if known>
- **Use:** ✅ <where OK> / ❌ <where NOT OK>
- **Notes:** <quality / ракурс / context>

### <filename-2>.{png,jpg}
...

## Suggested use

- For post on <platform>: use <file-N> because <reason>
- For carousel slide: use <file-N>
- For b-roll in video: use <file-N>
- Avoid for <use case>: <reason>

## Source hierarchy walk

1. Wikipedia: <result>
2. Wikimedia Commons: <result>
3. Official site: <result>
4. Google Images: <result>
5. ...

## Caveats

- <staleness check: photos from YYYY may be outdated>
- <license uncertainties to verify>
- <recommended next step if автор хочет deeper search>

## Related content angles

(Только для Mode C news)
- Angle 1: <one-liner content idea>
- Angle 2: ...
```

## Минимальный required block

Если skill спешит (single quick query) — минимум:

```markdown
# <query> — visual research <date>

## Files
- <file>: <source URL>, <license>, ✅/❌ commercial use

## Suggested
<one-liner>
```

Но full template — default для всех runs >2 files.

## Anti-patterns в README

- ❌ Не писать «See files» без описания каждого — теряется context
- ❌ Не оставлять License: UNKNOWN без явной flag-string «verify before use»
- ❌ Не давать "use" recommendation без license check
- ❌ Не предлагать commercial use если license CC-BY-NC
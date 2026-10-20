# Фаза 2. Telegram

Этот референс читается, когда в собираемом архиве есть Telegram. Два пути: Apify (дефолт, автоматический) и @ToCsvBot (ручной fallback для ретро без Apify-бюджета).

## Путь A. Apify `truefetch/telegram-channel-message` (дефолт)

```python
input = {
    "telegram_url": "https://t.me/<handle>",
    "start_date": f"{<число_дней_из_режима>} days",
    "max_results": 1500,
    "download_medias": "text"
}
```

Запуск через `mcp__Apify__call-actor` с `async: true`. Через 30–60 секунд фетч датасета через прямой API URL (см. `references/instagram-apify.md` Шаг 1.3 или `references/utilities.md`).

### Группировка альбомов программно по `album_id`

```python
albums, singles = {}, []
for it in items:
    if it['type'] == 'Service':
        continue
    aid = it.get('album_id')
    if aid:
        albums.setdefault(aid, []).append(it)
    else:
        singles.append(it)

records = list(singles)
for aid, group in albums.items():
    with_text = [g for g in group if (g.get('text') or '').strip()]
    chosen = with_text[0] if with_text else min(group, key=lambda x: x['id'])
    records.append(chosen)
```

Почему программно: Apify-датасет отдаёт альбом несколькими сообщениями с общим `album_id`. Брать первое — теряешь подпись (она обычно во втором или третьем). Берём то, у которого `text` непустой; если у всех пусто — то с минимальным `id`. Service-сообщения (вход/выход участников, закрепы) исключаем.

### Маппинг TG → frontmatter

| Поле frontmatter | Источник |
|---|---|
| `id` | `id` как строка |
| `network` | `Telegram` |
| `type` | `пост` |
| `status` | `новый` |
| `url` | `https://t.me/<handle>/<id>` |
| `caption` | `''` (у TG нет отдельной подписи) |
| `recognized_text` | `text` (`truncate_utf16(text, 1990)`). Если `text` пустой — оставляй пустым, это медиа-без-подписи. |
| `likes` | `sum(reactions.values())` или 0 |
| `comments` | `reply_count` |
| `shares` | `forward_count` |
| `viewers` | `view_count` |
| `published` | `date[:10]` |
| `author` | handle |
| `saves`, `reach`, `hypothesis` | пусто/0 |
| `scanned`, `updated` | сегодняшняя дата ISO |

Поле `published_tg` не пишем — база знаний Date-поле парсит обычную дату нормально, fallback из эпохи Notion больше не нужен.

## Путь B. @ToCsvBot CSV (fallback для ретро без Apify-бюджета)

Для эксперта без Apify-бюджета. Эксперт сам идёт в Telegram → @ToCsvBot → `<URL канала> по решению автора` → получает CSV → даёт тебе в чат как файл-аплоад.

После получения CSV — парси через pandas в bash, маппь по той же таблице, что и Путь A. Дедупликации альбомов программно нет — ToCsvBot уже сгруппировал.

Только для ретро-режима. В инкрементальном режиме ToCsvBot путь не используется — он требует ручного шага эксперта (поход в Telegram), а смысл инкрементального обновления — автоматизм.

# Утилиты

Этот референс читается, когда нужно вставить в скрипты-однострочники типовые helper-функции: UTF-16 обрезку, фетч Apify-датасета по прямому API, поиск файла по `id`, точечный апдейт метрик через python-frontmatter.

## UTF-16 безопасная обрезка

Применяется к длинным текстовым полям (`caption`, `recognized_text`). Лимит 1990 UTF-16 units выбран с запасом под миграцию в БД с жёстким лимитом 2000.

```python
def truncate_utf16(s, max_units=1990):
    if len(s.encode('utf-16-le')) // 2 <= max_units: return s
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if len(s[:mid].encode('utf-16-le')) // 2 <= max_units: lo = mid
        else: hi = mid - 1
    return s[:lo]
```

## Прямой Apify-API helper с ретраями

Для случаев, когда run ещё не закончил writeback в датасет — пустой массив возвращается, ждём и повторяем.

```python
import urllib.request, json
def fetch_dataset(runId, max_retries=5, sleep_s=10):
    import time
    url = f"https://api.apify.com/v2/actor-runs/{runId}/dataset/items?clean=1&format=json"
    for _ in range(max_retries):
        with urllib.request.urlopen(url) as r:
            data = json.loads(r.read())
        if data: return data
        time.sleep(sleep_s)
    return []
```

## Поиск файла по `id` (для дедупа в Фазе 4.0)

```python
import glob, os
def find_file_by_id(records_folder, post_id):
    matches = glob.glob(os.path.join(records_folder, f"* {post_id}.md"))
    return matches[0] if matches else None
```

## Обновление только метрик в существующем файле

```python
import frontmatter
def update_metrics(path, new_metrics):
    post = frontmatter.load(path)
    for key in ['likes', 'comments', 'shares', 'viewers', 'scanned', 'updated']:
        if key in new_metrics:
            post[key] = new_metrics[key]
    frontmatter.dump(post, path)
```

Замечание про python-frontmatter: на macOS системный python из CommandLineTools — 3.9. Свежий `python-frontmatter>=1.1` падает с `ImportError: cannot import name 'TypeGuard' from 'typing'`. Лечится `pip3 install --user --force-reinstall 'python-frontmatter==1.0.1'`. Проверяй `python3 --version` на Фазе 0.

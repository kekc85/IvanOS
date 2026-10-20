# Утилиты: python-сниппеты для аналитики архива

Готовые куски для code execution в bash. Используй как шаблон, адаптируй пути под `.business/growth/content-archive` своего `.business`.

## Чтение архива и расчёт ERV

```python
import frontmatter, glob, os
from datetime import datetime, timedelta
from collections import defaultdict
from statistics import median

def load_archive(records_folder, window_days):
    cutoff = datetime.now() - timedelta(days=window_days)
    records = []
    for path in glob.glob(os.path.join(records_folder, "*.md")):
        post = frontmatter.load(path)
        pub_str = post.get('published', '')
        if not pub_str: continue
        try:
            pub = datetime.strptime(str(pub_str), '%Y-%m-%d')
        except ValueError:
            continue
        if pub < cutoff: continue
        record = dict(post.metadata)
        record['_path'] = path
        record['_filename'] = os.path.basename(path).replace('.md', '')
        records.append(record)
    return records

def calc_erv(rec):
    likes = rec.get('likes') or 0
    comments = rec.get('comments') or 0
    shares = rec.get('shares') or 0
    viewers = rec.get('viewers') or 0
    if viewers > 0:
        return (likes + comments + shares) / viewers * 100
    return (likes + comments) / 10  # условный ERV для каруселей IG

def bucket_records(records):
    buckets = defaultdict(list)
    for r in records:
        net = r.get('network', '')
        typ = r.get('type', '')
        buckets[(net, typ)].append(r)
    return buckets
```

## Outlier-разметка (гибридная, та же что в №6)

```python
SUFFICIENT_THRESHOLDS = {'пост': 30, 'карусель': 20, 'рилз': 20}

def mark_outliers(buckets):
    for (net, typ), records in buckets.items():
        for r in records:
            r['_erv'] = calc_erv(r)
        ervs = [r['_erv'] for r in records]
        med = median(ervs) if ervs else 0
        sufficient = (len(records) >= SUFFICIENT_THRESHOLDS.get(typ, 30)
                      and len(records) >= 10)
        for r in records:
            r['median_engagement'] = med
            r['outlier_ratio'] = r['_erv'] / med if med else 0
            if sufficient:
                r['outlier'] = r['_erv'] >= med * 2
            else:
                # Малая выборка → outlier=True будет проставлен ниже в блоке топ-20%.
                # Реализуй по описанию (см. принцип 4 / Жёсткие принципы в SKILL.md):
                # 1) отсортировать посты network по ERV убыванию,
                # 2) пометить outlier=True у первых ceil(len(posts)*0.2) штук.
                raise NotImplementedError("реализуй топ-20% per-network здесь")
        if not sufficient:
            # топ-20% по ERV всех записей network (а не type).
            # Реализуй по описанию (см. принцип 4 / Жёсткие принципы в SKILL.md):
            # 1) отсортировать посты network по ERV убыванию,
            # 2) пометить outlier=True у первых ceil(len(posts)*0.2) штук.
            raise NotImplementedError("реализуй топ-20% per-network здесь")
    return buckets
```

## Сортировка Top-N / Bottom-N

```python
def top_n(records, n=5):
    return sorted(records, key=lambda r: r.get('_erv', 0), reverse=True)[:n]

def bottom_n(records, n=5):
    # отбрасываем посты с 0 reactions (могли не учиться или быть удалёнными)
    eligible = [r for r in records if (r.get('likes', 0) + r.get('comments', 0)) > 0]
    return sorted(eligible, key=lambda r: r.get('_erv', 0))[:n]
```

## Wikilink на запись из архива

```python
def to_wikilink(record):
    # имя файла без .md — это и есть title wikilink в базе знаний
    return f"[[{record['_filename']}]]"
```

## Группировка через code execution

```python
from collections import defaultdict
buckets = defaultdict(list)
for record in records:
    key = (record['network'], record['type'])
    buckets[key].append(record)
```

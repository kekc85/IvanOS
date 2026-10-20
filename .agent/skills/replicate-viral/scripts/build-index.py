#!/usr/bin/env python3
# Regenerate the motion-blocks index (makes the 94-block library USABLE — grep _INDEX.md to pick blocks).
# Usage: python3 build-index.py  [motion-blocks-dir]
import os, sys, json, re, glob
from collections import Counter

MB = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.business/growth/assets/motion-blocks")
blocks = []
seen = set()
for hf in glob.glob(os.path.join(MB, '*', '*', 'hyperframes.json')) + glob.glob(os.path.join(MB, '*', '*', 'index.html')):
    d = os.path.dirname(hf)
    if d in seen:
        continue
    seen.add(d)
    bid = os.path.basename(d)
    fam = os.path.basename(os.path.dirname(d))
    meta = {}
    mp = os.path.join(d, 'meta.json')
    if os.path.exists(mp):
        try:
            meta = json.load(open(mp))
        except Exception:
            pass
    name = meta.get('name') or bid
    desc = ''
    rp = os.path.join(d, 'README.md')
    if os.path.exists(rp):
        txt = open(rp, encoding='utf-8', errors='ignore').read()
        m = re.search(r'(?:Rourke prompt|prompt)\s*\n+\s*(.+?)(?:\n\n|\nVisual)', txt, re.S | re.I)
        if not m:
            m = re.search(r'\n([A-Z][^\n#]{40,200})', txt)
        if m:
            desc = re.sub(r'\s+', ' ', m.group(1)).strip()
            desc = desc.lstrip('`').lstrip().lstrip('`').strip('` ')[:160]  # drop code-fence junk
    blocks.append({
        'id': bid, 'family': fam, 'dir': d, 'name': name,
        'duration': meta.get('duration'), 'source': meta.get('source', ''),
        'tier': meta.get('tier', ''), 'polarity': meta.get('polarity', ''),
        'has_render': bool(glob.glob(os.path.join(d, 'renders', '*.mp4'))), 'desc': desc,
    })
blocks.sort(key=lambda b: (b['family'], b['id']))
json.dump(blocks, open(os.path.join(MB, '_index.json'), 'w'), ensure_ascii=False, indent=1)

lines = [f'# Motion-Blocks Index — {len(blocks)} блоков', '',
         'Машинный индекс (генерится `replicate-viral/scripts/build-index.py`). Бери блоки ОТСЮДА, не хендроль.',
         'Колонки: id 🎬(есть-рендер) · (длит) · что делает · src:рилз-источник.', '']
fam = None
for b in blocks:
    if b['family'] != fam:
        fam = b['family']
        lines.append(f'\n## {fam}\n')
    dur = f"{b['duration']}s" if b['duration'] else '?'
    r = '🎬' if b['has_render'] else '·'
    src = f" · src:{b['source'][:40]}" if b['source'] else ''
    lines.append(f"- **{b['id']}** {r} ({dur}) — {b['desc'] or b['name']}{src}")
open(os.path.join(MB, '_INDEX.md'), 'w', encoding='utf-8').write('\n'.join(lines))
print('blocks indexed:', len(blocks), '| by family:', dict(Counter(b['family'] for b in blocks)))

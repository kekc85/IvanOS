#!/usr/bin/env python3
"""words.json (whisper-cli -oj) -> subs.json: группы до 2 слов, UPPERCASE, тайминги встык.
v2 - золотой word-by-word karaoke: каждая группа несёт "words" с пословными таймингами
для последующей покраски активного слова в draw_subs.py. Логика парсинга/фильтра/стыка
не меняется, меняются только пороги группировки и добавленное поле words.
Usage: make_subs.py <words.json> <subs.json>"""
import json, re, sys

if len(sys.argv) != 3:
    sys.exit("usage: make_subs.py <words.json> <subs.json>")

d = json.load(open(sys.argv[1]))
words = []
for s in d['transcription']:
    raw = s['text'].strip()
    if not raw or (raw.startswith('[') and raw.endswith(']')):
        continue
    o = s['offsets']; t0, t1 = o['from'] / 1000.0, o['to'] / 1000.0
    ws = raw.split()
    if not ws:
        continue
    # word-тайминги внутри сегмента пропорционально длине слова
    # выбрасываем токены без букв/цифр (whisper иногда отдаёт голую пунктуацию отдельным словом)
    ws = [x for x in ws if any(ch.isalnum() for ch in x)]
    if not ws:
        continue
    lens = [len(x) for x in ws]; tot = sum(lens); span = max(0.001, t1 - t0); acc = t0
    for x, l in zip(ws, lens):
        dt = span * (l / tot); words.append({'w': x, 't0': acc, 't1': acc + dt}); acc += dt

G = []; cur = []
for wd in words:
    # новая группа: 2 слова набрано, пауза >0.34с или группа длиннее 1.2с
    if cur and (len(cur) >= 2 or wd['t0'] - cur[-1]['t1'] > 0.34 or wd['t1'] - cur[0]['t0'] > 1.2):
        G.append(cur); cur = []
    cur.append(wd)
if cur:
    G.append(cur)

subs = []
for g in G:
    txt = ' '.join(x['w'] for x in g)
    txt = re.sub(r'[.,!?:;]+$', '', txt).replace('«', '').replace('»', '').replace('"', '').upper()
    if not txt:
        continue
    # пословные тайминги для караоке: та же чистка (без пунктуации на конце слова), UPPERCASE
    gwords = []
    for x in g:
        w = re.sub(r'[.,!?:;]+$', '', x['w']).replace('«', '').replace('»', '').replace('"', '').upper()
        if not w:
            continue
        gwords.append({'w': w, 't0': round(x['t0'], 3), 't1': round(x['t1'], 3)})
    if not gwords:
        continue
    subs.append({
        'start': round(g[0]['t0'], 3),
        'end': round(g[-1]['t1'] + 0.1, 3),
        'text': txt,
        'words': gwords,
    })
# стык без наложений: конец группы не позже начала следующей
for i in range(len(subs) - 1):
    subs[i]['end'] = round(min(subs[i]['end'], subs[i + 1]['start'] - 0.02), 3)

if not subs:
    sys.exit("FAIL: 0 субтитров из транскрипта")
json.dump(subs, open(sys.argv[2], 'w'), ensure_ascii=False)
print(f'OK subs: {len(subs)} групп {subs[0]["start"]:.1f}-{subs[-1]["end"]:.1f}с -> {sys.argv[2]}')

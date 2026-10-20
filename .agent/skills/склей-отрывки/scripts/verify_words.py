#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_words.py - независимый верификатор потери слов при обрезке краёв.

Монтажник (montage.py) режет мёртвый воздух по краям каждого дубля. Верификатор
доказывает ФАКТОМ, что рез не съел слово: транскрибирует то, что выбрасывается,
и то, что остаётся, и сверяет.

Режим 1 (гейт до монтажа):
    python3 verify_words.py --plan plan.json
    plan.json = [{"path": "...", "start": 1.2, "end": 45.6, "dur": 47.0}, ...]
    (формат plan_clip() из montage.py; ключ "len" необязателен)

    Для каждого клипа:
      A. транскрибируем ВЫБРОШЕННЫЕ куски: голову [0..start] и хвост [end..dur].
         Услышали там слово - это потеря. Это главный, прямой критерий.
      B. страховка от галлюцинаций/молчания whisper на коротком куске: считаем
         слова в транскрипте ПОЛНОГО файла и в транскрипте keep-окна.
         Расхождение > 0 - подозрение, репортим.

Режим 2 (приёмка готового монтажа):
    python3 verify_words.py --sources ПАПКА --final ФИНАЛ.mp4
    Все слова исходников должны присутствовать в финале в том же порядке.

Код возврата: 0 - потерь нет, 1 - есть потеря (гейт конвейера), 2 - ошибка запуска.
Stdout: человекочитаемый отчёт + строка RESULT_JSON={...} в конце.
"""

import argparse
import concurrent.futures as cf
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata

WHISPER = "whisper-cli"
MODEL = os.path.expanduser("~/whisper-models/ggml-large-v3-turbo.bin")
VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm")

# Куски короче этого не транскрибируем: whisper на <0.25s стабильно выдаёт мусор,
# и физически в такое окно слово не помещается.
MIN_CHUNK = 0.25
# Порог фонетической близости слова из выброшенного куска к слову полного
# транскрипта. Whisper на коротком огрызке коверкает слово ("монетизации" ->
# "мандитата"), поэтому точное совпадение здесь не работает.
FUZZ = 0.62

# ГЛАВНАЯ ЗАЩИТА ОТ ЛОЖНОЙ ТРЕВОГИ.
# Whisper на тишине галлюцинирует титры из обучающей выборки ("Продолжение
# следует...", "Субтитры сделал DimaTorzok"). Замерено на реальных дублях:
# кусок с такой галлюцинацией = mean -63.9 dB / max -34.5 dB, то есть тишина;
# кусок с настоящей речью = mean -31.5 dB / max -10.7 dB. Разрыв больше 20 dB,
# порог их разделяет чисто. Без этого гейта верификатор блокировал бы монтаж
# на КАЖДОМ клипе с тихим хвостом - ровно на том, что и надо резать.
MAX_DB_SPEECH = -26.0   # max_volume ниже - в куске физически нет речи
MEAN_DB_SPEECH = -45.0  # mean_volume ниже - кусок это тишина/фон

# Фразы-галлюцинации whisper на тишине: если ВЕСЬ кусок сводится к ним, это не речь.
HALLUCINATIONS = {
    "продолжение следует", "субтитры сделал dimatorzok", "субтитры делал dimatorzok",
    "редактор субтитров а семкин корректор а егорова", "спасибо за просмотр",
    "субтитры и перевод сделал димасторзок", "подписывайтесь на канал",
    "продолжение следует", "спасибо", "спасибо за внимание", "тишина",
    "субтитры сделал", "переводчик субтитров", "аплодисменты", "музыка",
}


# ---------- shell ----------

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_dur(path):
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nk=1:nw=1", path])
    try:
        return float(p.stdout.strip())
    except (ValueError, TypeError):
        return None


def loudness(path, ss, dur):
    """(mean_dB, max_dB) окна [ss, ss+dur]. (None, None) если не замерить.

    Это физическая улика: есть ли в куске вообще звук речи. Транскрипт куска
    без звука - галлюцинация whisper, а не потерянное слово.
    """
    if dur <= 0.02:
        return None, None
    p = run(["ffmpeg", "-hide_banner", "-ss", f"{ss}", "-t", f"{dur}",
             "-i", path, "-vn", "-af", "volumedetect", "-f", "null", "-"])
    mean = mx = None
    m = re.search(r"mean_volume:\s*(-?[\d.]+) dB", p.stderr or "")
    if m:
        mean = float(m.group(1))
    m = re.search(r"max_volume:\s*(-?[\d.]+) dB", p.stderr or "")
    if m:
        mx = float(m.group(1))
    return mean, mx


def has_speech_energy(mean_db, max_db):
    """Есть ли в куске энергия, похожая на речь. None (не замерили) -> считаем что есть."""
    if max_db is None or mean_db is None:
        return True
    if max_db < MAX_DB_SPEECH:
        return False
    if mean_db < MEAN_DB_SPEECH:
        return False
    return True


def is_hallucination(text):
    """Весь кусок сводится к типовому титру whisper на тишине?"""
    norm = " ".join(normalize(text))
    if not norm:
        return True
    for h in HALLUCINATIONS:
        hn = " ".join(normalize(h))
        if hn and (norm == hn or similar(norm, hn) >= 0.85):
            return True
    # кусок целиком сводится к мычанию → это не речь, а прочищение горла
    for g in GRUNT_PHRASES:
        gn = " ".join(normalize(g))
        if gn and (norm == gn or similar(norm, gn) >= 0.85):
            return True
    # все токены куска - мычание/паразиты → тоже не потеря слова
    toks = norm.split()
    if toks and all(is_filler(t) or len(t) <= 2 for t in toks):
        return True
    return False


# ---------- нормализация текста ----------

PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

NUMWORDS = {
    "0": "ноль", "1": "один", "2": "два", "3": "три", "4": "четыре",
    "5": "пять", "6": "шесть", "7": "семь", "8": "восемь", "9": "девять",
    "10": "десять", "11": "одиннадцать", "12": "двенадцать", "13": "тринадцать",
    "14": "четырнадцать", "15": "пятнадцать", "16": "шестнадцать",
    "17": "семнадцать", "18": "восемнадцать", "19": "девятнадцать",
    "20": "двадцать", "30": "тридцать", "40": "сорок", "50": "пятьдесят",
    "60": "шестьдесят", "70": "семьдесят", "80": "восемьдесят",
    "90": "девяносто", "100": "сто", "1000": "тысяча",
}

# Слова-паразиты и междометия: whisper то слышит их на границе окна, то нет.
# Потерей НЕ считаются (проверяется отдельно, см. classify_lost).
FILLERS = {
    "а", "э", "ээ", "эм", "ну", "вот", "это", "так", "там", "тут", "же", "ли",
    "бы", "да", "нет", "и", "но", "или", "то", "уж", "аж", "вон", "ага", "угу",
    "мм", "хм", "ой", "ах", "ох", "эх", "типа", "как", "бы", "значит", "короче",
    "в", "с", "к", "у", "о", "об", "по", "за", "на", "из", "от", "до", "при",
    "же", "ведь", "лишь", "уже", "ещё", "еще",
    # МЫЧАНИЕ и прочищение горла перед фразой - это НЕ слова. Автор требует
    # вырезать их («начинаться должно не с кряхтения, а сразу со скрипта»),
    # поэтому их пропажа не должна валить сверку как «съеденное слово».
    # по решению автора верификатор поднял ложную тревогу LOST на «Ух-хм» ровно из-за этого.
    "ух", "ухм", "уху", "мхм", "ммм", "эмм", "кхм", "кха", "апчхи", "ага",
}
# Целые куски, которые сводятся к мычанию: сверка их игнорирует полностью
GRUNT_PHRASES = {"ух хм", "ух-хм", "м м м", "мм хм", "кх кх", "э э"}


def normalize(text):
    """нижний регистр, ё->е, убрать пунктуацию, схлопнуть пробелы -> список слов."""
    if not text:
        return []
    t = unicodedata.normalize("NFKC", text).lower().replace("ё", "е")
    t = PUNCT.sub(" ", t)
    words = t.split()
    out = []
    for w in words:
        # числительные к единой форме: "5" и "пять" не должны считаться разными
        out.append(NUMWORDS.get(w, w))
    return out


def similar(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio()


def is_filler(w):
    return w in FILLERS or len(w) <= 1


# ---------- whisper ----------

def _cache_key(path, ss, dur):
    st = os.stat(path)
    raw = f"{os.path.abspath(path)}|{st.st_size}|{int(st.st_mtime)}|{ss:.3f}|{dur:.3f}"
    return hashlib.sha1(raw.encode()).hexdigest()[:20]


def transcribe(path, cache_dir, ss=None, dur=None, tag=""):
    """Транскрибирует [ss, ss+dur] (или весь файл). Возвращает (text, meta).

    Кеш на диске: повторный прогон не гоняет whisper заново.
    """
    ss_v = 0.0 if ss is None else float(ss)
    dur_v = -1.0 if dur is None else float(dur)
    key = _cache_key(path, ss_v, dur_v)
    base = os.path.join(cache_dir, key)
    jpath = base + ".json"

    if os.path.exists(jpath):
        try:
            with open(jpath, encoding="utf-8") as f:
                d = json.load(f)
            return d.get("text", ""), {"cached": True, "tag": tag}
        except Exception:
            pass

    wav = base + ".wav"
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if ss is not None:
        cmd += ["-ss", f"{ss_v}"]
    cmd += ["-i", path]
    if dur is not None:
        cmd += ["-t", f"{dur_v}"]
    cmd += ["-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav]
    p = run(cmd)
    if p.returncode != 0 or not os.path.exists(wav) or os.path.getsize(wav) < 1000:
        _cleanup(wav)
        return "", {"error": "ffmpeg", "tag": tag}

    wp = run([WHISPER, "-m", MODEL, "-f", wav, "-l", "ru",
              "-oj", "-of", base, "-np", "-nt"])
    _cleanup(wav)
    if wp.returncode != 0 or not os.path.exists(jpath):
        return "", {"error": "whisper", "tag": tag,
                    "stderr": (wp.stderr or "")[-300:]}

    try:
        with open(jpath, encoding="utf-8") as f:
            d = json.load(f)
        segs = d.get("transcription", []) or []
        text = " ".join(s.get("text", "") for s in segs).strip()
    except Exception as e:
        return "", {"error": f"json:{e}", "tag": tag}

    # перезаписываем кеш компактно: только текст, чтобы папка не пухла
    try:
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump({"text": text, "path": path, "ss": ss_v, "dur": dur_v},
                      f, ensure_ascii=False)
    except Exception:
        pass
    return text, {"cached": False, "tag": tag}


def _cleanup(p):
    try:
        os.remove(p)
    except OSError:
        pass


# ---------- классификация потерь ----------

def classify_lost(chunk_words, full_words, keep_words):
    """Слова из ВЫБРОШЕННОГО куска -> реальные потери.

    Не потеря:
      - слово-паразит, которое присутствует в keep-окне (whisper его просто
        услышал дважды на границе);
      - слово, которое и так есть в keep-окне (окно перекрылось на границе реза).
    Потеря:
      - содержательное слово, отсутствующее в keep-окне.
    Whisper на коротком огрызке коверкает слово, поэтому сверка с keep нечёткая.
    """
    lost = []
    keep_set = set(keep_words)
    for w in chunk_words:
        if len(w) <= 1:
            continue
        if w in keep_set:
            continue  # слово доехало в keep, рез его не съел
        # нечёткое: тот же корень мог доехать в keep в другой форме
        if any(similar(w, kw) >= 0.85 for kw in keep_words):
            continue
        if is_filler(w):
            continue  # паразит на границе - не содержательная потеря
        # к какому слову полного транскрипта это ближе всего (для отчёта)
        best, score = None, 0.0
        for fw in full_words:
            s = similar(w, fw)
            if s > score:
                best, score = fw, s
        lost.append({"heard": w,
                     "matches_full": best if score >= FUZZ else None,
                     "score": round(score, 2)})
    return lost


# ---------- режим 1: проверка плана ----------

def verify_plan_clip(plan, cache_dir):
    path = plan["path"]
    name = os.path.basename(path)
    D = plan.get("dur") or probe_dur(path)
    if D is None:
        return {"file": name, "path": path, "status": "ERROR",
                "error": "не читается ffprobe"}
    start = float(plan.get("start", 0.0))
    end = float(plan.get("end", D))
    head_len = max(0.0, start)
    tail_len = max(0.0, D - end)

    jobs = {"full": (None, None), "keep": (start, max(0.0, end - start))}
    if head_len >= MIN_CHUNK:
        jobs["head"] = (0.0, head_len)
    if tail_len >= MIN_CHUNK:
        jobs["tail"] = (end, tail_len)

    texts, errors = {}, []
    for tag, (ss, dur) in jobs.items():
        t, meta = transcribe(path, cache_dir, ss, dur, tag)
        texts[tag] = t
        if meta.get("error"):
            errors.append(f"{tag}:{meta['error']}")

    full_w = normalize(texts.get("full", ""))
    keep_w = normalize(texts.get("keep", ""))

    # ДВЕ ЗАЩИТЫ ОТ ЛОЖНОЙ ТРЕВОГИ (функции были написаны, но не подключены):
    #  1) кусок физически тихий (по dB) → там нет речи, что бы whisper ни «услышал»;
    #  2) текст куска сводится к типовому титру-галлюцинации («Продолжение
    #     следует...», «Спасибо.») → это не слово, а заглушка модели на тишине.
    # Без них безопасный рез по чистой тишине помечался как LOST и валил монтаж.
    def real_speech(tag, ss, dur):
        txt = texts.get(tag, "")
        if not txt.strip(): return False
        if is_hallucination(txt): return False
        mean_db, max_db = loudness(path, ss, dur)
        if not has_speech_energy(mean_db, max_db): return False
        return True

    head_txt = normalize(texts.get("head", "")) if real_speech("head", 0.0, head_len) else []
    tail_txt = normalize(texts.get("tail", "")) if real_speech("tail", end, tail_len) else []
    lost_head = classify_lost(head_txt, full_w, keep_w)
    lost_tail = classify_lost(tail_txt, full_w, keep_w)

    # страховка B: расхождение по количеству слов full vs keep
    delta = len(full_w) - len(keep_w)

    # какие содержательные слова полного транскрипта не доехали в keep
    missing = []
    sm = difflib.SequenceMatcher(None, full_w, keep_w)
    for op, i1, i2, _j1, _j2 in sm.get_opcodes():
        if op in ("delete", "replace"):
            for w in full_w[i1:i2]:
                if not is_filler(w):
                    missing.append(w)

    lost = lost_head + lost_tail
    if lost:
        status = "LOST"
    elif missing:
        status = "SUSPECT"
    elif delta > 0:
        status = "SUSPECT"
    else:
        status = "OK"

    return {
        "file": name, "path": path,
        "dur": round(D, 2), "start": round(start, 2), "end": round(end, 2),
        "head_s": round(head_len, 2), "tail_s": round(tail_len, 2),
        "status": status,
        "lost_head": lost_head, "lost_tail": lost_tail,
        "words_full": len(full_w), "words_keep": len(keep_w), "delta": delta,
        "missing_from_keep": missing[:40],
        "head_text": texts.get("head", ""), "tail_text": texts.get("tail", ""),
        "full_text": texts.get("full", ""),
        "errors": errors,
    }


def mode_plan(args):
    with open(args.plan, encoding="utf-8") as f:
        plans = json.load(f)
    if isinstance(plans, dict):
        plans = plans.get("plans") or plans.get("clips") or []
    if not plans:
        print("Пустой план.")
        return 2, {}

    cache_dir = ensure_cache(args.cache_dir)
    print(f"Проверяю {len(plans)} клипов (workers={args.workers}, кеш={cache_dir})")
    print("-" * 78)

    results = [None] * len(plans)
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(verify_plan_clip, p, cache_dir): i
                for i, p in enumerate(plans)}
        done = 0
        for fut in cf.as_completed(futs):
            i = futs[fut]
            try:
                results[i] = fut.result()
            except Exception as e:
                results[i] = {"file": os.path.basename(plans[i].get("path", "?")),
                              "path": plans[i].get("path"), "status": "ERROR",
                              "error": str(e)}
            done += 1
            print(f"\r  транскрибировано {done}/{len(plans)}", end="", flush=True)
    print("\r" + " " * 40 + "\r", end="")

    ok = [r for r in results if r["status"] == "OK"]
    lost = [r for r in results if r["status"] == "LOST"]
    susp = [r for r in results if r["status"] == "SUSPECT"]
    err = [r for r in results if r["status"] == "ERROR"]

    for r in results:
        if r["status"] == "ERROR":
            print(f"ERROR  {r['file']:<26} {r.get('error', '')}")
            continue
        head = f"{r['file']:<26} keep=[{r['start']:.2f}..{r['end']:.2f}] " \
               f"из {r['dur']:.2f}s  срезано голова={r['head_s']:.2f}s хвост={r['tail_s']:.2f}s"
        if r["status"] == "OK":
            print(f"OK     {head}")
        else:
            print(f"{r['status']:<6} {head}")
            if r["lost_head"]:
                ws = ", ".join(f"«{x['heard']}»" + (f" (=«{x['matches_full']}»)"
                               if x["matches_full"] else "") for x in r["lost_head"])
                print(f"       ↳ в срезанной ГОЛОВЕ [0..{r['start']:.2f}] слышно: {ws}")
                print(f"         текст головы: «{r['head_text'].strip()}»")
            if r["lost_tail"]:
                ws = ", ".join(f"«{x['heard']}»" + (f" (=«{x['matches_full']}»)"
                               if x["matches_full"] else "") for x in r["lost_tail"])
                print(f"       ↳ в срезанном ХВОСТЕ [{r['end']:.2f}..{r['dur']:.2f}] слышно: {ws}")
                print(f"         текст хвоста: «{r['tail_text'].strip()}»")
            if r["status"] == "SUSPECT":
                print(f"       ↳ слов: полный={r['words_full']} keep={r['words_keep']} "
                      f"(расхождение {r['delta']})")
                if r["missing_from_keep"]:
                    print(f"       ↳ не доехало в keep: "
                          f"{', '.join('«'+w+'»' for w in r['missing_from_keep'][:12])}")
            if args.verbose:
                print(f"       ↳ полный транскрипт: «{r['full_text'].strip()[:400]}»")

    print("-" * 78)
    print(f"ИТОГ: чистых {len(ok)} · с потерей слов {len(lost)} · "
          f"подозрительных {len(susp)} · ошибок {len(err)} · всего {len(results)}")
    if lost:
        print("ВЕРДИКТ: РЕЗЫ СЪЕДАЮТ СЛОВА - монтаж с этим планом гнать нельзя")
    elif susp or err:
        print("ВЕРДИКТ: прямых потерь нет, но есть расхождения - глянь SUSPECT выше")
    else:
        print("ВЕРДИКТ: ни одно слово не потеряно")

    code = 1 if lost else 0
    result = {
        "mode": "plan", "clips": len(results),
        "ok": len(ok), "lost": len(lost), "suspect": len(susp), "errors": len(err),
        "clean": not lost,
        "lost_files": [{"file": r["file"],
                        "words": [x["heard"] for x in r["lost_head"] + r["lost_tail"]]}
                       for r in lost],
        "suspect_files": [{"file": r["file"], "delta": r["delta"],
                           "missing": r["missing_from_keep"][:10]} for r in susp],
        "exit_code": code,
    }
    return code, result


# ---------- режим 2: проверка готового монтажа ----------

def mode_final(args):
    src_dir = os.path.expanduser(args.sources)
    files = sorted(
        [os.path.join(src_dir, f) for f in os.listdir(src_dir)
         if f.lower().endswith(VIDEO_EXT)],
        key=lambda p: natural_key(p))
    if not files:
        print(f"В {src_dir} нет видео.")
        return 2, {}
    final = os.path.expanduser(args.final)
    if not os.path.exists(final):
        print(f"Нет финала: {final}")
        return 2, {}

    cache_dir = ensure_cache(args.cache_dir)
    print(f"Исходников: {len(files)} · финал: {os.path.basename(final)} "
          f"(workers={args.workers})")

    print("  транскрибирую финал...")
    final_text, fmeta = transcribe(final, cache_dir, tag="final")
    if fmeta.get("error"):
        print(f"Не смог транскрибировать финал: {fmeta['error']}")
        return 2, {}
    final_w = normalize(final_text)

    src_texts = [None] * len(files)
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(transcribe, p, cache_dir, None, None, os.path.basename(p)): i
                for i, p in enumerate(files)}
        done = 0
        for fut in cf.as_completed(futs):
            i = futs[fut]
            try:
                src_texts[i] = fut.result()[0]
            except Exception:
                src_texts[i] = ""
            done += 1
            print(f"\r  транскрибировано исходников {done}/{len(files)}",
                  end="", flush=True)
    print("\r" + " " * 46 + "\r", end="")

    # склеиваем слова исходников по порядку с меткой файла-владельца
    src_words, owner = [], []
    for path, txt in zip(files, src_texts):
        for w in normalize(txt):
            src_words.append(w)
            owner.append(os.path.basename(path))

    # выравнивание последовательностей: что из исходников не доехало в финал
    sm = difflib.SequenceMatcher(None, src_words, final_w, autojunk=False)
    missing_by_file = {}
    total_missing = 0
    for op, i1, i2, _j1, _j2 in sm.get_opcodes():
        if op in ("delete", "replace"):
            for k in range(i1, i2):
                w = src_words[k]
                if is_filler(w):
                    continue
                missing_by_file.setdefault(owner[k], []).append(w)
                total_missing += 1

    matched = sum(b.size for b in sm.get_matching_blocks())
    ratio = matched / len(src_words) if src_words else 0.0

    print("-" * 78)
    print(f"Слов в исходниках: {len(src_words)} · в финале: {len(final_w)} · "
          f"совпало по порядку: {matched} ({ratio*100:.1f}%)")
    if missing_by_file:
        print(f"НЕ ДОЕХАЛО в финал содержательных слов: {total_missing}")
        for fn in sorted(missing_by_file, key=lambda k: -len(missing_by_file[k])):
            ws = missing_by_file[fn]
            print(f"  {fn:<26} {len(ws):>3} слов: "
                  f"{', '.join('«'+w+'»' for w in ws[:10])}"
                  f"{' ...' if len(ws) > 10 else ''}")
        print("ВЕРДИКТ: в финале не хватает слов исходников")
    else:
        print("ВЕРДИКТ: все содержательные слова исходников присутствуют в финале по порядку")

    code = 1 if missing_by_file else 0
    result = {
        "mode": "final", "sources": len(files), "final": final,
        "words_sources": len(src_words), "words_final": len(final_w),
        "matched_in_order": matched, "match_ratio": round(ratio, 4),
        "missing_words": total_missing,
        "missing_by_file": {k: v[:20] for k, v in missing_by_file.items()},
        "clean": not missing_by_file, "exit_code": code,
    }
    return code, result


def natural_key(p):
    nums = re.findall(r"\d+", os.path.basename(p))
    return (int(nums[0]) if nums else 1 << 30, os.path.basename(p).lower())


def ensure_cache(cache_dir):
    d = os.path.expanduser(cache_dir) if cache_dir else \
        os.path.expanduser("~/.cache/verify_words")
    os.makedirs(d, exist_ok=True)
    return d


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(
        description="Верификатор потери слов при обрезке краёв дублей")
    ap.add_argument("--plan", help="plan.json от montage.py (режим 1)")
    ap.add_argument("--sources", help="папка исходников (режим 2)")
    ap.add_argument("--final", help="финальный смонтированный файл (режим 2)")
    ap.add_argument("--workers", type=int, default=4,
                    help="параллельных транскрипций (default 4)")
    ap.add_argument("--cache-dir", default=None,
                    help="кеш транскриптов (default ~/.cache/verify_words)")
    ap.add_argument("--verbose", action="store_true",
                    help="печатать полные транскрипты проблемных клипов")
    args = ap.parse_args()

    if not os.path.exists(WHISPER):
        print(f"Нет whisper-cli: {WHISPER}")
        sys.exit(2)
    if not os.path.exists(MODEL):
        print(f"Нет модели: {MODEL}")
        sys.exit(2)

    if args.plan:
        code, result = mode_plan(args)
    elif args.sources and args.final:
        code, result = mode_final(args)
    else:
        ap.print_help()
        sys.exit(2)

    print("RESULT_JSON=" + json.dumps(result, ensure_ascii=False))
    sys.exit(code)


if __name__ == "__main__":
    main()

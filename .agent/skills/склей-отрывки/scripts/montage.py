#!/usr/bin/env python3
"""
montage.py — собрать N видео-отрывков в один ролик, обрезав мёртвый воздух
в начале и конце каждого (внутренние паузы не трогаются). Без музыки.

ГЛАВНЫЙ ПРИНЦИП: НИ ОДИН СЛОГ РЕЧИ НЕ ТЕРЯЕТСЯ. Все сомнения решаются в
пользу сохранения материала — лучше лишняя секунда воздуха, чем срезанное
слово. Как это реально обеспечено (в этом порядке, ДО энкода):

  1) Детект речи идёт на речевой полосе (highpass200+lowpass3500), поэтому
     НЧ-возня (стук стола, пододвигание) не считается речью.
  2) КАЖДЫЙ блок речи попадает в keep-окно, даже длиной 0.15с. min_voice
     больше НЕ отбрасывает короткие слова («да», «так», «вот», «нет») —
     он работает только как фильтр одиночных кликов (потолок MICRO_CLICK_MAX
     = 0.12с) и только если рядом (в CLICK_ISOLATION с) нет другой речи.
  3) Паддинги по умолчанию (pad_lead 0.05, pad_trail 0.35). Лид намеренно
     микроскопический - автор требует старт впритык к первому слову, без
     воздуха. Сохранность слова держится не паддингом, а откатом (пункт 4).
     Хвостовой паддинг покрывает
     тихую фазу смычки взрывных согласных (п, т, к, б, д, г), которую
     детектор громкости читает как тишину.
  4) ИТЕРАТИВНЫЙ ОТКАТ (rollback_edges): замеряется громкость в речевой
     полосе непосредственно ДО start и ПОСЛЕ end по консервативному порогу
     ROLLBACK_THR (-40dB, ниже CUT_THR, чтобы ловить тихие окончания слов и
     вдох перед словом). Есть сомнение — граница отодвигается НАРУЖУ шагом
     ROLLBACK_STEP (0.15с), пока перед резом не станет чистая тишина или
     пока не упрёмся в границу файла.
  5) edge_audit гоняется ПО ПЛАНАМ ДО ЭНКОДА. Нашёл срез слова — клип
     автоматически пересобирается с расширенными границами, в пределе
     берётся ЦЕЛИКОМ (start=0, end=D). В энкод идут только чистые планы.
  6) safe-mode (ДЕФОЛТ, выключается --no-safe-mode): любое сомнение по клипу
     (аудит сработал хоть на одну сторону, детект тишины сорвался, речь
     начинается в первые SAFE_HEAD_WINDOW=0.3с файла) → клип берётся целиком.
  7) ЖЁСТКИЙ ГЕЙТ: если финальный аудит всё ещё показывает срез слова,
     скрипт НЕ печатает «ГОТОВО», печатает ошибку со списком клипов и
     выходит с кодом 1. Обход — только явным --allow-word-cut.

Нормализует все клипы к целевому формату, поэтому склейка остаётся чистой
даже при смешанных разрешениях/fps.

Запуск:
  python3 montage.py <input_dir | "glob/*.mp4"> [опции]

Опции:
  --out PATH         итоговый файл (по умолч. ~/montage_final/<имя-папки>-montage.mp4)
  --order MODE       natural (по числам в имени, по умолч.) | name | mtime
  --noise DB         порог тишины на РЕЧЕВОЙ полосе highpass200+lowpass3500 (по умолч. -38dB)
  --min-voice SEC    потолок отсева одиночных КЛИКОВ (по умолч. 0.12, жёстко
                     ограничен сверху 0.12 — слова короче он не тронет)
  --gap-merge SEC    склейка тишин через клики короче этого (по умолч. 0.12)
  --pad-lead SEC     оставлять до первого звука (по умолч. 0.05 - рез впритык к слову)
  --pad-trail SEC    оставлять после последнего звука (по умолч. 0.35)
  --safe-mode        при любом сомнении брать клип целиком (ВКЛЮЧЕНО по умолч.)
  --no-safe-mode     отключить safe-mode
  --allow-word-cut   аварийно пропустить гейт при word_cut > 0 (по умолч. выкл.)
  --crf N            качество libx264 (по умолч. 19; меньше = лучше/тяжелее)
  --preset P         пресет libx264 (по умолч. veryfast)
  --workers N        параллельных энкодов (по умолч. 4)
  --no-contact-sheet не делать контактный лист
  --keep-work        не удалять временную папку с сегментами

Stdout: человекочитаемый отчёт (по каждому клипу — сколько срезано с головы,
сколько с хвоста, был ли откат и на сколько) + строка RESULT_JSON={...}.

Код выхода: 0 — чисто; 1 — обнаружен срез слова (без --allow-word-cut) либо
сбой кодирования/склейки.
"""
import argparse, glob, json, os, re, subprocess, sys, tempfile, shutil
from concurrent.futures import ThreadPoolExecutor

VIDEO_EXT = (".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm")
LOUD_THRESH = -42.0   # dB: если у границы реза mean выше — там может быть речь → откат стороны

# --- пороги сохранности речи (см. docstring, пункты 2-6) ---
MICRO_CLICK_MAX  = 0.12   # с: блок речи короче — кандидат в «одиночный клик»
CLICK_ISOLATION  = 0.60   # с: клик отсеивается, только если в этом радиусе нет другой речи
ROLLBACK_THR     = -40.0  # dB: громче на границе реза → там речь → откат наружу
ROLLBACK_STEP    = 0.15   # с: шаг отката границы наружу
ROLLBACK_MAX     = 4.0    # с: предел отката с одной стороны (дальше берём клип целиком)
SAFE_HEAD_WINDOW = 0.30   # с: речь началась в этом окне от 0 → safe-mode берёт клип целиком

# --- отсев неречевых звуков автора перед первой фразой (кряхтение, «ух-хм», кашель,
# прочистка горла, вздох). Они ГРОМКИЕ (до -20dB), поэтому детектор тишины их не
# срезает и оставляет в начале ролика. Отличаются от речи спектром: энергия в НИЗАХ,
# разборчивости в верхах нет. Замер на живом материале (клип 19-54-00):
#   кряхтение «ух-хм»: низ -24.8dB / верх -37.8dB → перевес низа +13dB
#   речь «Привет...»:  низ -33.1dB / верх -28.1dB → перевес низа -5dB
GRUNT_LOW_BAND   = "highpass=f=80,lowpass=f=250"    # полоса гортанного гула
GRUNT_HIGH_BAND  = "highpass=f=800,lowpass=f=3500"  # полоса разборчивой речи
GRUNT_TILT_DB    = 10.0   # низ громче верха на столько → это не речь, а кряхтение.
                          # 10, а не 6: на живом материале блок с речью «Тебе здесь
                          # не нужно» дал перевес 6.0dB и при пороге 6 срезался бы -
                          # это был бы срез слова. У настоящего «ух-хм» перевес 13dB.
GRUNT_HIGH_FLOOR = -34.0  # верх громче этого → там есть разборчивая речь, не трогаем
GRUNT_MAX_LEN    = 1.20   # с: блоки длиннее уже не «кряхтение», не трогаем
GRUNT_MAX_GAP    = 2.50   # с: пауза после блока, за которой начинается настоящая речь

# ---------- ffprobe / ffmpeg helpers ----------

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def probe_dur(path):
    out = run(["ffprobe","-v","error","-show_entries","format=duration",
               "-of","csv=p=0", path]).stdout.strip()
    try: return float(out)
    except: return None

def probe_vparams(path):
    out = run(["ffprobe","-v","error","-select_streams","v:0",
               "-show_entries","stream=width,height,r_frame_rate",
               "-of","default=noprint_wrappers=1:nokey=1", path]).stdout.split()
    if len(out) < 3: return None
    w, h, rate = int(out[0]), int(out[1]), out[2]
    num, den = (rate.split("/")+["1"])[:2]
    fps = round(float(num)/float(den), 3) if float(den) else 30.0
    return w, h, fps

def has_audio(path):
    return bool(run(["ffprobe","-v","error","-select_streams","a:0",
                     "-show_entries","stream=codec_type","-of","csv=p=0", path]).stdout.strip())

def vol(path, ss, dur, prefilter=None):
    """mean dB на окне [ss, ss+dur]; None если окно вырождено.
    prefilter (напр. SPEECH_BAND) меряет громкость только в полосе голоса."""
    if dur <= 0.03 or ss < 0: return None
    af = "volumedetect" if not prefilter else f"{prefilter},volumedetect"
    p = run(["ffmpeg","-hide_banner","-ss",f"{ss}","-t",f"{dur}","-i",path,
             "-af",af,"-f","null","/dev/null"]).stderr
    for ln in p.splitlines():
        if "mean_volume" in ln:
            try: return float(ln.split("mean_volume:")[1].split("dB")[0])
            except: return None
    return None

SPEECH_BAND = "highpass=f=200,lowpass=f=3500"  # полоса голоса: режет НЧ-рокот (пододвигание/гул/стук стола)

def silences(path, noise, mind=0.25, prefilter=None):
    af = f"silencedetect=noise={noise}:d={mind}"
    if prefilter: af = f"{prefilter},{af}"
    p = run(["ffmpeg","-hide_banner","-i",path,"-af", af,"-f","null","/dev/null"]).stderr
    segs, cur = [], None
    for ln in p.splitlines():
        m = re.search(r"silence_start:\s*([-\d.]+)", ln)
        if m: cur = max(0.0, float(m.group(1))); continue
        m = re.search(r"silence_end:\s*([-\d.]+)", ln)
        if m and cur is not None:
            segs.append((cur, float(m.group(1)))); cur = None
    return segs

def merge_silences(segs, gap):
    if not segs: return []
    out = [list(segs[0])]
    for s, e in segs[1:]:
        if s - out[-1][1] < gap: out[-1][1] = e   # клик между двумя тишинами → одна тишина
        else: out.append([s, e])
    return [tuple(x) for x in out]

# ---------- planning ----------

def is_grunt(path, s, e):
    """Блок звука - это кряхтение/кашель/вздох, а не речь?
    Критерий спектральный: у гортанного звука энергия в НИЗАХ (80-250Гц), а в
    полосе разборчивости (800-3500Гц) провал. У речи наоборот. Порог GRUNT_TILT_DB
    выведен из замера на живом материале, см. константы выше."""
    dur = e - s
    if dur <= 0.02 or dur > GRUNT_MAX_LEN: return False
    low  = vol(path, s, dur, GRUNT_LOW_BAND)
    high = vol(path, s, dur, GRUNT_HIGH_BAND)
    if low is None or high is None: return False
    # страховка: есть разборчивость в верхах → это речь, что бы ни говорил перевес
    if high > GRUNT_HIGH_FLOOR: return False
    return (low - high) >= GRUNT_TILT_DB

def strip_leading_grunts(path, blocks):
    """Убирает из НАЧАЛА списка блоков неречевые звуки автора перед первой фразой.
    Условие снятия: блок опознан как кряхтение И после него есть заметная пауза
    (за ней начинается настоящая речь). Кряхтение вплотную к слову не трогаем -
    там риск задеть само слово, а это дороже лишнего звука."""
    i = 0
    while i < len(blocks) - 1:
        s, e = blocks[i]
        gap = blocks[i+1][0] - e
        if gap > GRUNT_MAX_GAP: break          # слишком далеко - уже не «перед фразой»
        if not is_grunt(path, s, e): break     # это речь - дальше не идём
        i += 1
    return blocks[i:] if i else blocks

def rollback_edges(path, start, end, D):
    """Двигает границы реза НАРУЖУ, пока у самого реза слышна речь.
    Возвращает (start, end, откат_головы_с, откат_хвоста_с).
    Порог ROLLBACK_THR намеренно ниже CUT_THR: лучше лишний воздух, чем слог."""
    s0, e0 = start, end
    moved = 0.0
    while start > 0.0 and moved < ROLLBACK_MAX:
        # смотрим в кусок, который СОБИРАЕМСЯ выбросить, впритык к резу
        probe = vol(path, max(0.0, start - ROLLBACK_STEP), ROLLBACK_STEP, SPEECH_BAND)
        if probe is None or probe < ROLLBACK_THR: break   # там тишина → рез безопасен
        start = max(0.0, start - ROLLBACK_STEP); moved += ROLLBACK_STEP
    if moved >= ROLLBACK_MAX: start = 0.0            # речь не кончается → берём с начала
    moved_t = 0.0
    while end < D and moved_t < ROLLBACK_MAX:
        probe = vol(path, end, ROLLBACK_STEP, SPEECH_BAND)
        if probe is None or probe < ROLLBACK_THR: break
        end = min(D, end + ROLLBACK_STEP); moved_t += ROLLBACK_STEP
    if moved_t >= ROLLBACK_MAX: end = D
    return start, end, round(s0 - start, 3), round(end - e0, 3)

def plan_clip(path, args):
    D = probe_dur(path)
    if D is None: return None
    # Детект на РЕЧЕВОЙ ПОЛОСЕ (SPEECH_BAND), а не на полном аудио: иначе
    # пододвигание ноутбука / гул / стук стола (НЧ-шум -35..-40dB) считается
    # «звуком» и край не режется. В полосе голоса этот шум падает до -50dB,
    # речь остаётся -25..-33dB → порог их чисто разделяет.
    sil = merge_silences(silences(path, args.noise, mind=0.10, prefilter=SPEECH_BAND), args.gap_merge)
    blocks, prev = [], 0.0
    for s, e in sil:
        if s - prev > 0.01: blocks.append((prev, s))
        prev = e
    if D - prev > 0.01: blocks.append((prev, D))
    # КАЖДЫЙ блок речи обязан попасть в keep-окно, даже длиной 0.15с: короткие
    # русские слова («да», «так», «вот», «нет», «и») занимают 0.3-0.5с, и старая
    # логика (отбрасывала всё короче min_voice) резала их как шум — это и был
    # дефект «вырезал целое слово в начале дубля».
    # Отсеиваем ТОЛЬКО одиночный клик: короче MICRO_CLICK_MAX и в радиусе
    # CLICK_ISOLATION вокруг нет другой речи (иначе это часть фразы).
    click_max = min(args.min_voice, MICRO_CLICK_MAX)
    def is_isolated_click(i, b):
        if b[1] - b[0] > click_max: return False
        prev_e = blocks[i-1][1] if i > 0 else None
        next_s = blocks[i+1][0] if i < len(blocks)-1 else None
        near = (prev_e is not None and b[0] - prev_e < CLICK_ISOLATION) or \
               (next_s is not None and next_s - b[1] < CLICK_ISOLATION)
        return not near
    voiced = [b for i, b in enumerate(blocks) if not is_isolated_click(i, b)]
    # снимаем с головы неречевые звуки перед первой фразой (кряхтение, «ух-хм»,
    # кашель): они громкие, детектор тишины их не режет, и они остаются в начале
    if voiced:
        voiced = strip_leading_grunts(path, voiced)
    if voiced:
        start = max(0.0, voiced[0][0] - args.pad_lead)
        end   = min(D,   voiced[-1][1] + args.pad_trail)
    else:
        start, end = 0.0, D
    length = end - start
    if length < 0.5 or length > D + 0.01:       # детект сорвался → берём клип целиком
        start, end, length = 0.0, D, D
    # ИТЕРАТИВНЫЙ ОТКАТ: при любом намёке на речь у границы двигаем её НАРУЖУ.
    # Порог ROLLBACK_THR консервативнее CUT_THR — ловит тихие окончания слов и
    # вдох перед словом. Сомнение всегда решается в пользу сохранения материала.
    start, end, rb_head, rb_tail = rollback_edges(path, start, end, D)
    length = end - start
    # safe-mode: речь начинается в первые SAFE_HEAD_WINDOW секунд файла →
    # головы там просто нет, любой рез головы рискован → берём клип целиком
    if getattr(args, "safe_mode", True) and voiced and voiced[0][0] < SAFE_HEAD_WINDOW and start > 0.0:
        start, end, length = 0.0, D, D
        rb_head = rb_tail = 0.0
    return {"path": path, "dur": round(D,3), "start": round(start,3),
            "end": round(end,3), "len": round(length,3),
            "rb_head": rb_head, "rb_tail": rb_tail}

# ---------- discovery / ordering ----------

def natural_key(p):
    nums = re.findall(r"\d+", os.path.basename(p))
    return (int(nums[0]) if nums else 1<<30, os.path.basename(p).lower())

def discover(inp, order):
    if any(c in inp for c in "*?[")          : files = glob.glob(os.path.expanduser(inp))
    elif os.path.isdir(os.path.expanduser(inp)):
        d = os.path.expanduser(inp)
        files = [os.path.join(d,f) for f in os.listdir(d) if f.lower().endswith(VIDEO_EXT)]
    else:
        files = [os.path.expanduser(inp)]
    files = [f for f in files if os.path.isfile(f)]
    if order == "name":  files.sort(key=lambda p: os.path.basename(p).lower())
    elif order == "mtime": files.sort(key=lambda p: os.path.getmtime(p))
    else:                files.sort(key=natural_key)
    return files

# ---------- encode / concat ----------

def encode_seg(plan, target, workdir, args, idx):
    w, h, fps = target
    out = os.path.join(workdir, f"seg{idx:04d}.ts")
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
          f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p")
    # -fps_mode cfr + aresample async=1: держат A/V синхрон даже на VFR-источниках
    if has_audio(plan["path"]):
        cmd = ["ffmpeg","-hide_banner","-loglevel","error","-y",
               "-ss",f"{plan['start']}","-i",plan["path"],"-t",f"{plan['len']}",
               "-vf",vf,"-c:v","libx264","-preset",args.preset,"-crf",str(args.crf),"-fps_mode","cfr",
               "-af","aresample=async=1:first_pts=0","-c:a","aac","-b:a","192k","-ar","48000","-ac","2"]
    else:                                        # нет звука → молчаливая дорожка для ровной склейки
        cmd = ["ffmpeg","-hide_banner","-loglevel","error","-y",
               "-ss",f"{plan['start']}","-i",plan["path"],
               "-f","lavfi","-t",f"{plan['len']}","-i","anullsrc=r=48000:cl=stereo",
               "-map","0:v:0","-map","1:a:0","-t",f"{plan['len']}",
               "-vf",vf,"-c:v","libx264","-preset",args.preset,"-crf",str(args.crf),"-fps_mode","cfr",
               "-c:a","aac","-b:a","192k","-ar","48000","-ac","2"]
    cmd += ["-video_track_timescale","90000","-f","mpegts", out]
    r = run(cmd)
    return (idx, out, r.returncode == 0 and os.path.exists(out) and os.path.getsize(out) > 1000)

def concat(seg_paths, final):
    os.makedirs(os.path.dirname(final), exist_ok=True)
    lst = final + ".list.txt"
    with open(lst, "w") as f:
        for p in seg_paths: f.write(f"file '{p}'\n")
    r = run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0",
             "-i",lst,"-c","copy","-bsf:a","aac_adtstoasc","-movflags","+faststart", final])
    try: os.remove(lst)
    except: pass
    return r.returncode == 0 and os.path.exists(final)

# ---------- verify / contact sheet ----------

def verify(final, workdir, make_sheet):
    def pr(stream, key):
        sel = ["-select_streams", stream] if stream else []
        return run(["ffprobe","-v","error",*sel,"-show_entries",key,
                    "-of","default=noprint_wrappers=1:nokey=1", final]).stdout.strip()
    dur = float(pr("","format=duration"))
    vdur, adur = pr("v:0","stream=duration"), pr("a:0","stream=duration")
    w, h, fps = pr("v:0","stream=width"), pr("v:0","stream=height"), pr("v:0","stream=avg_frame_rate")
    # Скан пустоты по ВСЕМУ финалу и обязательно по РЕЧЕВОЙ ПОЛОСЕ: на полном аудио
    # молчание в камеру с фоновым гулом не детектится как тишина и уезжает в сдачу
    # (по решению автора: 12.3с молчания на 07:06-07:20 прошли мимо, автор нашёл руками).
    _sil = run(["ffmpeg","-hide_banner","-i",final,"-af",
                f"{SPEECH_BAND},silencedetect=noise=-38dB:d=1.0","-f","null","/dev/null"]).stderr
    dead_air, _st = [], None
    for _l in _sil.splitlines():
        if "silence_start" in _l:
            try: _st = float(_l.split("silence_start:")[1].strip())
            except: _st = None
        elif "silence_end" in _l and _st is not None:
            try:
                _en = float(_l.split("silence_end:")[1].split("|")[0].strip())
                dead_air.append({"start": round(_st,2), "end": round(_en,2),
                                 "dur": round(_en-_st,2),
                                 "tc": f"{int(_st//60):02d}:{int(_st%60):02d}"})
            except: pass
            _st = None
    long_pauses = len(dead_air)
    sheet = None
    if make_sheet:
        sheet = os.path.join(workdir, "contact_sheet.png")
        N, cols = 24, 4
        tmp = os.path.join(workdir, "cs"); os.makedirs(tmp, exist_ok=True)
        for k in range(N):
            t = dur*(k+0.5)/N
            run(["ffmpeg","-hide_banner","-loglevel","error","-y","-ss",f"{t}","-i",final,
                 "-frames:v","1","-vf","scale=480:-1", os.path.join(tmp,f"f{k:02d}.png")])
        run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate","1",
             "-i",os.path.join(tmp,"f%02d.png"),
             "-vf",f"tile={cols}x{N//cols}:padding=6:margin=6:color=black",
             "-frames:v","1", sheet])
        if not os.path.exists(sheet): sheet = None
    try:
        av_skew = round(abs(float(vdur)-float(adur))*1000)
    except: av_skew = None
    return {"duration": round(dur,2), "video_dur": vdur, "audio_dur": adur,
            "av_skew_ms": av_skew, "res": f"{w}x{h}", "fps": fps,
            "pauses_over_2s": long_pauses, "dead_air": dead_air, "contact_sheet": sheet}

# ---------- edge audit (встроенная самопроверка краёв) ----------

def edge_audit(plans, args):
    """Проверяет КАЖДЫЙ рез по речевой полосе - две беды сразу:
      • срез слова: перед/после реза в полосе голоса ГРОМКО (>cut_thr) → отрезали речь;
      • грязный/пустой старт: после реза головы в первые 0.25с НЕ речь, хотя резали
        (start>0.15) → осталась возня/пустота (главная жалоба «шумлю, не говорю»).
    Возвращает счётчики + список проблемных клипов для отчёта."""
    CUT_THR, VOICE_THR = -33.0, -40.0
    word_cut, dirty_start, items = 0, 0, []
    # СПЛОШНАЯ ПРОВЕРКА ВЫБРОШЕННЫХ ЗОН (не только впритык к резу).
    # Прецедент по решению автора: в монтаже «Модуль2-Урок1» пропало «бренд ДНК» - блок речи
    # лежал в 0.5с ОТ границы, а старый аудит смотрел лишь окно 0.16-0.20с у самого
    # реза и его не видел. Теперь сканируем ВСЮ голову и ВЕСЬ хвост шагом 0.10с:
    # нашли звук громче DROP_THR - это выброшенная речь, брак.
    DROP_THR, SCAN_STEP = -40.0, 0.10
    def scan_dropped(path, a, b):
        """Максимальная громкость в речевой полосе на выброшенном отрезке [a,b]."""
        peak, t = None, a
        while t < b - 0.02:
            v = vol(path, t, min(SCAN_STEP, b - t), SPEECH_BAND)
            if v is not None and (peak is None or v > peak): peak = v
            t += SCAN_STEP
        return peak
    for p in plans:
        path, s, e, D = p["path"], p["start"], p["end"], p["dur"]
        nm = os.path.basename(path)
        if s > 0.05:
            pk = scan_dropped(path, 0.0, s)
            if pk is not None and pk > DROP_THR:
                word_cut += 1
                items.append(f"{nm}: в выброшенной ГОЛОВЕ [0..{s:.2f}] звук {pk:.0f}dB - там речь")
        if e < D - 0.05:
            pk = scan_dropped(path, e, D)
            if pk is not None and pk > DROP_THR:
                word_cut += 1
                items.append(f"{nm}: в выброшенном ХВОСТЕ [{e:.2f}..{D:.2f}] звук {pk:.0f}dB - там речь")
    for p in plans:
        path, s, e, D = p["path"], p["start"], p["end"], p["dur"]
        nm = os.path.basename(path)
        if s > 0.10:
            pre  = vol(path, s-0.20, 0.16, SPEECH_BAND)   # речь ДО реза (в выброшенной части)
            head = vol(path, s, 0.20, SPEECH_BAND)        # речь сразу ПОСЛЕ реза (в keep)
            # срез слова = речь идёт НЕПРЕРЫВНО через рез (с обеих сторон громко)
            if pre is not None and pre > CUT_THR and head is not None and head > CUT_THR:
                word_cut += 1; items.append(f"{nm}: голова срезала речь ({pre:.0f}dB до / {head:.0f}dB после реза)")
            # грязный старт = после паддинга в keep ВСЁ ещё нет речи ≥0.4с (недорез/шум).
            # окно берём ПОСЛЕ pad_lead, иначе намеренный воздух паддинга даёт ложь.
            else:
                hv = vol(path, s + args.pad_lead + 0.05, 0.35, SPEECH_BAND)
                if s > 0.25 and hv is not None and hv < VOICE_THR:
                    dirty_start += 1; items.append(f"{nm}: старт не с речи ({hv:.0f}dB после паддинга) - остался шум/пустота")
        if e < D - 0.10:
            post  = vol(path, e+0.02, 0.16, SPEECH_BAND)  # речь ПОСЛЕ реза (в выброшенной части)
            pre_e = vol(path, e-0.16, 0.14, SPEECH_BAND)  # речь ДО реза (в keep)
            # срез слова на хвосте = речь непрерывна через рез; изолированный добор
            # после паузы (pre_e тихо) НЕ считается срезом
            if post is not None and post > CUT_THR and pre_e is not None and pre_e > CUT_THR:
                word_cut += 1; items.append(f"{nm}: хвост срезал речь ({pre_e:.0f}dB до / {post:.0f}dB после реза)")
    return {"word_cut": word_cut, "dirty_start": dirty_start,
            "clean": word_cut == 0 and dirty_start == 0, "items": items}

# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out", default=None)
    ap.add_argument("--order", default="natural", choices=["natural","name","mtime"])
    ap.add_argument("--noise", default="-38dB")          # порог на РЕЧЕВОЙ полосе (SPEECH_BAND)
    ap.add_argument("--min-voice", type=float, default=MICRO_CLICK_MAX, dest="min_voice")
    ap.add_argument("--gap-merge", type=float, default=0.12, dest="gap_merge")
    # pad_lead 0.05, не 0.45: автор ловит лишний воздух перед первым словом
    # («там лишние были полсекунды, начинаться должно сразу со скрипта»). 0.05 -
    # запас только на атаку взрывной согласной, на слух рез впритык к слову.
    # Сохранность слова держится не паддингом, а откатом rollback_edges.
    ap.add_argument("--pad-lead", type=float, default=0.05, dest="pad_lead")
    ap.add_argument("--pad-trail", type=float, default=0.35, dest="pad_trail")
    ap.add_argument("--crf", type=int, default=19)
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-contact-sheet", action="store_true")
    ap.add_argument("--keep-work", action="store_true")
    ap.add_argument("--no-safe-mode", action="store_false", dest="safe_mode",
                    help="отключить safe-mode (по умолч. включён: сомнение → клип целиком)")
    ap.add_argument("--allow-word-cut", action="store_true",
                    help="аварийно пропустить гейт при обнаруженном срезе слова")
    ap.add_argument("--allow-dead-air", action="store_true",
                    help="аварийно пропустить гейт при оставленной тишине >1с в финале")
    ap.set_defaults(safe_mode=True)
    args = ap.parse_args()
    # min_voice больше НЕ может отбрасывать слова: он жёстко ограничен потолком
    # одиночного клика. Передали больше — молча зажимаем (старые вызовы с 0.55
    # не должны снова резать «да»/«так»/«вот»).
    if args.min_voice > MICRO_CLICK_MAX:
        print(f"  (min-voice {args.min_voice} > {MICRO_CLICK_MAX} — зажат до {MICRO_CLICK_MAX}: слова не отбрасываем)")
        args.min_voice = MICRO_CLICK_MAX

    files = discover(args.input, args.order)
    if not files: sys.exit("Не найдено видеофайлов по входу: " + args.input)

    # вывод: НИКОГДА не на Desktop (правило проекта)
    if args.out:
        out = os.path.abspath(os.path.expanduser(args.out))
        if "/Desktop/" in out or out.endswith("/Desktop"):
            sys.exit("Отказ: вывод на Desktop запрещён. Укажи другой --out.")
    else:
        base = os.path.basename(os.path.dirname(files[0])) or "clips"
        out = os.path.expanduser(f"~/montage_final/{base}-montage.mp4")

    print(f"Найдено клипов: {len(files)}  (порядок: {args.order})")
    for f in files: print(f"  - {os.path.basename(f)}")

    print("\nПланирую точки реза...")
    plans, skipped = [], []
    for f in files:
        p = plan_clip(f, args)
        if p is None: skipped.append(f); print(f"  ! пропуск (не читается): {os.path.basename(f)}"); continue
        trimmed = p["dur"] - p["len"]
        plans.append(p)
        rb = ""
        if p.get("rb_head") or p.get("rb_tail"):
            rb = f"  ОТКАТ: голова +{p['rb_head']:.2f}с хвост +{p['rb_tail']:.2f}с"
        print(f"  {os.path.basename(f):<22} raw={p['dur']:7.2f}  keep=[{p['start']:.2f}..{p['end']:.2f}]  "
              f"срез: голова {p['start']:.2f}с / хвост {p['dur']-p['end']:.2f}с  итого={trimmed:.2f}s{rb}")
    if not plans: sys.exit("Все клипы непригодны.")

    # АУДИТ ДО ЭНКОДА: нашли срез слова → клип пересобираем с расширенными
    # границами, в пределе берём целиком. В энкод идут только чистые планы.
    print("\nАудит краёв ДО энкода (речевая полоса)...")
    for attempt in range(1, 4):
        ea_pre = edge_audit(plans, args)
        if ea_pre["clean"]:
            print(f"  ✅ чисто с попытки {attempt}: срезов слова 0, грязных стартов 0")
            break
        bad = {it.split(":")[0] for it in ea_pre["items"]}
        print(f"  попытка {attempt}: проблемных клипов {len(bad)} → расширяю границы")
        for p in plans:
            if os.path.basename(p["path"]) not in bad: continue
            if attempt < 3:      # сначала пробуем щедрый откат наружу
                ns = max(0.0, p["start"] - ROLLBACK_STEP*4)
                ne = min(p["dur"], p["end"] + ROLLBACK_STEP*4)
            else:                # не помогло → клип целиком, слово важнее воздуха
                ns, ne = 0.0, p["dur"]
            print(f"    {os.path.basename(p['path'])}: [{p['start']:.2f}..{p['end']:.2f}] → [{ns:.2f}..{ne:.2f}]")
            p["start"], p["end"], p["len"] = round(ns,3), round(ne,3), round(ne-ns,3)

    target = probe_vparams(plans[0]["path"]) or (1920,1080,30.0)
    print(f"\nЦелевой формат: {target[0]}x{target[1]} @ {target[2]}fps")

    workdir = tempfile.mkdtemp(prefix="montage_")
    print(f"Кодирую {len(plans)} сегментов (workers={args.workers})...")
    results = [None]*len(plans)
    fails = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(encode_seg, p, target, workdir, args, i) for i,p in enumerate(plans)]
        for fu in futs:
            idx, segpath, ok = fu.result()
            results[idx] = segpath
            if not ok: fails.append(idx)
    if fails:
        if not args.keep_work: shutil.rmtree(workdir, ignore_errors=True)
        sys.exit(f"Сбой кодирования сегментов: {fails}")

    print("Склеиваю в финал...")
    if not concat(results, out):
        if not args.keep_work: shutil.rmtree(workdir, ignore_errors=True)
        sys.exit("Сбой склейки.")

    v = verify(out, workdir, not args.no_contact_sheet)
    ea = edge_audit(plans, args)
    raw_total = round(sum(p["dur"] for p in plans),1)

    # ЖЁСТКИЙ ГЕЙТ: срез слова = брак, а не предупреждение. Раньше здесь
    # печаталось «ГОТОВО» с ⚠ и кодом 0 — так брак и уехал в сдачу по решению автора.
    if ea["word_cut"] > 0 and not args.allow_word_cut:
        print("\n===== БРАК: СРЕЗ СЛОВА =====")
        print(f"Клипов со срезом речи: {ea['word_cut']}. Файл собран, но сдаче НЕ подлежит:")
        for it in ea["items"][:20]: print(f"    - {it}")
        print(f"\nЧерновик (не сдавать): {out}")
        print("Обход гейта - только явным --allow-word-cut.")
        if not args.keep_work: shutil.rmtree(workdir, ignore_errors=True)
        sys.exit(1)

    # ЖЁСТКИЙ ГЕЙТ №2: ОСТАВЛЕННАЯ ТИШИНА = такой же брак, как срез слова.
    # edge_audit проверяет ровно одну сторону (не отрезал ли слово) и дыру
    # физически не видит. Однажды зелёный edge_audit закрыл сдачу с 12.3с
    # молчания в камеру - автор нашёл руками. Симметрия обеих бед обязательна.
    if v["dead_air"] and not args.allow_dead_air:
        print("\n===== БРАК: ПУСТОТА В РОЛИКЕ =====")
        print(f"Пауз >1с в финале: {len(v['dead_air'])}. Файл собран, но сдаче НЕ подлежит:")
        for it in v["dead_air"][:20]:
            print(f"    - {it['tc']}  тишина {it['dur']}с  ({it['start']}-{it['end']})")
        print("\nПричина обычно одна: клип, где голова срезана на 0.00с (детект принял")
        print("шорох за речь), либо длинная пауза ВНУТРИ дубля - молчание в камеру.")
        print(f"\nЧерновик (не сдавать): {out}")
        print("Обход гейта - только явным --allow-dead-air.")
        if not args.keep_work: shutil.rmtree(workdir, ignore_errors=True)
        sys.exit(1)

    print("\n===== ГОТОВО =====")
    print(f"Файл: {out}  ({os.path.getsize(out)/1e6:.1f} MB)")
    print(f"Длительность: {v['duration']}s = {int(v['duration']//60)}м{int(v['duration']%60):02d}с  (из сырых {raw_total}s)")
    print(f"Формат: {v['res']} @ {v['fps']}   A/V расхождение: {v['av_skew_ms']} мс")
    print(f"Клипов склеено: {len(plans)}   пропущено: {len(skipped)}   пауз >2с: {v['pauses_over_2s']}")
    if ea["clean"]:
        print(f"Аудит краёв (речь-полоса): ✅ чисто - срезов слова 0, грязных стартов 0")
    else:
        print(f"⚠ Аудит краёв: срезов слова={ea['word_cut']}  грязных стартов={ea['dirty_start']} - ПРОВЕРЬ:")
        for it in ea["items"][:12]: print(f"    - {it}")
    if v["contact_sheet"]: print(f"Контактный лист: {v['contact_sheet']}")

    # доставка: финал ВСЕГДА дублируется на ~/Desktop - точка забора автора
    # (его приказ в даты запуска.2026; запрет Desktop выше - только про --out/промежуточное)
    desktop_copy = os.path.join(os.path.expanduser("~/Desktop"), os.path.basename(out))
    try:
        shutil.copy(out, desktop_copy)
        print(f"Копия на столе: {desktop_copy}")
    except Exception as e:
        desktop_copy = None
        print(f"⚠ Не смог положить копию на Desktop: {e}")

    result = {"final": out, "desktop_copy": desktop_copy,
              "size_mb": round(os.path.getsize(out)/1e6,1),
              "clips": len(plans), "skipped": [os.path.basename(s) for s in skipped],
              "raw_total_s": raw_total, "edge_audit": ea, **v, "workdir": workdir}
    if not args.keep_work:
        # финал и контактный лист уже скопированы наружу? нет — лист в workdir.
        if v.get("contact_sheet"):
            keep = os.path.expanduser("~/montage_final/contact_sheet.png")
            try: shutil.copy(v["contact_sheet"], keep); result["contact_sheet"] = keep
            except: pass
        shutil.rmtree(workdir, ignore_errors=True)
    print("RESULT_JSON=" + json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
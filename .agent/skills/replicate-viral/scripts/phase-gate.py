#!/usr/bin/env python3
"""
phase-gate.py — МАШИННОЕ принуждение полноты фаз конвейера replicate-viral
                ИЗ АРТЕФАКТОВ, не из заявлений. (паттерн launch-status.py)

Прецедент по решению автора (рилз AI-хедшоты): сессия молча пропустила ВЕСЬ конвейер
и собрала ролик на НЕпрослушанной HeyGen-озвучке (русский текст, украинская
фонетика) -> ролик удалён целиком после полной сборки. Машина это НЕ ловила,
потому что статус фаз читался из заявлений агента, а не из улик-артефактов.

Этот скрипт читает <project>/project-meta.json (декларация путей-улик) и для
КАЖДОЙ фазы проверяет ФАКТ наличия артефакта-улики с проверяемым маркером,
пишет <project>/.phase-ledger.json (фаза -> PASS/MISS -> улика-путь + маркер).

КРИТИЧНО (анти-stale, прецедент непрослушанной озвучки):
   Ф4 voice-approved.flag несёт md5 одобренного аудио. Гейт сверяет этот md5
   с ФАКТИЧЕСКИМ md5 аудио-файла, на котором собрана композиция. Не совпало =
   MISS: одобрено одно аудио, в ролике другое = тот самый ложный PASS.

Использование:
  phase-gate.py --check <project-dir>
      проверить все фазы -> .phase-ledger.json; exit 0 = все PASS, exit 1 = есть MISS
  phase-gate.py --mark <project-dir> <phase> --artifact <path>
      удобно записать улику фазы в project-meta.json (опционально)

Формат <project>/project-meta.json (минимум — пути, которые скрипт сам не угадает):
{
  "project": "karkas-reel",
  "created": "2026-06-12",
  "ingest_dir": "footage/ingest",          # Ф1: содержит transcript.txt + frames/
  "ui_report": "ui-report.md",             # Ф1
  "concept": "concept.md",                 # Ф2c
  "benchmark_map": "structure-map.md",     # Ф3 (раскадровка/карта эталона)
  "motion_map": "scene-plan.md",           # Ф3 (моушн-карта; ИЛИ таблица внутри concept)
  "composition_audio": "fullreel/assets/voiceover.wav",  # Ф4: аудио, НА КОТОРОМ собран ролик
  "voice_flag": "voice-approved.flag",     # Ф4: JSON-флаг одобрения автором
  "look_frame": "heygen/look.jpg",         # Ф4.6: кадр новой локации спикера
  "avatar_mp4": "heygen/avatar-scene9-intro.mp4",  # Ф5: HeyGen-аватар (полный decode)
  "render": "final/karkas-reel-v5.mp4",    # Ф6: финальный рендер 1080x1920
  "audit": "fullreel/renders"              # Ф6: .audit / .preflight / audit-вывод (файл ИЛИ dir)
}
Пути — относительно <project-dir> (абсолютные тоже принимаются).
Отсутствие project-meta.json = понятная ошибка с подсказкой формата (exit 2).
"""
import json, os, sys, re, hashlib, subprocess, datetime

# Журнал локаций спикера живёт в самом скилле (общий на все ролики), а не в проекте.
SPEAKER_JOURNAL = os.path.expanduser(
    "~/.claude/skills/replicate-viral/speaker-locations-journal.md")

# Higgsfield content-gate (AC3, автор): кадры локаций ОБЯЗАНЫ быть свежими
# (произведены В ЭТУ сессию), непустыми, числом == числу сегментов, и НЕ реюзом
# прошлого ролика. Окно свежести: HIGGS_SESSION_START (unix-ts) ИЛИ последние N часов.
HIGGS_FRESH_HOURS = float(os.environ.get("HIGGS_FRESH_HOURS", "12"))
HIGGS_MIN_BYTES = int(os.environ.get("HIGGS_MIN_BYTES", "5000"))  # реальный кадр >5КБ, не плейсхолдер

# Голоса, валидированные автором ОДИН раз (прослушка пройдена) — переслушивать каждый
# ролик НЕ нужно (автор: «хватит мою прослушку требовать, это не bottleneck»).
# Новый голос = разовая валидация прослушкой, потом сюда; дальше машинный гейт.
def _validated_voices():
    """Валидированные голоса = голос УЧЕНИКА из accounts.json (BYOA) + env-оверрайд.
    Канон: _shared/bring-your-own-account.md. Раньше тут был хардкод голоса автора —
    он отклонял голос ученика. Теперь источник = его accounts.json (heygen.voice_name/voice_id)."""
    import subprocess
    voices = set()
    ap = os.path.expanduser("~/.claude/skills/_shared/bin/account.py")
    if os.path.exists(ap):
        for field in ("voice_name", "voice_id"):
            try:
                v = subprocess.run(["python3", ap, "get", "heygen." + field],
                                   capture_output=True, text=True, timeout=10).stdout.strip()
                if v:
                    voices.add(v.lower())
            except Exception:
                pass
    for v in os.environ.get("VALIDATED_VOICES", "").split(","):
        if v.strip():
            voices.add(v.strip().lower())
    return voices

VALIDATED_VOICES = _validated_voices()

META_TEMPLATE = '''{
  "project": "<имя>",
  "created": "YYYY-MM-DD",
  "ingest_dir": "footage/ingest",
  "ui_report": "ui-report.md",
  "script": "script.md",
  "script_approved": "script-approved.flag",
  "concept": "concept.md",
  "concept_approved": "concept-approved.flag",
  "deconstruction": "deconstruction.md",
  "benchmark_map": "structure-map.md",
  "motion_map": "scene-plan.md",
  "source_subs_flag": "source-subs.flag",
  "composition_audio": "fullreel/assets/voiceover.wav",
  "voice_id": "<имя твоего голоса из accounts.json heygen.voice_name>",
  "voice_qa": "voice-qa.flag",
  "wow_inserts": "higgsfield/wow",
  "segments": [{"beat": "hook", "look_frame": "heygen/look-1.jpg", "avatar_mp4": "heygen/avatar-1.mp4"}],
  "look_frame": "heygen/look.jpg",
  "avatar_mp4": "heygen/avatar.mp4",
  "render": "final/reel.mp4",
  "source_vision": "source-vision.json",
  "audit": "fullreel/renders"
}'''


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rp(root, val):
    """Разрешить путь из меты относительно корня проекта (или абсолютный)."""
    if not val:
        return None
    return val if os.path.isabs(val) else os.path.join(root, val)


def nonempty_file(p, min_bytes=20):
    return bool(p) and os.path.isfile(p) and os.path.getsize(p) >= min_bytes


def full_decode_ok(p):
    """ffmpeg полный decode (moov может врать про длину — прецедент по решению автора)."""
    if not nonempty_file(p, 1000):
        return False, "файл отсутствует/пустой"
    try:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", p, "-f", "null", "-"],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=600)
    except FileNotFoundError:
        return False, "ffmpeg не найден"
    except subprocess.TimeoutExpired:
        return False, "decode timeout"
    if r.returncode != 0:
        return False, "decode errors: " + r.stderr.decode("utf-8", "ignore")[:120]
    return True, "decode ok"


def video_wh(p):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", p],
            capture_output=True, text=True, timeout=60).stdout.strip()
        w, h = out.split(",")[:2]
        return int(w), int(h)
    except Exception:
        return 0, 0


# --------- апрув-флаги: артефакт согласован автором (анти-stale по md5) ---------

def check_approved_flag(root, flag_key, artifact_key, label, m):
    """Флаг согласования артефакта автором.
    Прецедент по решению автора: сессия НЕ согласовала скрипт и проскочила в производство
    ('скипнул фазы как крыса'). Гейт: производство (Ф4.6/5/6) MISS, пока артефакт
    не согласован флагом с md5, совпадающим с самим артефактом (анти-подмена).
    Формат <artifact>-approved.flag: {"artifact":"script.md","md5":"…",
                                      "approved_by":"автор","date":"YYYY-MM-DD"}"""
    flag = rp(root, m.get(flag_key))
    art = rp(root, m.get(artifact_key))
    if not nonempty_file(art, 50):
        return False, "нет %s-артефакта (%s)" % (label, m.get(artifact_key, "—"))
    if not nonempty_file(flag, 10):
        return False, ("%s НЕ согласован автором: нет %s. "
                       "Производство стартовать НЕЛЬЗЯ" % (label, m.get(flag_key, "<flag>")))
    try:
        fj = json.load(open(flag, encoding="utf-8"))
    except Exception as e:
        return False, "%s-approved.flag не валидный JSON (%s)" % (label, e)
    miss = [k for k in ("artifact", "md5", "approved_by", "date") if not fj.get(k)]
    if miss:
        return False, "%s-approved.flag без полей %s" % (label, miss)
    actual = md5(art)
    if actual != fj["md5"]:
        return False, ("%s-approved.flag устарел: md5 %s… != факт %s… — согласован "
                       "ДРУГОЙ текст, а не текущий %s (анти-stale)"
                       % (label, fj["md5"][:12], actual[:12], os.path.basename(art)))
    return True, ("%s согласован %s %s md5=%s…"
                  % (label, fj["approved_by"], fj["date"], fj["md5"][:12]))


# --------- проверки по фазам: возвращают (PASS_bool, улика-строка) ---------

def check_f1(root, m):
    ing = rp(root, m.get("ingest_dir"))
    ui = rp(root, m.get("ui_report"))
    if not ing or not os.path.isdir(ing):
        return False, "нет ingest-dir (%s)" % m.get("ingest_dir", "—")
    tr = os.path.join(ing, "transcript.txt")
    frames = os.path.join(ing, "frames")
    if not nonempty_file(tr):
        return False, "нет %s/transcript.txt (непустой)" % ing
    if not (os.path.isdir(frames) and os.listdir(frames)):
        return False, "нет %s/frames/ с кадрами" % ing
    if not nonempty_file(ui):
        return False, "нет ui-report (%s)" % m.get("ui_report", "—")
    return True, "%s (transcript+frames) + %s" % (ing, os.path.basename(ui))


def check_f2(root, m):
    """Ф2 — СКРИПТ согласован автором ДО производства (новый гейт по решению автора)."""
    return check_approved_flag(root, "script_approved", "script", "скрипт", m)


def check_f2c(root, m):
    c = rp(root, m.get("concept"))
    if not nonempty_file(c, 200):
        return False, "нет непустого концепта (%s)" % m.get("concept", "—")
    # Деконструкция источника (вход тропинки, блупринт по решению автора): если объявлена — её
    # машинный вердикт ОБЯЗАН быть PASS, иначе сборка идёт на догадке (Build-on-guess).
    if m.get("deconstruction"):
        dv = os.path.join(root, ".deconstruction-verdict.json")
        if not os.path.isfile(dv):
            return False, ("деконструкция объявлена (%s), но нет .deconstruction-verdict.json — "
                           "прогони deconstruction-check.py ДО концепта" % m.get("deconstruction"))
        try:
            dj = json.load(open(dv, encoding="utf-8"))
        except Exception as e:
            return False, ".deconstruction-verdict.json не валидный JSON (%s)" % e
        if dj.get("verdict") != "PASS":
            return False, ("деконструкция НЕ прошла чек (%d проблем) — сборка на догадке запрещена; "
                           "см. issues в .deconstruction-verdict.json" % len(dj.get("issues", [])))
        # C1-фикс: деконструкция объявлена/PASS -> скелет монтажа ОБЯЗАН быть выведен из неё.
        # Иначе монтаж-биндинг опционален и монотон проходит мимо гейта (нет scene-skeleton.json
        # -> assemble skip + skeleton-match SKIP). Скелет выводит skeleton-derive.py.
        skel = os.path.join(root, "scene-skeleton.json")
        if not os.path.isfile(skel):
            return False, ("деконструкция PASS, но НЕТ scene-skeleton.json — скелет монтажа не "
                           "выведен из деконструкции; прогони skeleton-derive.py (монтаж-биндинг "
                           "обязателен, иначе монотон проходит мимо гейта)")
    ok, note = check_approved_flag(root, "concept_approved", "concept", "концепт", m)
    if ok and m.get("deconstruction"):
        note += " + деконструкция PASS + скелет выведен"
    return ok, note


def check_f3(root, m):
    bm = rp(root, m.get("benchmark_map"))
    mm = rp(root, m.get("motion_map"))
    if not nonempty_file(bm, 100):
        return False, "нет benchmark-map (%s)" % m.get("benchmark_map", "—")
    if nonempty_file(mm, 100):
        return True, "%s + %s" % (os.path.basename(bm), os.path.basename(mm))
    for cand in (rp(root, m.get("concept")), bm):
        if cand and os.path.isfile(cand):
            txt = open(cand, encoding="utf-8", errors="ignore").read()
            if "|" in txt and re.search(r"motion|моуш|build_order|раскадров|секунд", txt, re.I):
                return True, "%s + моушн-таблица внутри %s" % (os.path.basename(bm), os.path.basename(cand))
    return False, "нет моушн-карты (%s) и таблицы в концепте" % m.get("motion_map", "—")


def check_f3a_subs(root, m):
    """Ф3a-SUB (ЗАКОН B, автор): чужие субтитры из ЗАБРАННОГО футажа
    зачищены вызовом отдельного скилла subtitle-remover ДО сборки Ф6. Прецедент:
    рилзы уходили с двумя слоями субтитров / агент молча пропускал чистку.
    Требуем осознанное решение флагом source-subs.flag:
      {"status":"cleaned"|"none","cleaned":[...],"ocr_pass":true,"note":"..."}
    status='cleaned' — чистили (ocr_pass обязателен true: subtitle-remover дал PASS);
    status='none'    — в источнике вшитых субтитров нет, чистить нечего (осознанно)."""
    flag = rp(root, m.get("source_subs_flag") or "source-subs.flag")
    if not nonempty_file(flag, 5):
        return False, ("нет source-subs.flag — НЕ зафиксировано, зачищены ли чужие "
                       "субтитры (ЗАКОН B). Вызвать Skill('subtitle-remover') на "
                       "забранном футаже ИЛИ записать status='none', если их нет")
    try:
        fj = json.load(open(flag, encoding="utf-8"))
    except Exception as e:
        return False, "source-subs.flag не валидный JSON (%s)" % e
    st = fj.get("status")
    if st == "none":
        return True, "чужих субтитров в источнике нет (зафиксировано осознанно)"
    if st == "cleaned":
        if fj.get("ocr_pass") is not True:
            return False, ("source-subs.flag status=cleaned, но ocr_pass != true — "
                           "subtitle-remover не подтвердил чистый выход (его OCR-гейт)")
        n = len(fj.get("cleaned") or [])
        return True, "чужие субтитры зачищены subtitle-remover (%d кусков, OCR PASS)" % n
    return False, ("source-subs.flag status=%r — ожидается 'cleaned' или 'none'" % st)


def check_f4(root, m):
    """Озвучка — БЕЗ человеческой прослушки (автор: «не bottleneck»).
    Машинный гейт вместо уха: (1) голос = ВАЛИДИРОВАННЫЙ ID (пин убирает корень
    украинской-фонетики катастрофы = молча выбранный невалидный клон); (2) машинные
    TTS-проверки (textlint + whisper round-trip) прогнаны на ТОМ аудио, что в ролике
    (анти-stale md5). Прослушка нужна РАЗ при валидации нового голоса, не каждый ролик."""
    vid = str(m.get("voice_id", "")).strip().lower()
    if vid not in VALIDATED_VOICES:
        hint = ("подключи СВОЙ голос: python3 ~/.claude/skills/_shared/bin/account.py set heygen.voice_name <имя твоего голоса>"
                if not VALIDATED_VOICES else
                "новый голос валидировать ОДИН раз прослушкой, потом account.py set heygen.voice_name")
        return False, ("voice_id '%s' не из валидированных %s — %s"
                       % (m.get("voice_id", "—"), sorted(VALIDATED_VOICES), hint))
    comp = rp(root, m.get("composition_audio"))
    if not nonempty_file(comp, 1000):
        return False, "нет composition_audio (%s) — аудио, на котором собран ролик" % m.get("composition_audio", "—")
    qa = rp(root, m.get("voice_qa"))
    if not nonempty_file(qa, 10):
        return False, ("нет voice-qa.flag (%s) — машинные TTS-проверки (textlint + whisper "
                       "round-trip) не зафиксированы" % m.get("voice_qa", "—"))
    try:
        qj = json.load(open(qa, encoding="utf-8"))
    except Exception as e:
        return False, "voice-qa.flag не валидный JSON (%s)" % e
    miss = [k for k in ("audio", "md5", "checks") if not qj.get(k)]
    if miss:
        return False, "voice-qa.flag без полей %s (нужны audio/md5/checks)" % miss
    cmd5 = md5(comp)
    if cmd5 != qj["md5"]:
        return False, ("voice-qa.flag md5 %s… != композиция %s… — QA прогнан на ДРУГОМ "
                       "аудио, не на том что в ролике (анти-stale)"
                       % (qj["md5"][:12], cmd5[:12]))
    return True, ("голос '%s' (валидирован) + TTS-QA %s на %s"
                  % (m.get("voice_id"), qj.get("checks"), os.path.basename(comp)))


def _session_start_ts():
    """Начало окна свежести Higgsfield-кадров: HIGGS_SESSION_START (unix-ts) ИЛИ
    now - HIGGS_FRESH_HOURS. Кадр старше = реюз/протухший, не произведён в эту сессию."""
    env = os.environ.get("HIGGS_SESSION_START")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    import time
    return time.time() - HIGGS_FRESH_HOURS * 3600


def _collect_look_frames(root, m):
    """Список путей кадров-локаций: из segments[].look_frame (мульти-локация) ИЛИ
    одиночного look_frame (совместимость). Возвращает (paths, n_segments)."""
    segs = m.get("segments")
    paths = []
    if isinstance(segs, list) and segs:
        for s in segs:
            lf = s.get("look_frame") if isinstance(s, dict) else None
            if lf:
                paths.append(rp(root, lf))
        return paths, len(segs)
    single = rp(root, m.get("look_frame"))
    return ([single] if single else []), (1 if single else 0)


def _sibling_project_md5s(root):
    """md5 всех Higgsfield-кадров СОСЕДНИХ проектов (родительская папка) — для детекта
    реюза кадров прошлого ролика. Безопасно по объёму: только *.png/*.jpg в heygen/."""
    seen = set()
    parent = os.path.dirname(os.path.abspath(root.rstrip("/")))
    me = os.path.abspath(root.rstrip("/"))
    if not os.path.isdir(parent):
        return seen
    for entry in os.listdir(parent):
        sib = os.path.join(parent, entry)
        if not os.path.isdir(sib) or os.path.abspath(sib) == me:
            continue
        for dp, _, fns in os.walk(sib):
            if any(s in dp for s in ("/node_modules", "/.git", "/renders")):
                continue
            for fn in fns:
                if fn.lower().endswith((".png", ".jpg", ".jpeg")) and ("heygen" in dp or "higgs" in dp.lower() or "look" in fn.lower()):
                    fp = os.path.join(dp, fn)
                    try:
                        if os.path.getsize(fp) >= HIGGS_MIN_BYTES:
                            seen.add(md5(fp))
                    except OSError:
                        pass
    return seen


def check_f45(root, m):
    """Ф4.5 — ВАУ-ВСТАВКИ Higgsfield (теперь ОБЯЗАТЕЛЬНЫ каждый ролик, AC3 по решению автора).
    Раньше опциональны (в гейте не было фазы). Артефакт = кадр(ы)/клип(ы) вставок:
    meta-ключ wow_inserts (путь к файлу ИЛИ к директории с вставками). Проверки:
    непустой + свежий (произведён в эту сессию) + не реюз прошлого ролика."""
    wi = rp(root, m.get("wow_inserts"))
    if not wi:
        return False, ("нет wow_inserts в project-meta.json — вау-вставки Higgsfield "
                       "ОБЯЗАТЕЛЬНЫ каждый ролик (Ф4.5, AC3); объяви путь к файлу/папке вставок")
    files = []
    if os.path.isdir(wi):
        for fn in os.listdir(wi):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".mp4", ".mov", ".webm")):
                files.append(os.path.join(wi, fn))
    elif os.path.isfile(wi):
        files = [wi]
    files = [f for f in files if os.path.getsize(f) >= HIGGS_MIN_BYTES]
    if not files:
        return False, "wow_inserts (%s): нет непустых вставок (>%dБ)" % (m.get("wow_inserts"), HIGGS_MIN_BYTES)
    start = _session_start_ts()
    stale = [os.path.basename(f) for f in files if os.path.getmtime(f) < start]
    if stale:
        return False, ("вау-вставки протухли/реюз прошлого ролика (mtime до начала сессии): %s — "
                       "сгенерировать заново В ЭТУ сессию (anti-reuse)" % ", ".join(stale[:4]))
    sib = _sibling_project_md5s(root)
    dupd = [os.path.basename(f) for f in files if md5(f) in sib]
    if dupd:
        return False, "вау-вставки совпадают по md5 с кадрами другого ролика (реюз): %s" % ", ".join(dupd[:4])
    return True, "%d вау-вставок Higgsfield (непустые, свежие, не реюз)" % len(files)


def check_f46(root, m):
    """Ф4.6 — НОВАЯ ЛОКАЦИЯ СПИКЕРА (Higgsfield i2i). Усилен (AC3, автор): кадры
    локаций ОБЯЗАНЫ быть (1) непустые, (2) свежие — произведены В ЭТУ сессию,
    (3) числом == числу сегментов, (4) НЕ реюз прошлого ролика (md5), плюс свежая
    строка в журнале. Раньше ловил только наличие/тип файла = пропускал пустышку/реюз."""
    frames, n_seg = _collect_look_frames(root, m)
    if not frames:
        return False, "нет кадров локаций (look_frame / segments[].look_frame отсутствуют)"
    for lf in frames:
        if not (lf and lf.lower().endswith((".png", ".jpg", ".jpeg"))):
            return False, "кадр локации не png/jpg (%s)" % lf
        if not nonempty_file(lf, HIGGS_MIN_BYTES):
            return False, ("кадр локации %s пустой/мелкий (<%dБ) — пустышка, не реальная "
                           "Higgsfield-генерация" % (os.path.basename(lf or "—"), HIGGS_MIN_BYTES))
    # (3) число кадров == число сегментов
    if n_seg and len(frames) != n_seg:
        return False, ("кадров локаций %d != сегментов %d — на каждый бит свой кадр "
                       "(Ф4.6); набор не полон" % (len(frames), n_seg))
    # (2) свежесть: все кадры произведены В ЭТУ сессию
    start = _session_start_ts()
    stale = [os.path.basename(f) for f in frames if os.path.getmtime(f) < start]
    if stale:
        return False, ("кадры локаций протухли/реюз прошлого ролика (mtime до начала сессии): %s — "
                       "сгенерировать заново В ЭТУ сессию (anti-reuse)" % ", ".join(stale[:4]))
    # (4) не реюз: md5 не совпадает с кадрами соседних проектов
    sib = _sibling_project_md5s(root)
    dupd = [os.path.basename(f) for f in frames if md5(f) in sib]
    if dupd:
        return False, ("кадры локаций совпадают по md5 с другим роликом (реюз фона = AI-палево): %s"
                       % ", ".join(dupd[:4]))
    # журнал локаций (как было)
    if not nonempty_file(SPEAKER_JOURNAL):
        return False, "нет журнала локаций %s" % SPEAKER_JOURNAL
    jtxt = open(SPEAKER_JOURNAL, encoding="utf-8", errors="ignore").read()
    today = datetime.date.today().isoformat()
    proj = m.get("project", "")
    if not (today in jtxt or (proj and proj in jtxt)):
        return False, ("кадры есть, но в журнале нет свежей строки (дата %s или проект '%s')"
                       % (today, proj))
    return True, ("%d кадр(ов) локаций (непустые, свежие, не реюз) + строка в журнале"
                  % len(frames))


def check_f5(root, m):
    av = rp(root, m.get("avatar_mp4"))
    ok, note = full_decode_ok(av)
    if not ok:
        return False, "avatar mp4 (%s): %s" % (m.get("avatar_mp4", "—"), note)
    return True, "%s — %s" % (os.path.basename(av), note)


def check_source_vision(root, m, render):
    """ОБЯЗАТЕЛЬНО (автор): покадровое зрение реально прогнано. Без свежего
    source-vision.json (step=1, покрытие == каждый кадр) сборка/субтитры/гейт автора
    шли «на глаз раз в секунду» — корень утечек автора и промахов плашки. Артефакт =
    выход source_vision.py. Проверки: валиден, step==1, n_analyzed ≈ fps*dur (≥95%),
    и свежий (mtime не старше рендера на >2ч = произведён для этого ролика, не реюз)."""
    sv = rp(root, m.get("source_vision") or "source-vision.json")
    if not nonempty_file(sv, 100):
        return False, ("нет source-vision.json (%s) — ПОКАДРОВОЕ зрение не прогнано. "
                       "Запусти: python3 scripts/source_vision.py <src> --out source-vision.json"
                       % (m.get("source_vision") or "source-vision.json"))
    try:
        d = json.load(open(sv, encoding="utf-8"))
        s = d["summary"]
    except Exception as e:
        return False, "source-vision.json невалиден (%s)" % e
    if int(s.get("step", 0)) != 1:
        return False, ("source-vision.json step=%s != 1 — анализ прорежен, не КАЖДЫЙ кадр "
                       "(корень моргания «раз в секунду»)" % s.get("step"))
    fps, dur_frames = float(s.get("fps", 0)), int(s.get("n_frames_total", 0))
    n = int(s.get("n_analyzed", 0))
    if dur_frames and n < 0.95 * dur_frames:
        return False, ("source-vision покрытие %d/%d кадров (<95%%) — не сплошной покадровый "
                       "проход" % (n, dur_frames))
    if render and os.path.isfile(render):
        if os.path.getmtime(sv) < os.path.getmtime(render) - 7200:
            return False, ("source-vision.json старше рендера на >2ч — вероятно реюз "
                           "прошлого ролика, прогнать заново на этом источнике")
    return True, "покадрово %d кадров (step=1, fps=%.2f, движок=%s)" % (
        n, fps, s.get("face_engine", "?"))


def check_f6(root, m):
    r = rp(root, m.get("render"))
    if not nonempty_file(r, 10000):
        return False, "нет финального рендера (%s)" % m.get("render", "—")
    # анти-stale/анти-truncation .
    # video_wh/ffprobe читают МЕТАДАННЫЕ; full-decode гоняет ВСЕ кадры и ловит обрыв.
    dec_ok, dec_note = full_decode_ok(r)
    if not dec_ok:
        return False, ("рендер %s НЕ декодируется полностью (%s) — оборван/недокачан, "
                       "не валидный финал (ffprobe-метаданные могут врать)"
                       % (os.path.basename(r), dec_note))
    w, h = video_wh(r)
    if (w, h) != (1080, 1920):
        return False, "рендер %s %dx%d != 1080x1920" % (os.path.basename(r), w, h)
    # ОБЯЗАТЕЛЬНО: покадровое зрение прогнано (анти-«раз в секунду»)
    sv_ok, sv_note = check_source_vision(root, m, r)
    if not sv_ok:
        return False, sv_note
    aud = rp(root, m.get("audit"))
    audit_ok = bool(aud) and (os.path.isfile(aud) or (os.path.isdir(aud) and os.listdir(aud)))
    if not audit_ok:
        hits = []
        for dp, _, fns in os.walk(root):
            if any(s in dp for s in ("/node_modules", "/.git")):
                continue
            for fn in fns:
                if re.search(r"\.audit|\.preflight|audit", fn, re.I):
                    hits.append(os.path.join(dp, fn))
        if not hits:
            return False, "рендер %s %dx%d OK, но нет .audit/.preflight-вывода" % (os.path.basename(r), w, h)
        return True, "%s 1080x1920 + audit %s; %s" % (os.path.basename(r), os.path.basename(hits[0]), sv_note)
    return True, "%s 1080x1920 + audit %s; %s" % (os.path.basename(r), os.path.basename(aud.rstrip("/")), sv_note)


PHASES = [
    ("Ф1", "ingest+ui-detect", check_f1),
    ("Ф2", "скрипт согласован",  check_f2),
    ("Ф2c", "концепт согласован", check_f2c),
    ("Ф3", "benchmark+моушн",   check_f3),
    ("Ф3a", "чужие субтитры зачищены (subtitle-remover)", check_f3a_subs),
    ("Ф4", "озвучка (валид.голос+TTS-QA)", check_f4),
    ("Ф4.5", "вау-вставки Higgsfield (обяз.)", check_f45),
    ("Ф4.6", "новая локация спикера (Higgsfield)", check_f46),
    ("Ф5", "HeyGen аватар (decode)",  check_f5),
    ("Ф6", "рендер 1080x1920+audit",  check_f6),
]


def cmd_check(root):
    root = root.rstrip("/")
    if not os.path.isdir(root):
        print("ОШИБКА: нет папки проекта %s" % root, file=sys.stderr)
        return 2
    meta_p = os.path.join(root, "project-meta.json")
    if not os.path.isfile(meta_p):
        sys.stderr.write(
            "ОШИБКА: нет %s\n"
            "Phase-ledger требует декларацию путей-улик. Создай project-meta.json:\n\n"
            "%s\n\n"
            "(пути относительно папки проекта; объяви только то, что произвёл)\n"
            % (meta_p, META_TEMPLATE))
        return 2
    try:
        m = json.load(open(meta_p, encoding="utf-8"))
    except Exception as e:
        print("ОШИБКА: project-meta.json не валидный JSON: %s" % e, file=sys.stderr)
        return 2

    ledger, fails = {}, []
    for pid, name, fn in PHASES:
        try:
            ok, ev = fn(root, m)
        except Exception as e:
            ok, ev = False, "ошибка проверки: %s" % e
        ledger[pid] = {"name": name, "status": "PASS" if ok else "MISS", "evidence": ev}
        if not ok:
            fails.append((pid, name, ev))

    out = {
        "project": m.get("project", os.path.basename(root)),
        "checked": datetime.datetime.now().isoformat(timespec="seconds"),
        "verdict": "FAIL" if fails else "PASS",
        "phases": ledger,
    }
    json.dump(out, open(os.path.join(root, ".phase-ledger.json"), "w"),
              ensure_ascii=False, indent=1)

    print("\n  PHASE-LEDGER: %s — %s" % (out["project"], out["verdict"]))
    print("  " + "-" * 60)
    for pid, name, fn in PHASES:
        e = ledger[pid]
        mark = "v" if e["status"] == "PASS" else "x"
        print("  %s %-5s %-26s %s" % (mark, pid, name, e["status"]))
        print("       улика: %s" % e["evidence"])
    print("  " + "-" * 60)
    if fails:
        print("  ПРОПУЩЕННЫЕ ФАЗЫ:")
        for pid, name, ev in fails:
            print("   x ФАЗА %s ПРОПУЩЕНА: нет улики — %s" % (pid, ev))
    print("  ledger: %s\n" % os.path.join(root, ".phase-ledger.json"))
    return 1 if fails else 0


def cmd_mark(root, phase, artifact):
    root = root.rstrip("/")
    meta_p = os.path.join(root, "project-meta.json")
    m = json.load(open(meta_p, encoding="utf-8")) if os.path.isfile(meta_p) else {}
    keymap = {
        "Ф1": "ingest_dir", "Ф2": "script_approved", "Ф2c": "concept_approved",
        "Ф3": "benchmark_map", "Ф3a": "source_subs_flag", "Ф4": "voice_qa",
        "Ф4.5": "wow_inserts", "Ф4.6": "look_frame", "Ф5": "avatar_mp4", "Ф6": "render",
    }
    key = keymap.get(phase)
    if not key:
        print("ОШИБКА: неизвестная фаза %s; есть: %s" % (phase, list(keymap)), file=sys.stderr)
        return 2
    m[key] = artifact
    json.dump(m, open(meta_p, "w"), ensure_ascii=False, indent=1)
    print("записано: %s -> %s = %s  в %s" % (phase, key, artifact, meta_p))
    return 0


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 2
    if a[0] == "--check" and len(a) >= 2:
        return cmd_check(a[1])
    if a[0] == "--mark" and len(a) >= 3:
        artifact = None
        if "--artifact" in a:
            i = a.index("--artifact")
            artifact = a[i + 1] if i + 1 < len(a) else None
        if not artifact:
            print("ОШИБКА: --mark требует --artifact <path>", file=sys.stderr)
            return 2
        return cmd_mark(a[1], a[2], artifact)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())

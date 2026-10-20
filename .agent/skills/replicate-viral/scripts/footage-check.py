#!/usr/bin/env python3
"""
footage-check.py — АНТИ-GOODHART сверка футажа композиции против provenance/манифеста.

Корень (replicate-viral, реестр КОРЕНЬ 2 + karkas-reel по решению автора): субагенты ×3 подменяли
верхний футаж сцены на ЧУЖОЙ высокодвижный клип (signup-регистрацию) ради оси D —
метрика зелёная, смысл уничтожен. Машина не знала, ЧТО должно быть в кадре.
v3 (единый таймлайн руками) закрыл вектор субагентов, но остаточный риск — чужой/левый
клип в композиции без следа добычи — остаётся. Этот скрипт даёт МАШИННЫЙ сигнал:

  · video-src, которого НЕТ как файла (битая/чужая абсолютная ссылка) = FAIL (exit 2)
  · video-src есть, но НЕ аватар и НЕ числится ни в одном provenance.md
    и (если объявлен) противоречит footage-manifest.json = WARN (проверь, не подмена ли)
  · footage-manifest.json объявлен и плановый клип бита ОТСУТСТВУЕТ в композиции = WARN

Источники provenance (Ф3a добытчик):
  · <project>/**/provenance.md  (если копировался в проект)
  · ~/.business/growth/assets/footage/**/provenance.md  (общая библиотека)
Опциональный <project>/footage-manifest.json — авторитетная карта бит→футаж, которую
объявляет оркестратор: {"hook":"freepik-demo.mp4","ui-demo":"vscode-cast.mp4"}.

Использование:
  footage-check.py <project-dir>
Exit 0 = нет битых ссылок (могут быть WARN), 2 = битая/чужая ссылка (FAIL).
Пишет <project>/.footage-verdict.json. Аватар-клипы (heygen/avatar/segN) — всегда учтены.
"""
import json, os, re, sys, glob

LIB_FOOTAGE = os.path.expanduser("~/.business/growth/assets/footage")
AVATAR_HINTS = ("avatar", "heygen", "seg", "speaker", "look")
VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v")


def find_composition(proj):
    for cand in ("fullreel/index.html", "opening/index.html"):
        p = os.path.join(proj, cand)
        if os.path.isfile(p):
            return p
    hits = glob.glob(os.path.join(proj, "**", "index.html"), recursive=True)
    hits = [h for h in hits if "/node_modules/" not in h]
    return hits[0] if hits else None


def extract_video_srcs(html_path):
    """src/href из <video>/<source> + data-src — только видео-файлы."""
    t = open(html_path, encoding="utf-8", errors="ignore").read()
    srcs = set()
    for m in re.finditer(r"<(?:video|source)\b[^>]*?\b(?:src|data-src|href)\s*=\s*[\"']([^\"']+)[\"']", t, re.I):
        srcs.add(m.group(1))
    # JS-присвоения .src = "x.mp4" (рендерер иногда задаёт динамически)
    for m in re.finditer(r"\.src\s*=\s*[\"']([^\"']+\.(?:mp4|webm|mov|m4v))[\"']", t, re.I):
        srcs.add(m.group(1))
    return {s for s in srcs if s.lower().split("?")[0].endswith(VIDEO_EXT)}


def is_avatar(name):
    n = name.lower()
    return any(h in n for h in AVATAR_HINTS)


def collect_provenance_basenames(proj):
    """basename-ы всех клипов, упомянутых в любом provenance.md (проект + библиотека)."""
    names = set()
    prov_files = glob.glob(os.path.join(proj, "**", "provenance.md"), recursive=True)
    if os.path.isdir(LIB_FOOTAGE):
        prov_files += glob.glob(os.path.join(LIB_FOOTAGE, "**", "provenance.md"), recursive=True)
    for pf in prov_files:
        try:
            txt = open(pf, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for m in re.finditer(r"[\w./-]+\.(?:mp4|webm|mov|m4v)", txt, re.I):
            names.add(os.path.basename(m.group(0)))
    return names


def main():
    if len(sys.argv) < 2:
        print(__doc__); return 2
    proj = sys.argv[1].rstrip("/")
    if not os.path.isdir(proj):
        print("ОШИБКА: нет папки проекта %s" % proj, file=sys.stderr); return 2

    comp = find_composition(proj)
    fails, warns, accounted = [], [], []
    if not comp:
        # нет композиции = нечего проверять (ранние фазы); не краш
        verdict = {"verdict": "PASS", "note": "композиция (index.html) не найдена — нечего сверять",
                   "fails": [], "warns": []}
        json.dump(verdict, open(os.path.join(proj, ".footage-verdict.json"), "w"),
                  ensure_ascii=False, indent=1)
        print("footage-check: нет композиции — пропуск"); return 0

    srcs = extract_video_srcs(comp)
    prov = collect_provenance_basenames(proj)
    manifest_p = os.path.join(proj, "footage-manifest.json")
    manifest = {}
    if os.path.isfile(manifest_p):
        try:
            manifest = json.load(open(manifest_p, encoding="utf-8"))
        except Exception as e:
            warns.append("footage-manifest.json не валиден: %s" % e)
    manifest_clips = {os.path.basename(str(v)) for v in manifest.values()}

    comp_dir = os.path.dirname(comp)
    for s in sorted(srcs):
        bn = os.path.basename(s.split("?")[0])
        # резолв файла относительно композиции / проекта
        cands = [os.path.join(comp_dir, s), os.path.join(proj, s),
                 s if os.path.isabs(s) else None]
        exists = any(c and os.path.isfile(c) for c in cands if c)
        # data-URI / http(s) — не локальный файл, но и не «битый»: помечаем отдельно
        is_remote = s.startswith(("data:", "http://", "https://"))
        if not exists and not is_remote:
            fails.append("video-src НЕ найден как файл: %s (битая/чужая ссылка — рендер сломан или подмена)" % s)
            continue
        if is_avatar(bn):
            accounted.append("%s (аватар)" % bn); continue
        if bn in manifest_clips:
            accounted.append("%s (по footage-manifest)" % bn); continue
        if bn in prov:
            accounted.append("%s (provenance Ф3a)" % bn); continue
        warns.append("НЕУЧТЁННЫЙ футаж %s — нет в provenance.md и не аватар: проверь, "
                     "что это ПЛАНОВЫЙ клип бита, а не Goodhart-подмена чужим высокодвижным" % bn)

    # объявленный манифест: плановый клип не доехал до композиции
    comp_basenames = {os.path.basename(s.split("?")[0]) for s in srcs}
    for beat, clip in manifest.items():
        if os.path.basename(str(clip)) not in comp_basenames:
            warns.append("манифест: бит '%s' планировал футаж '%s', но его НЕТ в композиции" % (beat, clip))

    verdict = "FAIL" if fails else "PASS"
    out = {"verdict": verdict, "composition": comp,
           "video_srcs": sorted(srcs), "accounted": accounted,
           "fails": fails, "warns": warns,
           "manifest_used": bool(manifest), "provenance_clips": len(prov)}
    json.dump(out, open(os.path.join(proj, ".footage-verdict.json"), "w"),
              ensure_ascii=False, indent=1)

    print("========== FOOTAGE-CHECK: %s ==========" % verdict)
    print("  композиция: %s" % comp)
    print("  video-src: %d | учтено: %d | provenance-клипов: %d | manifest: %s"
          % (len(srcs), len(accounted), len(prov), "да" if manifest else "нет"))
    for a in accounted: print("  · %s" % a)
    for w in warns: print("  ⚠ %s" % w)
    for f in fails: print("  ✗ %s" % f)
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
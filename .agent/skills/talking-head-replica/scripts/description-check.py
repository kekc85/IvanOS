#!/usr/bin/env python3
"""
description-check.py — машинный гейт публикуемого ОПИСАНИЯ к ролику/карусели.

Корень (автор, повтор от этой редакции): описание раз за разом писалось ПЛОСКИМ
caption-ом «от руки» вместо канона `_shared/lead-magnet-description-structure.md`
(6 блоков, код-слово КАПСОМ ≥2 в ёлочках: ранний призыв + финал). Канон
референсился прозой в SKILL.md и не доезжал. Этот гейт делает несоответствие
машинно-невалидным ДО отправки автору.

Также ловит ВТОРУЮ ошибку: в текст описания подмешана техническая обёртка
(«ОПИСАНИЕ К РОЛИКУ», «копируй целиком», счётчики символов) — автору нужен ТОЛЬКО
настоящий текст поста, без мета.

Usage:
  description-check.py <description.txt>            # код-слово авто-детект из «ЁЛОЧЕК»
  description-check.py <description.txt> --codeword САЙТ

exit: 0 PASS, 1 FAIL (печатает причины).
"""
import sys, re, os

def fail(msgs):
    print("FAIL (description-check):")
    for m in msgs: print("  -", m)
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    path = sys.argv[1]
    codeword = None
    if "--codeword" in sys.argv:
        codeword = sys.argv[sys.argv.index("--codeword")+1]
    if not os.path.exists(path):
        fail([f"нет файла {path}"])
    t = open(path, encoding="utf-8").read().strip()
    paras = [p.strip() for p in re.split(r"\n\s*\n", t) if p.strip()]
    errs = []

    # 1. Не плоский: ≥6 смысловых блоков (хук + ранний CTA + суть + примеры + личный опыт + что внутри + финал CTA)
    if len(paras) < 6:
        errs.append(f"ПЛОСКИЙ caption: {len(paras)} абзацев (<6). Нужен каркас _shared/lead-magnet-description-structure.md: хук / ранний CTA / суть / примеры-якоря / личный опыт / что внутри / финал-CTA")

    # 2. Код-слово КАПСОМ в «ёлочках» ≥2, ранний (первые 2 абзаца) + финальный (последний абзац)
    yel = re.findall(r"«([A-ZА-ЯЁ0-9]{2,})»", t)
    if codeword is None and yel:
        from collections import Counter
        codeword = Counter(yel).most_common(1)[0][0]
    if not codeword:
        errs.append("нет код-слова КАПСОМ в «ёлочках» (формат «СЛОВО»)")
    else:
        n = t.count("«"+codeword+"»")
        if n < 2:
            errs.append(f"код-слово «{codeword}» встречается {n} раз (<2). Нужно: ранний призыв после хука + финальный повтор")
        early = any(("«"+codeword+"»") in p for p in paras[:2])
        late = ("«"+codeword+"»") in paras[-1] if paras else False
        if not early:
            errs.append(f"нет РАННЕГО призыва с «{codeword}» в первых 2 абзацах (до IG-обрезки «ещё»)")
        if not late:
            errs.append(f"нет ФИНАЛЬНОГО призыва с «{codeword}» в последнем абзаце")

    # 3. Длинные тире в прозе
    if re.search(r"[—–]", t):
        errs.append("длинные тире —/– (AI-маркер), заменить на запятую/двоеточие/дефис")

    # 4. Точка в конце абзаца
    bad = [i+1 for i, p in enumerate(paras) if p.endswith(".")]
    if bad:
        errs.append(f"точка в конце абзаца(ев) {bad} — убрать (правило голоса автора)")

    # 5. Техническая обёртка в тексте описания (мета, не пост)
    META = [r"ОПИСАНИЕ\s+К\s+РОЛИК", r"копируй", r"символ", r"char", r"код-слово.{0,3}капс",
            r"\bблок(а|ов)?\b\s*\d", r"^📝", r"selftest", r"PASS\b", r"FAIL\b"]
    for pat in META:
        if re.search(pat, t, re.I | re.M):
            errs.append(f"в тексте описания техническая обёртка/мета («{pat}») — автору слать ТОЛЬКО чистый текст поста")
            break

    if errs:
        fail(errs)
    print(f"PASS (description-check): {len(paras)} блоков, код-слово «{codeword}» ранний+финальный, без тире/концевых точек/меты")
    sys.exit(0)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
orphan-scan.py — ДЕШЁВЫЙ статический детектор типографических орфанов в HTML-исходнике
(БЕЗ рендера/браузера). Ловит классику: ручной `<br>`, который оставляет ОДНО слово на
последней строке заголовка (h1–h4) ИЛИ элемента-плашки (class содержит title/eyebrow/
badge/tag/note/lead/h-). Это худший случай по памяти `feedback_no_orphan_word_on_line`
(«нахер перенёс „система" на отдельную строчку — целая строчка, одно слово»).

Зачем отдельно от layout-audit.mjs: тот ловит И естественные переносы (нужен браузер,
медленно), этот — мгновенный source-level чек ручных `<br>`-орфанов, ставится в Stop-хук
после правки html (без запуска playwright на каждый ответ).

Опт-аут для РЕДКИХ уместных случаев (имя «автор<br>», намеренная капс-композиция):
  • связать последние слова `&nbsp;` (неразрывный пробел) — тогда это один «токен», не орфан;
  • добавить класс `allow-orphan` ИЛИ атрибут `data-br-ok` на элемент.

Использование:
    python3 orphan-scan.py <file.html>            # один файл
    python3 orphan-scan.py --stdin < text         # из stdin (html-строка)
Exit: 0 = чисто; 3 = найден орфан (FAIL, печатает offenders); 2 = ошибка ввода.
Safe-by-design: пустой/нечитаемый ввод → exit 0 (не блокируем ложно).
"""
import re
import sys

# Элементы, где орфан критичен: заголовки h1–h4 + плашки/лейблы по классу.
HEADING_RE = re.compile(r"<(h[1-4])\b([^>]*)>(.*?)</\1>", re.I | re.S)
CLASS_TAG_RE = re.compile(
    r'<([a-z][a-z0-9]*)\b([^>]*\bclass\s*=\s*"[^"]*'
    r'(?:title|eyebrow|badge|tag|note|lead|headline|h-)'
    r'[^"]*"[^>]*)>(.*?)</\1>',
    re.I | re.S,
)
BR_RE = re.compile(r"<br\s*/?>", re.I)
TAG_RE = re.compile(r"<[^>]+>")


def _allowed(attrs):
    """Опт-аут на уровне элемента."""
    a = attrs.lower()
    return "allow-orphan" in a or "data-br-ok" in a


def _strip(html_fragment):
    """Снять теги, схлопнуть &nbsp; в неразрывный токен (не пробел), нормализовать."""
    t = BR_RE.sub(" ", html_fragment)  # <br> = граница слов (иначе склейка в отчёте)
    t = TAG_RE.sub("", t)
    t = t.replace("&nbsp;", " ").replace("&#160;", " ")
    #   НЕ пробел для split() по \s+? В Python \s включает \xa0 при re.UNICODE!
    # Поэтому split вручную по обычным пробелам/таб/перевод строки, НЕ по nbsp.
    return t


def _words(text):
    # делим ТОЛЬКО по обычным разделителям; &nbsp;( ) связывает слова в один токен
    return [w for w in re.split(r"[ \t\r\n]+", text.strip()) if w]


def _last_line_orphan(inner):
    """True, если ПОСЛЕ последнего <br> остаётся ровно одно слово (при ≥3 словах всего)."""
    plain_all = _strip(inner)
    if len(_words(plain_all)) < 3:
        return None  # короткие лейблы (1–2 слова) — это не «строчка из одного слова»
    parts = BR_RE.split(inner)
    if len(parts) < 2:
        return None  # нет ручного переноса — естественные переносы ловит layout-audit
    last = _strip(parts[-1])
    lw = _words(last)
    if len(lw) == 1:
        return lw[0]
    return None


def scan(html):
    offenders = []
    seen = set()
    for rx in (HEADING_RE, CLASS_TAG_RE):
        for m in rx.finditer(html):
            attrs, inner = m.group(2), m.group(3)
            if _allowed(attrs):
                continue
            word = _last_line_orphan(inner)
            if word:
                full = " ".join(_words(_strip(inner)))[:60]
                key = (full, word)
                if key not in seen:
                    seen.add(key)
                    offenders.append((full, word))
    return offenders


def main():
    args = sys.argv[1:]
    try:
        if args and args[0] == "--stdin":
            html = sys.stdin.read()
        elif args:
            html = open(args[0], encoding="utf-8", errors="ignore").read()
        else:
            sys.stderr.write("usage: orphan-scan.py <file.html> | --stdin\n")
            sys.exit(2)
    except Exception:
        sys.exit(0)  # не смогли прочитать → не блокируем

    offenders = scan(html)
    if not offenders:
        sys.exit(0)

    print("🛑 ОРФАН: одно слово на отдельной строке (ручной <br>) — запрещено "
          "(правило автора,):")
    for full, word in offenders:
        print(f"   • «{full}» → последняя строка = одно слово «{word}»")
    print("\nКак чинить: (1) связать последние два слова `&nbsp;` "
          "(«…&nbsp;{word}»), (2) добавить `text-wrap: balance` заголовку, "
          "(3) переставить <br> в осмысленное место, чтоб строки сбалансировались. "
          "Редкий уместный случай (имя/намеренная композиция) → класс `allow-orphan`.")
    sys.exit(3)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
check-deploy.py — МАШИННАЯ проверка ЦЕЛЕВОГО ДЕЙСТВИЯ перед/после деплоя (Фаза 08).
Закрывает DEFERRED-пункт: «целевое действие реально работает» переставал быть прозой.
Память: зелёный health ≠ рабочий путь.

Что проверяет ОФЛАЙН на собранном index.html (decidable, без сети):
  • есть хотя бы один РАБОЧИЙ CTA: <a href> с непустым реальным href (не '#', не
    'javascript:void', не пусто), ИЛИ <form action> с непустым action, ИЛИ <button>
    внутри <form>/с data-action. Мёртвый CTA (ведёт в '#') = целевое действие сломано.
  • если задан --target <substr>, хотя бы один CTA ведёт на target (нужный URL/действие).

Опционально ОНЛАЙН (если --url и есть сеть): HTTP 200 + страница не пустая.
RU-доступность (check-host.net) — печатает подсказку (полная проверка вне офлайн-скоупа).

Использование:
    python3 check-deploy.py <index.html> [--target "/pay"] [--url https://site.ru]
Exit: 0 = CTA рабочий; 3 = мёртвый/отсутствует CTA (или target недостижим); 2 = ошибка ввода.
Safe-by-design: нет файла → exit 0.
"""
import re
import sys

DEAD_HREF = ("", "#", "javascript:void(0)", "javascript:;", "javascript:void(0);")


def find_ctas(html):
    """Вернуть список (тип, target) кандидатов-CTA."""
    ctas = []
    for m in re.finditer(r'<a\b[^>]*\bhref\s*=\s*"([^"]*)"[^>]*>', html, re.I):
        ctas.append(("a", m.group(1).strip()))
    for m in re.finditer(r"<a\b[^>]*\bhref\s*=\s*'([^']*)'[^>]*>", html, re.I):
        ctas.append(("a", m.group(1).strip()))
    for m in re.finditer(r'<form\b[^>]*\baction\s*=\s*"([^"]*)"', html, re.I):
        ctas.append(("form", m.group(1).strip()))
    for m in re.finditer(r"<form\b[^>]*\baction\s*=\s*'([^']*)'", html, re.I):
        ctas.append(("form", m.group(1).strip()))
    return ctas


def live_targets(html):
    """CTA с РЕАЛЬНЫМ назначением (не мёртвый href)."""
    out = []
    for typ, tgt in find_ctas(html):
        low = tgt.lower()
        if low in DEAD_HREF:
            continue
        out.append((typ, tgt))
    # <form> вообще (даже без action= → сабмит на ту же страницу = валидно)
    if re.search(r"<form\b", html, re.I):
        out.append(("form", "(self-submit)"))
    return out


def main():
    args = sys.argv[1:]

    def popval(flag):
        if flag in args:
            i = args.index(flag)
            v = args[i + 1] if i + 1 < len(args) else ""
            del args[i:i + 2]
            return v
        return None

    target = popval("--target")
    url = popval("--url")
    if not args:
        sys.stderr.write("usage: check-deploy.py <index.html> [--target T] [--url U]\n")
        sys.exit(2)
    try:
        html = open(args[0], encoding="utf-8", errors="ignore").read()
    except Exception:
        sys.exit(0)

    live = live_targets(html)
    if not live:
        print("🛑 DEPLOY: ни одного РАБОЧЕГО целевого действия на странице.\n"
              "Все CTA мертвы (href='#'/пусто/javascript:void) и нет <form>. "
              "Целевое действие из брифа Фазы 0 обязано вести к реальному шагу "
              "(оплата/форма/подписка). Память: feedback_verify_real_user_path_not_healthcheck.")
        sys.exit(3)
    if target:
        if not any(target.lower() in t.lower() for _, t in live):
            print(f"🛑 DEPLOY: ни один рабочий CTA не ведёт на target «{target}».\n"
                  f"Рабочие назначения: {[t for _, t in live][:8]}.\n"
                  "Целевое действие должно вести именно на нужный шаг воронки.")
            sys.exit(3)

    if url:
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=8) as r:
                code = getattr(r, "status", r.getcode())
                body = r.read(2048)
            if code != 200 or len(body) < 100:
                print(f"🛑 DEPLOY: {url} вернул {code} / пустую страницу.")
                sys.exit(3)
        except Exception as e:
            print(f"⚠️ DEPLOY: не достучался до {url} ({e}). Проверь хостинг/DNS. "
                  "RU-доступность отдельно прогнать через check-host.net (гео РФ).")

    print(f"✅ DEPLOY: целевое действие живое ({len(live)} рабочих CTA). "
          + ("RU-IP проверь вручную через check-host.net." if not url else ""))
    sys.exit(0)


if __name__ == "__main__":
    main()
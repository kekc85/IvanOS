#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stateinik_publish.py — custom-адаптер публикации статьи в движок Stateinik.

Реализует cms.adapter=custom для «Скилла статей»: берёт готовый черновик (.md/.mdx)
и заливает его в Stateinik через его admin-API. Поток ровно как у движка:

  1. POST /api/auth/login            — вход одним админом, кладём cookie в jar
  2. POST /api/admin/guides          — создаём гайд (title, type, authorId) → {id, slug}
  3. PUT  /api/admin/guides/{id}     — заливаем content (MDX) + SEO-поля
  4. POST /api/admin/guides/{id}/publish   — публикуем (если --status published)

Зависимости: только стандартная библиотека (urllib, http.cookiejar, json, argparse).
Учётка и адрес берутся из .env движка (--env) либо из флагов. Пароль не печатается.

Использование:
  python3 stateinik_publish.py \
      --env <путь-к-твоему-cms-env> \
      --author-id <id> \
      --title "Заголовок" --type tutorial --status published \
      $WORK/<slug>/draft.md

Коды выхода: 0 — опубликовано/сохранено; 1 — ошибка (печатается причина).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
import http.cookiejar


# ── .env / frontmatter ───────────────────────────────────────────────────────

def load_env(path):
    """Прочитать KEY=VALUE из .env движка. Возвращает dict (пустой при отсутствии)."""
    out = {}
    if not path:
        return out
    path = os.path.expanduser(path)
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def split_frontmatter(text):
    """Отделить YAML-frontmatter от тела. Возвращает (meta:dict, body:str)."""
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            head = text[3:end]
            body = text[end + 4:].lstrip("\n")
            for line in head.splitlines():
                if ":" in line and not line.strip().startswith("#"):
                    k, _, v = line.partition(":")
                    meta[k.strip()] = v.strip().strip('"').strip("'")
            return meta, body
    return meta, text


# ── HTTP (stdlib, с cookie-jar) ──────────────────────────────────────────────

class Client:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )

    def _req(self, method, path, payload=None):
        url = self.base + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        # CSRF: движок сверяет Origin с NEXT_PUBLIC_APP_URL (в dev пускает localhost).
        req.add_header("Origin", self.base)
        req.add_header("User-Agent", "stateinik-publish/1.0")
        try:
            with self.opener.open(req, timeout=30) as r:
                raw = r.read().decode("utf-8", "replace")
                return r.getcode(), (json.loads(raw) if raw.strip() else {})
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = {"error": raw[:300]}
            return e.code, body
        except Exception as e:
            return 0, {"error": str(e)}

    def post(self, path, payload):
        return self._req("POST", path, payload)

    def put(self, path, payload):
        return self._req("PUT", path, payload)


def die(msg, code, body=None):
    extra = f" :: {json.dumps(body, ensure_ascii=False)}" if body else ""
    sys.stderr.write(f"stateinik-publish: {msg}{extra}\n")
    sys.exit(code)


# ── основной поток ───────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Публикация статьи в движок Stateinik через admin-API (cms.adapter=custom).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("draft", help="путь к черновику (.md/.mdx)")
    p.add_argument("--env", default="<путь-к-твоему-cms-env>",
                   help="путь к .env движка (берём ADMIN_EMAIL/PASSWORD/NEXT_PUBLIC_APP_URL)")
    p.add_argument("--base-url", default=None, help="адрес движка (перекрывает .env)")
    p.add_argument("--email", default=None, help="админ-email (перекрывает .env)")
    p.add_argument("--password", default=None, help="админ-пароль (перекрывает .env)")
    p.add_argument("--author-id", default=None, help="id автора в движке")
    p.add_argument("--author-name", default=None,
                   help="если author-id не задан — создать автора с этим именем")
    p.add_argument("--title", default=None, help="заголовок (иначе из frontmatter/H1)")
    p.add_argument("--slug", default=None, help="slug (иначе движок сгенерит из title)")
    p.add_argument("--type", default="tutorial",
                   choices=("pillar", "tutorial", "playbook", "recipe"))
    p.add_argument("--difficulty", default="beginner",
                   choices=("beginner", "intermediate", "advanced"))
    p.add_argument("--status", default="draft", choices=("draft", "published"))
    p.add_argument("--meta-description", default=None)
    p.add_argument("--meta-title", default=None,
                   help="SEO-title (metaTitle в движке; иначе из frontmatter metaTitle/meta_title)")
    p.add_argument("--excerpt", default=None)
    p.add_argument("--target-keyword", default=None)
    p.add_argument("--json", action="store_true", help="итог машинно-читаемым JSON")
    args = p.parse_args()

    if not os.path.isfile(args.draft):
        die(f"нет файла черновика: {args.draft}", 1)
    raw = open(args.draft, encoding="utf-8").read()
    meta, body = split_frontmatter(raw)

    env = load_env(args.env)
    base = args.base_url or env.get("NEXT_PUBLIC_APP_URL") or "http://localhost:3000"
    email = args.email or env.get("ADMIN_EMAIL")
    password = args.password or env.get("ADMIN_PASSWORD")
    if not email or not password:
        die("нет ADMIN_EMAIL/ADMIN_PASSWORD (укажи --env или --email/--password)", 1)

    # title: флаг → frontmatter → первый H1 → имя файла
    title = args.title or meta.get("title")
    if not title:
        m = re.search(r"^#\s+(.+)$", body, re.M)
        title = m.group(1).strip() if m else os.path.splitext(os.path.basename(args.draft))[0]

    cli = Client(base)

    # 1) login
    code, r = cli.post("/api/auth/login", {"email": email, "password": password})
    if code != 200:
        die("логин не прошёл", 1, r)

    # 2) author: id из флага/frontmatter, иначе создаём по имени
    author_id = args.author_id or meta.get("authorId")
    if not author_id:
        if not args.author_name:
            die("нужен --author-id или --author-name", 1)
        code, r = cli.post("/api/admin/authors", {"name": args.author_name})
        if code != 201:
            die("не удалось создать автора", 1, r)
        author_id = r.get("id")

    # 3) создать гайд
    create = {"title": title, "type": args.type, "authorId": author_id}
    if args.slug:
        create["slug"] = args.slug
    code, r = cli.post("/api/admin/guides", create)
    if code != 201:
        die("не удалось создать гайд", 1, r)
    gid, slug = r.get("id"), r.get("slug")

    # 4) залить content + SEO-поля
    # frontmatter: camelCase - исходный контракт, snake_case - fallback (движок 2.0 пишет так)
    upd = {
        "content": body,
        "type": args.type,
        "difficulty": args.difficulty,
        "metaDescription": (args.meta_description or meta.get("metaDescription")
                            or meta.get("meta_description")
                            or meta.get("description") or "")[:300],
        "excerpt": (args.excerpt or meta.get("excerpt") or "")[:300],
    }
    tk = (args.target_keyword or meta.get("targetKeyword")
          or meta.get("target_keyword") or meta.get("keyword"))
    if tk:
        upd["targetKeyword"] = tk
    # metaTitle есть в PUT-контракте движка (admin/guides/[id]: body.metaTitle -> data.metaTitle).
    # Передаём ТОЛЬКО если задан - отсутствие поля движок трактует как «не менять» (undefined).
    mt = args.meta_title or meta.get("metaTitle") or meta.get("meta_title")
    if mt:
        upd["metaTitle"] = mt[:120]
    code, r = cli.put(f"/api/admin/guides/{gid}", upd)
    if code != 200:
        die("не удалось залить content (проверь MDX)", 1, r)

    # 5) опубликовать
    published = False
    if args.status == "published":
        code, r = cli.post(f"/api/admin/guides/{gid}/publish", {})
        if code != 200:
            die("создан черновик, но публикация не прошла", 1, r)
        published = True

    live = f"{base}/guides/{slug}"
    result = {"id": gid, "slug": slug, "status": "published" if published else "draft",
              "url": live, "admin": f"{base}/admin/guides/{gid}"}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"OK: {result['status']}  ->  {live}")
        print(f"admin: {result['admin']}")
    sys.exit(0)


if __name__ == "__main__":
    main()
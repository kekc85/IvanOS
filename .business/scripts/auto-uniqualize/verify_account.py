#!/usr/bin/env python3
"""
Gate аккаунта ChatGPT перед рендером карусели.

Подключается по CDP к УЖЕ ОТКРЫТОМУ Chrome (:9222), спрашивает у chatgpt.com,
какой аккаунт залогинен и какой у него тариф, и решает: можно рендерить или нет.

Правило: рендерить МОЖНО только если это Plus (или Pro/Team) — НИКОГДА на Go/Free.
Это тот самый предохранитель, которого раньше не было: машина молча жгла Go,
пока не упиралась в дневной лимит. Теперь при не-Plus — hard abort, ноль рендера.

Exit 0 = аккаунт годен (Plus). Exit 1 = не годен / не залогинен / браузер недоступен.
Печатает в stdout строку вида:  ACCOUNT ok=<bool> email=<...> plan=<...>

Использование:
    python3 verify_account.py                 # берёт cdp_url и ожидания из config.json
    python3 verify_account.py --cdp http://127.0.0.1:9222
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

CFG_PATH = Path(__file__).with_name("config.json")

# Тарифы, на которых рендерить РАЗРЕШЕНО (owner Custom GPT — Plus).
ALLOWED_PLANS = {"plus", "pro", "team", "enterprise"}
# Тарифы/аккаунты, на которых рендерить ЗАПРЕЩЕНО явно (для внятного сообщения).
FORBIDDEN_PLANS = {"free", "chatgptgo", "go"}


def load_cfg() -> dict:
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


async def probe(cdp_url: str) -> dict:
    """Возвращает {'email':..., 'plan':..., 'raw':...} или {'error':...}."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(cdp_url)
        except Exception as e:
            return {"error": f"CDP недоступен ({cdp_url}): {e}"}

        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        try:
            # 1) Кто залогинен: /api/auth/session отдаёт JSON с user.email и accessToken.
            await page.goto("https://chatgpt.com/api/auth/session",
                            wait_until="domcontentloaded", timeout=30000)
            body = await page.inner_text("body")
            session = {}
            try:
                session = json.loads(body)
            except Exception:
                return {"error": "session не JSON (вероятно не залогинен / Cloudflare)",
                        "raw": body[:300]}

            email = ((session.get("user") or {}).get("email") or "").lower()
            token = session.get("accessToken") or ""
            if not email:
                return {"error": "нет user.email — не залогинен", "raw": body[:300]}

            # 2) Какой тариф: accounts/check/v4 с Bearer-токеном из сессии.
            plan = ""
            if token:
                plan = await page.evaluate(
                    """async (tok) => {
                        try {
                            const r = await fetch(
                              'https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27',
                              { headers: { 'Authorization': 'Bearer ' + tok } });
                            const j = await r.json();
                            const accs = j.accounts || {};
                            for (const k of Object.keys(accs)) {
                                const pt = ((accs[k].entitlement || {}).plan_type)
                                        || (((accs[k].account || {}).plan_type))
                                        || '';
                                if (pt) return String(pt);
                            }
                            return '';
                        } catch (e) { return 'ERR:' + e; }
                    }""",
                    token,
                )
            return {"email": email, "plan": (plan or "").lower(), "raw": session}
        finally:
            try:
                await page.close()
            except Exception:
                pass
            # НЕ закрываем browser — это живой CDP-Chrome.


def decide(res: dict, cfg: dict) -> tuple[bool, str]:
    if "error" in res:
        return False, res["error"] + (f" | raw={res.get('raw','')}" if res.get("raw") else "")

    email = res.get("email", "")
    plan = res.get("plan", "")
    plus_email = (cfg.get("chatgpt_plus_email") or "").lower()
    forbidden_emails = {e.lower() for e in cfg.get("chatgpt_forbidden_emails", [])}

    # НАЗНАЧЕННЫЙ аккаунт (config chatgpt_plus_email) проходит ВСЕГДА, даже Go:
    # автор явно переключился на него по решению автора (Plus-лимит выжжен). Чужие Go/Free — стоп ниже.
    if plus_email and email == plus_email:
        return True, f"{email} (назначенный аккаунт, plan={plan or '?'})"

    # Явно чужой (Go) аккаунт по почте — стоп.
    if email in forbidden_emails:
        return False, f"аккаунт ЗАПРЕЩЁН по почте (это Go): {email} plan={plan or '?'}"
    if plan in FORBIDDEN_PLANS:
        return False, f"тариф не Plus: {email} plan={plan}"

    # Годен, если тариф в разрешённых ЛИБО почта совпала с ожидаемым Plus.
    if plan in ALLOWED_PLANS:
        return True, f"{email} plan={plan}"
    if plus_email and email == plus_email:
        return True, f"{email} (совпал ожидаемый Plus, plan={plan or '?'})"

    # Тариф не распознан и почта не подтверждена — не рискуем.
    return False, (f"аккаунт НЕ подтверждён как Plus: {email} plan={plan or '?'} "
                   f"(ожидался {plus_email or 'Plus-тариф'})")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cdp", default=None)
    args = ap.parse_args()

    cfg = load_cfg()
    cdp_url = args.cdp or cfg.get("cdp_url", "http://127.0.0.1:9222")

    res = await probe(cdp_url)
    ok, msg = decide(res, cfg)
    print(f"ACCOUNT ok={ok} {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

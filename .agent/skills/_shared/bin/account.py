#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BYOA account helper — конфиг внешних сервисов УЧЕНИКА (его аккаунты, не автора).
Канон: _shared/bring-your-own-account.md
Использование:
  account.py status  <service>
  account.py get     <service>.<field>   |   <service> <field>
  account.py set     <service>.<field> <value>
  account.py onboard <service>
Чистый stdlib, кроссплатформенно. Конфиг: ~/.business/processes/accounts.json (chmod 600).
"""
import sys, os, json

CFG = os.path.expanduser("~/.business/processes/accounts.json")

DEFAULTS = {
    "heygen":      {"mode": "browser", "avatar_name": "", "avatar_id": "", "voice_name": "", "api_key": "", "voice_id": ""},
    "elevenlabs":  {"api_key": "", "voice_id": ""},
    "higgsfield":  {"mode": "browser", "connected": False},
    "instagram":   {"cookies_path": "~/.business/processes/.ig-cookies.json"},
    "google_flow": {"mode": "browser", "cdp_profile": "~/.chrome-cdp-profile", "connected": False},
    "openai":      {"api_key": ""},
    "custom_gpt":  {"mode": "browser", "gpt_url": "https://chatgpt.com/g/g-6a18ce2cbacc8191b6410b0bb6810d03-carousels-<твой-бренд>"},
    "apify":       {"env_var": "APIFY_TOKEN"},
}

# главное поле, по которому судим «подключён ли сервис у ученика»
MAIN = {
    "heygen": "avatar_name",
    "elevenlabs": "api_key",
    "higgsfield": "connected",
    "instagram": "_cookie_file",     # спец: проверяем существование файла куки
    "google_flow": "connected",
    "openai": "api_key",
    "custom_gpt": "gpt_url",
    "apify": "_env_APIFY_TOKEN",     # спец: проверяем env/~/.claude/.env, не accounts.json
}

ONBOARD = {
    "custom_gpt": """[Custom GPT рендера каруселей — УЖЕ ПОДКЛЮЧЕНА, создавать ничего не надо]
Кастомка, которая рисует слайды, УЖЕ вписана в config (публичная ссылка автора). Она рисует
РОВНО твой текст, а твой бренд (палитра/watermark) приходит из _design.json на каждую серию.
Тебе нужно только войти в свой ChatGPT, чтобы она крутилась на ТВОЕЙ подписке:
1. Нужен ChatGPT Plus (chatgpt.com, платный тариф — кастомки работают только на нём).
2. Запусти онбординг машины: python3 ~/.business/scripts/auto-uniqualize/carousel_setup.py —
   он сам откроет браузер. В окне войди в свой ChatGPT (больше ничего настраивать не нужно).
3. Всё. Ссылку никуда вставлять не надо — она уже в config, драйвер ходит в неё на твоей сессии.""",
    "apify": """[ПОДКЛЮЧИ СВОЙ Apify — безопасный парсер Instagram (твой аккаунт вне цепочки)]
1. Заведи бесплатный аккаунт на https://apify.com (email, 1 минута; free-кредитов хватает на сотни постов).
2. В кабинете: Settings -> API & Integrations -> скопируй Personal API token.
3. Пришли мне токен — положу строкой APIFY_TOKEN=... в ~/.claude/.env (chmod 600).
4. Проверка: python3 ~/.business/scripts/ig-fetch/apify_ig.py profile <любой_публичный_профиль> 3
   — печатает посты и [cost] = работает. Это канон: парсинг НЕ под твоей IG-сессией, бана нет.""",
    "heygen": """[ПОДКЛЮЧИ СВОЙ HeyGen — цифровой двойник в кадре]
1. Заведи аккаунт на https://www.heygen.com (есть бесплатный тариф для пробы; рендер без вотермарки — на платном).
2. В СВОЁМ кабинете: Create avatar -> Avatar V (Clone a real person) -> загрузи СВОЁ видео, доведи аватар в студии. Это ТВОЙ двойник.
3. Подними залогиненный Chrome по CDP (см. replicate-viral/knowledge/heygen-browser.md под твою ОС), войди в СВОЙ HeyGen.
4. Назови имя своего аватара и голоса (как в твоём кабинете) — сохраню, дальше рендерю ТВОИМ аватаром.
Аватар/голос автора курса в твоём кабинете не существуют — используется ТОЛЬКО твой.""",
    "elevenlabs": """[ПОДКЛЮЧИ СВОЙ ElevenLabs — озвучка твоим голосом]
1. Заведи аккаунт https://elevenlabs.io (free даёт лимит символов; клон голоса — на платном).
2. Profile -> API key -> скопируй ключ.
3. (опц.) Клонируй СВОЙ голос (Voice Lab) или выбери из библиотеки, скопируй Voice ID.
4. Дай мне ключ и Voice ID — сохраню в твой accounts.json.""",
    "higgsfield": """[ПОДКЛЮЧИ СВОЙ Higgsfield — вау-вставки/инфографика]
1. Заведи аккаунт https://higgsfield.ai.
2. Войди в СВОЙ кабинет в Chrome (CDP-профиль, порт 9222).
3. Подтверди вход — ключ не нужен, работаем через твой залогиненный браузер.""",
    "instagram": """[ПОДКЛЮЧИ СВОЙ Instagram — парс виралок-доноров]
1. Скилл откроет окно Chromium с формой входа Instagram.
2. Войди в СВОЙ аккаунт (вкл. 2FA). Скрипт сам сохранит ТВОИ cookies в ~/.business/processes/.ig-cookies.json (chmod 600).
3. Это твоя сессия. Cookies автора в дистрибутиве отсутствуют.""",
    "google_flow": """[ПОДКЛЮЧИ СВОЙ Google Flow]
1. Подними залогиненный Chrome по CDP (порт 9222, профиль ~/.chrome-cdp-profile).
2. Войди в СВОЙ Google-аккаунт и открой Flow.
3. Подтверди вход — работаем на ТВОЕЙ сессии.""",
    "openai": """[ПОДКЛЮЧИ СВОЙ OpenAI ключ (если нужен скиллу)]
1. https://platform.openai.com/api-keys -> Create new secret key.
2. Дай мне ключ — сохраню в твой accounts.json.""",
}


def load():
    if not os.path.exists(CFG):
        return {}
    try:
        with open(CFG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save(data):
    d = os.path.dirname(CFG)
    os.makedirs(d, exist_ok=True)
    tmp = CFG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CFG)
    try:
        os.chmod(CFG, 0o600)
    except Exception:
        pass


def svc(data, name):
    if name not in data:
        data[name] = dict(DEFAULTS.get(name, {}))
    return data[name]


def is_connected(data, name):
    s = data.get(name, DEFAULTS.get(name, {}))
    main = MAIN.get(name)
    if main == "_cookie_file":
        p = os.path.expanduser(s.get("cookies_path", DEFAULTS["instagram"]["cookies_path"]))
        return os.path.exists(p) and os.path.getsize(p) > 0
    if main == "connected":
        return bool(s.get("connected"))
    return bool(str(s.get(main, "")).strip())


def parse_target(tok):
    # "service.field" или просто "service"
    if "." in tok:
        a, b = tok.split(".", 1)
        return a, b
    return tok, None


def main():
    a = sys.argv[1:]
    if not a:
        print("usage: account.py status|get|set|onboard <service>[.field] [value]", file=sys.stderr)
        return 2
    cmd = a[0]
    data = load()

    if cmd == "status":
        name = a[1]
        ok = is_connected(data, name)
        print("connected" if ok else "missing")
        return 0 if ok else 1

    if cmd == "onboard":
        name = a[1]
        print(ONBOARD.get(name, "[нет онбординг-блока для сервиса '%s']" % name))
        return 0

    if cmd == "get":
        name, field = parse_target(a[1])
        if len(a) >= 3:
            field = a[2]
        s = data.get(name, DEFAULTS.get(name, {}))
        if field is None:
            print(json.dumps(s, ensure_ascii=False))
        else:
            print(str(s.get(field, "")))
        return 0

    if cmd == "set":
        name, field = parse_target(a[1])
        if field is None and len(a) >= 4:
            field = a[2]; value = a[3]
        else:
            value = a[2] if field and len(a) >= 3 else (a[3] if len(a) >= 4 else "")
        if field is None:
            print("set требует <service>.<field> <value>", file=sys.stderr)
            return 2
        s = svc(data, name)
        # привести "true"/"false" к bool для connected-полей
        if value in ("true", "false"):
            s[field] = (value == "true")
        else:
            s[field] = value
        save(data)
        print("OK: %s.%s сохранено" % (name, field))
        return 0

    print("неизвестная команда: %s" % cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

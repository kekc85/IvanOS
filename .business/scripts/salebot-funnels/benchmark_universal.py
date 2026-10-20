#!/usr/bin/env python3
"""
benchmark_universal.py — структурный бенчмарк воронки ученика против УНИВЕРСАЛЬНОГО эталона.

В отличие от авторского benchmark.py (сверял копию с продающей дугой автора + его воркшоп),
этот проверяет ТОЛЬКО инварианты структуры, которые обязаны сохраниться при любой нише:
  - топология узлов и тайминги связей = как в эталоне (дуга не сломана)
  - 14 узлов (+ пара R1/R2, если заданы), sheets == []
  - код-слово в A0.condition (нижний регистр) и упомянуто в D7
  - TECH.condition == link_was_pressed <url кнопки B0>
  - НЕТ незаполненных плейсхолдеров {{...}} — каждый узел дуги написан под нишу
  - offer_url и channel_url реально подставлены (не остались {{OFFER_URL}}/{{CHANNEL_URL}})
  - в текстах нет длинных тире

Что писать в каждый узел — описано в SKILL.md (функции C1-C4 / D1-D7). Тут только проверка,
что ученик заполнил всё и не сломал каркас.

Запуск: python3 benchmark_universal.py   (гоняет все output/voronka-*.json против etalon-voronki.json)
"""
import json, glob, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ETALON = json.load(open(os.path.join(HERE, "etalon-voronki.json"), encoding="utf-8"))
CONN_IGNORE = {"id", "message_a_id", "message_b_id"}
PLACEHOLDER = re.compile(r"\{\{.*?\}\}", re.S)


def desc_key(msg):
    return msg["description"].split(" ", 1)[0].strip()


def index(data):
    return {desc_key(m): m for m in data["messages"]}


def conn_sig(conn, idx_map):
    rev = {m["id"]: dk for dk, m in idx_map.items()}
    rest = {f: v for f, v in conn.items() if f not in CONN_IGNORE}
    return (rev[conn["message_a_id"]], rev[conn["message_b_id"]],
            json.dumps(rest, sort_keys=True, ensure_ascii=False))


def check(path):
    errs = []
    gen = json.load(open(path, encoding="utf-8"))
    word = os.path.basename(path).replace("voronka-", "").replace(".json", "")

    # R1/R2 (пуши «не нажал Забрать») опциональны — валидируем и вырезаем, каркас мерим без них
    r_ids = {m["id"] for m in gen["messages"] if desc_key(m) in ("R1", "R2")}
    if r_ids:
        for m in gen["messages"]:
            if desc_key(m) in ("R1", "R2"):
                if not (m.get("answer") or "").strip():
                    errs.append(f"{desc_key(m)}: пустой текст")
                btns = json.loads(m.get("buttons") or "[]")
                # кнопка A0 = «Забрать» (без проверки) ИЛИ «Я подписался» (с проверкой подписки)
                if not (len(btns) == 1 and btns[0].get("text") in ("Забрать", "Я подписался")
                        and btns[0].get("type") == "reply"):
                    errs.append(f"{desc_key(m)}: нет reply-кнопки входа (Забрать / Я подписался)")
        gen = dict(gen,
                   messages=[m for m in gen["messages"] if m["id"] not in r_ids],
                   connections=[c for c in gen["connections"] if c["message_b_id"] not in r_ids])

    # каркас
    if set(gen.keys()) != set(ETALON.keys()):
        errs.append(f"верхние ключи: {set(gen.keys()) ^ set(ETALON.keys())}")
    if len(gen["messages"]) != len(ETALON["messages"]):
        errs.append(f"узлов {len(gen['messages'])}, в эталоне {len(ETALON['messages'])}")
    if len(gen["connections"]) != len(ETALON["connections"]):
        errs.append(f"связей {len(gen['connections'])}, в эталоне {len(ETALON['connections'])}")
    if gen.get("sheets") != []:
        errs.append("sheets не пустой")

    e_idx, g_idx = index(ETALON), index(gen)
    if set(e_idx) != set(g_idx):
        errs.append(f"узлы не совпали: {set(e_idx) ^ set(g_idx)}")
        return errs

    # топология + тайминги связей = как в эталоне (изоморфизм по desc_key + равенство полей)
    e_sigs = sorted(conn_sig(c, e_idx) for c in ETALON["connections"])
    g_sigs = sorted(conn_sig(c, g_idx) for c in gen["connections"])
    if e_sigs != g_sigs:
        errs.append("топология/тайминги связей сломаны относительно эталона")

    # каждый узел заполнен под нишу — плейсхолдеров не осталось
    for k, m in g_idx.items():
        leftover = PLACEHOLDER.findall(m.get("answer") or "")
        if leftover:
            errs.append(f"{k}: не заполнен под нишу (остался плейсхолдер {leftover[0][:40]}…)")
        for btn in json.loads(m.get("buttons") or "[]"):
            u = btn.get("url") or ""
            if "{{" in u:
                errs.append(f"{k}: кнопка ведёт на незаполненный плейсхолдер URL ({u})")

    # инварианты содержимого
    a0, b0, tech, d7 = g_idx["A0"], g_idx["B0"], g_idx["TECH"], g_idx["D7"]
    sub_check = "tg_get_chat_member" in (b0.get("saved_variables") or "")
    if sub_check:
        # ветка с проверкой подписки: выдача идёт калькулятором (tg_get_chat_member + if), не кнопкой
        sv = b0.get("saved_variables") or ""
        if "{{" in sv:
            errs.append("B0: не заполнен id канала для проверки подписки (остался плейсхолдер)")
        if "platform_id" not in sv or "if(" not in sv:
            errs.append("B0: калькулятор проверки подписки собран неверно")
    else:
        b0_btns = json.loads(b0.get("buttons") or "[]")
        if not b0_btns:
            errs.append("B0: нет кнопки выдачи")
        elif tech["condition"] != f"link_was_pressed {b0_btns[0]['url']}":
            errs.append("TECH.condition не совпадает с url кнопки B0")
    if a0["condition"] != a0["condition"].lower():
        errs.append("A0.condition (код-слово) не в нижнем регистре")
    if word not in d7["answer"]:
        errs.append(f"код-слово «{word}» не упомянуто в прощании D7")
    for k in g_idx:
        if re.search(r"[—–]", g_idx[k].get("answer") or ""):
            errs.append(f"длинное тире в {k}.answer (заменить на дефис)")

    # внутренняя консистентность id
    msg_ids = {m["id"] for m in gen["messages"]}
    for c in gen["connections"]:
        if c["message_a_id"] not in msg_ids or c["message_b_id"] not in msg_ids:
            errs.append(f"связь {c['id']} ссылается на несуществующий узел")
    return errs


def main():
    files = sorted(glob.glob(os.path.join(HERE, "output", "voronka-*.json")))
    if not files:
        sys.exit("нет файлов в output/ — сначала python3 generate.py content/<batch>.json")
    failed = 0
    for p in files:
        errs = check(p)
        name = os.path.basename(p)
        if errs:
            failed += 1
            print(f"FAIL {name}")
            for e in errs:
                print(f"     - {e}")
        else:
            print(f"PASS {name}")
    print(f"\nИтог: {len(files) - failed}/{len(files)} PASS")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

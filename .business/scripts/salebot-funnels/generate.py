#!/usr/bin/env python3
"""
generate.py — генератор SaleBot-воронок «код-слово → гайд → дожим на воркшоп».

Строит воронку НЕ с нуля, а глубокой копией эталона (etalon-voronki.json,
экспорт технаря из SaleBot, проект #100000). Меняются ТОЛЬКО разрешённые поля:

  A0   — condition (код-слово, нижний регистр) + answer (тематический текст) + description
  B0   — answer (тематический текст) + url кнопки «Забрать» → статья
  TECH — condition: link_was_pressed <url статьи>
  D7   — в answer слово КОДСЛОВО заменяется на новое код-слово
  все  — новые внутренне-консистентные id, сдвиг x (чтобы воронки не легли друг на друга на канвасе)

Всё остальное (тексты C1-C4, D1-D6, тайминги связей, кнопки на воркшоп,
message_type, comparision_method, флаги) — байт-в-байт из эталона.

Вход:  content/<batch>.json  (word, article_url, a0_mid, b0_body, b0_start)
Выход: output/voronka-<КОДСЛОВО>.json — файл под импорт технарём в SaleBot

Запуск: python3 generate.py content/batch-2026-07-02.json
После генерации ОБЯЗАТЕЛЬНО: python3 benchmark.py
"""
import json, sys, copy, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ETALON = os.path.join(HERE, "etalon-voronki.json")
OUTDIR = os.path.join(HERE, "output")

# A0 по умолчанию (subscribe_check=false): БЕЗ подписки - сразу выдаём лид-магнит по кнопке.
A0_TPL = ("<b>Привет! Держи то, ради чего ты здесь 👇</b>\r\n\r\n"
          "{a0_mid}\r\n\r\n"
          "<b>Жми «Забрать» - открою саму статью и расскажу, что внутри 👇</b>")

# A0 с проверкой подписки (subscribe_check=true): просим подписаться, кнопка «Я подписался».
A0_TPL_SUB = ("<b>Привет! Держи то, ради чего ты здесь 👇</b>\r\n\r\n"
              "{a0_mid}\r\n\r\n"
              "<b>Чтобы забрать гайд - подпишись на канал 👉 {channel_url}</b>\r\n\r\n"
              "<b>Подписался? Жми «Я подписался» - проверю и пришлю статью 👇</b>")

B0_TPL = ("<b>Финишная прямая, забирай эту детальную инструкцию, тебе точно зайдет</b>\r\n\r\n"
          "{b0_body}\r\n\r\n"
          "{b0_start}\r\n\r\n"
          "<b>Не читай всё подряд, делай по ходу. Жми кнопку 👇</b>")

X_SHIFT_STEP = 800  # сдвиг колонки на канвасе на каждую воронку


def desc_key(msg):
    """Ключ узла по префиксу description: A0 / B0 / TECH / C1..C4 / D1..D7."""
    return msg["description"].split(" ", 1)[0].strip()


REMINDER_BTN = '[{"line":0,"index_in_line":0,"text":"Забрать","type":"reply","callback":"123"}]'


def add_reminders(out, entry, idx, a0_btn="Забрать"):
    """R1/R2 - пуши тем, кто вошёл по слову, но не нажал кнопку A0 (автор).

    Топология: A0 +1ч → R1, R1 +23ч → R2. Оба узла несут ту же reply-кнопку
    «Забрать», что и A0. Движок воронкабота глушит их тегом magnet_taken
    (ставится при выдаче B0) и переносит из ночи в окно 10-21 МСК.
    Поля опциональны: батчи без r1_text/r2_text дают чистый эталон, как раньше.
    """
    if "r1_text" not in entry and "r2_text" not in entry:
        return
    if not (entry.get("r1_text") and entry.get("r2_text")):
        sys.exit(f"FAIL {entry['word']}: r1_text и r2_text задаются только парой")
    by_key = {desc_key(m): m for m in out["messages"]}
    a0 = by_key["A0"]
    hour_conn = next(c for c in out["connections"]
                     if str(c.get("timeout")) == "1" and c.get("timeout_type") == 3600)
    prev_id = a0["id"]
    for n, (key, text, hours) in enumerate(
            [("R1", entry["r1_text"], "1"), ("R2", entry["r2_text"], "23")], 15):
        msg = copy.deepcopy(a0)
        msg["id"] = int(f"7{idx:02d}000{n:02d}")
        msg["description"] = f"{key} — пуш «{a0_btn}» (не нажал кнопку)"
        msg["condition"] = "#{none}"
        msg["message_type"] = 0
        msg["answer"] = text
        msg["buttons"] = REMINDER_BTN.replace('"text":"Забрать"', f'"text":"{a0_btn}"')
        msg["y"] = msg.get("y", 0) - 300 * (n - 14)
        out["messages"].append(msg)
        conn = copy.deepcopy(hour_conn)
        conn["id"] = int(f"8{idx:02d}000{n - 3:02d}")
        conn["message_a_id"] = prev_id
        conn["message_b_id"] = msg["id"]
        conn["timeout"] = hours
        conn["timeout_type"] = 3600
        out["connections"].append(conn)
        prev_id = msg["id"]


def build(etalon, entry):
    word = entry["word"]
    url = entry["article_url"]
    idx = int(entry["idx"])
    out = copy.deepcopy(etalon)

    # вход = deep-link t.me/<бот>?start=<слово>; первое сообщение A0 просит подписаться на канал.
    # Развилка ученика (автор): subscribe_check=false (DEFAULT, проще, человек быстрее заберёт) -
    # кнопка «Забрать», выдача сразу; true - кнопка «Я подписался», ученик включает в SaleBot нативную
    # «проверку подписки» на этой кнопке (её JSON не изобретаем - это тумблер SaleBot с его каналом).
    channel = entry.get("channel_url") or "{{CHANNEL_URL}}"
    subscribe_check = bool(entry.get("subscribe_check", False))
    a0_btn = "Я подписался" if subscribe_check else "Забрать"

    # новые id: сообщения 7<idx:02>000NN, связи 8<idx:02>000NN — внутренне консистентны
    id_map = {}
    for n, msg in enumerate(out["messages"], 1):
        new_id = int(f"7{idx:02d}000{n:02d}")
        id_map[msg["id"]] = new_id
        msg["id"] = new_id
        msg["x"] = msg["x"] + idx * X_SHIFT_STEP
    for n, conn in enumerate(out["connections"], 1):
        conn["id"] = int(f"8{idx:02d}000{n:02d}")
        conn["message_a_id"] = id_map[conn["message_a_id"]]
        conn["message_b_id"] = id_map[conn["message_b_id"]]

    # C1-C4 + D1-D6 — узлы продающей/прогревной дуги. У автора берутся байт-в-байт из его
    # эталона (батч их не задаёт). У УЧЕНИКА эталон универсальный (плейсхолдеры), а тексты
    # под нишу приходят полями c1_text..d6_text + кнопки на offer_url. Поля опциональны:
    # заданы -> подставляем, нет -> остаётся как в эталоне (обратная совместимость).
    CD = {"C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4", "D5", "D6"}

    def _set_urls(msg, new_url):
        try:
            b = json.loads(msg.get("buttons") or "[]")
        except Exception:
            return
        for btn in b:
            if btn.get("url"):
                btn["url"] = new_url
        msg["buttons"] = json.dumps(b, ensure_ascii=False)

    for msg in out["messages"]:
        k = desc_key(msg)
        if k == "A0":
            msg["condition"] = word.lower()
            if subscribe_check:
                msg["answer"] = A0_TPL_SUB.format(a0_mid=entry["a0_mid"], channel_url=channel)
            else:
                msg["answer"] = A0_TPL.format(a0_mid=entry["a0_mid"])
            msg["description"] = f"A0 — старт по слову {word}"
            b = json.loads(msg["buttons"])
            for btn in b:
                btn["text"] = a0_btn                     # «Забрать» (default) или «Я подписался» (с проверкой)
            msg["buttons"] = json.dumps(b, ensure_ascii=False)
        elif k == "B0":
            msg["condition"] = a0_btn                     # выдача срабатывает на нажатие кнопки A0
            if subscribe_check:
                # РЕАЛЬНАЯ проверка подписки прямо в SaleBot, зашита в JSON (офиц. механизм,
                # docs.salebot.pro «Проверка подписки»): калькулятор блока зовёт tg_get_chat_member,
                # функция возвращает инфо о подписчике или None; оператор if отдаёт гайд только подписанному.
                chan_id = entry.get("channel_id") or "{{ID_КАНАЛА}}"
                nosub = f"Ты ещё не подписан на канал 👉 {channel}. Подпишись и снова жми «Я подписался»"
                deliver = f"Держи гайд, открой и делай по шагам 👉 {url}"
                msg["saved_variables"] = (f"sub = tg_get_chat_member(-100{chan_id}, platform_id)\n"
                                          f'otvet = if(sub == None, "{nosub}", "{deliver}")')
                msg["answer"] = "#{otvet}"
                msg["buttons"] = "[]"
            else:
                msg["answer"] = B0_TPL.format(b0_body=entry["b0_body"], b0_start=entry["b0_start"])
                btns = json.loads(msg["buttons"])
                btns[0]["url"] = url
                msg["buttons"] = json.dumps(btns, ensure_ascii=False)
        elif k == "TECH":
            msg["condition"] = f"link_was_pressed {url}"
        elif k in CD:
            fld = k.lower() + "_text"
            if entry.get(fld):
                msg["answer"] = entry[fld]
            if entry.get("offer_url"):
                _set_urls(msg, entry["offer_url"])
        elif k == "D7":
            if entry.get("d7_text"):
                msg["answer"] = entry["d7_text"]
            msg["answer"] = msg["answer"].replace("КОДСЛОВО", word)
            if entry.get("channel_url"):
                _set_urls(msg, entry["channel_url"])
    add_reminders(out, entry, idx, a0_btn)
    return out


def main():
    batch_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "content", "batch-2026-07-02.json")
    etalon = json.load(open(ETALON, encoding="utf-8"))
    batch = json.load(open(batch_path, encoding="utf-8"))
    os.makedirs(OUTDIR, exist_ok=True)
    for entry in batch["words"]:
        # страж формата: в тематических текстах нет длинных тире и запрещённой пунктуации
        for f in ("a0_mid", "b0_body", "b0_start", "r1_text", "r2_text",
                  "c1_text", "c2_text", "c3_text", "c4_text",
                  "d1_text", "d2_text", "d3_text", "d4_text", "d5_text", "d6_text", "d7_text"):
            if f not in entry:
                continue
            bad = re.findall(r"[—–]", entry[f])
            if bad:
                sys.exit(f"FAIL {entry['word']}: длинное тире в {f}")
        out = build(etalon, entry)
        path = os.path.join(OUTDIR, f"voronka-{entry['word']}.json")
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        print(f"OK {entry['word']:12} → {path}")


if __name__ == "__main__":
    main()

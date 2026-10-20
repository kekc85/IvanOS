"""Тесты рассылок: разбор черновика, сегменты, чекпоинт-курсор, 2ФА, счётчики.
Отправку в Telegram НЕ дёргаем - проверяем логику и БД.
Запуск: .venv/bin/python -m tests.test_broadcast
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.db import DB
from app import broadcast as bc
from engine.model import deeplink as _dl

_p=_f=0
def check(n,c):
    global _p,_f
    if c: _p+=1
    else: _f+=1; print(f"  FAIL: {n}")

# --- разбор черновика (текст + кнопка) ---
body, btns = bc.parse_draft("Привет!\nЗабирай запись\nСмотреть | " + _dl('KEY') + "")
import json
b = json.loads(btns)
check("кнопка распознана из последней строки", len(b)==1 and b[0]["url"].endswith("start=KEY"))
check("тело без строки кнопки", "Смотреть |" not in body and "Забирай запись" in body)
check("has_link=True при кнопке", bc.has_link(btns))
body2, btns2 = bc.parse_draft("Просто текст без ссылки")
check("has_link=False без кнопки", not bc.has_link(btns2))

# --- 2ФА TOTP (детерминированно, не зависит от .env окружения) ---
import pyotp
from engine.model import tg_url
_saved = bc.TOTP_SECRET
bc.TOTP_SECRET = ""
check("verify_totp True когда секрет пуст (2ФА выкл)", bc.verify_totp("000000"))
sec = pyotp.random_base32()
bc.TOTP_SECRET = sec
# now()-путь как в проде; 2 попытки страхуют от редкой 30-сек границы окна
ok = any(bc.verify_totp(pyotp.TOTP(sec).now()) for _ in range(2))
check("правильный код проходит (now-путь как в проде)", ok)
check("левый код не проходит", not bc.verify_totp("000000"))
bc.TOTP_SECRET = _saved  # вернуть как было

# --- сегменты ---
db = DB(tempfile.mktemp(suffix=".sqlite"))
# 4 контакта: 2 в воронке КОМАНДЫ (1 registered), 1 в САЙТ, 1 органический (без воронки)
db.upsert_contact(1,"a","A","DEMO"); db.add_tag(1,"f_КОМАНДЫ"); db.add_tag(1,"registered")
db.upsert_contact(2,"b","B","DEMO"); db.add_tag(2,"f_КОМАНДЫ")
db.upsert_contact(3,"c","C","САЙТ"); db.add_tag(3,"f_САЙТ")
db.upsert_contact(4,"d","D",None)  # органический подписчик канала
db.set_flag(5,"opted_out",True)    # отписан
db.add_tag(3,"vip")  # 3 - произвольный ручной тег (не f_-префикс воронки)

check("сегмент all = только вошедшие в воронку (3, без органического и отписанного)",
      sorted(db.segment_users("all"))==[1,2,3])
check("сегмент registered = 1", db.segment_users("registered")==[1])
check("сегмент not_registered = вошедшие без реги (2,3)", sorted(db.segment_users("not_registered"))==[2,3])
check("сегмент funnel:КОМАНДЫ = 1,2", sorted(db.segment_users("funnel:КОМАНДЫ"))==[1,2])
check("сегмент tag:registered = 1 (тег как есть, без f_)", db.segment_users("tag:registered")==[1])
check("сегмент tag:vip = 3", db.segment_users("tag:vip")==[3])
check("неизвестный сегмент = пусто", db.segment_users("bogus")==[])

# --- чекпоинт-курсор рассылки ---
bid = db.create_broadcast("all", "тело", '[{"text":"x","url":tg_url("x")}]')
db.snapshot_recipients(bid, [1,2,3])
check("статус running, total=3", db.broadcast_report(bid)["status"]=="running" and db.broadcast_report(bid)["total"]==3)
check("первый батч = 3 pending", len(db.broadcast_batch(bid, 10))==3)
# отправили 1 и 2, третий заблокировал
db.mark_recipient(bid,1,"sent"); db.mark_recipient(bid,2,"sent"); db.mark_recipient(bid,3,"blocked")
r = db.broadcast_report(bid)
check("счётчики: sent=2 blocked=1", r["sent"]==2 and r["blocked"]==1)
check("после отправки всех - батч пуст (чекпоинт)", db.broadcast_batch(bid,10)==[])
# идемпотентность: повторный snapshot не задваивает
db.snapshot_recipients(bid, [1,2,3])
check("повторный snapshot не плодит дублей", len(list(db._c.execute("SELECT 1 FROM broadcast_recipients WHERE broadcast_id=?",(bid,))))==3)

# --- рестарт посреди рассылки продолжает с pending, не дублит ---
bid2 = db.create_broadcast("all","t",'[{"text":"x","url":tg_url("x")}]')
db.snapshot_recipients(bid2,[10,11,12,13])
db.mark_recipient(bid2,10,"sent"); db.mark_recipient(bid2,11,"sent")
# «рестарт»: заново читаем pending
check("после рестарта осталось 2 pending (12,13)", sorted(db.broadcast_batch(bid2,10))==[12,13])
check("running_broadcast возвращает активную", db.running_broadcast()==bid2)

# --- режим copyMessage: парсинг ссылки на пост канала ---
sc, sm = bc.parse_post_url(tg_url("c/1000000001/1234"))
check("приватный канал: chat_id = -100<id>", sc == "-1001000000001")
check("приватный канал: message_id распознан", sm == 1234)
sc2, sm2 = bc.parse_post_url(tg_url("имя_канала/1234"))
check("публичный канал с кириллицей в имени НЕ матчится (юзернеймы TG латиница/цифры/_)",
      sc2 is None and sm2 is None)
sc3, sm3 = bc.parse_post_url(tg_url("u06f756/777"))
check("публичный канал: chat_id = @username", sc3 == "@u06f756")
check("публичный канал: message_id распознан", sm3 == 777)
sc4, sm4 = bc.parse_post_url(tg_url("c/1000000001/1234/"))
check("приватный канал: завершающий слэш не ломает разбор", sc4 == "-1001000000001" and sm4 == 1234)
sc5, sm5 = bc.parse_post_url("не ссылка вообще")
check("мусорная строка -> (None, None)", sc5 is None and sm5 is None)
sc6, sm6 = bc.parse_post_url(tg_url("joinchat/AbCdEf123"))
check("инвайт-ссылка (не пост) -> (None, None)", sc6 is None and sm6 is None)

# --- create_broadcast в режиме copy + чтение обратно через broadcast_report ---
bid3 = db.create_broadcast("all", "", "[]", mode="copy", src_chat_id="-1001000000001", src_message_id=1234)
r3 = db.broadcast_report(bid3)
check("mode=copy сохранился", r3["mode"] == "copy")
check("src_chat_id сохранился", r3["src_chat_id"] == "-1001000000001")
check("src_message_id сохранился", r3["src_message_id"] == 1234)
check("text пуст в copy-режиме", r3["text"] == "")

# --- обратная совместимость: старый вызов БЕЗ mode/src_* (3 позиционных аргумента) ---
bid4 = db.create_broadcast("registered", "старый текстовый вызов", '[{"text":"x","url":tg_url("x")}]')
r4 = db.broadcast_report(bid4)
check("старый вызов: mode по умолчанию = 'text'", r4["mode"] == "text")
check("старый вызов: src_chat_id по умолчанию = None", r4["src_chat_id"] is None)
check("старый вызов: src_message_id по умолчанию = None", r4["src_message_id"] is None)
check("старый вызов: текст сохранился как раньше", r4["text"] == "старый текстовый вызов")

# --- миграция на СУЩЕСТВУЮЩЕЙ базе без колонок mode/src_* (прод-сценарий) ---
import sqlite3
old_path = tempfile.mktemp(suffix=".sqlite")
raw = sqlite3.connect(old_path)
raw.execute("""CREATE TABLE broadcasts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, segment TEXT, text TEXT, buttons TEXT,
  status TEXT DEFAULT 'draft', total INTEGER DEFAULT 0, sent INTEGER DEFAULT 0,
  failed INTEGER DEFAULT 0, blocked INTEGER DEFAULT 0, created_at REAL)""")
raw.execute("INSERT INTO broadcasts(segment,text,buttons,created_at) VALUES('all','старый','[]',0)")
raw.commit(); raw.close()
db_old = DB(old_path)   # __init__ должен доналить колонки через _ensure_column, не упасть
cols = {row[1] for row in db_old._c.execute("PRAGMA table_info(broadcasts)")}
check("миграция долила mode/src_chat_id/src_message_id на старой базе",
      {"mode", "src_chat_id", "src_message_id"} <= cols)
old_report = db_old.broadcast_report(1)
check("старая запись читается, mode=NULL/дефолт не ломает broadcast_report",
      old_report is not None and old_report["text"] == "старый")
# новая запись на мигрированной базе - обычный путь работает как на свежей
bid5 = db_old.create_broadcast("all", "", "[]", mode="copy", src_chat_id="@ch", src_message_id=5)
check("на мигрированной базе create_broadcast(copy) работает",
      db_old.broadcast_report(bid5)["mode"] == "copy")

print(f"\nИтог рассылки: {_p} passed, {_f} failed")
sys.exit(1 if _f else 0)

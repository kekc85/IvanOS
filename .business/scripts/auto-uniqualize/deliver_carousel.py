#!/usr/bin/env python3
"""Доставка карусели (видео/фото) в Telegram-бот: штампует <твой-хэндл> на КАЖДЫЙ слайд
(ротация позиции), бьёт на альбомы <=10, шлёт + чистое описание + кнопка-оригинал.
Usage: deliver_carousel.py <parent_dir(с out/ и caption.txt)> <source_url>"""
import os, sys, json, time, tempfile, subprocess, requests
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path.home()/".business/scripts/auto-uniqualize/.env")
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"); CHAT=os.getenv("TELEGRAM_USER_ID")
STAMP=str(Path.home()/".business/scripts/auto-uniqualize/stamp_watermark.py")
VPY=str(Path.home()/"work/_venvs/auto-uniqualize-venv/bin/python")
d=Path(sys.argv[1]); out=d/"out"
caption=(d/"caption.txt").read_text().strip()
src_url=sys.argv[2] if len(sys.argv)>2 else ""
if not src_url:
    sf=d/"_source_url.txt"
    src_url=sf.read_text().strip() if sf.exists() else ""
# ЗАКОН №3 (по решению автора): каждая карусель = переделка РЕАЛЬНОЙ виралки с живой ссылкой на оригинал.
# Нет ссылки = сочинено/без источника = НЕ доставлять (страхует ЗАКОН №1 «не сочинять»).
if not src_url.startswith("http") or not ("/p/" in src_url or "/reel/" in src_url):
    sys.exit("BLOCKED (ЗАКОН №3): _source_url.txt должен быть ссылкой на КОНКРЕТНЫЙ пост-оригинал "
             "(instagram.com/p/<shortcode>/ или /reel/), не на профиль и не пусто. "
             "Каждая карусель = переделка реальной залетевшей виралки с живой ссылкой на ОРИГИНАЛ. "
             "Ссылка на профиль / пусто = ты сочинил сам = доставке не подлежит (ЗАКОН №1).")
files=[f for f in sorted(out.iterdir(), key=lambda p:p.name) if f.suffix.lower() in (".png",".jpg",".mp4")]
tmp=Path(tempfile.mkdtemp())
stamped=[]
for i,f in enumerate(files):
    o=tmp/f"{i:02d}{f.suffix.lower()}"
    subprocess.run([VPY,STAMP,str(f),str(i),str(o)],check=True)
    stamped.append(o)
print(f"stamped {len(stamped)} слайдов <твой-хэндл> (ротация углов)")
def send_album(chunk):
    media=[]; data={}
    for i,f in enumerate(chunk):
        key=f"f{i}"; typ="video" if f.suffix.lower()==".mp4" else "photo"
        media.append({"type":typ,"media":f"attach://{key}"})
        data[key]=(f.name, open(f,"rb"), "video/mp4" if typ=="video" else "image/jpeg")
    data["chat_id"]=(None,str(CHAT)); data["media"]=(None,json.dumps(media))
    r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMediaGroup",files=data,timeout=300)
    print("album",len(chunk),r.status_code,r.json().get("ok"))
for i in range(0,len(stamped),10):
    send_album(stamped[i:i+10]); time.sleep(2)
requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT,"text":caption,"disable_web_page_preview":"true"},timeout=60); time.sleep(1)
if src_url:
    btn={"inline_keyboard":[[{"text":"🔗 Оригинал карусели","url":src_url}]]}
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",data={"chat_id":CHAT,"text":"🔗 Оригинал","reply_markup":json.dumps(btn)},timeout=60)
print("delivered ✓ (с водяной подписью)")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT_DIR = "workspace/carousel/kofe/slides_v3"
os.makedirs(OUT_DIR, exist_ok=True)

FONT_IMPACT = "C:/Windows/Fonts/impact.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"

BRAND_NAME = "Андрей Зубков"
BRAND_HANDLE = "@andrei_pro_zdorovie"
COLOR_ACCENT = (245, 166, 35)      # Янтарный #F5A623
COLOR_CYAN = (0, 210, 255)         # Ледяной циан #00D2FF
COLOR_RED = (255, 82, 82)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (175, 185, 200)
COLOR_DARK_CARD = (16, 22, 34, 255)
COLOR_BG = (10, 14, 22)

IMG_AUTHOR = "workspace/assets/photos/author/author.jpg"
IMG_COVER_AUTHOR = "workspace/assets/backgrounds/author_cover_cold.jpg"
IMG_MITO = "workspace/assets/backgrounds/mitochondria.jpg"
IMG_COFFEE_CRASH = "workspace/assets/backgrounds/coffee_crash.jpg"

def draw_header_counter(draw, slide_num, total=7, outline_color=COLOR_CYAN):
    w, h = 114, 50
    x, y = 1080 - w - 55, 46
    draw.rounded_rectangle([x, y, x + w, y + h], radius=25, fill=(10, 14, 22, 255), outline=outline_color, width=2)
    font = ImageFont.truetype(FONT_BOLD, 24)
    text = f"{slide_num}/{total}"
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + (h - th) // 2 - 2), text, fill=COLOR_WHITE, font=font)

def draw_badge(draw, text, x=60, y=50, color=COLOR_CYAN):
    f_badge = ImageFont.truetype(FONT_BOLD, 22)
    bbox = f_badge.getbbox(text)
    bw = (bbox[2] - bbox[0]) + 36
    bh = 46
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=23, fill=(18, 26, 42, 240), outline=color, width=2)
    draw.text((x + 18, y + 10), text, fill=color, font=f_badge)

def draw_footer_brand(draw, accent_color=COLOR_CYAN, bg_color=COLOR_BG):
    draw.rectangle([0, 1235, 1080, 1350], fill=bg_color)
    draw.line([(80, 1255), (1000, 1255)], fill=(35, 50, 75), width=1)
    
    f_name = ImageFont.truetype(FONT_BOLD, 26)
    f_pipe = ImageFont.truetype(FONT_REGULAR, 24)
    f_handle = ImageFont.truetype(FONT_REGULAR, 24)
    
    t_name = BRAND_NAME
    t_pipe = "  |  "
    t_handle = BRAND_HANDLE
    
    wn = f_name.getbbox(t_name)[2] - f_name.getbbox(t_name)[0]
    wp = f_pipe.getbbox(t_pipe)[2] - f_pipe.getbbox(t_pipe)[0]
    wh = f_handle.getbbox(t_handle)[2] - f_handle.getbbox(t_handle)[0]
    
    total_w = wn + wp + wh
    sx = (1080 - total_w) // 2
    ty = 1276
    
    draw.text((sx, ty), t_name, fill=COLOR_WHITE, font=f_name)
    draw.text((sx + wn, ty + 1), t_pipe, fill=(100, 120, 150), font=f_pipe)
    draw.text((sx + wn + wp, ty + 2), t_handle, fill=accent_color, font=f_handle)

def draw_swipe_pill(draw, x, y, text="ЛИСТАЙ →", outline_col=COLOR_ACCENT):
    f = ImageFont.truetype(FONT_BOLD, 26)
    bbox = f.getbbox(text)
    tw = bbox[2] - bbox[0]
    pw = max(260, tw + 60)
    ph = 68
    draw.rounded_rectangle([x, y, x + pw, y + ph], radius=34, fill=(30, 40, 55, 240), outline=outline_col, width=2)
    draw.text((x + (pw - tw) // 2, y + (ph - (bbox[3] - bbox[1])) // 2 - 2), text, fill=COLOR_WHITE, font=f)

# ─── СЛАЙД 1: ОБЛОЖКА ────────────────────────────────────────────────────────
def render_slide_1():
    # Открываем фотографию Андрея (справа)
    im = Image.open(IMG_COVER_AUTHOR).convert("RGBA")
    im = ImageOps.fit(im, (1080, 1350), centering=(0.5, 0.5))
    
    # Мягкий градиент слева, чтобы текст был идеально читаем
    grad = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    for x in range(650):
        alpha = int(245 * (1 - x / 650) ** 1.3)
        gdraw.line([(x, 0), (x, 1350)], fill=(8, 12, 22, alpha))
    for y in range(400):
        alpha = int(180 * (1 - y / 400) ** 1.3)
        gdraw.line([(0, y), (1080, y)], fill=(8, 12, 22, alpha))
    im = Image.alpha_composite(im, grad)
    draw = ImageDraw.Draw(im)

    font_title = ImageFont.truetype(FONT_IMPACT, 80)
    lines = [
        ("ЛОVУШКА", COLOR_WHITE),
        ("3 ЧАШЕК", COLOR_ACCENT),
        ("КОФЕ", COLOR_ACCENT),
        ("ПОЧЕМУ НЕТ СИЛ", COLOR_CYAN),
        ("В 14:00?", COLOR_CYAN),
    ]
    cur_y = 160
    for line, color in lines:
        line_clean = line.replace("ЛОVУШКА", "ЛОВУШКА")
        draw.text((64, cur_y + 4), line_clean, fill=(0, 0, 0, 240), font=font_title)
        draw.text((60, cur_y), line_clean, fill=color, font=font_title)
        cur_y += 98

    draw_swipe_pill(draw, 60, cur_y + 40, "ЛИСТАЙ →", COLOR_CYAN)
    draw_header_counter(draw, 1, 7, outline_color=COLOR_CYAN)
    draw_footer_brand(draw, accent_color=COLOR_CYAN)

    out = f"{OUT_DIR}/slide_01_cover.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 1 готов: {out}")

# ─── СЛАЙД 2: ВТОРИЧНЫЙ ХУК ──────────────────────────────────────────────────
def render_slide_2():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "СЕКРЕТ БОДРОСТИ", color=COLOR_CYAN)
    draw_header_counter(draw, 2, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 70)
    draw.text((60, 135), "УСТАЛ ОТ ВЯЛОСТИ И", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 215), "КОФЕ ЛИТРАМИ?", fill=COLOR_ACCENT, font=f_title)

    # Карточка 1: Организму не нужны стимуляторы
    c1 = [60, 320, 1020, 750]
    draw.rounded_rectangle(c1, radius=24, fill=(16, 24, 38, 255), outline=COLOR_CYAN, width=3)
    f_c1_h = ImageFont.truetype(FONT_BOLD, 32)
    draw.text((95, 360), "ОРГАНИЗМУ НЕ НУЖНЫ СТИМУЛЯТОРЫ", fill=COLOR_CYAN, font=f_c1_h)
    
    f_body = ImageFont.truetype(FONT_REGULAR, 27)
    p1 = (
        "Большинство пытается заглушить упадок сил очередной чашкой кофе или энергетиком.\n"
        "Но это лишь берет аварийную энергию в долг у надпочечников.\n\n"
        "Внутри каждого из нас уже заложен мощный природный генератор бодрости.\n"
        "Ему просто нужны целые мембраны клеток, а не бесконечный допинг."
    )
    cy = 430
    for block in p1.split("\n\n"):
        for l in textwrap.wrap(block, width=48):
            draw.text((95, cy), l, fill=COLOR_WHITE, font=f_body)
            cy += 40
        cy += 16

    # Карточка 2: Что ты узнаешь дальше
    c2 = [60, 780, 1020, 1050]
    draw.rounded_rectangle(c2, radius=24, fill=(20, 28, 42, 255), outline=(50, 65, 90), width=2)
    f_c2_h = ImageFont.truetype(FONT_BOLD, 28)
    draw.text((95, 815), "ЧТО ВЫ УЗНАЕТЕ ДАЛЬШЕ В КАРУСЕЛИ:", fill=COLOR_ACCENT, font=f_c2_h)

    bullets = [
        "• Почему кофе глушит датчик усталости, а не дает сил",
        "• Кредит у надпочечников: почему в 15:00 накрывает яма",
        "• Митохондрии: где на самом деле рождается 95% АТФ"
    ]
    by = 875
    f_b = ImageFont.truetype(FONT_REGULAR, 25)
    for b in bullets:
        draw.text((95, by), b, fill=COLOR_GRAY, font=f_b)
        by += 44

    draw_swipe_pill(draw, 60, 1100, "СМОТРИ РАЗБОР →", COLOR_ACCENT)
    draw_footer_brand(draw)

    out = f"{OUT_DIR}/slide_02_hook.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 2 готов: {out}")

# ─── СЛАЙД 3: НАУКА (АДЕНОЗИН И КРАШ) ────────────────────────────────────────
def render_slide_3():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "МЕХАНИКА ОБМАНА", color=COLOR_RED)
    draw_header_counter(draw, 3, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 70)
    draw.text((60, 135), "КОФЕ НЕ ДАЁТ ЭНЕРГИЮ", fill=COLOR_WHITE, font=f_title)

    # 3D изображение кружки / краша
    if os.path.exists(IMG_COFFEE_CRASH):
        cimg = Image.open(IMG_COFFEE_CRASH).convert("RGBA")
        cimg = ImageOps.fit(cimg, (960, 420), centering=(0.5, 0.5))
        im.paste(cimg, (60, 240))
        draw.rounded_rectangle([60, 240, 1020, 660], radius=20, outline=(60, 75, 100), width=2)

    c = [60, 690, 1020, 1160]
    draw.rounded_rectangle(c, radius=24, fill=(16, 24, 38, 255), outline=COLOR_RED, width=3)
    f_h = ImageFont.truetype(FONT_BOLD, 32)
    draw.text((95, 735), "БЛОКИРОВКА ДАТЧИКА УСТАЛОСТИ", fill=COLOR_RED, font=f_h)

    f_p = ImageFont.truetype(FONT_REGULAR, 26)
    p = (
        "В течение дня в клетках накапливается аденозин — естественный датчик усталости.\n\n"
        "Кофеин по форме идентичен аденозину. Он садится на его рецепторы и глушит сигнал тревоги.\n\n"
        "Усталость никуда не исчезает! Ты просто отключил горящую лампочку перегрева в автомобиле."
    )
    cy = 805
    for block in p.split("\n\n"):
        for l in textwrap.wrap(block, width=48):
            draw.text((95, cy), l, fill=COLOR_WHITE, font=f_p)
            cy += 38
        cy += 14

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_03_science.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 3 готов: {out}")

# ─── СЛАЙД 4: КРЕДИТ У НАДПОЧЕЧНИКОВ ─────────────────────────────────────────
def render_slide_4():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "ЦЕНА ИЛЛЮЗИИ", color=COLOR_ACCENT)
    draw_header_counter(draw, 4, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 68)
    draw.text((60, 135), "КРЕДИТ ПОД 100% ГОДОВЫХ", fill=COLOR_WHITE, font=f_title)

    # Две просторные карточки без наезда
    c1 = [60, 240, 1020, 640]
    draw.rounded_rectangle(c1, radius=24, fill=(18, 26, 40, 255), outline=COLOR_ACCENT, width=2)
    draw.text((95, 280), "1. Всплеск кортизола и адреналина", fill=COLOR_ACCENT, font=ImageFont.truetype(FONT_BOLD, 30))
    t1 = (
        "Кофеин заставляет надпочечники мобилизовать аварийный запас энергии.\n\n"
        "Пульс учащается, сосуды спазмируются, нервная система работает в режиме опасности. Это кратковременный форсаж за счёт износа систем."
    )
    cy = 345
    for block in t1.split("\n\n"):
        for l in textwrap.wrap(block, width=48):
            draw.text((95, cy), l, fill=COLOR_WHITE, font=ImageFont.truetype(FONT_REGULAR, 25))
            cy += 36
        cy += 12

    c2 = [60, 670, 1020, 1100]
    draw.rounded_rectangle(c2, radius=24, fill=(22, 20, 30, 255), outline=COLOR_RED, width=2)
    draw.text((95, 715), "2. Провал в яму усталости в 15:00", fill=COLOR_RED, font=ImageFont.truetype(FONT_BOLD, 30))
    t2 = (
        "Через 2 часа кофеин утилизируется в печени.\n\n"
        "Вся лавина накопленного аденозина обрушивается на рецепторы одновременно. Голова чугунная, наступает разбитость, и рука сама тянется за третьей чашкой."
    )
    cy = 780
    for block in t2.split("\n\n"):
        for l in textwrap.wrap(block, width=48):
            draw.text((95, cy), l, fill=COLOR_WHITE, font=ImageFont.truetype(FONT_REGULAR, 25))
            cy += 36
        cy += 12

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_04_debt.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 4 готов: {out}")

# ─── СЛАЙД 5: МИТОХОНДРИИ 3D ────────────────────────────────────────────────
def render_slide_5():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "ИСТИННЫЙ ИСТОЧНИК", color=COLOR_CYAN)
    draw_header_counter(draw, 5, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 70)
    draw.text((60, 135), "ЭНЕРГИЯ ЖИВЁТ", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 215), "В МИТОХОНДРИЯХ", fill=COLOR_CYAN, font=f_title)

    # 3D изображение митохондрии
    if os.path.exists(IMG_MITO):
        mimg = Image.open(IMG_MITO).convert("RGBA")
        mimg = ImageOps.fit(mimg, (960, 480), centering=(0.5, 0.5))
        im.paste(mimg, (60, 310))
        draw.rounded_rectangle([60, 310, 1020, 790], radius=20, outline=COLOR_CYAN, width=2)

    c = [60, 820, 1020, 1170]
    draw.rounded_rectangle(c, radius=24, fill=(16, 24, 38, 255), outline=(50, 65, 90), width=2)
    f_h = ImageFont.truetype(FONT_BOLD, 30)
    draw.text((95, 860), "95% ВСЕЙ ЭНЕРГИИ ТЕЛА = СИНТЕЗ АТФ", fill=COLOR_WHITE, font=f_h)

    f_p = ImageFont.truetype(FONT_REGULAR, 26)
    p = (
        "Митохондрия вырабатывает энергию только тогда, когда её мембрана эластична и целостна.\n\n"
        "Стресс и дефициты повреждают мембраны — и клетки буквально задыхаются без чистой энергии."
    )
    cy = 920
    for block in p.split("\n\n"):
        for l in textwrap.wrap(block, width=48):
            draw.text((95, cy), l, fill=COLOR_GRAY, font=f_p)
            cy += 36
        cy += 10

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_05_mitochondria.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 5 готов: {out}")

# ─── СЛАЙД 6: МОКАП ДИРЕКТА (КАК ЗАБРАТЬ ГАЙД) ────────────────────────────────
def render_slide_6():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "КАК ЗАБРАТЬ РАЗБОР", color=COLOR_ACCENT)
    draw_header_counter(draw, 6, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 68)
    draw.text((60, 125), "ИНТЕРАКТИВНЫЙ ГАЙД", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 195), "И КАЛЬКУЛЯТОР ДОЛГА", fill=COLOR_ACCENT, font=f_title)

    # Окно Директа
    mx, my, mw, mh = 100, 290, 880, 860
    draw.rounded_rectangle([mx, my, mx + mw, my + mh], radius=32, fill=(15, 20, 30, 255), outline=(45, 55, 75), width=3)
    
    # Шапка переписки
    draw.rounded_rectangle([mx, my, mx + mw, my + 95], radius=32, fill=(22, 28, 42, 255))
    draw.rectangle([mx, my + 50, mx + mw, my + 95], fill=(22, 28, 42, 255))
    
    # Аватар Андрея
    if os.path.exists(IMG_AUTHOR):
        av = Image.open(IMG_AUTHOR).convert("RGBA")
        s = min(av.size)
        av = av.crop(((av.width - s)//2, (av.height - s)//4, (av.width + s)//2, (av.height + s)//4 + s)).resize((64, 64), Image.Resampling.LANCZOS)
        mask = Image.new("L", (64, 64), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, 64, 64), fill=255)
        av.putalpha(mask)
        im.paste(av, (mx + 30, my + 16), av)
    else:
        draw.ellipse([mx + 30, my + 16, mx + 94, my + 80], fill=COLOR_ACCENT)

    draw.text((mx + 110, my + 20), "Андрей Зубков", fill=COLOR_WHITE, font=ImageFont.truetype(FONT_BOLD, 26))
    draw.text((mx + 110, my + 52), "@andrei_pro_zdorovie", fill=COLOR_ACCENT, font=ImageFont.truetype(FONT_REGULAR, 20))

    # Сообщение пользователя
    ux, uy = mx + mw - 260, my + 140
    draw.rounded_rectangle([ux, uy, mx + mw - 35, uy + 80], radius=24, fill=(55, 115, 245))
    draw.text((ux + 45, uy + 16), "КОФЕ", fill=COLOR_WHITE, font=ImageFont.truetype(FONT_IMPACT, 46))

    # Ответ бота
    bx, by = mx + 35, my + 260
    draw.rounded_rectangle([bx, by, mx + mw - 50, by + 460], radius=24, fill=(26, 34, 50))
    
    f_bot = ImageFont.truetype(FONT_REGULAR, 26)
    bot_text = [
        "Приветствую!",
        "",
        "Держи ссылку на интерактивный гайд:",
        "• Калькулятор твоего кофеинового долга",
        "• Биохимия аденозина и надпочечников",
        "• Восстановление мембран за 148 ₽/день",
        "• Бесплатный доступ ко всем 8 видеоурокам",
        "  Школы долголетия в Telegram!"
    ]
    ty = by + 28
    for line in bot_text:
        draw.text((bx + 30, ty), line, fill=COLOR_WHITE, font=f_bot)
        ty += 36

    # Кнопка в сообщении
    btn = [bx + 30, by + 370, mx + mw - 80, by + 435]
    draw.rounded_rectangle(btn, radius=18, fill=COLOR_ACCENT)
    f_btn = ImageFont.truetype(FONT_BOLD, 26)
    bt = "Читать интерактивный гайд ☕"
    bw = f_btn.getbbox(bt)[2] - f_btn.getbbox(bt)[0]
    draw.text((btn[0] + (btn[2] - btn[0] - bw) // 2, btn[1] + 18), bt, fill=(10, 14, 24), font=f_btn)

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_06_direct.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 6 готов: {out}")

# ─── СЛАЙД 7: ФИНАЛЬНЫЙ CTA (ОРГАНИЧНОЕ ФОТО АНДРЕЯ) ──────────────────────────
def render_slide_7():
    # Открываем фотографию Андрея
    im = Image.open(IMG_COVER_AUTHOR).convert("RGBA")
    im = ImageOps.fit(im, (1080, 1350), centering=(0.5, 0.5))
    
    # Накладываем глубокий вертикальный градиент снизу вверх
    grad = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    for y in range(500, 1350):
        alpha = int(255 * min(1.0, ((y - 500) / 450) ** 1.2))
        gdraw.line([(0, y), (1080, y)], fill=(8, 12, 22, alpha))
    for x in range(500):
        alpha = int(180 * (1 - x / 500) ** 1.3)
        gdraw.line([(x, 0), (x, 1350)], fill=(8, 12, 22, alpha))
    im = Image.alpha_composite(im, grad)
    draw = ImageDraw.Draw(im)

    draw_header_counter(draw, 7, 7, outline_color=COLOR_ACCENT)

    # Бейдж автора
    draw_badge(draw, "ПРОВОДНИК В ЗДОРОВЬЕ КЛЕТОК", x=60, y=550, color=COLOR_ACCENT)

    # Имя и ник
    f_auth_n = ImageFont.truetype(FONT_IMPACT, 64)
    draw.text((60, 620), BRAND_NAME, fill=COLOR_WHITE, font=f_auth_n)
    
    f_auth_h = ImageFont.truetype(FONT_BOLD, 30)
    draw.text((60, 700), BRAND_HANDLE, fill=COLOR_ACCENT, font=f_auth_h)

    # Карточка призыва
    c = [60, 770, 1020, 1160]
    draw.rounded_rectangle(c, radius=28, fill=(16, 22, 34, 250), outline=(50, 65, 90), width=2)

    f_cta_h = ImageFont.truetype(FONT_IMPACT, 44)
    draw.text((95, 805), "ХОЧЕШЬ РАССЧИТАТЬ СВОЙ ДОЛГ?", fill=COLOR_WHITE, font=f_cta_h)

    f_cta_p = ImageFont.truetype(FONT_REGULAR, 26)
    tp = "В интерактивном гайде тебя ждёт калькулятор кофеина и бесплатный доступ ко всем 8 видеоурокам Школы долголетия в Telegram."
    py = 865
    for l in textwrap.wrap(tp, width=48):
        draw.text((95, py), l, fill=COLOR_GRAY, font=f_cta_p)
        py += 36

    # Большая кнопка кодового слова
    pill = [95, 960, 985, 1060]
    draw.rounded_rectangle(pill, radius=30, fill=COLOR_ACCENT)
    f_pill = ImageFont.truetype(FONT_IMPACT, 46)
    pt = "НАПИШИ «КОФЕ» В ДИРЕКТ"
    pw = f_pill.getbbox(pt)[2] - f_pill.getbbox(pt)[0]
    draw.text((pill[0] + (pill[2] - pill[0] - pw) // 2, 985), pt, fill=(10, 14, 24), font=f_pill)

    f_sub = ImageFont.truetype(FONT_REGULAR, 23)
    st = "или в комментариях — бот пришлёт ссылку на гайд и уроки"
    sw = f_sub.getbbox(st)[2] - f_sub.getbbox(st)[0]
    draw.text((540 - sw // 2, 1090), st, fill=COLOR_WHITE, font=f_sub)

    draw_footer_brand(draw, accent_color=COLOR_ACCENT)
    out = f"{OUT_DIR}/slide_07_cta.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 7 готов: {out}")

def main():
    print("🎨 Генерация чистовой карусели v3 «Ловушка кофе»...")
    render_slide_1()
    render_slide_2()
    render_slide_3()
    render_slide_4()
    render_slide_5()
    render_slide_6()
    render_slide_7()
    print("🎉 Все 7 слайдов v3 готовы в", OUT_DIR)

if __name__ == "__main__":
    main()

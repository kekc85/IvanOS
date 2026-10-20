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

OUT_DIR = "workspace/carousel/kofe/slides_v2"
os.makedirs(OUT_DIR, exist_ok=True)

FONT_IMPACT = "C:/Windows/Fonts/impact.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"

BRAND_NAME = "Андрей Зубков"
BRAND_HANDLE = "@andrei_pro_zdorovie"
COLOR_ACCENT = (245, 166, 35)      # Янтарный оранжевый #F5A623
COLOR_CYAN = (0, 210, 255)         # Ледяной циан #00D2FF
COLOR_RED = (255, 82, 82)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (175, 185, 200)
COLOR_DARK_CARD = (18, 24, 38, 240)
COLOR_BG = (10, 14, 22)

IMG_AUTHOR = "workspace/assets/photos/author/author.jpg"
IMG_COVER_BG = "workspace/assets/backgrounds/cover_author.jpg"
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

def get_author_circle(size=210):
    im = Image.open(IMG_AUTHOR).convert("RGBA")
    w, h = im.size
    s = min(w, h)
    left = (w - s) // 2
    top = (h - s) // 4
    sq = im.crop((left, top, left + s, top + s)).resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    m_draw = ImageDraw.Draw(mask)
    m_draw.ellipse((0, 0, size, size), fill=255)
    circ = ImageOps.fit(sq, mask.size, centering=(0.5, 0.5))
    circ.putalpha(mask)
    return circ

# ─── СЛАЙД 1: ОБЛОЖКА ────────────────────────────────────────────────────────
def render_slide_1():
    im = Image.open(IMG_COVER_BG).convert("RGBA").resize((1080, 1350), Image.Resampling.LANCZOS)
    
    # Левый темный градиент для читаемости текста
    grad = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    for x in range(650):
        alpha = int(240 * (1 - x / 650) ** 1.3)
        gdraw.line([(x, 0), (x, 1350)], fill=(8, 12, 22, alpha))
    for y in range(400):
        alpha = int(180 * (1 - y / 400) ** 1.3)
        gdraw.line([(0, y), (1080, y)], fill=(8, 12, 22, alpha))
    im = Image.alpha_composite(im, grad)
    draw = ImageDraw.Draw(im)

    font_title = ImageFont.truetype(FONT_IMPACT, 78)
    lines = [
        ("ЛОВУШКА", COLOR_WHITE),
        ("3 ЧАШЕК КОФЕ", COLOR_ACCENT),
        ("ПОЧЕМУ БОДРОСТЬ", COLOR_WHITE),
        ("ДЛИТСЯ 20 МИНУТ?", COLOR_CYAN),
    ]
    cur_y = 220
    for line, color in lines:
        draw.text((64, cur_y + 4), line, fill=(0, 0, 0, 240), font=font_title)
        draw.text((60, cur_y), line, fill=color, font=font_title)
        cur_y += 94

    draw_swipe_pill(draw, 60, cur_y + 40, "ЛИСТАЙ →", COLOR_ACCENT)
    draw_header_counter(draw, 1, 7, outline_color=COLOR_ACCENT)
    draw_footer_brand(draw, accent_color=COLOR_ACCENT)

    out = f"{OUT_DIR}/slide_01_cover.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 1 готов: {out}")

# ─── СЛАЙД 2: ВТОРИЧНЫЙ ХУК ──────────────────────────────────────────────────
def render_slide_2():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "БИОХИМИЯ ЭНЕРГИИ", color=COLOR_CYAN)
    draw_header_counter(draw, 2, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 64)
    draw.text((60, 135), "УСТАЛ ОТ ВЯЛОСТИ И", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 205), "КОФЕ ЛИТРАМИ?", fill=COLOR_ACCENT, font=f_title)

    # Карточка 1: Организму не нужны стимуляторы
    c1 = [60, 310, 1020, 640]
    draw.rounded_rectangle(c1, radius=24, fill=(16, 22, 36, 240), outline=COLOR_CYAN, width=2)
    f_c1_h = ImageFont.truetype(FONT_BOLD, 30)
    draw.text((100, 350), "ОРГАНИЗМУ НЕ НУЖНЫ СТИМУЛЯТОРЫ", fill=COLOR_CYAN, font=f_c1_h)
    
    f_body = ImageFont.truetype(FONT_REGULAR, 26)
    p1 = "Большинство пытается заглушить упадок сил очередной чашкой кофе или энергетиком. Но это лишь берёт энергию в долг у надпочечников.\n\nВнутри каждой твоей клетки уже заложен природный генератор бодрости. Ему просто нужны целые мембраны."
    cy = 410
    for line in p1.split("\n"):
        if not line:
            cy += 14
            continue
        for l in textwrap.wrap(line, width=50):
            draw.text((100, cy), l, fill=COLOR_WHITE, font=f_body)
            cy += 36

    # Карточка 2: Что ты узнаешь дальше
    c2 = [60, 680, 1020, 1060]
    draw.rounded_rectangle(c2, radius=24, fill=(16, 22, 34, 240), outline=(45, 55, 75), width=2)
    f_c2_h = ImageFont.truetype(FONT_BOLD, 28)
    draw.text((100, 725), "ЧТО ТЫ УЗНАЕШЬ В КАРУСЕЛИ:", fill=COLOR_ACCENT, font=f_c2_h)

    bullets = [
        "• Почему кофе не дает энергию, а глушит датчик усталости",
        "• Кредит у надпочечников: почему в 15:00 накрывает яма",
        "• Митохондрии: где на самом деле рождается 95% АТФ",
        "• Восстановление мембран за 148 ₽ в день без ломки"
    ]
    by = 790
    for b in bullets:
        for l in textwrap.wrap(b, width=48):
            draw.text((100, by), l, fill=COLOR_GRAY, font=f_body)
            by += 36
        by += 10

    draw_swipe_pill(draw, 60, 1110, "СМОТРИ РАЗБОР →", COLOR_CYAN)
    draw_footer_brand(draw)

    out = f"{OUT_DIR}/slide_02_hook.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 2 готов: {out}")

# ─── СЛАЙД 3: КАК ЭТО РАБОТАЕТ ───────────────────────────────────────────────
def render_slide_3():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "МЕХАНИКА ОБМАНА", color=COLOR_RED)
    draw_header_counter(draw, 3, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 72)
    draw.text((60, 135), "КОФЕ НЕ ДАЁТ ЭНЕРГИЮ", fill=COLOR_WHITE, font=f_title)

    # Изображение чашки / краша
    if os.path.exists(IMG_COFFEE_CRASH):
        cimg = Image.open(IMG_COFFEE_CRASH).convert("RGBA").resize((960, 480), Image.Resampling.LANCZOS)
        im.paste(cimg, (60, 240))
        draw.rounded_rectangle([60, 240, 1020, 720], radius=20, outline=(50, 60, 80), width=2)

    c = [60, 760, 1020, 1160]
    draw.rounded_rectangle(c, radius=24, fill=(16, 22, 36, 240), outline=COLOR_RED, width=2)
    f_h = ImageFont.truetype(FONT_BOLD, 30)
    draw.text((100, 805), "БЛОКИРОВКА РЕЦЕПТОРОВ АДЕНОЗИНА", fill=COLOR_RED, font=f_h)

    f_p = ImageFont.truetype(FONT_REGULAR, 26)
    p = "В течение дня в мозге копится аденозин — молекула усталости.\n\nКофеин садится на её рецепторы и глушит сигнал. Усталость никуда не исчезает! Ты просто отключил мигающую красную лампочку перегрева в автомобиле."
    cy = 870
    for line in p.split("\n"):
        if not line:
            cy += 14
            continue
        for l in textwrap.wrap(line, width=50):
            draw.text((100, cy), l, fill=COLOR_WHITE, font=f_p)
            cy += 36

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

    f_title = ImageFont.truetype(FONT_IMPACT, 70)
    draw.text((60, 135), "КРЕДИТ ПОД 100% ГОДОВЫХ", fill=COLOR_WHITE, font=f_title)

    # 3 карточки последствий
    cards = [
        ("1. Всплеск кортизола", "Кофеин заставляет надпочечники выжимать аварийные запасы. Пульс растет, сосуды спазмируются.", COLOR_ACCENT),
        ("2. Провал в яму в 15:00", "Через 2 часа кофеин утилизируется, и вся лавина аденозина накрывает мозг. Голова чугунная.", COLOR_RED),
        ("3. Толерантность и доза", "Мозг выращивает новые рецепторы. Одной чашки уже мало — нужны 3-4, чтобы просто не спать.", COLOR_GRAY)
    ]
    
    cy = 260
    f_ch = ImageFont.truetype(FONT_BOLD, 28)
    f_cp = ImageFont.truetype(FONT_REGULAR, 24)
    for title, desc, col in cards:
        draw.rounded_rectangle([60, cy, 1020, cy + 240], radius=20, fill=(16, 22, 34, 240), outline=col, width=2)
        draw.text((100, cy + 30), title, fill=col, font=f_ch)
        py = cy + 85
        for l in textwrap.wrap(desc, width=50):
            draw.text((100, py), l, fill=COLOR_WHITE, font=f_cp)
            py += 34
        cy += 270

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_04_debt.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 4 готов: {out}")

# ─── СЛАЙД 5: МИТОХОНДРИИ ────────────────────────────────────────────────────
def render_slide_5():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "ИСТИННЫЙ ИСТОЧНИК", color=COLOR_CYAN)
    draw_header_counter(draw, 5, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 68)
    draw.text((60, 135), "ЭНЕРГИЯ ЖИВЁТ", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 210), "В МИТОХОНДРИЯХ", fill=COLOR_CYAN, font=f_title)

    # 3D изображение митохондрии
    if os.path.exists(IMG_MITO):
        mimg = Image.open(IMG_MITO).convert("RGBA").resize((960, 480), Image.Resampling.LANCZOS)
        im.paste(mimg, (60, 310))
        draw.rounded_rectangle([60, 310, 1020, 790], radius=20, outline=COLOR_CYAN, width=2)

    c = [60, 830, 1020, 1170]
    draw.rounded_rectangle(c, radius=24, fill=(16, 22, 36, 240), outline=(45, 60, 85), width=2)
    f_h = ImageFont.truetype(FONT_BOLD, 30)
    draw.text((100, 870), "95% ВСЕЙ ЭНЕРГИИ ТЕЛА = АТФ", fill=COLOR_WHITE, font=f_h)

    f_p = ImageFont.truetype(FONT_REGULAR, 26)
    p = "Митохондрия синтезирует АТФ только тогда, когда её мембрана эластична и целостна. При поврежденных мембранах клетки буквально задыхаются без энергии."
    cy = 935
    for l in textwrap.wrap(p, width=50):
        draw.text((100, cy), l, fill=COLOR_GRAY, font=f_p)
        cy += 36

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_05_mitochondria.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 5 готов: {out}")

# ─── СЛАЙД 6: РЕШЕНИЕ (СИБИКС) ───────────────────────────────────────────────
def render_slide_6():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "РЕШЕНИЕ БЕЗ СТИМУЛЯТОРОВ", color=COLOR_ACCENT)
    draw_header_counter(draw, 6, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 68)
    draw.text((60, 135), "ВОССТАНОВЛЕНИЕ МЕМБРАН", fill=COLOR_WHITE, font=f_title)

    # Карточка СибИКС
    c1 = [60, 240, 1020, 680]
    draw.rounded_rectangle(c1, radius=24, fill=(16, 22, 36, 240), outline=COLOR_ACCENT, width=2)
    f_c1_h = ImageFont.truetype(FONT_BOLD, 32)
    draw.text((100, 285), "ПОЛИПРЕНОЛЫ ПИХТЫ (СИБИКС)", fill=COLOR_ACCENT, font=f_c1_h)
    
    f_body = ImageFont.truetype(FONT_REGULAR, 26)
    p = "Полипренолы в печени превращаются в долихолы — природный строительный материал, который латает бреши в мембранах митохондрий.\n\nКлетка восстанавливает дыхание и начинает вырабатывать собственную чистую энергию без кофеина."
    cy = 350
    for line in p.split("\n"):
        if not line:
            cy += 14
            continue
        for l in textwrap.wrap(line, width=50):
            draw.text((100, cy), l, fill=COLOR_WHITE, font=f_body)
            cy += 36

    # Сравнение лоб в лоб
    c2 = [60, 720, 1020, 1150]
    draw.rounded_rectangle(c2, radius=24, fill=(16, 22, 34, 240), outline=(50, 60, 80), width=2)
    f_c2_h = ImageFont.truetype(FONT_BOLD, 28)
    draw.text((100, 765), "СРАВНЕНИЕ В ДЕНЬГАХ И ЭФФЕКТЕ:", fill=COLOR_WHITE, font=f_c2_h)

    draw.text((100, 840), "☕ 3 чашки кофе в кофейне: 450 - 600 ₽/день", fill=COLOR_RED, font=f_body)
    draw.text((100, 885), "   (аварийный кредит + вечерний откат)", fill=COLOR_GRAY, font=ImageFont.truetype(FONT_REGULAR, 22))

    draw.text((100, 950), "🌲 Восстановление СибИКС: 148 ₽/день", fill=COLOR_ACCENT, font=f_body)
    draw.text((100, 995), "   (стабильная чистая энергия с утра до вечера)", fill=COLOR_GRAY, font=ImageFont.truetype(FONT_REGULAR, 22))

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_06_solution.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 6 готов: {out}")

# ─── СЛАЙД 7: ФИНАЛЬНЫЙ CTA ──────────────────────────────────────────────────
def render_slide_7():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 24, 255))
    draw = ImageDraw.Draw(im)
    draw_header_counter(draw, 7, 7, outline_color=COLOR_ACCENT)

    # Фото автора с золотым кругом
    if os.path.exists(IMG_AUTHOR):
        auth = get_author_circle(210)
        im.paste(auth, (435, 120), auth)
        draw.ellipse([433, 118, 647, 332], outline=COLOR_ACCENT, width=4)

    f_auth_n = ImageFont.truetype(FONT_BOLD, 36)
    f_auth_h = ImageFont.truetype(FONT_REGULAR, 26)
    draw.text((540 - f_auth_n.getbbox(BRAND_NAME)[2] // 2, 355), BRAND_NAME, fill=COLOR_WHITE, font=f_auth_n)
    draw.text((540 - f_auth_h.getbbox(BRAND_HANDLE)[2] // 2, 402), BRAND_HANDLE, fill=COLOR_ACCENT, font=f_auth_h)

    # Карточка призыва
    card = [60, 470, 1020, 1170]
    draw.rounded_rectangle(card, radius=24, fill=COLOR_DARK_CARD, outline=(50, 60, 85), width=2)

    f_cta_h = ImageFont.truetype(FONT_IMPACT, 52)
    draw.text((100, 520), "ХОЧЕШЬ РАССЧИТАТЬ", fill=COLOR_WHITE, font=f_cta_h)
    draw.text((100, 580), "СВОЙ КОФЕИНОВЫЙ ДОЛГ?", fill=COLOR_ACCENT, font=f_cta_h)

    f_cta_p = ImageFont.truetype(FONT_REGULAR, 26)
    text_p = "Я создал интерактивный гайд с калькулятором кофеинового долга и бесплатными 8 видеоуроками «Школы долголетия: Люди без возраста» в Telegram."
    py = 665
    for l in textwrap.wrap(text_p, width=48):
        draw.text((100, py), l, fill=COLOR_GRAY, font=f_cta_p)
        py += 38

    # Кнопка кодового слова
    pill = [100, 860, 980, 980]
    draw.rounded_rectangle(pill, radius=30, fill=COLOR_ACCENT)
    f_pill = ImageFont.truetype(FONT_IMPACT, 46)
    pt = "НАПИШИ «КОФЕ» В ДИРЕКТ"
    pw = f_pill.getbbox(pt)[2] - f_pill.getbbox(pt)[0]
    draw.text((540 - pw // 2, 890), pt, fill=(10, 14, 24), font=f_pill)

    f_bot = ImageFont.truetype(FONT_REGULAR, 24)
    bt = "или в комментариях — бот пришлет доступ к гайду и урокам"
    bw = f_bot.getbbox(bt)[2] - f_bot.getbbox(bt)[0]
    draw.text((540 - bw // 2, 1020), bt, fill=COLOR_WHITE, font=f_bot)

    draw_footer_brand(draw, accent_color=COLOR_ACCENT)
    out = f"{OUT_DIR}/slide_07_cta.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 7 готов: {out}")

def main():
    print("🎨 Генерация 7 слайдов авторской карусели «Ловушка кофе»...")
    render_slide_1()
    render_slide_2()
    render_slide_3()
    render_slide_4()
    render_slide_5()
    render_slide_6()
    render_slide_7()
    print("🎉 Все 7 слайдов карусели успешно сгенерированы в", OUT_DIR)

if __name__ == "__main__":
    main()

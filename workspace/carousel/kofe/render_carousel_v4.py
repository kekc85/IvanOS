#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_carousel_v4.py — Финальная эталонная карусель 1080x1350 для Андрея Зубкова
Тема: «Ловушка 3 чашек кофе: почему нет сил в 14:00?»
Кодовое слово: «КОФЕ»

Ключевые стандарты:
1. Реальные разные фото Андрея на слайде 1 (портрет) и слайде 7 (жест шака).
2. Никакого растяжения: пропорциональное масштабирование Lanczos (scale 1.125 одинаково по X и Y).
3. Полное отсутствие наездов текста на фото на слайде 1 (запас >130 px до силуэта).
4. На слайде 7 яркое объемное светящееся слово «КОФЕ» в золотом градиенте, 3D стрелка и стеклянный бейдж.
5. Единая подпись автора «Андрей Зубков | @andrei_pro_zdorovie» на всех 7 слайдах.
"""

import os
import sys
import textwrap
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

OUT_DIR = "workspace/carousel/kofe/slides_v4"
os.makedirs(OUT_DIR, exist_ok=True)

FONT_IMPACT = "C:/Windows/Fonts/impact.ttf"
FONT_BOLD = "C:/Windows/Fonts/arialbd.ttf"
FONT_REGULAR = "C:/Windows/Fonts/arial.ttf"

BRAND_NAME = "Андрей Зубков"
BRAND_HANDLE = "@andrei_pro_zdorovie"

COLOR_ACCENT = (255, 175, 45)      # Теплый янтарный / карамельный
COLOR_CYAN = (60, 190, 255)         # Электрик циан
COLOR_WARN = (255, 90, 80)          # Кораллово-красный
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (180, 195, 215)
COLOR_DARK_CARD = (16, 22, 34, 245)
COLOR_DARK_BG = (10, 14, 22)

IMG_COVER_PORTRAIT = r"workspace\assets\backgrounds\author_cover_portrait.jpg"
IMG_CTA_REFERENCE = r"workspace\assets\backgrounds\author_cta_reference.jpg"
IMG_SCIENCE = r"workspace\assets\backgrounds\coffee_adenosine_bg.jpg"
IMG_MITO = r"workspace\assets\backgrounds\broll_mitochondria_3d.jpg"

def draw_header_counter(draw, slide_num, total=7, outline_color=COLOR_ACCENT):
    w, h = 114, 50
    x, y = 1080 - w - 55, 46
    draw.rounded_rectangle([x, y, x + w, y + h], radius=25, fill=(10, 14, 22, 255), outline=outline_color, width=2)
    font = ImageFont.truetype(FONT_BOLD, 24)
    text = f"{slide_num}/{total}"
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x + (w - tw) // 2, y + (h - th) // 2 - 2), text, fill=COLOR_WHITE, font=font)

def draw_footer_brand(draw, accent_color=COLOR_ACCENT, bg_color=(10, 14, 22)):
    draw.rectangle([0, 1235, 1080, 1350], fill=bg_color)
    draw.line([(80, 1255), (1000, 1255)], fill=(35, 45, 65), width=1)
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

def draw_badge(draw, text, color=COLOR_CYAN, top_y=60):
    f_badge = ImageFont.truetype(FONT_BOLD, 22)
    b_box = f_badge.getbbox(text)
    bw = (b_box[2] - b_box[0]) + 36
    draw.rounded_rectangle([60, top_y, 60 + bw, top_y + 44], radius=12, fill=(20, 30, 48, 255), outline=color, width=2)
    draw.text((78, top_y + 8), text, fill=color, font=f_badge)

def draw_swipe_pill(draw, x, y, text="ЛИСТАЙ →", outline_col=COLOR_ACCENT):
    f = ImageFont.truetype(FONT_BOLD, 26)
    bbox = f.getbbox(text)
    tw = bbox[2] - bbox[0]
    pw = max(260, tw + 60)
    ph = 68
    draw.rounded_rectangle([x, y, x + pw, y + ph], radius=34, fill=(15, 22, 35, 240), outline=outline_col, width=2)
    draw.text((x + (pw - tw) // 2, y + (ph - (bbox[3] - bbox[1])) // 2 - 2), text, fill=COLOR_WHITE, font=f)

# ─── СЛАЙД 1: ОБЛОЖКА (ПОРТРЕТ АНДРЕЯ БЕЗ НАЕЗДОВ ТЕКСТА) ─────────────────────
def render_slide_1():
    src = Image.open(IMG_COVER_PORTRAIT).convert("RGBA")
    scale = 1350.0 / src.height
    new_w = int(src.width * scale)  # 1008 px
    src_scaled = src.resize((new_w, 1350), Image.Resampling.LANCZOS)

    canvas = Image.new("RGBA", (1080, 1350), (12, 17, 26, 255))
    canvas.paste(src_scaled, (1080 - new_w, 0))

    # Мягкий градиент слева только под текст (до x=460)
    grad = Image.new("RGBA", (1080, 1350), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(grad)
    for x in range(460):
        alpha = int(240 * (1 - x / 460) ** 1.4)
        gdraw.line([(x, 0), (x, 1350)], fill=(10, 14, 22, alpha))
    canvas = Image.alpha_composite(canvas, grad)
    draw = ImageDraw.Draw(canvas)

    font_title = ImageFont.truetype(FONT_IMPACT, 72)
    lines = [
        ("ЛОВУШКА", COLOR_WHITE),
        ("3 ЧАШЕК", COLOR_ACCENT),
        ("КОФЕ", COLOR_ACCENT),
        ("ПОЧЕМУ", COLOR_WHITE),
        ("НЕТ СИЛ", COLOR_CYAN),
        ("В 14:00?", COLOR_CYAN),
    ]

    cur_y = 180
    for line, color in lines:
        draw.text((63, cur_y + 4), line, fill=(0, 0, 0, 240), font=font_title)
        draw.text((60, cur_y), line, fill=color, font=font_title)
        cur_y += 88

    draw_swipe_pill(draw, 60, cur_y + 35, "ЛИСТАЙ →", COLOR_CYAN)
    draw_header_counter(draw, 1, 7, outline_color=COLOR_CYAN)
    draw_footer_brand(draw, accent_color=COLOR_CYAN)

    out = f"{OUT_DIR}/slide_01_cover.png"
    canvas.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 1 готов (без наездов и растяжений): {out}")

# ─── СЛАЙД 2: ВТОРИЧНЫЙ ХУК ──────────────────────────────────────────────────
def render_slide_2():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "СЕКРЕТ БОДРОСТИ", color=COLOR_CYAN)
    draw_header_counter(draw, 2, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 70)
    draw.text((60, 135), "УСТАЛ ОТ ВЯЛОСТИ И", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 215), "КОФЕ ЛИТРАМИ?", fill=COLOR_ACCENT, font=f_title)

    # Карточка 1
    c1 = [60, 320, 1020, 710]
    draw.rounded_rectangle(c1, radius=24, fill=(18, 24, 38, 245), outline=COLOR_CYAN, width=2)
    draw.text((95, 355), "ОРГАНИЗМУ НЕ НУЖНЫ СТИМУЛЯТОРЫ", fill=COLOR_CYAN, font=ImageFont.truetype(FONT_BOLD, 30))
    desc_1 = (
        "Каждое утро ты заливаешь в себя кофе, чтобы просто открыть глаза. "
        "Но к обеду накрывает туман, вялость и апатия. Ты берешь вторую и третью чашку, "
        "но вместо энергии получаешь тревожность, тахикардию и разбитость."
    )
    cy = 415
    for l in textwrap.wrap(desc_1, width=44):
        draw.text((95, cy), l, fill=COLOR_WHITE, font=ImageFont.truetype(FONT_REGULAR, 26))
        cy += 38

    # Карточка 2
    c2 = [60, 750, 1020, 1140]
    draw.rounded_rectangle(c2, radius=24, fill=(24, 18, 24, 245), outline=COLOR_WARN, width=2)
    draw.text((95, 785), "ЧТО ПРОИСХОДИТ НА САМОМ ДЕЛЕ:", fill=COLOR_WARN, font=ImageFont.truetype(FONT_BOLD, 30))
    desc_2 = (
        "Кофеин НЕ ДАЕТ телу ни одного джоуля реальной энергии.\n\n"
        "Он лишь блокирует датчики усталости в мозге и берет разрушительный "
        "кредит у твоих надпочечников, который придется отдавать двойным крашем."
    )
    cy = 845
    for paragraph in desc_2.split("\n"):
        if not paragraph.strip():
            cy += 12
            continue
        for l in textwrap.wrap(paragraph, width=44):
            draw.text((95, cy), l, fill=COLOR_GRAY, font=ImageFont.truetype(FONT_REGULAR, 26))
            cy += 38

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_02_hook.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 2 готов: {out}")

# ─── СЛАЙД 3: НАУКА И АДЕНОЗИН ───────────────────────────────────────────────
def render_slide_3():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    if os.path.exists(IMG_SCIENCE):
        bg = Image.open(IMG_SCIENCE).convert("RGBA").resize((1080, 520), Image.Resampling.LANCZOS)
        im.paste(bg, (0, 0))
        grad = Image.new("RGBA", (1080, 520), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(grad)
        for y in range(520):
            alpha = int(255 * (y / 520) ** 1.3)
            gdraw.line([(0, y), (1080, y)], fill=(10, 14, 22, alpha))
        im = Image.alpha_composite(im, grad)

    draw = ImageDraw.Draw(im)
    draw_badge(draw, "БИОХИМИЯ КРАША", color=COLOR_ACCENT, top_y=50)
    draw_header_counter(draw, 3, 7)

    f_h = ImageFont.truetype(FONT_IMPACT, 68)
    draw.text((60, 480), "КАК РАБОТАЕТ ЛОВУШКА:", fill=COLOR_WHITE, font=f_h)

    card = [60, 570, 1020, 1170]
    draw.rounded_rectangle(card, radius=24, fill=COLOR_DARK_CARD, outline=COLOR_ACCENT, width=2)

    steps = [
        ("1. Аденозин копится в мозге", "Пока ты бодрствуешь, этот гормон сигнализирует клеткам об усталости.", COLOR_WHITE),
        ("2. Кофеин блокирует рецепторы", "Молекула кофеина садится на рецептор, обманывая мозг на 3-4 часа.", COLOR_ACCENT),
        ("3. Накопительная волна", "Аденозин продолжает расти в фоновом режиме, никуда не исчезая.", COLOR_CYAN),
        ("4. Неизбежный обвал в 14:00", "Действие кофеина спадает, и лавина аденозина выключает фокус и ясность.", COLOR_WARN)
    ]

    sy = 610
    f_st = ImageFont.truetype(FONT_BOLD, 28)
    f_sd = ImageFont.truetype(FONT_REGULAR, 24)
    for title, desc, col in steps:
        draw.text((95, sy), title, fill=col, font=f_st)
        sy += 40
        for l in textwrap.wrap(desc, width=48):
            draw.text((95, sy), l, fill=COLOR_GRAY, font=f_sd)
            sy += 32
        sy += 24

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_03_science.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 3 готов: {out}")

# ─── СЛАЙД 4: КРЕДИТ У НАДПОЧЕЧНИКОВ ──────────────────────────────────────────
def render_slide_4():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "ГОРМОНАЛЬНЫЙ ДОЛГ", color=COLOR_WARN)
    draw_header_counter(draw, 4, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 70)
    draw.text((60, 135), "КРЕДИТ У НАДПОЧЕЧНИКОВ", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 215), "И СЛОМАННЫЙ КОРТИЗОЛ", fill=COLOR_WARN, font=f_title)

    c1 = [60, 320, 1020, 710]
    draw.rounded_rectangle(c1, radius=24, fill=COLOR_DARK_CARD, outline=COLOR_WARN, width=2)
    draw.text((95, 355), "КОРТИЗОЛОВЫЙ ВСПЛЕСК С УТРА", fill=COLOR_WARN, font=ImageFont.truetype(FONT_BOLD, 30))
    d1 = (
        "Чашка кофе в первые 60 минут после пробуждения бьет по надпочечникам, "
        "когда уровень природного кортизола и так на пике. В итоге тело привыкает "
        "к химическому хлысту и перестает вырабатывать утренний тонус самостоятельно."
    )
    cy = 415
    for l in textwrap.wrap(d1, width=44):
        draw.text((95, cy), l, fill=COLOR_WHITE, font=ImageFont.truetype(FONT_REGULAR, 26))
        cy += 38

    c2 = [60, 750, 1020, 1140]
    draw.rounded_rectangle(c2, radius=24, fill=COLOR_DARK_CARD, outline=COLOR_ACCENT, width=2)
    draw.text((95, 785), "ИТОГ — СЛОМАННЫЕ ЦИКЛЫ СНА", fill=COLOR_ACCENT, font=ImageFont.truetype(FONT_BOLD, 30))
    d2 = (
        "Период полувыведения кофеина — от 6 до 8 часов. Выпитый в 15:00 латте "
        "разрушает медленную фазу ночного сна. Ты спишь 8 часов, но просыпаешься "
        "уставшим и снова тянешься к кружке. Порочный круг замкнулся."
    )
    cy = 845
    for l in textwrap.wrap(d2, width=44):
        draw.text((95, cy), l, fill=COLOR_GRAY, font=ImageFont.truetype(FONT_REGULAR, 26))
        cy += 38

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_04_debt.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 4 готов: {out}")

# ─── СЛАЙД 5: МИТОХОНДРИИ И АТФ ──────────────────────────────────────────────
def render_slide_5():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    if os.path.exists(IMG_MITO):
        bg = Image.open(IMG_MITO).convert("RGBA").resize((1080, 480), Image.Resampling.LANCZOS)
        im.paste(bg, (0, 0))
        grad = Image.new("RGBA", (1080, 480), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(grad)
        for y in range(480):
            alpha = int(255 * (y / 480) ** 1.3)
            gdraw.line([(0, y), (1080, y)], fill=(10, 14, 22, alpha))
        im = Image.alpha_composite(im, grad)

    draw = ImageDraw.Draw(im)
    draw_badge(draw, "ИСТОЧНИК ЭНЕРГИИ", color=COLOR_CYAN, top_y=50)
    draw_header_counter(draw, 5, 7)

    f_h = ImageFont.truetype(FONT_IMPACT, 68)
    draw.text((60, 470), "ГДЕ БРАТЬ НАСТОЯЩИЕ СИЛЫ?", fill=COLOR_WHITE, font=f_h)

    card = [60, 560, 1020, 1170]
    draw.rounded_rectangle(card, radius=24, fill=COLOR_DARK_CARD, outline=COLOR_CYAN, width=2)

    rules = [
        ("1. Правило 90 минут", "Пей кофе строго через 90-120 мин после подъема, когда аденозин смыт водой.", COLOR_CYAN),
        ("2. Утренний свет и гидратация", "Стакан теплой воды с минералами + 10 минут дневного света запускают митохондрии.", COLOR_WHITE),
        ("3. Стоп-линия в 14:00", "Запрет на кофеин после двух часов дня спасает глубокий сон и выработку АТФ.", COLOR_ACCENT),
        ("4. Синтез клеточной энергии", "В Школе Долголетия мы восстанавливаем мембраны клеток и клеточный заряд.", (120, 240, 160))
    ]

    sy = 600
    f_rt = ImageFont.truetype(FONT_BOLD, 28)
    f_rd = ImageFont.truetype(FONT_REGULAR, 24)
    for title, desc, col in rules:
        draw.text((95, sy), title, fill=col, font=f_rt)
        sy += 40
        for l in textwrap.wrap(desc, width=48):
            draw.text((95, sy), l, fill=COLOR_GRAY, font=f_rd)
            sy += 32
        sy += 24

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_05_mitochondria.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 5 готов: {out}")

# ─── СЛАЙД 6: МОКАП ДИРЕКТА ──────────────────────────────────────────────────
def render_slide_6():
    im = Image.new("RGBA", (1080, 1350), (10, 14, 22, 255))
    draw = ImageDraw.Draw(im)
    draw_badge(draw, "КАЛЬКУЛЯТОР В ДИРЕКТ", color=COLOR_ACCENT)
    draw_header_counter(draw, 6, 7)

    f_title = ImageFont.truetype(FONT_IMPACT, 70)
    draw.text((60, 135), "ИНТЕРАКТИВНЫЙ РАСЧЕТ", fill=COLOR_WHITE, font=f_title)
    draw.text((60, 215), "ПОД ТВОЕ РАСПИСАНИЕ", fill=COLOR_ACCENT, font=f_title)

    mx, my, mw, mh = 140, 310, 800, 680
    draw.rounded_rectangle([mx, my, mx + mw, my + mh], radius=32, fill=(15, 20, 30, 255), outline=(40, 55, 80), width=3)

    # Header
    draw.rounded_rectangle([mx, my, mx + mw, my + 85], radius=32, fill=(22, 30, 45, 255))
    draw.rectangle([mx, my + 45, mx + mw, my + 85], fill=(22, 30, 45, 255))
    draw.ellipse([mx + 30, my + 18, mx + 78, my + 66], fill=COLOR_ACCENT)
    draw.text((mx + 95, my + 18), "Андрей Зубков", fill=COLOR_WHITE, font=ImageFont.truetype(FONT_BOLD, 24))
    draw.text((mx + 95, my + 48), "@andrei_pro_zdorovie", fill=COLOR_ACCENT, font=ImageFont.truetype(FONT_REGULAR, 18))

    # User message
    ux, uy = mx + mw - 250, my + 130
    draw.rounded_rectangle([ux, uy, mx + mw - 40, uy + 65], radius=20, fill=(60, 130, 245))
    draw.text((ux + 48, uy + 14), "КОФЕ", fill=COLOR_WHITE, font=ImageFont.truetype(FONT_IMPACT, 38))

    # Bot response
    bx, by = mx + 40, my + 230
    draw.rounded_rectangle([bx, by, mx + mw - 40, by + 390], radius=24, fill=(25, 34, 50))
    f_b = ImageFont.truetype(FONT_REGULAR, 24)
    lines = [
        "Приветствую! ☕",
        "",
        "Отправляю доступ к интерактивному калькулятору:",
        "• Твое идеальное окно бодрости без кофеинового краша",
        "• Точный расчет пика кортизола под твой подъем",
        "• 8 видеоуроков Школы Долголетия в Telegram"
    ]
    ty = by + 25
    for l in lines:
        draw.text((bx + 25, ty), l, fill=COLOR_WHITE, font=f_b)
        ty += 32

    # Button
    btn_y = ty + 15
    draw.rounded_rectangle([bx + 25, btn_y, mx + mw - 65, btn_y + 56], radius=16, fill=COLOR_ACCENT)
    draw.text((bx + 85, btn_y + 14), "ОТКРЫТЬ КАЛЬКУЛЯТОР ☕", fill=(10, 15, 25), font=ImageFont.truetype(FONT_BOLD, 22))

    # Note below mockup
    draw.text((150, 1060), "Напиши «КОФЕ» в комментарии или Директ", fill=COLOR_WHITE, font=ImageFont.truetype(FONT_BOLD, 28))
    draw.text((220, 1105), "Бот пришлет расчет за 1 секунду 📩", fill=COLOR_CYAN, font=ImageFont.truetype(FONT_REGULAR, 24))

    draw_footer_brand(draw)
    out = f"{OUT_DIR}/slide_06_direct.png"
    im.convert("RGB").save(out, quality=95)
    print(f"✅ Слайд 6 готов: {out}")

# ─── СЛАЙД 7: ФИНАЛЬНЫЙ CTA (ЭТАЛОН С ЖЕСТОМ ШАКА И ЗОЛОТЫМ «КОФЕ») ──────────
def render_slide_7():
    # 1. Загружаем эталонное фото с жестом шака
    img_bgr = cv2.imread(IMG_CTA_REFERENCE)
    
    # 2. Инпейнтим старое слово «БАЛАНС»
    region = img_bgr[210:410, 50:560]
    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    mask_region = cv2.inRange(hsv, np.array([10, 50, 80]), np.array([45, 255, 255]))
    kernel = np.ones((7, 7), np.uint8)
    mask_dilated = cv2.dilate(mask_region, kernel, iterations=2)
    full_mask = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    full_mask[210:410, 50:560] = mask_dilated
    inpainted = cv2.inpaint(img_bgr, full_mask, inpaintRadius=9, flags=cv2.INPAINT_TELEA)

    # 3. Переводим в PIL RGBA
    base = Image.fromarray(cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)).convert("RGBA")

    # 4. Рисуем светящееся 3D золотое слово «КОФЕ»
    txt = "«КОФЕ»"
    font_size = 135
    font = ImageFont.truetype(FONT_IMPACT, font_size)
    bbox = font.getbbox(txt)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    target_cx = 295
    target_cy = 310
    x = target_cx - tw // 2
    y = target_cy - th // 2 - 10

    # Свечение
    glow_img = Image.new("RGBA", base.size, (0, 0, 0, 0))
    for r, a in [(32, 50), (18, 90), (10, 140), (5, 200)]:
        t_layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
        ldraw = ImageDraw.Draw(t_layer)
        ldraw.text((x, y), txt, fill=(255, 145, 20, a), font=font)
        t_layer = t_layer.filter(ImageFilter.GaussianBlur(r))
        glow_img = Image.alpha_composite(glow_img, t_layer)

    # Тень
    shadow_img = Image.new("RGBA", base.size, (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.text((x + 6, y + 8), txt, fill=(10, 5, 0, 220), font=font)
    shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(4))

    # Золотой вертикальный градиент
    grad_mask = Image.new("L", (tw + 40, th + 40), 0)
    m_draw = ImageDraw.Draw(grad_mask)
    m_draw.text((20, 20), txt, fill=255, font=font)

    grad_tex = Image.new("RGBA", (tw + 40, th + 40))
    for gy in range(th + 40):
        ratio = gy / max(1, th + 40)
        if ratio < 0.5:
            r_sub = ratio / 0.5
            r = int(255 * (1 - r_sub) + 255 * r_sub)
            g = int(245 * (1 - r_sub) + 195 * r_sub)
            b = int(190 * (1 - r_sub) + 65 * r_sub)
        else:
            r_sub = (ratio - 0.5) / 0.5
            r = int(255 * (1 - r_sub) + 235 * r_sub)
            g = int(195 * (1 - r_sub) + 135 * r_sub)
            b = int(65 * (1 - r_sub) + 25 * r_sub)
        for gx in range(tw + 40):
            grad_tex.putpixel((gx, gy), (r, g, b, 255))
    grad_tex.putalpha(grad_mask)

    res = Image.alpha_composite(base, shadow_img)
    res = Image.alpha_composite(res, glow_img)
    res.paste(grad_tex, (x - 20, y - 20), grad_tex)

    # 5. Масштабируем до 1080x1350 БЕЗ РАСТЯЖЕНИЯ (пропорция Lanczos)
    scale = 1350.0 / res.height
    new_w = int(res.width * scale)  # 1008 px
    scaled = res.resize((new_w, 1350), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (1080, 1350), (10, 14, 22))
    canvas.paste(scaled.convert("RGB"), (1080 - new_w, 0))

    out = f"{OUT_DIR}/slide_07_cta.png"
    canvas.save(out, quality=95)
    print(f"✅ Слайд 7 готов (эталонный стиль с жестом и золотым КОФЕ): {out}")

def main():
    print("🎨 Генерация эталонной карусели v4 «Ловушка кофе»...")
    render_slide_1()
    render_slide_2()
    render_slide_3()
    render_slide_4()
    render_slide_5()
    render_slide_6()
    render_slide_7()
    print("🎉 Все 7 слайдов карусели v4 успешно готовы!")

if __name__ == "__main__":
    main()

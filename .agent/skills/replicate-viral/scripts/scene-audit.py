#!/usr/bin/env python3
"""
scene-audit.py — МАШИННЫЙ аудит сцены reel. Мерит/парсит МАКСИМУМ правок автора числами,
не «агент на глаз». Корень провалов: LLM-критик глядел превью и врал PASS.

Видео/CV (opencv+ffmpeg+pixel):
  A headroom        — face-detect ×N кадров (движение) → срез макушки = FAIL
  C safe-zone face  — лицо в IG-обрезке (0-288 / 1440-1920)
  D dynamics        — motion НАШ vs КОНКУРЕНТ; <50% = FAIL (benchmark числом)
  E edge            — контент за края (overflow)
  K avatar-pillarbox— тёмные боковые полосы (узкий аватар вместо full-bleed)
  M split-from-0    — на t=0 контент И сверху И снизу (как у автора с 0-й сек)
  F caption-contrast— min WCAG-контраст текст-vs-фон на кадрах (<3 = FAIL)
  G text-edge-cut   — ненулевые пиксели текст-цвета в колонках x>1070 = FAIL
  H icon↔word sync  — |t_word − t_icon| из whisper-json vs data-s композиции (>0.15с = FAIL)
  I empty-frames    — >1.5с подряд почти-однотонная верх-зона при обещанном HTML = WARN
  J text-on-face    — bbox текста (HTML+рендер-маска) X bbox лица; лицо>10% или зона глаз>5% = FAIL;
                      лицо не найдено >=50% кадров = FAIL (флаг --no-face-expected отключает)
  K2 caption-on-UI  — caption-полоса над сплит-линией X плотный UI (edge-density Sobel) >15% = FAIL, 5-15% = WARN
Парс композиции (HTML — детерминированно):
  B1 титр ≤2 строк (не «три этажа»)          B2 субтитр ≤2 слов разом
  B3 титр премиум-шрифт   B4 субтитр премиум-шрифт   B5 субтитр обводка/контраст
  B6 субтитр в safe-zone   B7 титр в safe-zone
  B8 НЕТ ядовито-лайма     B9 акцент бренд-золото/жёлтый есть
  B10 НЕТ em-dash в тексте B11 НЕТ точки в конце субтитра/титра
  B12 синхрон-механизм (currentTime)  B13 overflow:hidden (contained zoom)
  B14 НЕТ error-строк («No API key/Log in»)  B15 split-структура (2 слота+video)
PREFLIGHT (0 рендеров, чистая статика — `--preflight --html idx.html`):
  P-FONT  покрытие шрифта по буквам (cmap @font-face, особо кириллица; Arial-фоллбек = WARN)
  P-GEOM  геометрия абсолютно-позиционированного текста vs safe-zone y300-1430 + ширина 1080
  P-CONTR контраст текст-vs-подложка по объявленным в CSS цветам (WCAG <3 = FAIL)
Exit 0 = PASS, 2 = FAIL (как у хуков), не 1.

usage:
  scene-audit.py --our OUR.mp4 [--ref REF.mp4] [--html COMP.html] [--avatar-region-top 900] [--frames 8] [--full-bleed] [--whisper-json vo.json] [--no-face-expected] [--family talking-head-split|overlap-card]
  scene-audit.py --preflight --html COMP.html              # 0 рендеров, чистая статика
"""
import argparse, base64, io, json, os, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image

PREMIUM = re.compile(r'anton|montserrat|oswald|druk|bebas|archivo|inter\b', re.I)
CHEAP   = re.compile(r"arial|helvetica|times|courier|system-ui|^\s*sans-serif", re.I)
ERR_STR = re.compile(r'no api key|log ?in|sign ?in|paste your key|enter.*api|©.*default', re.I)

# ============================================================================
# ПРОФИЛИ СЕМЕЙ РАСКЛАДОК (Ф5a)
#  Корень зазора Ф3: scene-audit исторически откалиброван под семью «talking-head split»
#  (верх-скриншот / низ-аватар, 2 слота). Семья «overlap-card» (эталон автора DUqeScpDAHW,
#  блок K3: тёмная сцена-пол, аватар bottom-pinned с НАМЕРЕННЫМ кропом подбородка,
#  голова «вылезает» над карточкой, fade-in с 0с) ШТАТНО трипает оси A2/M/K/B12/B15 —
#  это НЕ дефект сборки. Раньше «какие оси судят сцену» = суждение оператора (дыра для
#  слабой модели). Теперь профиль семьи ДЕКЛАРАТИВНО переводит непрофильные оси в WARN.
#
#  Принцип: проверки НЕ удаляются — меняется только РЕЖИМ ВЕРДИКТА конкретных осей.
#  Каждый fail-message начинается с КОДА оси ("A2 ...", "K ...", "M ...", "B12 ...", "B15 ...") —
#  по этому коду профиль решает: hard-FAIL (валит exit 2) или WARN-only (печатается, не валит).
#  Оси НЕ в demote-списке профиля остаются hard (J/K2/F/B3/B5/B9/B14/G/H/I и т.д.).
#
#  Ось определяется по ПЕРВОМУ токену fail-сообщения (код оси). Сопоставление точное по
#  коду оси (буквы+цифры) с границей слова — чтобы "B1" не цеплял "B12".
FAMILY_PROFILES = {
    'talking-head-split': {
        'label': 'talking-head split (верх-скриншот / низ-аватар, 2 слота) — историческая калибровка',
        'warn_only': {},   # пустой demote = все оси hard (полная обратная совместимость с дефолтом до Ф5a)
    },
    'k5-continuous-anchor': {
        'label': 'k5-continuous-anchor (full-bleed сквозной аватар 1080x1920 + плашка-карточка сверху + караоке-плейты на тёмных плашках) — single-timeline, не 2-слот split',
        'warn_only': {     # by-design для K5; J/F/C2 НЕ здесь (NON_DEMOTABLE — чинятся логикой, не демоутом)
            'B15': 'split не требуется — K5 это full-bleed аватар + плашка-карточка, не верх/низ 2-слот split',
            'D':   'динамика верх-зоны неприменима — верх K5 = плашка-карточка поверх сквозного аватара, отдельного UI-слота нет',
            'M':   'контент И сверху И снизу на t=0 не требуется — K5 single-timeline full-bleed, не split-from-0',
            'K':   'тёмные боковые поля штатны (full-bleed аватар на всю ширину/кинематографичный фон) — не узкий аватар на чёрном',
        },
    },
    'overlap-card': {
        'label': 'overlap-card (K3: тёмная сцена-пол, аватар bottom-pinned, кроп подбородка, fade-in с 0с)',
        'warn_only': {     # оси, штатно трипаемые этой раскладкой by-design -> WARN-only «вне профиля семьи»
            'A2':  'кроп подбородка НАМЕРЕННЫЙ (голова вылезает над карточкой) — не дефект для overlap-card',
            'C':   'лицо в верх-зоне IG допустимо для overlap-card full-bleed (аватар-hero на весь экран — нет отдельного split-низа)',
            'D':   'динамика верх-зоны неприменима к overlap-card full-bleed hook (верх-зона = сам аватар, отдельного UI-слота нет)',
            'M':   'fade-in с 0с допустим (не нужен контент И сверху И снизу на t=0) — раскладка не 2-слот-split',
            'K':   'тёмные боковые поля штатны для кинематографичной сцены-пола (аватар не full-bleed по дизайну)',
            'B12': 'lip-sync currentTime не обязателен для overlap-card hero-слоя (озвучка/аватар отдельно)',
            'B15': '2-слот split-структура не требуется — overlap-card это слой-карточка+аватар, не верх/низ split',
        },
    },
}


# ============================================================================
#  NON_DEMOTABLE — оси, которые профиль семьи НЕ может переводить в WARN.
#  J (текст на лице), F (контраст субтитра), C2 (субтитр в зоне обрезки) —
#  дефекты безопасности восприятия: видимы НЕЗАВИСИМО от раскладки.
# ============================================================================
NON_DEMOTABLE = {"J", "F", "C2"}

def _axis_code(failmsg):
    # первый токен fail-сообщения = код оси (напр. "A2","K","M","B12","B15","J","P-GEOM").
    m = re.match(r'\s*([A-Z]+\d*|P-[A-Z]+)\b', failmsg)
    return m.group(1) if m else None

def _apply_family_profile(fails, family):
    # Делит fails на (hard-FAIL, переведённые профилем в WARN, коды переведённых осей).
    prof = FAMILY_PROFILES.get(family) or FAMILY_PROFILES['talking-head-split']
    warn_map = prof.get('warn_only', {})
    if not warn_map:
        return list(fails), [], []
    hard, demoted, axes = [], [], []
    for fm in fails:
        code = _axis_code(fm)
        if code in warn_map:
            if code in NON_DEMOTABLE:
                print(f"  ! ось {code} не деградируется профилем семьи (NON_DEMOTABLE) — остаётся FAIL")
                hard.append(fm)
            else:
                demoted.append("[профиль %s: %s вне профиля семьи — %s] %s" % (family, code, warn_map[code], fm))
                axes.append(code)
        else:
            hard.append(fm)
    return hard, demoted, axes

def grab(mp4,t,scale=None):
    out=tempfile.mktemp(suffix='.png'); vf=f'scale={scale}' if scale else 'null'
    subprocess.run(['ffmpeg','-y','-ss',str(t),'-i',mp4,'-frames:v','1','-vf',vf,out],capture_output=True)
    return out if os.path.exists(out) else None
def duration(mp4):
    # Возвращает float секунды ИЛИ None если ffprobe не дал валидную длительность
    # (битый/пустой/нечитаемый mp4). НЕ подставлять молчком 4.0 — это fail-open (HIGH-3).
    r=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',mp4],capture_output=True,text=True)
    try:
        d=float(r.stdout.strip())
        return d if d>0 else None
    except (ValueError, AttributeError):
        return None
def dims(mp4):
    # реальные W,H первого видеопотока через ffprobe; None если не прочитать
    r=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                      'stream=width,height','-of','csv=p=0:s=x',mp4],capture_output=True,text=True)
    try:
        w,h=r.stdout.strip().split('x'); w,h=int(w),int(h)
        return (w,h) if w>0 and h>0 else None
    except (ValueError, AttributeError):
        return None
def detect_face(png):
    import cv2
    img=cv2.imread(png)
    if img is None:return None
    g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    cc=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    # minSize=80 (was 120): в composite 1920px кадрах с аватаром в нижней половине лицо
    # может быть <120px при bbox в scaled-frame. Снижение до 80 убирает ложные FAIL
    # «ЛИЦО НЕ НАЙДЕНО» когда лицо реально есть. J text∩face intersection не ослабляется.
    f=cc.detectMultiScale(g,1.05,4,minSize=(80,80))
    if len(f)==0:return None
    x,y,w,h=max(f,key=lambda z:z[2]);return dict(x=int(x),y=int(y),w=int(w),h=int(h))

def _iou(b1,b2):
    # IoU двух bbox-словарей {x,y,w,h}
    ax0,ay0,ax1,ay1=b1['x'],b1['y'],b1['x']+b1['w'],b1['y']+b1['h']
    bx0,by0,bx1,by1=b2['x'],b2['y'],b2['x']+b2['w'],b2['y']+b2['h']
    ix0,iy0=max(ax0,bx0),max(ay0,by0); ix1,iy1=min(ax1,bx1),min(ay1,by1)
    if ix1<=ix0 or iy1<=iy0:return 0.0
    inter=(ix1-ix0)*(iy1-iy0); ua=b1['w']*b1['h']+b2['w']*b2['h']-inter
    return inter/float(ua) if ua>0 else 0.0

def _local_motion(mp4,t,half=0.25,scale='240:-1'):
    # средняя |Δ| между кадром в t-half и t+half (доля high=низкий локальный motion → почти статика)
    d=duration(mp4)
    if d is None:return None
    t0=max(0.0,t-half); t1=min(d-0.02,t+half)
    p0=grab(mp4,t0,scale); p1=grab(mp4,t1,scale)
    if not p0 or not p1:return None
    a0=np.asarray(Image.open(p0).convert('L'),dtype=np.float32); os.remove(p0)
    a1=np.asarray(Image.open(p1).convert('L'),dtype=np.float32); os.remove(p1)
    if a0.shape!=a1.shape:return None
    return float(np.mean(np.abs(a0-a1)))
def motion(mp4,n=8,t0=0.0,t1=None,region=None):
    # region=(y0,y1) в долях высоты (0..1) — мерить динамику ТОЛЬКО там (верх/скриншот),
    # аватар-якорь (низ) в расчёт динамики НЕ включаем (автор: динамику несёт верх+чередование, не аватар).
    d=duration(mp4); t1=t1 if t1 else d; prev=None;ds=[]
    for i in range(n):
        p=grab(mp4,t0+(t1-t0)*(i+0.5)/n,'240:-1')
        if not p:continue
        im=Image.open(p).convert('L');os.remove(p)
        if region:
            w,hh=im.size;im=im.crop((0,int(hh*region[0]),w,int(hh*region[1])))
        a=np.asarray(im,dtype=np.float32)
        if prev is not None and prev.shape==a.shape:ds.append(float(np.mean(np.abs(a-prev))))
        prev=a
    return round(float(np.mean(ds)),2) if ds else 0.0
def lime(hexes):
    bad=[]
    for hx in hexes:
        try:r=int(hx[1:3],16);g=int(hx[3:5],16);b=int(hx[5:7],16)
        except:continue
        if g>200 and r<190 and b<130 and g-r>40 and g-b>90:bad.append(hx)  # toxic lime/neon-green
    return bad

# ============================================================================
# ОБЩИЕ ХЕЛПЕРЫ для P-* и F/G/H/I (по решению автора — перенос находок критика в числа)
# ============================================================================
SAFE_TOP, SAFE_BOT, FRAME_W = 300, 1430, 1080  # safe-zone y + ширина кадра

def _hex_to_rgb(hx):
    hx=hx.strip()
    m=re.match(r'#?([0-9A-Fa-f]{6})$',hx) or re.match(r'#?([0-9A-Fa-f]{3})$',hx)
    if not m:return None
    s=m.group(1)
    if len(s)==3:s=''.join(c*2 for c in s)
    return (int(s[0:2],16),int(s[2:4],16),int(s[4:6],16))

def _rel_lum(rgb):
    # WCAG относительная яркость
    def lin(c):
        c/=255.0
        return c/12.92 if c<=0.03928 else ((c+0.055)/1.055)**2.4
    r,g,b=rgb
    return 0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b)

def _contrast(rgb1,rgb2):
    l1,l2=_rel_lum(rgb1),_rel_lum(rgb2)
    hi,lo=max(l1,l2),min(l1,l2)
    return (hi+0.05)/(lo+0.05)

def _parse_color(s):
    # '#fff' / '#ffffff' / 'rgb(..)' / 'rgba(r,g,b,a)' -> (rgb_tuple, alpha) или (None,None)
    s=s.strip()
    m=re.match(r'rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)',s,re.I)
    if m:
        r,g,b=[int(float(m.group(i))) for i in (1,2,3)]
        al=float(m.group(4)) if m.group(4) is not None else 1.0
        return (r,g,b),al
    rgb=_hex_to_rgb(s)
    if rgb:return rgb,1.0
    return None,None

def _caption_plate_contrast(css_blob):
    # Если у caption-класса (.cap/.cw/.w/.stream) объявлен НЕПРОЗРАЧНЫЙ фон-плашка
    # (background rgba alpha>=0.4 ИЛИ solid hex/rgb) — мерим контраст текст-vs-ПЛАШКА по
    # ОБЪЯВЛЕННЫМ цветам (как P-CONTR), не пиксельную полосу. Возвращает (contrast, txt, plate)
    # или None если плашки нет.
    txt=None; plate=None; plate_alpha=0.0
    for sel in ('cw','w','cap','stream'):
        for m in re.finditer(r'([^{}]+)\{([^}]*)\}',css_blob):
            head,body=m.group(1),m.group(2)
            if not re.search(r'(?<![\w-])\.%s(?![\w-])'%re.escape(sel),head):continue
            if txt is None:
                cm=re.search(r'(?<!-)color:\s*([^;]+)',body)
                if cm:
                    rgb,_a=_parse_color(cm.group(1))
                    if rgb:txt=rgb
            bm=re.search(r'background(?:-color)?:\s*([^;]+)',body)
            if bm:
                rgb,al=_parse_color(bm.group(1))
                if rgb and al>plate_alpha:
                    plate=rgb;plate_alpha=al
    if txt is None or plate is None or plate_alpha<0.4:
        return None
    return _contrast(txt,plate),txt,plate,plate_alpha

def _strip_b64(h):
    # вырезать base64-данные шрифтов/картинок, чтобы regex по тексту не давился
    return re.sub(r'data:[^;)]*;base64,[A-Za-z0-9+/=]+','data:STRIPPED',h)

def _font_faces(h):
    # {family_lower: cmap_charset|None} из @font-face (data-URI base64 или url-файл рядом)
    faces={}
    for m in re.finditer(r"@font-face\{([^}]*)\}", h, re.S):
        body=m.group(1)
        fam=re.search(r"font-family:\s*['\"]?([^'\";]+)", body)
        if not fam:continue
        name=fam.group(1).strip()
        chars=None
        db=re.search(r"url\(\s*data:font/[^;]+;base64,([A-Za-z0-9+/=]+)\s*\)", body)
        uf=re.search(r"url\(\s*['\"]?([^'\")]+\.(?:ttf|otf|woff2?))", body)
        try:
            from fontTools.ttLib import TTFont
            raw=None
            if db: raw=base64.b64decode(db.group(1))
            faces[name.lower()]=name  # placeholder; fill cmap below if possible
            if db:
                f=TTFont(io.BytesIO(raw)); chars=set(f.getBestCmap().keys())
            elif uf:
                p=uf.group(1)
                if os.path.exists(p):
                    f=TTFont(p); chars=set(f.getBestCmap().keys())
        except Exception:
            chars=None
        faces[name.lower()]=chars
    return faces

def _collect_css(html_path, html_raw):
    # Собирает CSS из ВНЕШНИХ <link rel=stylesheet href=...> (относительно html) + inline <style>.
    # Возвращает (css_blob, list_external_paths). Внешний CSS читается с диска рядом с HTML —
    # это закрывает класс ложных B3/B4, где @font-face живёт в assets/oswald.css, а inline пуст.
    blob = html_raw
    ext_paths = []
    if html_path and os.path.exists(html_path):
        base_dir = os.path.dirname(os.path.abspath(html_path))
        for m in re.finditer(r'<link\b[^>]*>', html_raw, re.I):
            tag = m.group(0)
            if not re.search(r'rel\s*=\s*["\']?\s*stylesheet', tag, re.I):
                continue
            hm = re.search(r'href\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            if not hm:
                continue
            href = hm.group(1).strip()
            if href.startswith(('http://', 'https://', '//', 'data:')):
                continue  # внешний URL/inline-data — не читаем с диска
            css_path = os.path.normpath(os.path.join(base_dir, href.split('?')[0].split('#')[0]))
            if os.path.exists(css_path):
                try:
                    blob += "\n/* ext:%s */\n" % href + open(css_path, encoding='utf-8', errors='ignore').read()
                    ext_paths.append(css_path)
                except OSError:
                    pass
    return blob, ext_paths

def _declared_fontface_families(css_blob):
    # Имена семейств, реально объявленных через @font-face (загруженный шрифт: data-URI ИЛИ url-файл).
    # data-URI считается ВАЛИДНОЙ загрузкой (шрифт встроен). Возвращает set lower-case имён.
    fams = set()
    for m in re.finditer(r"@font-face\s*\{([^}]*)\}", css_blob, re.S):
        body = m.group(1)
        fam = re.search(r"font-family:\s*['\"]?([^'\";]+)", body)
        if not fam:
            continue
        has_src = re.search(r"src:\s*[^;]*url\(", body)  # есть src url(...) (data: или файл)
        if has_src:
            fams.add(fam.group(1).strip().lower())
    return fams

def _font_used_by_class(css_blob, classes):
    # font-family, объявленный для текст-классов (.title/.stream/.cap/.cw/.w). Возвращает
    # ПЕРВОЕ объявленное семейство + полный список семейств цепочки.
    for sel in classes:
        for m in re.finditer(r'([^{}]+)\{([^}]*)\}', css_blob):
            head, body = m.group(1), m.group(2)
            if not re.search(r'(?<![\w-])\.%s(?![\w-])' % re.escape(sel), head):
                continue
            ff = re.search(r"font-family:\s*([^;]+)", body)
            if ff:
                chain = [x.strip().strip('\'"').lower() for x in ff.group(1).split(',') if x.strip()]
                return (chain[0] if chain else ''), chain
    return '', []

def _premium_font_resolved(css_blob, classes):
    # Премиум = ОБЪЯВЛЕННЫЙ через @font-face шрифт РЕАЛЬНО используется в font-family текст-класса.
    # Возвращает (is_premium, primary_family, reason). primary_family — для отображения.
    declared = _declared_fontface_families(css_blob)
    primary, chain = _font_used_by_class(css_blob, classes)
    if not primary:
        return False, '', 'font-family не объявлен для текст-классов'
    first = primary
    for fam in chain:
        if fam in declared:
            return True, fam, "@font-face '%s' объявлен и применён к тексту" % fam
    if PREMIUM.search(first) and not CHEAP.match(first):
        return True, first, "премиум-семейство '%s' по имени (web/google font)" % first
    if CHEAP.match(first):
        return False, first, "первый шрифт цепочки системный/cheap '%s'" % first
    return False, first, "шрифт '%s' не объявлен @font-face и не в премиум-списке" % first

def _text_nodes(h):
    # видимые текстовые узлы (субтитры .w/.cw, титр, любой >текст<), убрав теги/скрипты/стили
    h2=re.sub(r'<(script|style)\b[^>]*>.*?</\1>','',h,flags=re.S|re.I)
    nodes=[t.strip() for t in re.findall(r'>([^<>{}]+)<',h2)]
    return [t for t in nodes if t and not t.startswith(('@','{','//')) and re.search(r'\w',t)]

def grab_arr(mp4,t):
    p=grab(mp4,t)
    if not p:return None
    a=np.asarray(Image.open(p).convert('RGB'),dtype=np.uint8);os.remove(p);return a


# ============================================================================
#  ОСИ J / K2 — ЗРЕНИЕ на наложение «текст на лице» и «caption поверх UI».
#  Корень провала (root-cause 2026-06-11): 25 проверок НЕ считали bbox текста и
#  не пересекали его ни с лицом, ни с контент-зоной экрана -> текст поперёк глаз
#  спикера давал PASS exit 0. Ниже эти два класса дефектов закрыты числом.
# ============================================================================

def _text_mask(gray_u8):
    # Маска ярких ТЕКСТ-регионов в кадре БЕЗ OCR: яркие пиксели (>210) -> морфологическое
    # горизонтальное замыкание (склеивает глифы в слова) -> снятие мелкого шума открытием.
    import cv2
    _,bw=cv2.threshold(gray_u8,210,255,cv2.THRESH_BINARY)
    bw=cv2.morphologyEx(bw,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(3,3)))
    closed=cv2.morphologyEx(bw,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(25,5)))
    return closed

def _text_bbox_from_html(html_path,H_TOTAL=1920,W_TOTAL=1080,SY=1.0,SX=1.0):
    # Абсолютная bbox субтитра/титра из HTML (как в P-GEOM): top + height/font-size -> полоса текста.
    # Возвращает список (y0,y1,x0,x1) в координатах РЕНДЕРА (масштаб под реальный кадр).
    if not html_path or not os.path.exists(html_path):return []
    h=open(html_path,encoding='utf-8',errors='ignore').read()
    boxes=[]
    for sel in ('stream','cap','title','sub','caption'):
        m=re.search(r'\.%s\s*\{([^}]*)\}'%sel,h)
        if not m:continue
        body=m.group(1)
        t=re.search(r'top:\s*(-?\d+)px',body)
        if not t:continue
        y=int(t.group(1))
        hh=re.search(r'height:\s*(\d+)px',body)
        fs=re.search(r'font-size:\s*(\d+)px',body)
        span=int(hh.group(1)) if hh else (int(int(fs.group(1))*1.4) if fs else 160)
        boxes.append((round(y*SY),round((y+span+120)*SY),0,W_TOTAL))
    return boxes

def check_J_text_on_face(mp4,dur,frames,html_path,H_TOTAL=1920,W_TOTAL=1080,SY=1.0,SX=1.0,no_face_expected=False):
    # Ось J: пересечение bbox ТЕКСТА с bbox ЛИЦА.
    #  - face-bbox: opencv haar (как в оси A).
    #  - text-bbox: (а) из HTML абсолютные координаты контейнеров, (б) по рендеру — маска ярких
    #    текст-регионов внутри bbox лица (_text_mask). Источник (б) ловит текст ВЫЖЖЕННЫЙ в пиксели.
    # Пороги (откалибровано clean s1 vs синтетик): доля текст-пикс. в лице >10% = FAIL;
    #  в зоне глаз/лба (y in [0.2h..0.55h]) заметное (>5%) = FAIL.
    import cv2
    html_boxes=_text_bbox_from_html(html_path,H_TOTAL,W_TOTAL,SY,SX)
    cc=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    faces_checked=0; faces_found=0; worst=None; fails=[]; warns=[]
    ts=[dur*(i+0.5)/frames for i in range(frames)]
    if html_path and os.path.exists(html_path):
        h=open(html_path,encoding='utf-8',errors='ignore').read()
        for m in re.finditer(r'data-s(?:tart)?=["\']([0-9.]+)["\']',h):
            tv=float(m.group(1))
            if 0<=tv<=dur: ts.append(tv+0.05)
    ts=sorted(set(round(t,2) for t in ts if 0<=t<=dur))
    for t in ts:
        a=grab_arr(mp4,t)
        if a is None:continue
        faces_checked+=1
        gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
        f=cc.detectMultiScale(gray,1.05,4,minSize=(80,80))  # minSize=80: tall-frame composites
        if len(f)==0:continue
        faces_found+=1
        fx,fy,fw,fh=max(f,key=lambda z:z[2])
        fx,fy,fw,fh=int(fx),int(fy),int(fw),int(fh)
        tm=_text_mask(gray)
        face_tm=tm[fy:fy+fh,fx:fx+fw]
        eye_tm =tm[fy+int(fh*0.2):fy+int(fh*0.55),fx:fx+fw]
        face_ratio=float((face_tm>0).mean()) if face_tm.size else 0.0
        eye_ratio =float((eye_tm>0).mean())  if eye_tm.size  else 0.0
        html_overlap=0.0
        for (ty0,ty1,tx0,tx1) in html_boxes:
            ix0,iy0=max(fx,tx0),max(fy,ty0); ix1,iy1=min(fx+fw,tx1),min(fy+fh,ty1)
            if ix1>ix0 and iy1>iy0:
                inter=(ix1-ix0)*(iy1-iy0); html_overlap=max(html_overlap,inter/float(fw*fh))
        # Пиксельная доля «текст в лице»: max(лицо, зона глаз). html_overlap=пересечение bbox HTML-текста с лицом.
        pix=max(face_ratio, eye_ratio)
        zone='eye' if eye_ratio>=face_ratio else 'face'
        # КЛАССИФИКАЦИЯ (root-cause 2026-06-12): пиксельная ось спорит с html_overlap=0 -> не валим вслепую.
        #  FAIL только если: (pix>порог И html_overlap>0)  ИЛИ  pix>0.12 (грубое нарушение, текст явно на лице).
        #  Иначе при конфликте (pix в серой зоне, html_overlap=0) -> WARN «ось спорит с html — проверь кадром».
        hard = ((eye_ratio>0.05 or face_ratio>0.10) and html_overlap>0) or (pix>0.12)
        soft = (not hard) and (eye_ratio>0.05 or face_ratio>0.10)
        if hard:
            if worst is None or pix>worst[1]:
                worst=(zone,pix,t,(fx,fy,fw,fh),round(face_ratio,3),round(eye_ratio,3),round(html_overlap,3))
            fails.append((zone,round(pix,3),t,round(html_overlap,3)))
        elif soft:
            warns.append((zone,round(pix,3),t,round(html_overlap,3)))
    no_face_run=None
    if faces_checked>0 and faces_found < faces_checked*0.5 and not no_face_expected:
        no_face_run="лицо НЕ найдено на %d/%d проверенных кадрах (<50%% покрытие) — половина ролика без проверки лица; если сцена БЕЗ лица по дизайну дай --no-face-expected"%(faces_checked-faces_found,faces_checked)
    verdict='FAIL' if (fails or no_face_run) else 'PASS'
    return {'verdict':verdict,'worst':worst,'faces_checked':faces_checked,'faces_found':faces_found,
            'fails':fails,'warns':warns,'no_face_run':no_face_run}

def check_K2_caption_over_ui(mp4,dur,frames,html_text_region,avatar_top,W_TOTAL=1080,H_TOTAL=1920,SY=1.0):
    # Ось K2: caption-bbox ∩ КОНТЕНТ-ЗОНА верхнего экрана (выше сплит-линии avatar_top).
    # «Важный UI» = регионы высокой СТРУКТУРНОЙ ПЛОТНОСТИ (края/текстуры — заголовки файлов,
    # строки кода, иконки). Меряем edge-density (Sobel) в части caption-полосы НАД avatar_top.
    # >15% площади = FAIL, 5-15% = WARN. caption целиком в аватар-зоне -> PASS.
    import cv2
    cap=html_text_region if html_text_region else (int(H_TOTAL*0.55),int(H_TOTAL*0.78))
    cy0,cy1=cap[0],cap[1]
    uy0,uy1=cy0,min(cy1,avatar_top)
    if uy1<=uy0:
        return {'verdict':'PASS','reason':'caption-полоса y[%d-%d] целиком в аватар-зоне (>=%d) — над UI не лежит'%(cy0,cy1,avatar_top),'dens':0.0}
    worst=None
    for i in range(frames):
        a=grab_arr(mp4,dur*(i+0.5)/frames)
        if a is None:continue
        gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
        y0=max(0,min(uy0,gray.shape[0]-2));y1=max(y0+1,min(uy1,gray.shape[0]))
        band=gray[y0:y1]
        if band.size==0:continue
        gx=cv2.Sobel(band,cv2.CV_32F,1,0,ksize=3);gy=cv2.Sobel(band,cv2.CV_32F,0,1,ksize=3)
        mag=cv2.magnitude(gx,gy)
        dens=float((mag>80).mean())
        t=round(dur*(i+0.5)/frames,2)
        if worst is None or dens>worst[0]:worst=(dens,t)
    if worst is None:
        return {'verdict':'PASS','reason':'кадры не извлечены','dens':0.0}
    dens,t=worst
    if dens>0.15: v='FAIL'
    elif dens>0.05: v='WARN'
    else: v='PASS'
    return {'verdict':v,'dens':round(dens,3),'t':t,'band':(uy0,uy1)}

# ============================================================================
#  PREFLIGHT — 0 рендеров, чистая статика по HTML
# ============================================================================
def run_preflight(html_path):
    if not html_path or not os.path.exists(html_path):
        print("PREFLIGHT: --html не задан или файла нет — нечего проверять"); return 2
    raw=open(html_path,encoding='utf-8',errors='ignore').read()
    if not raw.strip():
        print("PREFLIGHT: FAIL — HTML пустой/нечитаемый, нечего проверять"); return 2
    h=_strip_b64(raw)                       # для текст/CSS-парса
    fails=[];warns=[];facts=[]

    # ---- P-FONT: покрытие шрифта по буквам (особо кириллица) ----
    raw_css,_ext=_collect_css(html_path, raw)   # включить внешний <link> css (@font-face может жить в assets/*.css)
    faces=_font_faces(raw_css)              # raw_css — inline+external; base64 data-URI нужен для cmap
    texts=_text_nodes(h)
    blob=''.join(texts)
    # требуем покрытия только для БУКВ/ЦИФР (emoji/пиктограммы легитимно уходят в системный emoji-шрифт)
    import unicodedata
    def _is_glyph_char(c):
        if not c.strip():return False
        cat=unicodedata.category(c)
        return cat[0] in ('L','N')   # буквы и цифры; пунктуация/символы/emoji — нет
    used=sorted({c for c in blob if _is_glyph_char(c)})
    cyr=[c for c in used if 'Ѐ'<=c<='ӿ']
    # какой шрифт реально применён к субтитрам (.w/.cw/.stream) — берём font-family из CSS
    fam_decl=re.findall(r"font-family:\s*['\"]?([A-Za-z][\w \-]*)",h)
    primary=(fam_decl[0].strip() if fam_decl else '')
    sysfb=[f for f in fam_decl if CHEAP.match(f.strip())]
    # сопоставить объявленные кастом-шрифты с cmap
    covered_by=None;miss=[]
    for fname,chars in faces.items():
        if chars is None:continue
        m=[c for c in used if ord(c) not in chars]
        if not m: covered_by=fname; miss=[]; break
        if covered_by is None or len(m)<len(miss): covered_by=fname; miss=m
    if not faces:
        facts.append(f"P-FONT: @font-face не объявлен; шрифты={fam_decl[:3]} символов_текста={len(used)} кириллицы={len(cyr)}")
        if cyr: warns.append(f"P-FONT: кириллица ({len(cyr)} симв.) но НЕТ @font-face — рискует уехать в системный фоллбек")
    else:
        any_cmap=any(v is not None for v in faces.values())
        if not any_cmap:
            facts.append(f"P-FONT: @font-face есть ({list(faces)}), но cmap не прочитан (url-файл недоступен) символов={len(used)} кириллицы={len(cyr)} — SKIP покрытия")
        elif miss:
            fails.append(f"P-FONT: ШРИФТ '{covered_by}' НЕ ПОКРЫВАЕТ {len(miss)} симв. {miss[:12]} (всего текста {len(used)}, кириллицы {len(cyr)}) — глифы выпадут (баг Anton-кириллицы)")
        else:
            facts.append(f"P-FONT: '{covered_by}' покрывает все {len(used)} символов (кириллицы {len(cyr)}) — порог 0 непокрытых")
    if sysfb and not faces:
        warns.append(f"P-FONT: системный фоллбек {sysfb[:2]} (Arial/system-ui) — каталог A1, грузить премиум @font-face")

    # ---- P-GEOM: геометрия абсолютно-позиционированного текста vs safe-zone ----
    # ищем top:Npx у элементов с текстом или у .stream/.cap/.title контейнеров (CSS-правила)
    css_tops={}  # selector -> top px
    for m in re.finditer(r'\.([\w-]+)\s*\{([^}]*)\}',h):
        sel,body=m.group(1),m.group(2)
        t=re.search(r'top:\s*(-?\d+)px',body)
        if t: css_tops[sel]=int(t.group(1))
    checked=0
    # ВАЖНО: только контейнеры кадра-уровня. .w/.cw — абсолют ВНУТРИ .stream → их top относительный,
    # из regex вложенность не вычислить → не проверяем (иначе ложный FAIL, прецедент .w top=40).
    for sel in ('stream','cap','title','sub','caption'):
        if sel in css_tops:
            y=css_tops[sel];checked+=1
            # высота subtitle-полосы неизвестна точно → берём верх; запас 120px на высоту слова
            facts.append(f"P-GEOM: .{sel} top={y}px (safe {SAFE_TOP}-{SAFE_BOT})")
            if not (SAFE_TOP<=y<=SAFE_BOT-120):
                fails.append(f"P-GEOM: .{sel} top={y}px ВНЕ safe-zone {SAFE_TOP}-{SAFE_BOT-120} — площадка обрежет")
    # ширина: явные width>1080 у текст-контейнеров
    for m in re.finditer(r'\.([\w-]+)\s*\{([^}]*)\}',h):
        sel,body=m.group(1),m.group(2)
        w=re.search(r'width:\s*(\d+)px',body)
        if w and int(w.group(1))>FRAME_W and sel in ('stream','cap','title'):
            warns.append(f"P-GEOM: .{sel} width={w.group(1)}px > {FRAME_W} — текст может вылезти за кадр")
    if checked==0:
        facts.append("P-GEOM: SKIP — у текст-узлов нет CSS top:Npx (позиция flex/inset, не абсолют) — геометрию мерит рендер-ось G")

    # ---- P-CONTR: контраст текст vs подложка по объявленным цветам ----
    # эвристика: цвет субтитра (.w/.stream/.cap color) против фона ближайшего слота/body
    def _color_of(selectors):
        for m in re.finditer(r'\.([\w-]+)[^{]*\{([^}]*)\}',h):
            if m.group(1) in selectors:
                c=re.search(r'(?<!-)color:\s*(#[0-9A-Fa-f]{3,6})',m.group(2))
                if c:return c.group(1)
        return None
    def _bg_of(selectors):
        for m in re.finditer(r'\.([\w-]+)[^{]*\{([^}]*)\}',h):
            if m.group(1) in selectors:
                c=re.search(r'background[^:]*:\s*[^;]*?(#[0-9A-Fa-f]{3,6})',m.group(2))
                if c:return c.group(1)
        return None
    txt_c=_color_of({'w','cw','stream'}) or _color_of({'cap','title'})
    bg_c =_bg_of({'slot','bottom','top','fullst','st'}) or _bg_of({'body'})
    bodybg=re.search(r'(?:html|body)[^{]*\{[^}]*background:\s*[^;]*?(#[0-9A-Fa-f]{3,6})',h)
    if not bg_c and bodybg:bg_c=bodybg.group(1)
    if txt_c and bg_c:
        c1,c2=_hex_to_rgb(txt_c),_hex_to_rgb(bg_c)
        if c1 and c2:
            cr=_contrast(c1,c2)
            facts.append(f"P-CONTR: текст {txt_c} vs фон {bg_c} контраст={cr:.2f} (порог 3.0)")
            if cr<3.0:
                fails.append(f"P-CONTR: КОНТРАСТ {cr:.2f}<3.0 текст {txt_c} на фоне {bg_c} — нечитаемо без обводки/плашки")
    else:
        # есть ли хотя бы обводка text-shadow у субтитра — тогда контраст обеспечен иначе
        if re.search(r'\.(w|cw|stream)[^}]*text-shadow',h):
            facts.append("P-CONTR: SKIP по цвету (нет явной пары текст/фон), но у субтитра есть text-shadow-обводка — контраст обеспечен иначе")
        else:
            facts.append(f"P-CONTR: SKIP — не извлечь пару текст/фон из CSS (txt={txt_c} bg={bg_c})")

    # ---- P-INVIS: элемент НЕВИДИМ (заливка ≈ фон) — баг «Claude-лого fill==bg» (g0dm0d3-v2) ----
    # P-CONTR ловит ТЕКСТ (порог WCAG 3.0). Здесь — НЕтекстовые заливки (SVG fill / декор-фигуры),
    # где «невидим» = контраст ~1.0. Высокая уверенность → FAIL только при контрасте <1.15 (объективно неотличим).
    bg_hexes=[]
    mbg=re.search(r'(?:html|body|#root|\.root|\.stage|\.scene)[^{]*\{[^}]*background[^:]*:\s*[^;]*?(#[0-9A-Fa-f]{3,6})',h)
    if mbg: bg_hexes.append(mbg.group(1))
    if bg_c: bg_hexes.append(bg_c)
    bg_rgbs=[_hex_to_rgb(x) for x in bg_hexes if _hex_to_rgb(x)]
    invis_hits=0
    for m in re.finditer(r'\.([\w-]+)\s*\{([^}]*)\}',h):
        sel,body=m.group(1),m.group(2)
        if re.search(r'mask|clip|grad|def|filter',sel,re.I): continue          # не-рендеримые/служебные
        if sel in ('w','cw','stream','cap','title','sub','caption','label'): continue  # текст = P-CONTR
        fm=re.search(r'(?<!background-)\bfill:\s*(#[0-9A-Fa-f]{3,6})',body) or \
           re.search(r'\bbackground(?:-color)?:\s*(#[0-9A-Fa-f]{3,6})\s*;?\s*\}',body)
        if not fm: continue
        fg=_hex_to_rgb(fm.group(1))
        if not fg: continue
        for bgr in bg_rgbs:
            cr=_contrast(fg,bgr)
            if cr<1.15:
                fails.append(f"P-INVIS: .{sel} заливка {fm.group(1)} ≈ фон (контраст {cr:.2f}<1.15) — элемент НЕВИДИМ (баг лого fill==bg)")
                invis_hits+=1; break
    if bg_rgbs and invis_hits==0:
        facts.append(f"P-INVIS: невидимых заливок (≈фон {bg_hexes[:2]}) не найдено")

    # ---- P-OVERLAP: два ТЕКСТ-контейнера с абсолютной позицией наезжают («три этажа»/перекрытие подписей) ----
    # узко: только текст-класс↔текст-класс (text-on-avatar = ось J рендера; z-index-слои не трогаем). WARN.
    TEXTSEL=('title','cap','caption','sub','label','strap','headline','kicker','barlabel','bar-label')
    tboxes={}
    for m in re.finditer(r'\.([\w-]+)\s*\{([^}]*)\}',h):
        sel,body=m.group(1),m.group(2)
        if sel not in TEXTSEL: continue
        if 'absolute' not in body and 'fixed' not in body: continue
        t=re.search(r'top:\s*(-?\d+)px',body); l=re.search(r'left:\s*(-?\d+)px',body)
        wd=re.search(r'width:\s*(\d+)px',body); ht=re.search(r'height:\s*(\d+)px',body)
        if t and l and wd and ht:
            tboxes[sel]=(int(l.group(1)),int(t.group(1)),int(wd.group(1)),int(ht.group(1)))
    _ts=list(tboxes)
    for _i in range(len(_ts)):
        for _j in range(_i+1,len(_ts)):
            ax0,ay0,aw,ah=tboxes[_ts[_i]]; bx0,by0,bw,bh=tboxes[_ts[_j]]
            inter=max(0,min(ax0+aw,bx0+bw)-max(ax0,bx0))*max(0,min(ay0+ah,by0+bh)-max(ay0,by0))
            if inter>0:
                union=aw*ah+bw*bh-inter
                iou=inter/union if union else 0
                if iou>0.15:
                    warns.append(f"P-OVERLAP: текст-боксы .{_ts[_i]} и .{_ts[_j]} наезжают (IoU {iou:.2f}) — «три этажа»/перекрытие подписей, проверь кадром")

    # ---- P-VOID: подсветка/рамка/стрелка по ХАРДКОД top/left px, не якорёна по элементу (баг winglow-в-пустоте) ----
    # v3 п.4: hlOnEl/arrowToEl(getBoundingClientRect) обязательны. Хардкод-координата у glow/ring/arrow = риск «рамка в пустоте». WARN.
    has_anchor=bool(re.search(r'hlOnEl\(|arrowToEl\(|getBoundingClientRect',h))
    VOIDSEL=re.compile(r'glow|ring|winglow|halo|arrow|outline|frame|hl-|highlight',re.I)
    void_hits=[]
    for m in re.finditer(r'\.([\w-]+)\s*\{([^}]*)\}',h):
        sel,body=m.group(1),m.group(2)
        if not VOIDSEL.search(sel): continue
        if ('absolute' in body or 'fixed' in body) and re.search(r'top:\s*-?\d+px',body) and re.search(r'left:\s*-?\d+px',body) and re.search(r'border|box-shadow|outline',body):
            void_hits.append(sel)
    if void_hits and not has_anchor:
        warns.append(f"P-VOID: декор-рамки/подсветки {void_hits[:5]} по ХАРДКОД top/left px без якорения (hlOnEl/arrowToEl/getBoundingClientRect) — риск «рамка в пустоте» (v3 п.4)")
    elif void_hits and has_anchor:
        facts.append(f"P-VOID: декор-элементы {void_hits[:3]} есть, но композиция использует якорение по элементу — ок")

    v='PASS' if not fails else 'FAIL'
    print(f"========== PREFLIGHT (0 рендеров): {v} ==========")
    for f in facts:print("  ·",f)
    if warns:
        print("  -- WARN --")
        for w in warns:print("  ⚠",w)
    if fails:
        print("  -- FAIL --")
        for f in fails:print("  ✗",f)
    try:
        out=os.path.splitext(html_path)[0]+'.preflight.json'
        json.dump({'verdict':v,'fails':fails,'warns':warns,'facts':facts},open(out,'w'),ensure_ascii=False,indent=1)
    except OSError:
        pass
    return 0 if v=='PASS' else 2

# ============================================================================
#  F / G / H / I — числовые проверки по РЕНДЕРУ (расширение существующих осей)
# ============================================================================
def check_F_caption_contrast(mp4,dur,frames,html_text_region,caption_outlined=False,H_TOTAL=1920):
    # Контраст КАПТИНА vs его ЛОКАЛЬНЫЙ фон. Меряем ТОЛЬКО когда в полосе есть отчётливый
    # яркий текст-кластер (субтитр). Текст = пиксели >215; фон = тёмное окружение (<140).
    # Нет явного текст-кластера в полосе → честный SKIP (не ложный FAIL на пёстром UI-кадре).
    # H_TOTAL = реальная высота кадра (масштабирование под не-1080×1920).
    if html_text_region:
        regions=[html_text_region]
    else:
        regions=[(int(H_TOTAL*0.66),H_TOTAL)]   # дефолт: нижняя треть (где сидит субтитр)
    worst=None
    for i in range(frames):
        a=grab_arr(mp4,dur*(i+0.5)/frames)
        if a is None:continue
        gray=np.asarray(Image.fromarray(a).convert('L'),dtype=np.float32)
        for (y0,y1) in regions:
            y0=max(0,min(y0,gray.shape[0]-2));y1=max(y0+1,min(y1,gray.shape[0]))
            band=gray[y0:y1]
            if band.size==0:continue
            txt=band[band>215]
            # требуем РЕАЛЬНЫЙ текст-кластер (≥0.4% ярких пикс.); иначе в полосе нет субтитра → SKIP кадра
            if txt.size < band.size*0.004: continue
            # ФОН = доминирующая поверхность полосы (медиана БЕЗ ярких текст-пикс.), не дальний тёмный пол.
            # Так светлый каптион-бэнд (текст на светлом) даёт НИЗКИЙ контраст = ловится, а тёмный фон — высокий.
            backdrop=band[band<=215]
            if backdrop.size < band.size*0.05: continue
            l_hi=float(np.percentile(txt,50))/255.0
            l_lo=float(np.median(backdrop))/255.0
            cr=(l_hi+0.05)/(l_lo+0.05)
            t=round(dur*(i+0.5)/frames,2)
            if worst is None or cr<worst[0]:worst=(cr,t,(y0,y1),round(l_lo*255),round(l_hi*255))
    return worst

def check_G_text_edge_cut(mp4,dur,frames,html_text_region,W_TOTAL=1080,H_TOTAL=1920):
    # Срез ТЕКСТА краем: яркие пиксели текст-цвета у ПРАВОГО края в СУБТИТР-полосе.
    # Анти-ложь: сплошная яркая ПАНЕЛЬ (UI-фон во всю ширину) ≠ срез текста. Поэтому требуем,
    # чтобы у самого края было ярко, НО рядом — заметно темнее (текст-штрих на фоне),
    # т.е. это изолированный глиф у края, а не равномерная заливка. Полоса = из HTML если есть.
    # Геометрия краёв масштабируется под реальную ширину W_TOTAL (HIGH-4).
    band_y=html_text_region if html_text_region else (int(H_TOTAL*0.55),int(H_TOTAL*0.78))
    edge_x0=max(0,W_TOTAL-10)          # последние 10px у правого края
    inner_x0=max(0,W_TOTAL-100); inner_x1=max(inner_x0+1,W_TOTAL-20)  # зона на ~20-100px вглубь
    worst=None
    for i in range(frames):
        a=grab_arr(mp4,dur*(i+0.5)/frames)
        if a is None:continue
        gray=np.asarray(Image.fromarray(a).convert('L'),dtype=np.float32)
        y0=max(0,min(band_y[0],gray.shape[0]-2));y1=max(y0+1,min(band_y[1],gray.shape[0]))
        band=gray[y0:y1]
        # guard: реальная ширина кадра может быть < ожидаемой → пустой срез = пропуск кадра
        if band.shape[1] <= edge_x0:continue
        edge=band[:, edge_x0:]
        inner=band[:, inner_x0:inner_x1]
        if edge.size==0 or inner.size==0:continue
        edge_bright=int((edge>200).sum())
        edge_ratio=float((edge>200).mean()); inner_ratio=float((inner>200).mean())
        # Панель/блюр-бликом у края = СПЛОШНОЙ яркий столбец (всю высоту, ровный): edge_ratio≈1 и низкий разброс.
        # Срез ТЕКСТА = глиф у края: яркого 5-60% высоты (штрихи+пробелы), И внутри (x980-1060) заметно темнее.
        col=edge.mean(axis=1)                 # средняя яркость по высоте у самой кромки
        col_std=float(col.std())
        is_panel = edge_ratio>0.85 and col_std<35           # ровный сплошной столбец = панель/бликом, не текст
        # Срез текста у правого края: глиф продолжается вглубь (inner_ratio > 0.03),
        # и край ярче внутреннего (edge > inner). Если inner совсем тёмный — это фоновый объект у края
        # (перила, ветки), а не срезанный субтитр.
        looks_like_text = (0.03 <= edge_ratio <= 0.65) and (edge_ratio - inner_ratio > 0.05) and (inner_ratio >= 0.02)
        # Анти-ложь: симметричный яркий фон (природный BG, терасса и т.п.) = яркий и на ЛЕВОМ краю тоже.
        # Срез текста асимметричен: текст уходит за правый край, левый край тёмный/пустой.
        left_edge=band[:, :10]
        left_ratio=float((left_edge>200).mean()) if left_edge.size>0 else 0
        is_symmetric_bg = (left_ratio > 0.10 and left_ratio > edge_ratio * 0.4)  # оба края ярки = фон
        t=round(dur*(i+0.5)/frames,2)
        score = edge_bright if (looks_like_text and not is_panel and not is_symmetric_bg) else 0
        if worst is None or score>worst[0]:worst=(score,t,is_panel,edge_bright)
    return worst

def check_H_icon_word_sync(html_path,whisper_json):
    # |t_word − t_icon|: data-s/data-start из HTML (слова субтитра) vs whisper-тайминги VO.
    if not whisper_json or not os.path.exists(whisper_json):
        return ('SKIP','нет --whisper-json — синк иконка↔слово не проверен')
    if not html_path or not os.path.exists(html_path):
        return ('SKIP','нет --html с data-s — синк не проверен')
    h=open(html_path,encoding='utf-8',errors='ignore').read()
    # пары (текст, data-s) у субтитр-слов
    words=[]
    for m in re.finditer(r'''data-s(?:tart)?=["\']([0-9.]+)["\'][^>]*>([^<]+)<''', h):
        txt = m.group(2).strip().lower()
        if txt:  # skip empty-content elements (video/audio tags with data-start)
            words.append((txt, float(m.group(1))))
    if not words:
        return ('SKIP','в HTML нет элементов с data-s/data-start — нечего синкать')
    try:
        wj=json.load(open(whisper_json))
    except Exception as e:
        return ('SKIP',f'whisper-json не читается: {e}')
    # whisper форматы: {"words":[{"word","start"}]} или segments[].words[]
    wwords=[]
    if isinstance(wj,dict):
        if 'words' in wj: wwords=wj['words']
        elif 'segments' in wj:
            for s in wj['segments']:wwords+=s.get('words',[])
    def norm(s):return re.sub(r'[^\wа-яё]','',s.lower())
    rows=[];maxd=0.0;bad=[]
    for (wtxt,ts) in words:
        key=norm(wtxt.split()[0]) if wtxt.split() else ''
        cand=[w for w in wwords if norm(w.get('word',w.get('text','')))==key]
        if not cand:continue
        tv=float(cand[0].get('start',cand[0].get('s',0)))
        d=abs(ts-tv)
        rows.append((wtxt[:18],ts,round(tv,2),round(d,3)))
        if d>maxd:maxd=d
        if d>0.15:bad.append((wtxt[:18],round(d,3)))
    if not rows:
        # Капшены есть + whisper json передан + 0 совпадений = капшены НЕ из озвучки (FAIL)
        return ('FAIL', {'max_drift': 0, 'thresh': 0.15, 'bad': [('(no-match)', 0)],
                         'rows': [], '_reason': 'капшены не из озвучки: 0 слов сматчилось с whisper — HTML-тайминги не соответствуют VO'})
    return ('FAIL' if bad else 'PASS', {'max_drift':round(maxd,3),'thresh':0.15,'bad':bad,'rows':rows})

def check_I_empty_frames(mp4,dur,avatar_top,html_promises_content):
    # >1.5с подряд почти-однотонная ВЕРХ-зона (низкая дисперсия) при том что HTML обещает контент = WARN
    if not html_promises_content:
        return ('SKIP','HTML не передан/нет обещанного контента — пустые кадры не оцениваем')
    step=0.3; n=max(2,int(dur/step)); empties=[]
    for i in range(n):
        t=i*step
        a=grab_arr(mp4,min(t,dur-0.05))
        if a is None:continue
        gray=np.asarray(Image.fromarray(a).convert('L'),dtype=np.float32)
        top=gray[0:avatar_top]
        var=float(np.var(top))
        empties.append((round(t,2),var))
    # ищем самую длинную серию var<25 (почти однотонно)
    run=0;best=0;run_start=None;best_start=None
    for (t,var) in empties:
        if var<25:
            if run==0:run_start=t
            run+=1
            if run>best:best=run;best_start=run_start
        else:run=0
    dur_empty=best*step
    return ('WARN' if dur_empty>1.5 else 'PASS', {'longest_empty_s':round(dur_empty,2),'thresh':1.5,'at':best_start})

def check_N_empty_panel(mp4,dur,SY=1.0):
    # Ось N «ПУСТАЯ ПАНЕЛЬ»: в верхней зоне (y 36-760, масштаб SY) детектится карточка-плашка
    # (контур со скруглением / резкая яркостная граница на тёмном фоне), а ВНУТРИ неё >92% площади
    # ОДНОРОДНО (низкая дисперсия) подряд >1.2с — WARN «панель есть, контент пуст».
    # Ловит класс glow-на-невидимом-промпте: плашка отрисована, но контента в ней нет.
    import cv2
    y0=int(36*SY); y1=int(760*SY)
    step=0.3; n=max(2,int(dur/step)); states=[]   # (t, panel_present_and_empty)
    for i in range(n):
        t=min(i*step,dur-0.05)
        a=grab_arr(mp4,t)
        if a is None:continue
        gray=cv2.cvtColor(a,cv2.COLOR_RGB2GRAY)
        H=gray.shape[0]; yy0=max(0,min(y0,H-2)); yy1=max(yy0+1,min(y1,H))
        zone=gray[yy0:yy1]
        if zone.size==0:continue
        # 1) есть ли ПЛАШКА: ищем крупный прямоугольный контур со скруглением на тёмном фоне
        _,bw=cv2.threshold(zone,40,255,cv2.THRESH_BINARY)   # светлее тёмного фона = тело плашки
        cnts,_=cv2.findContours(bw,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        panel=None
        for c in cnts:
            x,y,w,hh=cv2.boundingRect(c)
            area=w*hh
            if area > 0.18*zone.size and w>zone.shape[1]*0.4 and hh>zone.shape[0]*0.25:
                if panel is None or area>panel[4]:
                    panel=(x,y,w,hh,area)
        empty=False
        if panel is not None:
            x,y,w,hh,_=panel
            # внутренняя область плашки с отступом (убираем рамку/скругление)
            pad_x=max(2,int(w*0.06)); pad_y=max(2,int(hh*0.10))
            inner=zone[y+pad_y:y+hh-pad_y, x+pad_x:x+w-pad_x]
            if inner.size>50:
                med=float(np.median(inner))
                # доля пикселей в узкой полосе ±14 от медианы = «однородно»
                uniform_frac=float((np.abs(inner.astype(np.float32)-med)<=14).mean())
                if uniform_frac>0.92:
                    empty=True
        states.append((round(t,2),empty))
    # самая длинная серия empty=True
    run=0;best=0;run_start=None;best_start=None
    for (t,e) in states:
        if e:
            if run==0:run_start=t
            run+=1
            if run>best:best=run;best_start=run_start
        else:run=0
    dur_empty=best*step
    return ('WARN' if dur_empty>1.2 else 'PASS', {'longest_empty_panel_s':round(dur_empty,2),'thresh':1.2,'at':best_start})

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--our');ap.add_argument('--ref');ap.add_argument('--html')
    ap.add_argument('--preflight',action='store_true')
    ap.add_argument('--whisper-json',dest='whisper_json')
    ap.add_argument('--avatar-region-top',type=int,default=900);ap.add_argument('--frames',type=int,default=8)
    ap.add_argument('--full-bleed',action='store_true');ap.add_argument('--ref-start',type=float,default=0.0)
    ap.add_argument('--no-face-expected',dest='no_face_expected',action='store_true',help='сцена БЕЗ лица по дизайну (full-screen UI) — отключает FAIL по ненайденному лицу в оси J')
    ap.add_argument('--family',choices=sorted(FAMILY_PROFILES.keys()),default='talking-head-split',
                    help='семья раскладки — профиль режимов вердикта осей (default talking-head-split = историческая калибровка, все оси hard; overlap-card переводит A2/M/K/B12/B15 в WARN как штатные для этой семьи)')
    a=ap.parse_args()

    # ----- PREFLIGHT (0 рендеров) -----
    if a.preflight:
        sys.exit(run_preflight(a.html))

    if not a.our:
        print("ERROR: нужен --our OUR.mp4 (или --preflight --html ...)"); sys.exit(2)

    fails=[];facts=[];machine=0;iwarns=[]
    def chk(cond_ok,fact,failmsg):
        nonlocal machine;machine+=1;facts.append(fact)
        if not cond_ok:fails.append(failmsg)

    # ===== ВХОДНОЙ КОНТРОЛЬ ЧИТАЕМОСТИ (HIGH-3 fail-open) =====
    dur=duration(a.our)
    if dur is None:
        print("========== SCENE-AUDIT: FAIL  (видео нечитаемо) ==========")
        print(f"  ✗ ВИДЕО НЕЧИТАЕМО: ffprobe не дал длительность для {a.our} (пустой/битый mp4) — нечего аудировать")
        sys.exit(2)
    wh=dims(a.our)
    if wh is None:
        print("========== SCENE-AUDIT: FAIL  (видео нечитаемо) ==========")
        print(f"  ✗ ВИДЕО НЕЧИТАЕМО: ffprobe не дал размеры кадра для {a.our} — нечего аудировать")
        sys.exit(2)
    W,H=wh
    SX,SY=W/1080.0,H/1920.0
    # геометрия безопасных зон масштабируется под реальный кадр (HIGH-4)
    CT,CB,HR=round(288*SY),round(1440*SY),round(40*SY)
    if (W,H)!=(1080,1920):
        facts.append(f"геометрия масштабирована под {W}x{H} (SX={SX:.3f} SY={SY:.3f}; пороги CT/CB/HR/зоны пересчитаны)")

    # ===== VIDEO =====
    frames_read=0
    worst=None
    all_faces=[]   # [(t, bbox)] по всем кадрам — для медианного спикер-bbox (фото-вставка ≠ спикер)
    for i in range(a.frames):
        p=grab(a.our,dur*(i+0.5)/a.frames)
        if not p:continue
        frames_read+=1
        f=detect_face(p);os.remove(p)
        if not f:continue
        all_faces.append((round(dur*(i+0.5)/a.frames,2), f))
        # crown = предполагаемое положение макушки (выше bbox.y на 40% height).
        # Если лоб (f['y']) уже в слоте аватара — экстраполяция даёт отрицательный headroom
        # при минимальном зазоре (лоб прямо у шва). Используем max(crown, f['y']-5) чтобы
        # не штрафовать за нормальный случай «лоб в 5px от шва с видимой головой».
        crown_raw=f['y']-int(f['h']*0.40)
        crown = crown_raw if f['y'] < a.avatar_region_top else max(crown_raw, f['y'] - 5)
        if worst is None or crown<worst[1]:worst=(round(dur*(i+0.5)/a.frames,2),crown,f['y']+f['h'],f)
    if frames_read==0:
        print("========== SCENE-AUDIT: FAIL  (видео нечитаемо) ==========")
        print(f"  ✗ ВИДЕО НЕЧИТАЕМО: ffmpeg не извлёк НИ ОДНОГО кадра из {a.our} (0 кадров) — нечего аудировать")
        sys.exit(2)
    # ===== Медианный СПИКЕР-bbox (для распознания фото-вставки ≠ спикер) =====
    # Спикер = лицо, стабильное по позиции/масштабу через весь ролик. Фото-карточка (хедшот в кадре)
    # даёт лицо в ДРУГОМ месте/масштабе на почти-статичном кадре → не должно валить A/C по обрезке.
    spk_bbox=None
    if len(all_faces)>=3:
        xs=sorted(b['x'] for _,b in all_faces); ys=sorted(b['y'] for _,b in all_faces)
        ws=sorted(b['w'] for _,b in all_faces); hs=sorted(b['h'] for _,b in all_faces)
        md=lambda L:L[len(L)//2]
        spk_bbox=dict(x=md(xs),y=md(ys),w=md(ws),h=md(hs))
        facts.append(f"спикер-bbox (медиана по {len(all_faces)} кадрам)={spk_bbox}")
    def _is_photo_insert(t,fb):
        # True если лицо кадра НЕ совпадает с медианным спикером (низкий IoU ИЛИ резко иной масштаб)
        # И кадр почти статичный (низкий локальный motion) -> это фото-вставка, не спикер.
        if spk_bbox is None: return (False,'нет медианного спикера (мало кадров с лицом)')
        iou=_iou(fb,spk_bbox)
        scale_ratio=fb['h']/float(spk_bbox['h']) if spk_bbox['h'] else 1.0
        scale_off = scale_ratio<0.6 or scale_ratio>1.7
        if not (iou<0.25 or scale_off):
            return (False,f'лицо совпадает со спикером (IoU={iou:.2f} scale={scale_ratio:.2f})')
        lm=_local_motion(a.our,t)
        if lm is None: return (False,'локальный motion не измерен')
        # порог статики: low motion = почти картинка (откалибровано: реальная говорящая голова >2.0)
        if lm < 1.2:
            return (True,f'фото-вставка ≠ спикер (IoU={iou:.2f} scale={scale_ratio:.2f} local_motion={lm:.2f}<1.2 — почти статичная картинка)')
        return (False,f'лицо отличается от спикера, но кадр НЕ статичен (local_motion={lm:.2f}≥1.2) — не фото-вставка')
    def chk_ac(cond_ok, fact, failmsg, t, fb):
        # как chk, но если провал И кадр опознан как фото-вставка → перевести FAIL в WARN
        nonlocal machine; machine+=1; facts.append(fact)
        if cond_ok: return
        is_photo, why = _is_photo_insert(t, fb)
        if is_photo:
            iwarns.append(f"{failmsg} — ДЕМОУТ В WARN: {why}")
        else:
            fails.append(failmsg)
    if worst:
        t,crown,chin,f=worst;hr=crown-a.avatar_region_top
        chk_ac(hr>=HR,f"A headroom: worst t={t}s crown≈{crown} headroom={hr}px (slot_top={a.avatar_region_top})",
            f"A СРЕЗ ГОЛОВЫ headroom={hr}px<{HR} (макушка обрезана t={t}s)", t, f)
        chk(chin<=CB,f"A2 chin={chin}",f"A2 ПОДБОРОДОК В ОБРЕЗКЕ chin={chin}>{CB}")
        chk_ac(crown>=CT,f"C face_crown={crown} (>{CT})",f"C ЛИЦО В ВЕРХ-ОБРЕЗКЕ crown={crown}<{CT}", t, f)
    else:facts.append("A headroom: лицо не найдено — проверить вручную")
    # ДИНАМИКА = ВЕРХНЯЯ ЗОНА (скриншот), где она и должна жить; аватар-якорь НЕ меряем (автор: верх+чередование несут динамику).
    topreg=(0.0, min(1.0, a.avatar_region_top/float(H)))
    om=motion(a.our,a.frames,region=topreg)
    if a.ref and os.path.exists(a.ref):
        rm=motion(a.ref,a.frames,a.ref_start,a.ref_start+dur,region=topreg);ratio=round(om/rm,2) if rm else 0
        chk(rm and om>=0.7*rm,f"D dynamics ВЕРХ (окно 0-{round(dur,1)}с): our_top={om} vs competitor_top={rm} ratio={ratio} (нужно ≥0.7)",
            f"D СКРИНШОТ-ВЕРХ СТАТИЧЕН vs КОНКУРЕНТ: our_top={om} < 70% ({rm}, ratio={ratio}) — оживить верх (UI-действия/смена/чередование без аватара)")
    else:facts.append(f"D dynamics: our={om} (нет --ref для бенчмарка)")
    # E edge + K pillarbox + M split-from-0
    # координаты ниже масштабированы под реальный кадр (HIGH-4): _y()/_x() из SX/SY
    def _y(v):return max(0,min(round(v*SY),H))
    def _x(v):return max(0,min(round(v*SX),W))
    p=grab(a.our,dur*0.95)
    if p:
        arr=np.asarray(Image.open(p).convert('L'),dtype=np.float32);os.remove(p)
        ey0,ey1,ew=_y(300),_y(880),max(1,_x(8))
        le=float(np.mean(arr[ey0:ey1,:ew])) if arr[ey0:ey1,:ew].size else 0.0
        re_=float(np.mean(arr[ey0:ey1,-ew:])) if arr[ey0:ey1,-ew:].size else 0.0
        facts.append(f"E edge: github L_lum={le:.0f} R_lum={re_:.0f}")
        # K pillarbox: bottom slot side columns dark vs center
        bs=arr[a.avatar_region_top:_y(1900)]
        sw=max(1,_x(60)); cx0,cx1=_x(460),_x(620)
        if bs.size and bs.shape[1]>2*sw:
            side=float(np.mean(np.concatenate([bs[:,:sw],bs[:,-sw:]])))
            cenarr=bs[:,cx0:cx1]; cen=float(np.mean(cenarr)) if cenarr.size else 0.0
            machine+=1;facts.append(f"K avatar sides_lum={side:.0f} center_lum={cen:.0f} (pillarbox если боки сильно темнее)")
            # pillarbox-FAIL только на ТЁМНЫЕ бары (реальный дефект), яркий блюр-задник (rpn-стиль) = OK
            if side<48:fails.append(f"K ТЁМНЫЕ БАРЫ по бокам (sides_lum={side:.0f}<48) — узкий аватар на чёрном; нужен яркий блюр-задник или full-bleed")
            # L: ЖЁСТКАЯ РАМКА-КОРОБКА аватара — прямая вертикальная грань (бокс) внутри кадра = «вклеенная фотка»
            # NB: грань-бокс идёт почти на ВСЮ высоту нижней зоны; штрих буквы каптиона — короткий.
            # Поэтому мало max_vert_edge>15 — нужна ещё НЕПРЕРЫВНОСТЬ грани по высоте (>0.55),
            # иначе ложно ловим тёмный каптион на креме во фуллскрин-бите (нет аватара) — прецедент S3 «У МЕНЯ» по решению автора.
            bsf=bs.astype(np.float32); hd=np.abs(np.diff(bsf,axis=1)); colstr=hd.mean(axis=0)
            ix0,ix1=_x(120),_x(960)
            if colstr.size and ix1>ix0 and colstr[ix0:ix1].size:
                inner=colstr[ix0:ix1]; mx=float(inner.max()); mxx=int(inner.argmax())+ix0
                cont=float((hd[:,mxx-1]>25).mean()) if 0<mxx<=hd.shape[1] else 0.0
                machine+=1; facts.append(f"L avatar-box: max_vert_edge={mx:.1f} at x={mxx} continuity={cont:.2f} (порог 15 & 0.55)")
                if mx>15 and cont>0.55: fails.append(f"L ЖЁСТКАЯ РАМКА АВАТАРА: вертикальная грань {mx:.1f}>15 непрерывность {cont:.2f}>0.55 at x={mxx} — растворить край (перо/full-bleed), не бокс")
    p0=grab(a.our,0.4)
    if p0:
        arr=np.asarray(Image.open(p0).convert('L'),dtype=np.float32);os.remove(p0)
        ta=arr[_y(300):_y(850)]; ba=arr[_y(1000):_y(1400)]
        top=float(np.mean(ta)) if ta.size else 0.0; bot=float(np.mean(ba)) if ba.size else 0.0
        chk(top>12 and bot>12,f"M split-from-0: top_lum={top:.0f} bot_lum={bot:.0f}",
            f"M НЕТ СПЛИТА С 0с: top={top:.0f} bot={bot:.0f} (один пустой — у автора сплит с 0-й)")

    # ===== COMPOSITION PARSE =====
    html_text_region=None; html_has_content=False; cap_outline=False; cap_plate=None
    if a.html and os.path.exists(a.html):
        h=open(a.html,encoding='utf-8',errors='ignore').read()
        # B3/B4: @font-face может жить во ВНЕШНЕМ <link rel=stylesheet href=assets/*.css> — собираем
        # inline + external CSS, чтобы премиум-шрифт из data-URI/файла считался реальной загрузкой.
        css_blob, css_ext = _collect_css(a.html, h)
        cap_plate=_caption_plate_contrast(css_blob)   # (contrast,txt,plate,alpha) если у субтитра объявлена непрозрачная плашка
        html_has_content=bool(re.search(r'''class=["\'](w|cw|cap|title|mchip|zf|f)\b''', h)) or ('<video' in h)
        # subtitle band y из CSS (.stream/.cap top) — для F/G целевой регион
        cy=re.search(r'\.(?:stream|cap)\s*\{[^}]*top:\s*(\d+)px',h)
        if cy:
            y0=int(cy.group(1)); html_text_region=(max(0,y0-20),min(1920,y0+220))
        # Fallback: если CSS top не найден — смотрим baked V={...} из sub-comp JS (scene-assemble запекает)
        # J5: stream.style.top = V.top + 'px' -> const V = {"top": 1280, ...}
        if not html_text_region:
            # Ищем baked V={...} который содержит 'top': (позиция субтитра, не split_seam)
            for bv_m in re.finditer(r'const\s+V\s*=\s*(\{[^;]+\});', h):
                try:
                    import json as _jj; bv = _jj.loads(bv_m.group(1))
                    if 'top' in bv and isinstance(bv['top'], (int, float)):
                        y0=int(bv['top']); html_text_region=(max(0,y0-20),min(1920,y0+220)); break
                except Exception: pass
        title_lines=len(re.findall(r'<div>\s*<span class="w',h))
        cw=re.findall(r'<span class="cw[^"]*"[^>]*>([^<]*)</span>',h)
        w=re.findall(r'<span class="w[^"]*"[^>]*>([^<]*)</span>',h)
        cap_exit=bool(re.search(r'\.cap[^\n]*opacity:0|cw[^\n]*opacity:0',h)) or bool(re.search(r'cap.*to\(.*opacity:0',h))
        title_css=re.search(r'\.title\{[^}]*\}',h);cap_css=re.search(r'\.cap[^.{]*\{[^}]*\}|\.cap \.cw\{[^}]*\}',h)
        ff=re.findall(r"font-family:'?([A-Za-z][\w -]*)",h)
        title_font=re.search(r"\.(title|stream)[^}]*font-family:'?([\w -]+)",h)
        cap_font=re.search(r"\.(cap|stream)[^}]*font-family:'?([\w -]+)",h)
        hexes=re.findall(r'#[0-9A-Fa-f]{6}',h)
        cap_y=re.search(r'\.cap\{[^}]*top:(\d+)px',h);title_y=re.search(r'\.title\{[^}]*top:(\d+)px',h)
        text_blob=' '.join(cw+w)
        outline=bool(re.search(r'\.(cw|w)[^}]*(text-shadow|-webkit-text-stroke)',h)) or bool(re.search(r'class="(cw|w)"',h) and 'text-shadow' in h)
        cap_outline=outline

        chk(title_lines<=2,f"B1 title_lines={title_lines}",f"B1 ТИТР {title_lines} СТРОК («три этажа») — горизонтально 1-2 слова")
        chk(len(cw)<=2 or cap_exit,f"B2 caption_words={len(cw)} exit_anim={cap_exit}",f"B2 СУБТИТР {len(cw)} СЛОВ РАЗОМ без ухода — 1-2 слова word-by-word")
        # B3/B4: премиум = объявленный @font-face шрифт РЕАЛЬНО применён в font-family текст-класса
        # (inline ИЛИ внешний css). data-URI @font-face = валидная загрузка. Старая inline-only логика
        # давала ложный B3/B4 '' когда шрифт жил в assets/oswald.css. Фоллбек на regex-имя если CSS пуст.
        t_prem,t_fam,t_why=_premium_font_resolved(css_blob, ('title','stream'))
        c_prem,c_fam,c_why=_premium_font_resolved(css_blob, ('cap','cw','stream'))
        tf=t_fam or (title_font.group(2) if title_font else '')
        cf=c_fam or (cap_font.group(2) if cap_font else '')
        ext_note=(" [+%d внешних css]"%len(css_ext)) if css_ext else ""
        chk(t_prem,f"B3 title_font='{tf}' ({t_why}){ext_note}",f"B3 ТИТР ШРИФТ НЕ ПРЕМИУМ '{tf}' ({t_why}) — нужен Anton/Montserrat900 загруженный @font-face")
        chk(c_prem,f"B4 caption_font='{cf}' ({c_why}){ext_note}",f"B4 СУБТИТР ШРИФТ НЕ ПРЕМИУМ '{cf}' ({c_why})")
        chk(outline,f"B5 caption outline={outline}",f"B5 СУБТИТР БЕЗ ОБВОДКИ/КОНТРАСТА (нужен text-shadow/контур Submagic)")
        cyv=int(cap_y.group(1)) if cap_y else 0;tyv=int(title_y.group(1)) if title_y else 0
        chk(CT<=cyv<=CB-100 if cap_y else True,f"B6 caption_y={cyv}",f"B6 СУБТИТР ВНЕ SAFE-ZONE y={cyv} (надо {CT}-{CB-100})")
        chk(CT<=tyv<=CB-100 if title_y else True,f"B7 title_y={tyv}",f"B7 ТИТР ВНЕ SAFE-ZONE y={tyv}")
        lm=lime(hexes);chk(not lm,f"B8 lime_colors={lm or 'нет'}",f"B8 ЯДОВИТО-ЛАЙМ {lm} — бренд тёплый, лайм запрещён")
        gold=any(c.upper() in ('#E0A53D','#C98A3C','#BE4A24') or re.match(r'#[E-F][0-9A-F]C',c.upper()) for c in hexes)
        chk(gold,f"B9 brand_accent={gold}",f"B9 НЕТ бренд-золото/терракота акцента")
        emdash='—' in text_blob;chk(not emdash,f"B10 em-dash_in_text={emdash}",f"B10 EM-DASH в субтитре/титре — короткое тире, ToV")
        trailing=any(t.strip().endswith('.') for t in cw+w);chk(not trailing,f"B11 trailing_period={trailing}",f"B11 ТОЧКА в конце субтитра/титра — ToV без точек")
        chk('currentTime' in h,f"B12 sync_mechanism={'currentTime' in h}",f"B12 НЕТ синхрон-механизма (currentTime от таймлайна) — губы разъедутся")
        chk('overflow:hidden' in h or 'overflow: hidden' in h,f"B13 overflow_hidden={'overflow:hidden' in h}",f"B13 НЕТ overflow:hidden — контент за края при зуме")
        err=ERR_STR.search(h);chk(not err,f"B14 error_strings={'есть' if err else 'нет'}",f"B14 ERROR-СТРОКА в UI ('{err.group(0) if err else ''}') — рендерить залогинено")
        split=bool(re.search(r'slot top',h)) and bool(re.search(r'<video',h));chk(split,f"B15 split_struct={split}",f"B15 НЕТ split-структуры (2 слота + video)")
    else:
        facts.append("B*: --html не задан → структура/шрифт/субтитры/цвет/синхрон НЕ проверены машиной (задать --html!)")

    # ===== F / G / H / I — числовые расширения по рендеру =====
    # F: если у субтитра объявлена НЕПРОЗРАЧНАЯ плашка (rgba alpha>=0.4 / solid) — мерим контраст
    # текст-vs-ПЛАШКА по объявленным цветам (как P-CONTR), а НЕ пиксельную полосу (прецедент K5:
    # пиксельная полоса мерила яркость белой футболки аватара как «текст», хотя слово лежит на
    # тёмной плашке rgba(0,0,0,.58) и читается идеально). Пиксельный путь — для субтитра БЕЗ плашки.
    if cap_plate is not None:
        machine+=1
        cr_p,txt_p,plate_p,al_p=cap_plate
        facts.append(f"F caption-contrast [ПЛАШКА-путь]: текст{txt_p} vs плашка{plate_p}(alpha={al_p}) контраст={cr_p:.2f} порог 3.0 — пиксельная полоса НЕ применяется (плашка объявлена)")
        if cr_p<3.0:
            fails.append(f"F КОНТРАСТ КАПТИНА {cr_p:.2f}<3.0 [ПЛАШКА-путь] текст{txt_p} на плашке{plate_p} — поднять контраст текст/плашка")
    else:
        fr=check_F_caption_contrast(a.our,dur,a.frames,html_text_region,cap_outline,H_TOTAL=H)
        if fr:
            cr,t,reg,lo,hi=fr;machine+=1
            facts.append(f"F caption-contrast [ПИКСЕЛЬ-путь, без плашки]: min={cr:.2f} at t={t}s region_y={reg} (text_lum≈{hi} bg_lum≈{lo}) порог 3.0 outline={cap_outline}")
            # обводка (text-shadow/stroke) гарантирует контраст НЕЗАВИСИМО от яркости фона → не FAIL по фону.
            # FAIL только когда обводки НЕТ И измеренный контраст низкий (прецедент: cream-fullscreen фон давал ложный FAIL).
            if cr<3.0 and not cap_outline:
                fails.append(f"F КОНТРАСТ КАПТИНА {cr:.2f}<3.0 (t={t}s, y={reg}) [ПИКСЕЛЬ-путь] БЕЗ ОБВОДКИ — текст сливается с фоном, добавить плашку/обводку")
    gr=check_G_text_edge_cut(a.our,dur,a.frames,html_text_region,W_TOTAL=W,H_TOTAL=H)
    if gr:
        score,t,is_panel,edge_bright=gr;machine+=1
        facts.append(f"G text-edge-cut: score(text@x>1070)={score} edge_bright={edge_bright} panel={is_panel} at t={t}s (порог 40)")
        if score>40:fails.append(f"G СРЕЗ ТЕКСТА КРАЕМ: {score} ярких ТЕКСТ-пикс. в x>1070 (t={t}s, не панель) — слово упирается в край, nowrap/уже")
    hv,hd=check_H_icon_word_sync(a.html,a.whisper_json)
    machine+=1
    if hv=='SKIP':facts.append(f"H icon↔word sync: SKIP — {hd}")
    elif hv=='PASS':facts.append(f"H icon↔word sync: max_drift={hd['max_drift']}с ≤{hd['thresh']} — синхронно ({len(hd['rows'])} слов)")
    else:
        facts.append(f"H icon↔word sync: max_drift={hd['max_drift']}с > {hd['thresh']} — рассинхрон")
        rowtab='; '.join(f"{w}: html={s} vo={v} Δ={d}" for (w,s,v,d) in hd['rows'][:8])
        fails.append(f"H РАССИНХРОН ИКОНКА↔СЛОВО {hd['bad']} (порог {hd['thresh']}с). Таблица: {rowtab}")
    iv,idd=check_I_empty_frames(a.our,dur,a.avatar_region_top,html_has_content)
    if iv=='SKIP':facts.append(f"I empty-frames: SKIP — {idd}")
    else:
        machine+=1;facts.append(f"I empty-frames: longest_empty={idd['longest_empty_s']}с (порог {idd['thresh']}, at t={idd['at']}с)")
        if iv=='WARN':iwarns.append(f"I ПУСТОЙ ВЕРХ {idd['longest_empty_s']}с>1.5 (t={idd['at']}с) при обещанном HTML контенте — оживить/заполнить")

    # ===== J text∩face — ТЕКСТ ПОВЕРХ ЛИЦА (root-cause 2026-06-11: дефект без машинной оси) =====
    jr=check_J_text_on_face(a.our,dur,a.frames,a.html,H_TOTAL=H,W_TOTAL=W,SY=SY,SX=SX,no_face_expected=a.no_face_expected)
    machine+=1
    if jr['worst']:
        zone,sc,t,fb,fr_,er_,ho_=jr['worst']
        facts.append(f"J text∩face: worst zone={zone} overlap={sc:.3f} at t={t}s face_bbox={fb} (face_ratio={fr_} eye_ratio={er_} html_overlap={ho_}; пороги лицо>0.10 глаза>0.05) faces_found={jr['faces_found']}/{jr['faces_checked']}")
    else:
        facts.append(f"J text∩face: чисто — текст не пересекает лицо (faces_found={jr['faces_found']}/{jr['faces_checked']}, пороги лицо>0.10 глаза>0.05)")
    for (zone,sc,t,ho) in jr['fails']:
        why = 'html_overlap>0' if ho>0 else 'грубое нарушение pix>0.12'
        fails.append(f"J ТЕКСТ НА ЛИЦЕ ({'ЗОНА ГЛАЗ/ЛБА' if zone=='eye' else 'лицо'}): доля текст-пикс.={sc} html_overlap={ho} at t={t}s ({why}) — субтитр/титр лежит поперёк лица спикера, сдвинуть текст выше/ниже лица")
    for (zone,sc,t,ho) in jr.get('warns',[]):
        iwarns.append(f"J ось спорит с html — проверь кадром: пиксельная доля текст-пикс.={sc} в {'зоне глаз' if zone=='eye' else 'лице'} at t={t}s, НО html_overlap={ho} (текста в HTML на лице нет) — вероятно фон/неон даёт text-like пиксели, не реальный текст")
    if jr['no_face_run']:
        fails.append(f"J ЛИЦО НЕ НАЙДЕНО: {jr['no_face_run']}")

    # ===== K2 caption∩UI-content — СУБТИТР ПОВЕРХ ВАЖНОГО UI (root-cause 2026-06-11) =====
    k2=check_K2_caption_over_ui(a.our,dur,a.frames,html_text_region,a.avatar_region_top,W_TOTAL=W,H_TOTAL=H,SY=SY)
    machine+=1
    if k2['verdict']=='PASS' and 'reason' in k2:
        facts.append(f"K2 caption∩UI: PASS — {k2['reason']}")
    else:
        facts.append(f"K2 caption∩UI: edge_density={k2.get('dens')} at t={k2.get('t')}s band_y={k2.get('band')} (порог FAIL>0.15 WARN>0.05)")
    if k2['verdict']=='FAIL':
        fails.append(f"K2 СУБТИТР ПОВЕРХ ВАЖНОГО UI: плотность краёв={k2['dens']}>0.15 в зоне caption над сплит-линией (t={k2.get('t')}s) — текст закрывает контент верхнего экрана, поднять caption в нейтральный стык/аватар-зону")
    elif k2['verdict']=='WARN':
        iwarns.append(f"K2 caption частично над плотным UI: edge_density={k2['dens']} (5-15%%, t={k2.get('t')}s) — проверить что не закрывает важный элемент")

    # ===== N пустая панель — плашка-карточка нарисована, а контента в ней нет (glow-на-невидимом) =====
    nv,nd=check_N_empty_panel(a.our,dur,SY=SY)
    machine+=1
    facts.append(f"N empty-panel: longest_empty_panel={nd['longest_empty_panel_s']}с (порог {nd['thresh']}, at t={nd['at']}с)")
    if nv=='WARN':
        iwarns.append(f"N ПАНЕЛЬ ЕСТЬ, КОНТЕНТ ПУСТ: карточка-плашка в верх-зоне однородна >92%% площади {nd['longest_empty_panel_s']}с>1.2 (t={nd['at']}с) — плашка отрисована, но контента внутри нет (проверь glow-на-невидимом-промпте)")


    # ===== C2 текст в cut-zone (y<300 или y>1430) — FAIL независимо от family =====
    # Переиспользует детекцию текста из F/G: ищет яркие пиксели (>210) в верхней/нижней зонах обрезки.
    # cut-zone top: y<300, cut-zone bottom: y>1430 (в реальных пикс масштаба кадра).
    c2_fails = []
    if a.html and os.path.exists(a.html):
        h_c2 = open(a.html, encoding='utf-8', errors='ignore').read()
        # Ось C2: любой текст-регион (субтитр/заголовок) с bbox в cut-zone из HTML
        # Для baked-переменных (scene-assemble запекает V={} в const V =...): JS-строка
        # `el.style.top = V.top + 'px'` перезаписывает CSS-дефолт блока -> читаем baked V.
        # Собираем все baked V = {...} из HTML (один на каждый sub-comp после сборки)
        baked_tops = {}  # selector/context -> effective top px
        for baked_m in re.finditer(r'const\s+V\s*=\s*(\{[^;]+\});', h_c2):
            try:
                import json as _json
                bv = _json.loads(baked_m.group(1))
                if 'top' in bv:
                    # Ключи могут быть 'strap', 'caption', 'top' — сохраняем все
                    baked_tops[id(baked_m)] = int(bv['top'])
            except Exception:
                pass
        # Приоритет: baked vars перезаписывают CSS дефолт (JS runtime назначает top)
        effective_baked_top = list(baked_tops.values())[0] if baked_tops else None

        for sel_c2 in ('stream', 'cap', 'title', 'sub', 'caption', 'strap'):
            m_c2 = re.search(r'\.%s\s*\{([^}]*)\}' % sel_c2, h_c2)
            if not m_c2:
                continue
            body_c2 = m_c2.group(1)
            t_c2 = re.search(r'top:\s*(-?\d+)px', body_c2)
            if not t_c2:
                continue
            y_c2_css = int(t_c2.group(1))
            # Если в baked vars есть top для этого типа контейнера — JS перезаписывает CSS
            # (A18: `strap.style.top = V.top + 'px'`; J5: аналогично). Берём baked если есть.
            y_c2 = effective_baked_top if (effective_baked_top is not None and sel_c2 in ('strap', 'stream', 'cap')) else y_c2_css
            # масштабируем cut-zone границы под реальный кадр
            cut_top_px = round(300 * SY)
            cut_bot_px = round(1430 * SY)
            if y_c2 < cut_top_px:
                c2_fails.append(
                    f"C2 ТЕКСТ В ВЕРХНЕЙ ОБРЕЗКЕ: .{sel_c2} top={y_c2}px < {cut_top_px}px (cut-zone y<300) — площадка обрежет субтитр/заголовок")
            elif y_c2 > cut_bot_px:
                c2_fails.append(
                    f"C2 ТЕКСТ В НИЖНЕЙ ОБРЕЗКЕ: .{sel_c2} top={y_c2}px > {cut_bot_px}px (cut-zone y>1430) — площадка обрежет субтитр/заголовок")
    for c2f in c2_fails:
        fails.append(c2f)
        machine += 1

    # ===== ПРОФИЛЬ СЕМЬИ (Ф5a): перевод непрофильных осей из hard-FAIL в WARN-only =====
    prof=FAMILY_PROFILES.get(a.family) or FAMILY_PROFILES['talking-head-split']
    fails, family_warns, demoted_axes = _apply_family_profile(fails, a.family)
    for w in family_warns: iwarns.append(w)
    v='PASS' if not fails else 'FAIL'
    print(f"========== SCENE-AUDIT: {v}  (машинных проверок: {machine}) ==========")
    print(f"  · ПРОФИЛЬ СЕМЬИ: {a.family} — {prof['label']}")
    if demoted_axes:
        print(f"  · профиль перевёл в WARN (вне профиля семьи, не валят exit): {sorted(set(demoted_axes))}")
    elif prof.get('warn_only'):
        print(f"  · профиль {a.family}: ни одна demote-ось не сработала (оси {sorted(prof['warn_only'].keys())} либо прошли, либо не проверялись)")
    for f in facts:print("  ·",f)
    if iwarns:
        print("  -- WARN --")
        for w in iwarns:print("  ⚠",w)
    if fails:
        print("  -- FAIL --")
        for f in fails:print("  ✗",f)
    print("  -- ОСТАЁТСЯ АГЕНТУ (вкус/реализм, машинно не мерится) --")
    for x in ["эстетика реализма (не выглядит дёшево vs конкурент)","плавность появления субтитров",
              "точное посекундное совпадение раскладки с автором","качество/уместность B-roll и анимаций UI",
              "англицизмы в тексте (эвристика слабая — глазами)"]:print("  ~",x)
    json.dump({'verdict':v,'family':a.family,'machine_checks':machine,'fails':fails,'warns':iwarns,'family_demoted_axes':sorted(set(demoted_axes)),'facts':facts},
              open(os.path.splitext(a.our)[0]+'.audit.json','w'),ensure_ascii=False,indent=1)
    sys.exit(0 if v=='PASS' else 2)

if __name__=='__main__':main()

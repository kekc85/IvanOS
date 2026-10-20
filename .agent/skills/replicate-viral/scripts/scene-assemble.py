#!/usr/bin/env python3
"""
scene-assemble.py — детерминированный сборщик сцены reel из декларативной spec.json.

ФИЛОСОФИЯ (AC1 плана replicate-viral v2.0 «тропинки для Opus»):
  Модель решает ЧТО (какие блоки, какие params из enum-меню канона).
  Скрипт решает КАК (CSS, тайминги, z-стек, nested compositions) — из ГОТОВЫХ
  валидированных сниппетов библиотеки motion-blocks. Модель НИКОГДА не верстает руками.

ВХОД : scene.spec.json (схема scene-spec.schema.json)
ВЫХОД: <out>/index.html (+ blocks/ + assets/) — собранная HyperFrames-композиция 1080x1920.

Сборка = nested compositions HyperFrames:
  - КАЖДЫЙ слой = блок, загруженный как sub-composition через data-composition-src.
  - variable-блоки (E5/A18/F5/G24-27/J5/O6): params уходят в data-variable-values
    (getVariables() в блоке их читает).
  - slot-блоки без composition-variables (K3): копируем папку блока, подменяем src
    ассетов в его index.html на переданные файлы (под дефолтным именем слота).
  - z-index слоёв -> CSS z-index host-элемента.
  - impact-роль -> инлайн oswald.css в root (канон-шрифт, @font-face работает ТОЛЬКО inline).
  - SFX -> отдельные <audio data-start data-volume> по mapping.md.

ДЕТЕРМИНИЗМ: одинаковая спека -> байт-в-байт одинаковый HTML (сорт ключей, без дат/рандома).

usage:
  scene-assemble.py spec.json -o OUTDIR [--render] [--quiet]
    (по умолчанию: валидация + сборка + preflight аудит результата)
    --render: дополнительно npx hyperframes render + полный scene-audit по mp4.
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from skeleton_common import (  # ЕДИНЫЙ источник констант скелета (L3-фикс, не дублировать)
    LAYOUT_ENUM as _SK_LAYOUT_ENUM,
    AVATAR_FULLSCREEN_LAYOUT as _SK_AVATAR_FULLSCREEN_LAYOUT,
    AVATAR_BEARING_BLOCKS as _SK_AVATAR_BEARING_BLOCKS,
    AVATAR_OK_ROLES as _SK_AVATAR_OK_ROLES,
)
SCHEMA_PATH = os.path.join(HERE, 'scene-spec.schema.json')
MB_ROOT = os.path.expanduser('~/.business/growth/assets/motion-blocks')
SFX_ROOT = os.path.expanduser('~/.business/growth/assets/sfx')
FONT_OSWALD = os.path.join(MB_ROOT, '_tokens', 'fonts', 'oswald.css')
AUDIT = os.path.join(HERE, 'scene-audit.py')

# id блока -> относительный путь в библиотеке (family/id)
BLOCK_DIRS = {
    'E5-perspective-grid-floor': 'E-lighting-material/E5-perspective-grid-floor',
    'K1-vertical-5050-stacked': 'K-split-screen/K1-vertical-5050-stacked',
    'K6-vertical-5050-instant': 'K-split-screen/K6-vertical-5050-instant',
    'K8-fullbleed-plate': 'K-split-screen/K8-fullbleed-plate',
    'K3-overlap-card-avatar': 'K-split-screen/K3-overlap-card-avatar',
    'K7-avatar-hero-inset': 'K-split-screen/K7-avatar-hero-inset',
    'O6-avatar-feathered-fill': 'O-character-storytelling/O6-avatar-feathered-fill',
    'A18-title-strap-caps': 'A-typography/A18-title-strap-caps',
    'F5-ai-model-icon-row': 'F-mixed-media/F5-ai-model-icon-row',
    'G24-repo-file-list': 'G-ui-mocks/G24-repo-file-list',
    'G25-readme-card': 'G-ui-mocks/G25-readme-card',
    'G26-glow-frame-highlight': 'G-ui-mocks/G26-glow-frame-highlight',
    'G27-command-input-typeon': 'G-ui-mocks/G27-command-input-typeon',
    'G28-vscode-tree-reveal': 'G-ui-mocks/G28-vscode-tree-reveal',
    'G29-readme-card-hero': 'G-ui-mocks/G29-readme-card-hero',
    'G30-glow-frame-hero': 'G-ui-mocks/G30-glow-frame-hero',
    'J5-word-stream-whisper-sync': 'J-captions/J5-word-stream-whisper-sync',
    'J6-word-stream-nunito': 'J-captions/J6-word-stream-nunito',
}

# событие->категория уже в spec; дефолтный файл на категорию (из sfx/_INDEX.md)
SFX_DEFAULT = {
    'whoosh': 'whoosh/whoosh-02-fast-cut.wav',
    'click': 'click/click-01-tap.wav',
    'ui': 'ui/ui-01-select.wav',
    'pop': 'pop/pop-03-pluck.wav',
    'ding': 'ding/ding-01-confirm.wav',
    'riser': 'riser/riser-03-short-sweep.wav',
    'keyboard': 'keyboard/keyboard-01-typing-loop.wav',
    'negative': 'negative/negative-01-failure.wav',
}

BG_COLORS = {
    'dark': '#060608', 'near-black': '#060608', 'black': '#000000',
    'cream': '#FAF6EF', 'grid-floor': '#060608',
}

VIDEO_EXT = ('.mp4', '.webm', '.mov', '.m4v')

# ---- montage skeleton binding (Ф2) — константы из skeleton_common.py (L3, единый источник) ----
SKELETON_LAYOUT_ENUM = set(_SK_LAYOUT_ENUM)
# роли скелет-бита, на которых аватар-несущий блок / говорящая голова легитимны
AVATAR_FULLSCREEN_ROLES = set(_SK_AVATAR_OK_ROLES)
# layout спеки, означающий avatar full-screen (говорящую голову на весь кадр)
AVATAR_FULLSCREEN_LAYOUT = set(_SK_AVATAR_FULLSCREEN_LAYOUT)
# блоки, НЕСУЩИЕ аватар в кадре (O6 full-screen + K3 overlap-card) — на absent-бите запрещены
AVATAR_BEARING_BLOCKS = set(_SK_AVATAR_BEARING_BLOCKS)
SKELETON_DUR_EPS = 0.05  # допуск на длительность бита (t1-t0) спеки vs скелета


class SpecError(Exception):
    pass


def err(msg):
    raise SpecError(msg)


def load_block_meta(block_id):
    d = os.path.join(MB_ROOT, BLOCK_DIRS[block_id])
    meta = os.path.join(d, 'meta.json')
    if not os.path.exists(meta):
        err(f"блок {block_id}: нет meta.json в {d}")
    m = json.load(open(meta, encoding='utf-8'))
    return d, m


def ffprobe_dims_dur(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=width,height', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True)
    out = [x for x in r.stdout.strip().splitlines() if x.strip()]
    try:
        w = int(out[0]); h = int(out[1]); dur = float(out[2])
        return w, h, dur
    except Exception:
        return None


# ============================================================================
#  ВАЛИДАЦИЯ СПЕКИ (jsonschema если стоит, иначе ручная по обязательным/enum)
# ============================================================================
def validate_spec(spec):
    errors = []
    # 1) Схема, если jsonschema доступен — даёт глубокую проверку enum/типов
    try:
        import jsonschema
        schema = json.load(open(SCHEMA_PATH, encoding='utf-8'))
        v = jsonschema.Draft7Validator(schema)
        for e in sorted(v.iter_errors(spec), key=lambda x: list(x.path)):
            loc = '/'.join(str(p) for p in e.path) or '(root)'
            errors.append(f"схема [{loc}]: {e.message}")
    except ImportError:
        # 2) Ручная проверка обязательных полей + enum + структура
        errors += _manual_validate(spec)
    # 3) Доменная проверка ВСЕГДА (блоки, params против meta.json, ассеты)
    errors += _domain_validate(spec)
    return errors


def _manual_validate(spec):
    e = []
    schema = json.load(open(SCHEMA_PATH, encoding='utf-8'))
    if not isinstance(spec, dict):
        return ["спека не объект"]
    for req in schema['required']:
        if req not in spec:
            e.append(f"нет обязательного поля '{req}'")
    if 'duration' in spec and not (0.5 <= float(spec['duration']) <= 60):
        e.append(f"duration={spec['duration']} вне диапазона 0.5..60")
    if 'background' in spec and spec['background'] not in BG_COLORS:
        e.append(f"background '{spec['background']}' не в enum {sorted(BG_COLORS)}")
    if 'family' in spec and spec['family'] not in ('talking-head-split', 'overlap-card'):
        e.append(f"family '{spec['family']}' не в enum ['overlap-card', 'talking-head-split']")
    layers = spec.get('layers', [])
    if not isinstance(layers, list) or not layers:
        e.append("layers пуст или не массив")
    block_enum = set(BLOCK_DIRS)
    for i, L in enumerate(layers if isinstance(layers, list) else []):
        if not isinstance(L, dict) or 'block' not in L:
            e.append(f"слой {i}: нет поля 'block'"); continue
        if L['block'] not in block_enum:
            e.append(f"слой {i}: блок '{L['block']}' не существует в библиотеке (enum: {sorted(block_enum)})")
        for tk in ('t0','t1'):
            if tk in L and not isinstance(L[tk], (int, float)):
                e.append(f"слой {i}: '{tk}' должен быть числом")
        fr = L.get('font_role')
        if fr is not None and fr not in ('impact', 'sans-strap', 'serif-italic', 'mono', 'none'):
            e.append(f"слой {i}: font_role '{fr}' не в enum")
    cat_enum = set(SFX_DEFAULT)
    for i, s in enumerate(spec.get('sfx', []) or []):
        if 'category' not in s or 't' not in s:
            e.append(f"sfx {i}: нужны 't' и 'category'"); continue
        if s['category'] not in cat_enum:
            e.append(f"sfx {i}: category '{s['category']}' не в enum {sorted(cat_enum)}")
    beats = spec.get('beats')
    if beats is not None:
        if not isinstance(beats, list):
            e.append("beats не массив")
        else:
            for i, b in enumerate(beats):
                if not isinstance(b, dict) or 'layout' not in b:
                    e.append(f"beat {i}: нет обязательного 'layout'"); continue
                if b['layout'] not in SKELETON_LAYOUT_ENUM:
                    e.append(f"beat {i}: layout '{b['layout']}' не в enum {sorted(SKELETON_LAYOUT_ENUM)}")
                # M2: t0/t1 обязательны на каждом бите (без них длительность не проверить)
                for tk in ('t0', 't1'):
                    if tk not in b:
                        e.append(f"beat {i}: нет обязательного '{tk}' (без t0/t1 длительность не проверить, M2)")
    caps = spec.get('captions')
    if caps is not None:
        if 'words' not in caps:
            e.append("captions: нет 'words'")
        st = caps.get('style')
        if st is not None and st not in ('word-stream-whisper', 'mono-caps-chip', 'serif-italic-pop'):
            e.append(f"captions.style '{st}' не в enum")
    for i, o in enumerate(spec.get('overrides', []) or []):
        for k in ('field', 'value', 'why'):
            if k not in o:
                e.append(f"override {i}: нет '{k}' (каждый override обязан нести why-обоснование)")
    return e


def _domain_validate(spec):
    """Блоки существуют; params входят в variables∪slots блока; видео-ассеты под требования слота."""
    e = []
    for i, L in enumerate(spec.get('layers', []) or []):
        bid = L.get('block')
        if bid not in BLOCK_DIRS:
            continue  # уже поймано выше
        try:
            bdir, meta = load_block_meta(bid)
        except SpecError as se:
            e.append(str(se)); continue
        allowed = set((meta.get('variables') or {}).keys()) | set((meta.get('slots') or {}).keys())
        params = L.get('params', {}) or {}
        for pk in params:
            if pk not in allowed:
                e.append(f"слой {i} ({bid}): param '{pk}' не входит в variables/slots блока "
                         f"(допустимо: {sorted(allowed) or 'нет'})")
        # видео-слоты: проверить аспект/длительность реального файла
        slots = meta.get('slots') or {}
        for sk in slots:
            if sk not in params:
                continue
            val = params[sk]
            if not isinstance(val, str) or not val.lower().endswith(VIDEO_EXT):
                continue
            path = _resolve_asset(val, bdir)
            if not os.path.exists(path):
                e.append(f"слой {i} ({bid}): ассет слота '{sk}' не найден: {path}")
                continue
            info = ffprobe_dims_dur(path)
            if info is None:
                e.append(f"слой {i} ({bid}): ассет '{sk}' не читается ffprobe: {path}")
                continue
            w, h, dur = info
            req = _slot_requirement(bid, sk)
            if req:
                rw, rh, rdur = req
                if rw and rh and (w, h) != (rw, rh):
                    e.append(f"слой {i} ({bid}): слот '{sk}' аспект {w}x{h} != требуемого {rw}x{rh} "
                             f"(риск-флаг ресёрча: K3 ждёт head-and-shoulders 720x1280)")
                if rdur and dur + 0.05 < rdur:
                    e.append(f"слой {i} ({bid}): слот '{sk}' длительность {dur:.2f}s < требуемых {rdur}s")
    return e


def _slot_requirement(block_id, slot_key):
    """Требования (w,h,min_dur) к видео-слоту. Из README/ресёрча блоков (K3 риск-флаг)."""
    REQ = {
        ('K3-overlap-card-avatar', 'avatar_video_src'): (720, 1280, 5.0),
        ('K7-avatar-hero-inset', 'avatar_video_src'): (720, 1280, 4.0),
        ('K7-avatar-hero-inset', 'avatar_cutout_src'): (None, None, 4.0),
        ('K7-avatar-hero-inset', 'card_video_src'): (None, None, 4.0),
        ('K3-overlap-card-avatar', 'avatar_cutout_src'): (None, None, 5.0),
        ('K3-overlap-card-avatar', 'card_video_src'): (None, None, 5.0),
    }
    return REQ.get((block_id, slot_key))


def _resolve_asset(val, block_dir):
    if os.path.isabs(val):
        return val
    p = os.path.expanduser(val)
    if os.path.isabs(p):
        return p
    # относительный — сначала от cwd, потом от папки блока (дефолты слотов)
    if os.path.exists(val):
        return os.path.abspath(val)
    return os.path.join(block_dir, val)


# ============================================================================
#  ПРИНУЖДЕНИЕ СКЕЛЕТА (montage skeleton binding, Ф2)
# ============================================================================
def find_skeleton(spec_path, outdir, explicit=None):
    """Найти scene-skeleton.json: явный путь → dirname(spec) → outdir.
    Нет нигде → None (backward-compat: принуждение выключено)."""
    cands = []
    if explicit:
        cands.append(explicit)
    if spec_path:
        cands.append(os.path.join(os.path.dirname(os.path.abspath(spec_path)), 'scene-skeleton.json'))
    if outdir:
        cands.append(os.path.join(os.path.abspath(outdir), 'scene-skeleton.json'))
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def _spec_beat_bears_avatar(beat):
    """Бит спеки НЕСЁТ аватар (говорящую голову) в кадре?
    Сигнал: layout==full-head (avatar full-screen) ИЛИ block — аватар-несущий блок
    (O6 full-screen ИЛИ K3 overlap-card-avatar). C2-фикс: K3 раньше протаскивал
    говорящую голову на absent-битах, т.к. детектор знал только full-head/O6."""
    if beat.get('layout') in AVATAR_FULLSCREEN_LAYOUT:
        return True
    blk = beat.get('block')
    if blk and blk in AVATAR_BEARING_BLOCKS:
        return True
    return False


def _enforce_skeleton(spec, skeleton_path):
    """Проверить, что beats[] спеки ВОСПРОИЗВОДЯТ замороженный скелет эталона.
    Возвращает список ошибок (пуст = PASS). Принуждение включается ТОЛЬКО при наличии
    skeleton_path; иначе функция не вызывается (backward-compat в main)."""
    e = []
    try:
        skel = json.load(open(skeleton_path, encoding='utf-8'))
    except Exception as ex:
        return [f"скелет {skeleton_path} не читается как JSON: {ex}"]

    skel_beats = skel.get('beats') or []
    n_skel = skel.get('n_beats', len(skel_beats))

    spec_beats = spec.get('beats')
    if not spec_beats:
        return [
            f"найден scene-skeleton.json ({skeleton_path}), но в спеке НЕТ beats[].",
            f"  Спека ОБЯЗАНА содержать beats[] по скелету ({n_skel} битов): "
            f"layout каждого бита по скелету, dur≤скелета, full-head только на bookend/anchor.",
        ]

    # 1) число битов
    if len(spec_beats) != n_skel:
        e.append(f"число битов спеки={len(spec_beats)} != скелета={n_skel} "
                 f"(спека обязана воспроизводить скелет побитно)")

    # 2..N) побитная сверка (по индексу/порядку, в пределах общего числа)
    pairs = min(len(spec_beats), len(skel_beats))
    for i in range(pairs):
        sb = spec_beats[i] if isinstance(spec_beats[i], dict) else {}
        kb = skel_beats[i] if isinstance(skel_beats[i], dict) else {}
        sl = sb.get('layout')
        kl = kb.get('layout')
        role = kb.get('avatar_role')

        # layout бита совпадает со скелетом
        if sl != kl:
            e.append(f"бит {i}: layout спеки '{sl}' != скелета '{kl}' "
                     f"(монтаж обязан повторять раскладку эталона побитно)")

        # длительность бита спеки ≤ скелета (+EPS)
        try:
            s_dur = float(sb.get('t1')) - float(sb.get('t0'))
        except (TypeError, ValueError):
            s_dur = None
        try:
            k_dur = float(kb.get('t1')) - float(kb.get('t0'))
        except (TypeError, ValueError):
            k_dur = None
        if s_dur is not None and k_dur is not None and s_dur > k_dur + SKELETON_DUR_EPS:
            e.append(f"бит {i}: длительность спеки {s_dur:.2f}s > скелета {k_dur:.2f}s "
                     f"(раскладка держится дольше эталон-бита = монотонность)")

        # аватар-несущий бит (full-head / O6 / K3) допустим ТОЛЬКО на bookend/anchor-битах скелета
        if _spec_beat_bears_avatar(sb) and role not in AVATAR_FULLSCREEN_ROLES:
            _blk = sb.get('block')
            e.append(f"бит {i}: аватар (говорящая голова: layout '{sl}'"
                     f"{', block ' + _blk if _blk in AVATAR_BEARING_BLOCKS else ''}) запрещён — "
                     f"у эталона тут avatar_role='{role}' (контент, не лицо). Говорящую голову "
                     f"только на битах bookend/anchor (анти-монотонность).")
    return e


# ============================================================================
#  СБОРКА
# ============================================================================
def block_has_variables(meta):
    return bool(meta.get('variables'))


def assemble(spec, outdir):
    os.makedirs(outdir, exist_ok=True)
    blocks_out = os.path.join(outdir, 'blocks')
    assets_out = os.path.join(outdir, 'assets')
    os.makedirs(blocks_out, exist_ok=True)
    os.makedirs(assets_out, exist_ok=True)

    scene_id = spec['scene_id']
    duration = float(spec['duration'])
    bg = BG_COLORS.get(spec.get('background', 'dark'), '#060608')

    layers = spec['layers']
    # z по умолчанию = индекс; затем стабильная сортировка по z для порядка в DOM
    enriched = []
    for idx, L in enumerate(layers):
        z = L.get('z', idx)
        enriched.append((z, idx, L))
    enriched.sort(key=lambda t: (t[0], t[1]))

    need_impact = any((L.get('font_role') == 'impact') for _, _, L in enriched)

    host_html = []
    host_cids = []
    for order, (z, idx, L) in enumerate(enriched):
        bid = L['block']
        bdir, meta = load_block_meta(bid)
        params = dict(L.get('params', {}) or {})
        cid = f"L{order}-{bid.split('-')[0].lower()}"   # уникальный composition-id слоя
        bdest = os.path.join(blocks_out, cid)
        if os.path.exists(bdest):
            shutil.rmtree(bdest)
        os.makedirs(bdest, exist_ok=True)

        raw = open(os.path.join(bdir, 'index.html'), encoding='utf-8').read()

        # 1) ассеты-слоты: скопировать переданные файлы под дефолтным именем слота в папку слоя
        for sk, default_name in (meta.get('slots') or {}).items():
            if sk in params and isinstance(params[sk], str):
                src = _resolve_asset(params[sk], bdir)
                if not os.path.exists(src):
                    err(f"{bid}: слот '{sk}' -> файл не найден {src}")
                shutil.copy2(src, os.path.join(bdest, os.path.basename(default_name)))
            else:
                # дефолтный ассет блока (если есть рядом) — взять как есть
                dft = os.path.join(bdir, os.path.basename(default_name))
                if os.path.exists(dft):
                    shutil.copy2(dft, os.path.join(bdest, os.path.basename(default_name)))

        # 2) запечь переменные (build-time): defaults блока + params слоя
        baked = None
        if block_has_variables(meta):
            baked = {k: v.get('default') for k, v in (meta.get('variables') or {}).items()}
            baked.update(params)
            baked.setdefault('duration', duration)
            # слоты внутри baked не нужны как vars — они подменяются как файлы; но O6 хранит slot-имя в vars? нет.

        # 3) трансформировать в template-обёрнутый sub-comp с уникальным cid + media-prefix
        media_prefix = f"blocks/{cid}"
        sub = _to_subcomp(raw, cid, baked_vars=baked, duration=duration, media_prefix=media_prefix)
        open(os.path.join(bdest, 'index.html'), 'w', encoding='utf-8').write(sub)

        host_cids.append(cid)
        # окно слоя: t0/t1 спеки (смена раскладок по битам внутри одной сцены). Без них — вся сцена.
        l_t0 = float(L.get('t0', 0) or 0)
        l_t1 = float(L.get('t1', duration) if L.get('t1') is not None else duration)
        l_t1 = min(max(l_t1, l_t0), duration)
        l_dur = round(l_t1 - l_t0, 4)
        host_html.append(
            f'      <div id="host-{cid}" class="layer" style="z-index:{z}"\n'
            f'           data-composition-id="{cid}"\n'
            f'           data-composition-src="blocks/{cid}/index.html"\n'
            f'           data-start="{_num(l_t0)}" data-duration="{_num(l_dur)}" data-track-index="{order}"></div>')

    # SFX + audio дорожки
    audio_html = []
    track = len(enriched)
    sfx = spec.get('sfx', []) or []
    for s in sorted(sfx, key=lambda x: x['t']):
        cat = s['category']
        fname = s.get('file') or SFX_DEFAULT[cat]
        src = os.path.join(SFX_ROOT, fname)
        base = os.path.basename(fname)
        tgt = os.path.join(assets_out, base)
        if os.path.exists(src):
            shutil.copy2(src, tgt)
        vol = s.get('volume', 0.16)
        audio_html.append(
            f'      <audio id="sfx-{track}-{cat}" class="clip" src="assets/{base}" data-start="{_num(s["t"])}" '
            f'data-track-index="{track}" data-volume="{_num(vol)}"></audio>')
        track += 1

    audio = spec.get('audio') or {}
    if audio.get('vo_src'):
        src = _resolve_asset(audio['vo_src'], outdir)
        base = os.path.basename(src)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(assets_out, base))
        audio_html.append(
            f'      <audio id="audio-vo" class="clip" src="assets/{base}" data-start="0" '
            f'data-track-index="{track}" data-volume="{_num(audio.get("vo_volume",1))}"></audio>')
        track += 1
    if audio.get('music_src'):
        src = _resolve_asset(audio['music_src'], outdir)
        base = os.path.basename(src)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(assets_out, base))
        audio_html.append(
            f'      <audio id="audio-music" class="clip" src="assets/{base}" data-start="0" '
            f'data-track-index="{track}" data-volume="{_num(audio.get("music_volume",0.12))}"></audio>')
        track += 1

    # инлайн oswald.css при impact-роли (канон-шрифт работает ТОЛЬКО inline)
    font_style = ''
    if need_impact and os.path.exists(FONT_OSWALD):
        font_style = '\n  <style id="impact-font">\n' + open(FONT_OSWALD, encoding='utf-8').read() + '\n  </style>'

    root = _root_template(scene_id, duration, bg, font_style, host_html, audio_html)
    idx_path = os.path.join(outdir, 'index.html')
    open(idx_path, 'w', encoding='utf-8').write(root)
    audit_path = _write_audit_html(outdir, idx_path, host_cids)

    # минимальный package.json под npx render (как у блоков)
    pkg = {
        "name": f"scene-{scene_id}", "private": True, "type": "module",
        "scripts": {
            "render": "npx --yes hyperframes@0.6.91 render",
            "check": "npx --yes hyperframes@0.6.91 lint && npx --yes hyperframes@0.6.91 validate",
        },
    }
    open(os.path.join(outdir, 'package.json'), 'w').write(json.dumps(pkg, indent=2))
    # hyperframes.json (registry-конвенция как у блоков)
    hf = {"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
          "paths": {"blocks": "blocks", "assets": "assets"}}
    open(os.path.join(outdir, 'hyperframes.json'), 'w').write(json.dumps(hf, indent=2))
    return idx_path, audit_path


def _num(x):
    f = float(x)
    return str(int(f)) if f == int(f) else f"{f:g}"


def _to_subcomp(html, cid, baked_vars=None, duration=5, media_prefix=''):
    """Превратить standalone-блок (index.html) в template-обёрнутый sub-comp HyperFrames:
       - запечь переменные (заменить getVariables() константой) — детерминизм без runtime-vars;
       - убрать data-composition-variables с <html>;
       - переписать относит. media src на media_prefix/<file> (резолв от ROOT);
       - переименовать composition-id main->cid, id="root"->cid-root и ССЫЛКИ getElementById('root');
       - переименовать __timelines['main']->cid;
       - проставить data-duration сцены;
       - собрать в <template id="cid-tpl"><div data-composition-id=cid ...>style+gsap+content+script</div></template>.
    Доказано рендером: K3+A18 этим способом композятся (videos + strap)."""
    import json as _json
    # 1) bake vars
    if baked_vars is not None:
        html = re.sub(r"const\s+V\s*=\s*window\.__hyperframes\.getVariables\(\)\s*;",
                      "const V = " + _json.dumps(baked_vars, ensure_ascii=False) + ";", html)
    # 2) strip declared variables
    html = re.sub(r"\s*data-composition-variables='\[.*?\]'", "", html, flags=re.S)
    # 3) media prefix
    if media_prefix:
        def _mp(m):
            attr, q, val = m.group(1), m.group(2), m.group(3)
            if val.startswith(('http://', 'https://', 'data:', '/', media_prefix + '/')):
                return m.group(0)
            return f'{attr}={q}{media_prefix}/{val}{q}'
        html = re.sub(r'\b(src)=(["\'])([^"\']+\.(?:mp4|webm|mov|m4v|wav|mp3))\2', _mp, html)
    # 4) extract style + inline scripts + root content div
    styles = ''.join(re.findall(r'<style>(.*?)</style>', html, re.S))
    scripts = re.findall(r'<script>(.*?)</script>', html, re.S)   # inline only (CDN gsap re-added)
    mbody = re.search(r'<body>(.*?)</body>', html, re.S)
    body = mbody.group(1) if mbody else html
    mroot = re.search(r'(<div id="root".*?)\n\s*<script>', body, re.S)
    if not mroot:
        mroot = re.search(r'(<div id="root".*</div>)', body, re.S)
    root = mroot.group(1)
    # rename ids/composition-id
    root = root.replace('data-composition-id="main"', f'data-composition-id="{cid}"')
    root = root.replace('id="root"', f'id="{cid}-root"', 1)
    root = re.sub(r'data-duration="[\d.]+"', f'data-duration="{_num(duration)}"', root, count=1)
    # fix script references to getElementById('root') and timelines + ken-burns duration
    fixed_scripts = []
    for sc in scripts:
        sc = sc.replace("getElementById('root')", f"getElementById('{cid}-root')")
        sc = sc.replace('getElementById("root")', f'getElementById("{cid}-root")')
        sc = sc.replace('__timelines["main"]', f'__timelines["{cid}"]')
        sc = sc.replace("__timelines['main']", f"__timelines['{cid}']")
        # ken-burns: duration:5 ... ease:"none" -> scene duration
        sc = re.sub(r'(duration:\s*)5(\s*,\s*ease:\s*"none")',
                    lambda m: m.group(1) + _num(duration) + m.group(2), sc)
        fixed_scripts.append(sc)
    # split root opening tag from inner
    open_tag, inner = root.split('>', 1)
    style_block = f'<style>{styles}</style>' if styles.strip() else ''
    script_block = '\n'.join(f'<script>{sc}</script>' for sc in fixed_scripts)
    return (f'<template id="{cid}-tpl">\n'
            f'{open_tag}>\n'
            f'{style_block}\n'
            f'<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>\n'
            f'{inner}\n'
            f'{script_block}\n'
            f'</div>\n'
            f'</template>\n')


def _root_relative_media(html, prefix):
    """Переписать относительные src= видео/аудио/img внутри sub-comp на root-относительный
    путь blocks/<bid>/<file>, т.к. при загрузке через data-composition-src медиа резолвятся
    от ROOT index.html, а не от папки блока (иначе 404)."""
    def repl(m):
        attr, q, val = m.group(1), m.group(2), m.group(3)
        low = val.lower()
        if val.startswith(('http://', 'https://', 'data:', '/', '../', prefix + '/')):
            return m.group(0)
        if not low.endswith(('.mp4', '.webm', '.mov', '.m4v', '.wav', '.mp3', '.png', '.jpg', '.jpeg', '.svg', '.gif')):
            return m.group(0)
        return f'{attr}={q}{prefix}/{val}{q}'
    return re.sub(r'\b(src)=(["\'])([^"\']+)\2', repl, html)


def _retime_block(html, duration):
    """Проставить duration сцены в data-duration root-композиции и её клипов (slot-блок без variables)."""
    d = _num(duration)
    # root data-duration
    html = re.sub(r'(data-composition-id="main"[^>]*?data-duration=")[^"]*(")',
                  lambda m: m.group(1) + d + m.group(2), html, count=1)
    # ken-burns длительность под сцену (scale tween duration:5 -> duration)
    html = re.sub(r'(duration:\s*)5(\s*,\s*ease:\s*"none")',
                  lambda m: m.group(1) + d + m.group(2), html)
    return html


def _root_template(scene_id, duration, bg, font_style, host_html, audio_html):
    layers = '\n'.join(host_html)
    audios = ('\n' + '\n'.join(audio_html)) if audio_html else ''
    return f'''<!doctype html>
<html lang="ru" data-resolution="portrait">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=1080, height=1920"/>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>{font_style}
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html, body {{ width:1080px; height:1920px; overflow:hidden; background:{bg}; }}
    #root {{ position:absolute; inset:0; background:{bg}; overflow:hidden; }}
    .layer {{ position:absolute; inset:0; width:1080px; height:1920px; }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{_num(duration)}" data-width="1080" data-height="1920">
{layers}{audios}
  </div>
  <script>
    window.__timelines = window.__timelines || {{}};
    window.__timelines["main"] = gsap.timeline({{ paused:true }});
  </script>
</body>
</html>
'''


# ============================================================================
#  АУДИТ-ВЫЗОВЫ
# ============================================================================
def _write_audit_html(outdir, idx_path, host_blocks):
    """Собрать ПЛОСКИЙ index.audit.html: root + развёрнутое содержимое каждого sub-comp
    (вынуть <div data-composition-id> из <template>), чтобы HTML-парс осей B/M аудита
    видел РЕАЛЬНУЮ разметку слоёв (шрифты, цвета, split-маркеры, captions), а не пустой
    nesting-root. Это НЕ ослабление аудита — это полный вид того же контента для парсера."""
    root = open(idx_path, encoding='utf-8').read()
    inlined = []
    for cid in host_blocks:
        fp = os.path.join(outdir, 'blocks', cid, 'index.html')
        if not os.path.exists(fp):
            continue
        sub = open(fp, encoding='utf-8').read()
        m = re.search(r'<template[^>]*>(.*)</template>', sub, re.S)
        inlined.append(m.group(1) if m else sub)
    flat = root.replace('</body>', '\n<!-- FLATTENED SUBCOMPS FOR AUDIT -->\n' + '\n'.join(inlined) + '\n</body>')
    # ВНЕ дерева проекта: иначе hyperframes-runtime обнаружит второй data-composition-id
    # (multiple_root_compositions). Кладём как .audit-html (не .html) рядом с outdir.
    ap = os.path.join(os.path.dirname(os.path.abspath(outdir)) or '.',
                      os.path.basename(os.path.abspath(outdir)) + '.audit-html')
    open(ap, 'w', encoding='utf-8').write(flat)
    return ap


def run_preflight(idx_path):
    print("\n===== PREFLIGHT (0 рендеров) =====")
    # P-PLACEHOLDER: grep итогового HTML на запрещённые плейсхолдеры
    _placeholder_rc = _check_placeholder(idx_path)
    if _placeholder_rc != 0:
        return _placeholder_rc
    r = subprocess.run([sys.executable, AUDIT, '--preflight', '--html', idx_path])
    return r.returncode


_PLACEHOLDER_RE = re.compile(
    r'FREEPIK|ACME|LOREM|PLACEHOLDER|YOUR\s+TEXT|SAMPLE',
    re.IGNORECASE
)

def _check_placeholder(html_path):
    """P-PLACEHOLDER: grep итогового HTML на запрещённые плейсхолдеры (без регистра).
    FAIL если найдено (без override-why). Защищает от вытекания демо-контента Freepik/Acme/Lorem."""
    if not html_path or not os.path.exists(html_path):
        return 0  # нечего проверять — аудит сообщит сам
    try:
        text = open(html_path, encoding='utf-8', errors='ignore').read()
    except OSError:
        return 0
    # Удаляем src/href/data-src атрибуты (содержат пути к ассетам с легитимными именами)
    # перед тем как убрать теги — иначе пути файлов ("freepik-spaces/...") ложно триггерят
    text_no_attrs = re.sub(
        r'(?:src|href|data-src|data-composition-src)=(["\'])[^"\']*\\1',
        '', text, flags=re.I)
    # Также убираем data-variable-values (запечённые переменные блоков — могут содержать пути)
    text_no_attrs = re.sub(r'const\s+V\s*=\s*\{[^;]+\};', '', text_no_attrs, flags=re.S)
    text_only = re.sub(r'<[^>]+>', ' ', text_no_attrs)
    m = _PLACEHOLDER_RE.search(text_only)
    if m:
        print(f"  ✗ P-PLACEHOLDER: FAIL — найдено запрещённое слово «{m.group(0)}» в тексте HTML ({html_path})")
        print("    Это демо-контент (Freepik/ACME/Lorem/…). Замените все слоты реальными материалами.")
        print("    Если это намеренная заглушка — добавьте override-why в спеку (поле overrides[].why).")
        return 2
    print("  · P-PLACEHOLDER: PASS (запрещённые слова не найдены)")
    return 0


def run_render_and_audit(outdir, idx_path, audit_html=None, no_face=False, family=None):
    print("\n===== RENDER (npx hyperframes render) =====")
    rr = subprocess.run(['npx', '--yes', 'hyperframes@0.6.91', 'render'], cwd=outdir)
    if rr.returncode != 0:
        print("RENDER FAILED"); return rr.returncode, None
    mp4 = _find_latest_mp4(outdir)
    if not mp4:
        print("RENDER: mp4 не найден"); return 2, None
    print(f"render mp4: {mp4}")
    print("\n===== FULL SCENE-AUDIT =====")
    cmd = [sys.executable, AUDIT, '--our', mp4, '--html', audit_html or idx_path]
    if no_face:
        cmd.append('--no-face-expected')
    if family:
        cmd += ['--family', family]   # семья раскладки из спеки -> профиль вердикта аудита (Ф5a)
    r = subprocess.run(cmd)
    return r.returncode, mp4


def _find_latest_mp4(outdir):
    cands = []
    for root, _, files in os.walk(outdir):
        for f in files:
            if f.endswith('.mp4'):
                p = os.path.join(root, f)
                cands.append((os.path.getmtime(p), p))
    if not cands:
        return None
    cands.sort()
    return cands[-1][1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('spec')
    ap.add_argument('-o', '--out', required=True)
    ap.add_argument('--render', action='store_true', help='+ npx render + полный scene-audit')
    ap.add_argument('--skeleton', default=None,
                    help='явный путь к scene-skeleton.json (иначе ищется рядом со спекой / в out-dir)')
    ap.add_argument('--no-face-expected', action='store_true', help='пробросить в полный аудит (сцена без лица)')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()

    try:
        spec = json.load(open(a.spec, encoding='utf-8'))
    except Exception as ex:
        print(f"СПЕКА не читается как JSON: {ex}"); sys.exit(2)

    errors = validate_spec(spec)
    if errors:
        print("========== ВАЛИДАЦИЯ СПЕКИ: FAIL ==========")
        for e in errors:
            print("  ✗", e)
        sys.exit(2)
    print("ВАЛИДАЦИЯ СПЕКИ: PASS")

    # ПРИНУЖДЕНИЕ СКЕЛЕТА (montage skeleton binding, Ф2): есть scene-skeleton.json →
    # beats[] спеки ОБЯЗАНЫ воспроизводить скелет; нет скелета → backward-compat (как было).
    skeleton_path = find_skeleton(a.spec, a.out, explicit=a.skeleton)
    if skeleton_path:
        skel_errors = _enforce_skeleton(spec, skeleton_path)
        if skel_errors:
            print("========== ПРИНУЖДЕНИЕ СКЕЛЕТА: REJECT ==========")
            print(f"  скелет: {skeleton_path}")
            for se in skel_errors:
                print("  ✗", se)
            sys.exit(2)
        print(f"ПРИНУЖДЕНИЕ СКЕЛЕТА: PASS (beats[] воспроизводят {skeleton_path})")
    else:
        print("ПРИНУЖДЕНИЕ СКЕЛЕТА: skip (нет scene-skeleton.json — backward-compat)")

    # предупреждение по плотности SFX (1/1.5с) — не блокирует
    sfx = sorted((spec.get('sfx') or []), key=lambda x: x['t'])
    for i in range(1, len(sfx)):
        if sfx[i]['t'] - sfx[i-1]['t'] < 1.5:
            print(f"  ⚠ SFX плотность: {sfx[i-1]['t']}s и {sfx[i]['t']}s ближе 1.5с (mapping.md: каша)")

    try:
        idx, audit_html = assemble(spec, a.out)
    except SpecError as se:
        print("========== СБОРКА: FAIL ==========")
        print("  ✗", se); sys.exit(2)
    print(f"СБОРКА: PASS -> {idx}")

    pf = run_preflight(audit_html)
    if a.render:
        spec_family = spec.get('family', 'talking-head-split')  # прокидка семьи спеки в авто-аудит (Ф5a)
        rc, mp4 = run_render_and_audit(a.out, idx, audit_html=audit_html, no_face=a.no_face_expected, family=spec_family)
        sys.exit(0 if (pf == 0 and rc == 0) else 2)
    sys.exit(0 if pf == 0 else 2)


if __name__ == '__main__':
    main()

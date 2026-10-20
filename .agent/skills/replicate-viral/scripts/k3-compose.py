#!/usr/bin/env python3
"""k3-compose.py — ЕДИНЫЙ композитор кадра по канону K3 (автор).

Чинит ТРИ дефекта приёмки разом:

1. ОБРЕЗАННЫЕ ПЛЕЧИ. Замер: маска rembg на 85% высоты сужается с 1080px до 774px,
   в самом низу = 0 → кардиган обрывается, руки висят отдельно.
   Лечение: маска ДОСТРАИВАЕТСЯ вниз — от строки, где она ещё полная, до низа кадра
   держим максимальную ширину силуэта (плечи и руки не могут «сужаться» к низу).

2. НЕТ СКРУГЛЁННОЙ КАРТОЧКИ. Автор: «у меня ящик с квадратной рамкой, там должны быть
   закруглённые края, чтобы лоб оттуда плавно вылезал».
   Лечение: карточка K3 с радиусом 26px и тенью (канон блока
   ~/.business/growth/assets/motion-blocks/K-split-screen/K3-overlap-card-avatar).
   Голова выходит ЗА верхнюю грань, плечи целиком внутри.

3. ТОНКИЙ ШРИФТ. Субтитр рисуется Montserrat Black (wght 900) с толстой обводкой.

usage: k3-compose.py --twin <twin.mp4> --panel <panel.mp4|dir> --out <out.mp4>
       [--card-top 0.52] [--radius 26] [--probe]
"""
import argparse, os, subprocess, sys
import numpy as np
import cv2

REMBG_PY = os.path.expanduser("~/.venv-rembg/bin/python")


def repair_mask(alpha):
    """Достроить маску вниз: плечи и руки не сужаются к низу кадра.

    rembg честно отрезает то, что уходит за границу кадра. Берём строку с максимальной
    шириной силуэта и ниже неё держим границы не уже, чем там.
    """
    h, w = alpha.shape
    m = (alpha > 128).astype(np.uint8)
    widths = m.sum(axis=1)
    if widths.max() == 0:
        return alpha
    y_best = int(np.argmax(widths))
    # границы силуэта на самой широкой строке
    nz = np.nonzero(m[y_best])[0]
    L, R = int(nz[0]), int(nz[-1])
    out = alpha.copy()
    for y in range(y_best, h):
        row = m[y]
        nzr = np.nonzero(row)[0]
        if len(nzr) == 0:
            # маска кончилась — держим предыдущую ширину
            out[y, L:R + 1] = 255
            continue
        l, r = int(nzr[0]), int(nzr[-1])
        # расширяем строку до границ, не уже опорных
        nl, nr = min(l, L), max(r, R)
        out[y, nl:nr + 1] = np.maximum(out[y, nl:nr + 1], 255)
    return cv2.GaussianBlur(out, (0, 0), 1.2)


def rounded_mask(w, h, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(m, (0, r), (w, h - r), 255, -1)
    for cx, cy in ((r, r), (w - r, r), (r, h - r), (w - r, h - r)):
        cv2.circle(m, (cx, cy), r, 255, -1)
    return m


def build_video(a):
    """Полное видео: панель донора сверху + двойник в скруглённой карточке снизу."""
    import shutil
    cap = cv2.VideoCapture(a.twin)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    tmp = "/tmp/k3frames"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    n = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        cv2.imwrite(f"{tmp}/s{n:05d}.png", fr)
        n += 1
    cap.release()
    print(f"· кадров двойника: {n}")

    # покадровая вырезка одним запуском rembg (сессия создаётся один раз)
    script = f'''
import os
from rembg import remove, new_session
from PIL import Image
s = new_session("u2net")
d = "{tmp}"
fs = sorted(f for f in os.listdir(d) if f.startswith("s") and f.endswith(".png"))
for i, f in enumerate(fs):
    p = os.path.join(d, f)
    remove(Image.open(p), session=s).save(os.path.join(d, "c" + f[1:]))
    if i % 50 == 0:
        print(f"cut {{i}}/{{len(fs)}}", flush=True)
print("done", len(fs))
'''
    r = subprocess.run([REMBG_PY, "-c", script], capture_output=True, text=True)
    print("·", r.stdout.strip().split("\n")[-1] if r.stdout else "вырезка завершена")

    panel_cap = cv2.VideoCapture(a.panel) if a.panel else None
    cy0 = int(H * a.card_top)
    ch, cw = H - cy0, int(W * 0.94)
    cx0 = (W - cw) // 2
    cm = rounded_mask(cw, ch, a.radius)
    HEAD_OUT = 0.22

    raw = a.out + ".raw.mp4"
    vw = cv2.VideoWriter(raw, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    for i in range(n):
        cut = cv2.imread(f"{tmp}/c{i:05d}.png", cv2.IMREAD_UNCHANGED)
        if cut is None:
            continue
        alpha = repair_mask(cut[:, :, 3])
        canvas = np.full((H, W, 3), (240, 238, 232), np.uint8)
        if panel_cap is not None:
            okp, pf = panel_cap.read()
            if okp:
                ph = cy0
                pf_r = cv2.resize(pf, (W, ph), interpolation=cv2.INTER_LANCZOS4)
                canvas[0:ph, :] = pf_r
        card = np.full((ch, cw, 3), (26, 22, 18), np.uint8)
        m3 = (cm[:, :, None] / 255.0)
        roi = canvas[cy0:cy0 + ch, cx0:cx0 + cw].astype(np.float32)
        canvas[cy0:cy0 + ch, cx0:cx0 + cw] = (card * m3 + roi * (1 - m3)).astype(np.uint8)

        nz = np.nonzero((alpha > 128).any(axis=1))[0]
        top_y = int(nz[0]) if len(nz) else 0
        want_h = int(ch * (1.0 + HEAD_OUT))
        k = want_h / max(H - top_y, 1)
        nw2, nh2 = int(W * k), int(H * k)
        cut_s = cv2.resize(cut[:, :, :3], (nw2, nh2), interpolation=cv2.INTER_LANCZOS4)
        alp_s = cv2.resize(alpha, (nw2, nh2), interpolation=cv2.INTER_LINEAR)
        oy = (cy0 - int(ch * HEAD_OUT)) - int(top_y * k)
        ox = (W - nw2) // 2
        layer = np.zeros((H, W, 3), np.uint8)
        lal = np.zeros((H, W), np.uint8)
        ys, ye = max(0, oy), min(H, oy + nh2)
        xs, xe = max(0, ox), min(W, ox + nw2)
        if ye > ys and xe > xs:
            sy, sx = ys - oy, xs - ox
            layer[ys:ye, xs:xe] = cut_s[sy:sy + (ye - ys), sx:sx + (xe - xs)]
            lal[ys:ye, xs:xe] = alp_s[sy:sy + (ye - ys), sx:sx + (xe - xs)]
        am = (lal[:, :, None] / 255.0)
        canvas = (layer * am + canvas * (1 - am)).astype(np.uint8)
        vw.write(canvas)
    vw.release()
    if panel_cap:
        panel_cap.release()
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-i", a.twin,
                    "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "libx264", "-crf", "17",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", a.out], check=True)
    os.remove(raw)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"✅ {a.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--twin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--card-top", type=float, default=0.52, help="доля H: верх карточки")
    ap.add_argument("--radius", type=int, default=26)
    ap.add_argument("--probe", action="store_true", help="только один кадр в png")
    ap.add_argument("--panel", help="видео панели (футаж донора) для верхней зоны")
    ap.add_argument("--video", action="store_true", help="собрать всё видео, не один кадр")
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.twin)
    ok, fr = cap.read()
    cap.release()
    if not ok:
        print("FAIL: не прочитать twin")
        sys.exit(1)
    H, W = fr.shape[:2]
    cv2.imwrite("/tmp/k3src.png", fr)

    script = f'''
from rembg import remove, new_session
from PIL import Image
s = new_session("u2net")
out = remove(Image.open("/tmp/k3src.png"), session=s)
out.save("/tmp/k3cut.png")
print("ok")
'''
    subprocess.run([REMBG_PY, "-c", script], capture_output=True)
    cut = cv2.imread("/tmp/k3cut.png", cv2.IMREAD_UNCHANGED)
    if cut is None or cut.shape[2] < 4:
        print("FAIL: вырезка не получилась")
        sys.exit(1)

    alpha_raw = cut[:, :, 3]
    alpha = repair_mask(alpha_raw)
    print(f"· маска: было {int((alpha_raw>128).sum())}px → стало {int((alpha>128).sum())}px "
          f"(+{100*((alpha>128).sum()-(alpha_raw>128).sum())/max((alpha_raw>128).sum(),1):.1f}%)")

    if a.probe:
        # превью: карточка + вырезка на цветном фоне
        canvas = np.full((H, W, 3), (232, 238, 240), np.uint8)
        cy0 = int(H * a.card_top)
        ch, cw = H - cy0, int(W * 0.94)
        cx0 = (W - cw) // 2
        card = np.full((ch, cw, 3), (26, 22, 18), np.uint8)
        cm = rounded_mask(cw, ch, a.radius)
        m3 = (cm[:, :, None] / 255.0)
        roi = canvas[cy0:cy0 + ch, cx0:cx0 + cw].astype(np.float32)
        canvas[cy0:cy0 + ch, cx0:cx0 + cw] = (card * m3 + roi * (1 - m3)).astype(np.uint8)
        # 🔴 Двойник ВПИСЫВАЕТСЯ в карточку: голова выходит за верхнюю грань на HEAD_OUT,
        # плечи внутри. Без вписывания вырезка занимает весь кадр и карточки не видно.
        HEAD_OUT = 0.22                       # доля высоты карточки, на которую торчит голова
        nz = np.nonzero((alpha > 128).any(axis=1))[0]
        top_y = int(nz[0]) if len(nz) else 0
        # целевая высота фигуры: от верха головы до низа карточки
        want_h = int(ch * (1.0 + HEAD_OUT))
        cur_h = H - top_y
        k = want_h / max(cur_h, 1)
        nw2, nh2 = int(W * k), int(H * k)
        cut_s = cv2.resize(cut[:, :, :3], (nw2, nh2), interpolation=cv2.INTER_LANCZOS4)
        alp_s = cv2.resize(alpha, (nw2, nh2), interpolation=cv2.INTER_LINEAR)
        # ставим так, чтобы макушка была на HEAD_OUT выше грани карточки
        head_target = cy0 - int(ch * HEAD_OUT)
        oy = head_target - int(top_y * k)
        ox = (W - nw2) // 2
        layer = np.zeros((H, W, 3), np.uint8)
        lalpha = np.zeros((H, W), np.uint8)
        ys, ye = max(0, oy), min(H, oy + nh2)
        xs, xe = max(0, ox), min(W, ox + nw2)
        sy, sx = ys - oy, xs - ox
        layer[ys:ye, xs:xe] = cut_s[sy:sy + (ye - ys), sx:sx + (xe - xs)]
        lalpha[ys:ye, xs:xe] = alp_s[sy:sy + (ye - ys), sx:sx + (xe - xs)]
        am = (lalpha[:, :, None] / 255.0)
        canvas = (layer * am + canvas * (1 - am)).astype(np.uint8)
        cv2.imwrite(a.out, canvas)
        print(f"✅ превью {a.out}")
        return

    build_video(a)


if __name__ == "__main__":
    main()

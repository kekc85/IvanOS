#!/usr/bin/env python3
"""vfx-spike.py — спайк-тест Veo 3.1 для VFX-вставок в рилзы (кандидат v2.1).

Проверяет на НАШЕМ аватаре: похожесть лица + качество эффекта + IP-фильтр.
Механика теста: кадр аватара (t=3с) как first frame → image-to-video с промптом эффекта.
NB: боевая механика = video-to-video (Flow Insert, правка существующего клипа — губы
сохраняются, наблюдение автора); спайк отвечает на «держит ли Veo лицо автора»
самым дешёвым способом ДО интеграции.

Использование:
  python3 vfx-spike.py --list                          # какие veo-модели доступны ключу
  python3 vfx-spike.py --effect transparent-laptop --yes  # один тест-клип (~$0.75 Fast 5с)
  python3 vfx-spike.py --effect spider-suit --yes      # тест IP-фильтра
Ключ: env GEMINI_API_KEY, иначе X-Goog-Api-Key из ~/.claude.json.
Цена называется ДО генерации (правило cost-upfront), запуск только с --yes.
"""
import argparse, base64, json, os, pathlib, re, subprocess, sys, time, urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
AVATAR = pathlib.Path.home() / "<твоя-рабочая-папка-ролика>/public/avatar.mp4"
OUT = pathlib.Path.home() / "Desktop"

EFFECTS = {
    "transparent-laptop": "The man keeps talking naturally to camera. He waves his hand over the laptop in front of him and the laptop smoothly turns transparent like glass, glowing slightly. His face, hair and clothes stay exactly the same. Static camera, same lighting.",
    "iron-suit": "The man keeps talking naturally to camera. A high-tech red-and-gold armored suit materializes piece by piece over his body, assembling with glowing seams, then dissolves away. His face stays exactly the same and fully visible. Static camera, same lighting.",
    "spider-suit": "The man keeps talking naturally to camera. A red and blue superhero suit with web pattern appears on his body for two seconds, then vanishes. His face stays exactly the same. Static camera, same lighting.",
}
PRICE = {"fast": 0.15, "lite": 0.05}
DUR = 5

def key():
    k = os.environ.get("GEMINI_API_KEY")
    if k: return k
    t = pathlib.Path.home().joinpath(".claude.json").read_text()
    m = re.search(r'"X-Goog-Api-Key": "([^"]+)"', t)
    if not m: sys.exit("Нет ключа: задай GEMINI_API_KEY или X-Goog-Api-Key в ~/.claude.json")
    return m.group(1)

def req(url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r, timeout=120))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--effect", choices=list(EFFECTS))
    ap.add_argument("--model", default=None)
    ap.add_argument("--frame-t", type=float, default=3.0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    k = key()

    models = req(f"{API}/models?key={k}").get("models", [])
    veo = [m["name"] for m in models if "veo" in m["name"].lower()]
    if a.list or not a.effect:
        print("Veo-модели:", *(["  " + v for v in veo] or ["  НЕТ — у ключа нет доступа к Veo"]), sep="\n")
        return
    if not veo: sys.exit("У ключа нет Veo-моделей (включи Gemini API + billing в проекте ключа)")
    model = a.model or next((m for m in veo if "fast" in m), veo[0])
    tier = "fast" if "fast" in model else ("lite" if "lite" in model else "standard")
    cost = PRICE.get(tier, 0.40) * DUR
    print(f"Модель: {model} | {DUR}с | ЦЕНА ≈ ${cost:.2f}")
    if not a.yes: sys.exit("Платная генерация: перезапусти с --yes")

    frame = "/tmp/vfx_frame.png"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(a.frame_t), "-i", str(AVATAR),
                    "-frames:v", "1", frame], check=True)
    img_b64 = base64.b64encode(pathlib.Path(frame).read_bytes()).decode()

    op = req(f"{API}/{model}:predictLongRunning?key={k}", {
        "instances": [{"prompt": EFFECTS[a.effect],
                       "image": {"bytesBase64Encoded": img_b64, "mimeType": "image/png"}}],
        "parameters": {"aspectRatio": "9:16", "durationSeconds": DUR},
    })
    name = op.get("name") or sys.exit(f"Нет operation: {op}")
    print("Жду генерацию:", name)
    for _ in range(60):
        time.sleep(10)
        st = req(f"{API}/{name}?key={k}")
        if st.get("done"):
            resp = json.dumps(st.get("response", {}))
            uri = re.search(r'"(https://[^"]+\.mp4[^"]*)"', resp)
            b64 = re.search(r'"bytesBase64Encoded":\s*"([A-Za-z0-9+/=]{1000,})"', resp)
            out = OUT / f"vfx-spike-{a.effect}.mp4"
            if uri:
                u = uri.group(1)
                urllib.request.urlretrieve(u + ("" if "key=" in u else f"&key={k}"), out)
            elif b64:
                out.write_bytes(base64.b64decode(b64.group(1)))
            else:
                sys.exit(f"done, но видео не найдено: {resp[:400]}")
            print(f"ГОТОВО → {out}")
            return
    sys.exit("Таймаут 10 мин")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""broll-swap pipeline.

Takes a split-screen vertical reel (top = content, bottom = generic B-roll),
keeps the top, replaces the bottom with fresh free stock footage, renders a
finished MP4. The skill does NOT discover reels - the user supplies one.

Subcommands (Claude orchestrates the decision points between them):
  analyze  <url-or-file> [--split R]   download + probe + detect split line,
                                        export control frame + bottom samples
  stock    --query "..."  [--n 3]      fetch N free Pexels candidates ($0, no key)
  build    --manifest M --bottom CLIP  crop top + new bottom -> finished MP4

Pure stdlib + Pillow + ffmpeg/ffprobe/yt-dlp. No paid APIs, no signup.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")

GROWTH = os.path.expanduser("~/.business/growth/broll-swap")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def run(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def ffprobe_stream(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height",
               "-show_entries", "format=duration",
               "-of", "json", path]).stdout
    d = json.loads(out)
    w = int(d["streams"][0]["width"])
    h = int(d["streams"][0]["height"])
    dur = float(d["format"]["duration"])
    return w, h, dur


def even(n):
    n = int(round(n))
    return n - (n % 2)


def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return (s or "reel")[:40]


def kv(**pairs):
    for k, v in pairs.items():
        print(f"{k}={v}")


# --------------------------------------------------------------------------- #
# split-line auto-detection (pure PIL, no numpy)
# --------------------------------------------------------------------------- #
def detect_split_ratio(video, duration, workdir):
    """Return (ratio, confidence). A real split divider is a horizontal row
    that stays a strong edge across ALL sampled frames -> take per-row MIN edge
    strength across frames, argmax within the central band."""
    from PIL import Image

    sample_dir = os.path.join(workdir, "_split_samples")
    os.makedirs(sample_dir, exist_ok=True)
    n = 7
    times = [duration * (i + 1) / (n + 1) for i in range(n)]
    rows_per_frame = []
    W = 240
    height = None
    for i, t in enumerate(times):
        fp = os.path.join(sample_dir, f"s_{i}.jpg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-ss", f"{t:.2f}", "-i", video,
                        "-vframes", "1", "-vf", f"scale={W}:-1", fp],
                       check=True)
        if not os.path.exists(fp):
            continue
        im = Image.open(fp).convert("L")
        w, h = im.size
        height = h
        px = im.load()
        edges = [0.0] * h
        for y in range(h - 1):
            acc = 0
            for x in range(0, w, 3):          # stride 3 for speed
                acc += abs(px[x, y] - px[x, y + 1])
            edges[y] = acc / (w / 3)
        rows_per_frame.append(edges)

    if not rows_per_frame or height is None:
        return 0.5, 0.0

    band_lo, band_hi = int(height * 0.20), int(height * 0.80)
    best_y, best_min = band_lo, -1.0
    all_mins = []
    for y in range(band_lo, band_hi):
        m = min(f[y] for f in rows_per_frame if y < len(f))
        all_mins.append(m)
        if m > best_min:
            best_min, best_y = m, y
    median = sorted(all_mins)[len(all_mins) // 2] if all_mins else 1.0
    confidence = best_min / (median + 1e-6)
    ratio = best_y / height
    return ratio, confidence


def draw_control_frame(video, duration, split_y_full, H, out):
    """Mid frame with a red line drawn at the detected split row (full-res y)."""
    from PIL import Image, ImageDraw
    tmp = out + ".raw.jpg"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{duration/2:.2f}", "-i", video,
                    "-vframes", "1", tmp], check=True)
    im = Image.open(tmp).convert("RGB")
    w, h = im.size
    y = int(round(split_y_full / H * h))
    d = ImageDraw.Draw(im)
    d.rectangle([0, y - 3, w, y + 3], fill=(255, 0, 60))
    d.text((10, max(0, y - 24)), "SPLIT", fill=(255, 255, 255))
    im.save(out, quality=88)
    os.remove(tmp)


# --------------------------------------------------------------------------- #
# analyze
# --------------------------------------------------------------------------- #
def cmd_analyze(args):
    date = datetime.date.today().isoformat()
    src = args.input
    is_url = src.startswith("http")
    slug = slugify(os.path.splitext(os.path.basename(src))[0]) if not is_url else "reel"
    workdir = os.path.join(GROWTH, f"{date}-{slug}-work")
    os.makedirs(workdir, exist_ok=True)

    if is_url:
        cookies = os.path.expanduser("~/.config/yt-dlp/instagram-cookies.txt")
        cmd = ["yt-dlp", "--no-warnings", "-o",
               os.path.join(workdir, "src.%(ext)s"), src]
        if os.path.exists(cookies):
            cmd[1:1] = ["--cookies", cookies]
        run(cmd)
        cands = [f for f in os.listdir(workdir)
                 if f.startswith("src.") and f.split(".")[-1] in
                 ("mp4", "webm", "mkv", "mov")]
        if not cands:
            print("ERROR=download_failed (private or invalid URL?)", file=sys.stderr)
            sys.exit(1)
        video = os.path.join(workdir, cands[0])
        if not video.endswith(".mp4"):
            mp4 = os.path.join(workdir, "src.mp4")
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video,
                 "-c:v", "libx264", "-crf", "20", "-preset", "fast",
                 "-c:a", "aac", mp4])
            video = mp4
    else:
        video = os.path.abspath(os.path.expanduser(src))
        if not os.path.exists(video):
            print(f"ERROR=input_not_found {video}", file=sys.stderr)
            sys.exit(1)

    W, H, dur = ffprobe_stream(video)

    if args.split is not None:
        ratio, conf = float(args.split), 999.0
        method = "manual"
    else:
        ratio, conf = detect_split_ratio(video, dur, workdir)
        method = "auto"
        if conf < 1.8:                       # weak signal -> safe default
            ratio, method = 0.5, "fallback-0.5"

    split_y = even(H * ratio)
    top_h = split_y
    bottom_h = even(H - top_h)

    control = os.path.join(workdir, "control-split.jpg")
    draw_control_frame(video, dur, split_y, H, control)

    bottom_frames = []
    for i in range(4):
        t = dur * (i + 1) / 5
        fp = os.path.join(workdir, f"bottom-sample-{i+1}.jpg")
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-ss", f"{t:.2f}", "-i", video, "-vframes", "1",
             "-vf", f"crop={W}:{bottom_h}:0:{top_h}", fp])
        bottom_frames.append(fp)

    manifest = {
        "input": src, "video": video, "workdir": workdir,
        "width": W, "height": H, "duration": round(dur, 3),
        "split_ratio": round(ratio, 4), "split_method": method,
        "split_confidence": round(conf, 2),
        "split_y": split_y, "top_h": top_h, "bottom_h": bottom_h,
        "control_frame": control, "bottom_frames": bottom_frames,
        "date": date, "slug": slug,
    }
    mpath = os.path.join(workdir, "manifest.json")
    with open(mpath, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    kv(MANIFEST=mpath, VIDEO=video, WIDTH=W, HEIGHT=H, DURATION=round(dur, 2),
       SPLIT_RATIO=round(ratio, 4), SPLIT_METHOD=method,
       SPLIT_CONFIDENCE=round(conf, 2), TOP_H=top_h, BOTTOM_H=bottom_h,
       CONTROL_FRAME=control,
       BOTTOM_FRAMES=";".join(bottom_frames),
       STATUS="ready_for_description")


# --------------------------------------------------------------------------- #
# stock (free Pexels, public scrape, no key)
# --------------------------------------------------------------------------- #
def pexels_links(query):
    url = ("https://www.pexels.com/search/videos/"
           + urllib.parse.quote(query) + "/")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    raw = re.findall(r"https://videos\.pexels\.com/video-files/[^\"\\ ]+?\.mp4", html)
    # group by clip id, prefer ~hd 1280-1920 rendition per clip
    by_id = {}
    for link in raw:
        m = re.search(r"video-files/(\d+)/", link)
        if not m:
            continue
        cid = m.group(1)
        by_id.setdefault(cid, []).append(link)

    def score(link):
        wm = re.search(r"_(\d{3,4})_", link)
        wv = int(wm.group(1)) if wm else 0
        return -abs(wv - 1280) if wv else -9999

    chosen = []
    for cid, links in by_id.items():
        best = sorted(links, key=score, reverse=True)[0]
        chosen.append((cid, best))
    return chosen


def cmd_stock(args):
    outdir = args.out or os.path.join(GROWTH, "_stock-candidates")
    os.makedirs(outdir, exist_ok=True)
    try:
        cands = pexels_links(args.query)
    except Exception as e:                                   # noqa
        print(f"ERROR=pexels_scrape_failed {type(e).__name__}: {e}",
              file=sys.stderr)
        sys.exit(2)
    if not cands:
        print("ERROR=no_stock_results (try a simpler EN query)", file=sys.stderr)
        sys.exit(3)

    saved = []
    for i, (cid, link) in enumerate(cands[: args.n]):
        mp4 = os.path.join(outdir, f"cand-{i+1}-{cid}.mp4")
        req = urllib.request.Request(link, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r, open(mp4, "wb") as f:
            f.write(r.read())
        thumb = os.path.join(outdir, f"cand-{i+1}-{cid}.jpg")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", mp4, "-vframes", "1",
                        "-vf", "scale=480:-1", thumb], check=True)
        w, h, dur = ffprobe_stream(mp4)
        saved.append((mp4, thumb, w, h, round(dur, 1), link))

    print(f"QUERY={args.query}")
    for i, (mp4, thumb, w, h, dur, link) in enumerate(saved):
        print(f"CAND_{i+1}_VIDEO={mp4}")
        print(f"CAND_{i+1}_THUMB={thumb}")
        print(f"CAND_{i+1}_SIZE={w}x{h} dur={dur}s")
        print(f"CAND_{i+1}_SOURCE={link}")
    print("STATUS=candidates_ready  # Claude: read thumbs, pick best, pass to build --bottom")


# --------------------------------------------------------------------------- #
# build (crop top + new bottom -> finished MP4)
# --------------------------------------------------------------------------- #
def cmd_build(args):
    with open(args.manifest) as f:
        m = json.load(f)
    W, H = m["width"], m["height"]
    top_h, bottom_h = m["top_h"], m["bottom_h"]
    dur = m["duration"]
    video = m["video"]
    bottom = os.path.abspath(os.path.expanduser(args.bottom))
    if not os.path.exists(bottom):
        print(f"ERROR=bottom_not_found {bottom}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(GROWTH, exist_ok=True)
    out = args.out or os.path.join(GROWTH, f"{m['date']}-{m['slug']}-swapped.mp4")

    fc = (
        f"[0:v]crop={W}:{top_h}:0:0,setsar=1[top];"
        f"[1:v]scale={W}:{bottom_h}:force_original_aspect_ratio=increase,"
        f"crop={W}:{bottom_h},setsar=1[bot];"
        f"[top][bot]vstack=inputs=2[v]"
    )
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-i", video,
           "-stream_loop", "-1", "-i", bottom,
           "-filter_complex", fc,
           "-map", "[v]", "-map", "0:a?",
           "-t", f"{dur}",
           "-c:v", "libx264", "-crf", "20", "-preset", "medium",
           "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k",
           "-movflags", "+faststart", out]
    run(cmd)

    sidecar = os.path.splitext(out)[0] + ".txt"
    with open(sidecar, "w") as f:
        f.write("broll-swap output\n")
        f.write(f"source reel: {m['input']}\n")
        f.write(f"frame: {W}x{H}  split_y={m['split_y']} "
                f"({m['split_method']}, conf={m['split_confidence']})\n")
        f.write(f"top kept: {W}x{top_h}   new bottom: {W}x{bottom_h}\n")
        f.write(f"bottom source: {bottom}\n")
        if args.bottom_desc:
            f.write(f"bottom description: {args.bottom_desc}\n")
        if args.bottom_source_url:
            f.write(f"bottom stock url: {args.bottom_source_url}\n")
        f.write("license: Pexels License (free, no attribution required) "
                "if sourced via stock; verify if Higgsfield-generated\n")

    kv(FINAL=out, SIDECAR=sidecar, STATUS="done")


# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(prog="swap.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze")
    a.add_argument("input")
    a.add_argument("--split", type=float, default=None,
                   help="manual split ratio 0..1 (top fraction), e.g. 0.5")
    a.set_defaults(func=cmd_analyze)

    s = sub.add_parser("stock")
    s.add_argument("--query", required=True)
    s.add_argument("--n", type=int, default=3)
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_stock)

    b = sub.add_parser("build")
    b.add_argument("--manifest", required=True)
    b.add_argument("--bottom", required=True)
    b.add_argument("--out", default=None)
    b.add_argument("--bottom-desc", default=None)
    b.add_argument("--bottom-source-url", default=None)
    b.set_defaults(func=cmd_build)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
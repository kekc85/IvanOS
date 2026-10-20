#!/usr/bin/env python3
"""Плотная речь без воздуха: energy-VAD вырезает ВСЕ паузы, склейка встык + ускорение 1.15x.
Убирает дыхание/чавканье/паузы между словами. автор: "говорю-говорю-говорю без выдоха".
Использование: python3 vad_tight.py <video.mp4> <out_dir> <tag> [speed=1.15]"""
import sys, os, wave, subprocess
import numpy as np

WIN = 0.02          # окно анализа энергии
HANGOVER = 0.16     # режем паузы длиннее, короткий ритм речи оставляем (как оригинал)
PAD = 0.03          # запас вокруг речи
MIN_SEG = 0.05      # минимальная длина речевого куска
HEAD_TRIM = 0.02

def run(c): subprocess.run(c, check=True)

def speech_intervals(wav):
    w = wave.open(wav); sr = w.getframerate()
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    win = int(sr*WIN)
    n = (len(a)-win)//win
    rms = np.array([np.sqrt(np.mean(a[i*win:i*win+win]**2)+1) for i in range(n)])
    db = 20*np.log10(rms/32768+1e-9)
    # адаптивный порог: гистограмма db бимодальна (фон-пауза + речь),
    # порог = долина между модами (иначе шумный фон комнаты проходит как речь)
    noise = np.percentile(db, 20)   # мода фона (паузы у DJI-микрофона ~-43dB, не тишина)
    peak = np.percentile(db, 90)    # мода речи
    thr = noise + (peak-noise)*0.42
    speech = db > thr
    # hangover: закрыть короткие дыры внутри речи
    hg = int(HANGOVER/WIN)
    i = 0
    while i < len(speech):
        if not speech[i]:
            j = i
            while j < len(speech) and not speech[j]: j += 1
            if (j-i) <= hg and i > 0 and j < len(speech):
                speech[i:j] = True
            i = j
        else: i += 1
    # интервалы речи с pad
    ivs = []
    i = 0
    while i < len(speech):
        if speech[i]:
            j = i
            while j < len(speech) and speech[j]: j += 1
            t0 = max(0, i*WIN - PAD); t1 = j*WIN + PAD
            if t1-t0 >= MIN_SEG: ivs.append([t0, t1])
            i = j
        else: i += 1
    # merge пересекающихся после pad
    merged = []
    for iv in ivs:
        if merged and iv[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], iv[1])
        else: merged.append(iv)
    return merged

def build(video, outdir, tag, speed=1.15):
    os.makedirs(outdir, exist_ok=True)
    wav = os.path.join(outdir, f"{tag}_16k.wav")
    run(["ffmpeg","-y","-v","error","-i",video,"-ar","16000","-ac","1","-c:a","pcm_s16le",wav])
    ivs = speech_intervals(wav)
    total_speech = sum(b-a for a,b in ivs)
    # ОДИН проход: select вырезает все интервалы речи, видео+аудио из одного источника (синхрон гарантирован)
    sel = "+".join(f"between(t,{t0:.3f},{t1:.3f})" for t0,t1 in ivs)
    vf = f"select='{sel}',setpts=N/FRAME_RATE/TB,scale=1080:1920:flags=lanczos,setsar=1,fps=30,setpts=PTS/{speed}"
    af = f"aselect='{sel}',asetpts=N/SR/TB,aresample=48000,atempo={speed}"
    out = os.path.join(outdir, f"{tag}_tight.mp4")
    run(["ffmpeg","-y","-v","error","-i",video,"-vf",vf,"-af",af,
        "-c:v","libx264","-pix_fmt","yuv420p","-crf","18","-preset","medium",
        "-c:a","aac","-b:a","192k","-ar","48000",out])
    dv = float(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=duration","-of","default=nk=1:nw=1",out],capture_output=True,text=True).stdout.strip())
    da = float(subprocess.run(["ffprobe","-v","error","-select_streams","a:0","-show_entries","stream=duration","-of","default=nk=1:nw=1",out],capture_output=True,text=True).stdout.strip())
    print(f"{tag}: {len(ivs)} кусков, {total_speech:.1f}s речи -> видео {dv:.1f}s / аудио {da:.1f}s (синхрон Δ{abs(dv-da)*1000:.0f}мс)")
    return out

if __name__ == "__main__":
    video, outdir, tag = sys.argv[1], sys.argv[2], sys.argv[3]
    speed = float(sys.argv[4]) if len(sys.argv)>4 else 1.15
    build(video, outdir, tag, speed)

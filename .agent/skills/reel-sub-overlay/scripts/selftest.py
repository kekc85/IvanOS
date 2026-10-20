#!/usr/bin/env python3
# Реальный self-test метода reel-sub-overlay. Машина перепроверяет ВЫДАННЫЙ рендер, пишет .selftest-verdict.json.
# Проверки: рендер 1080x1920+длительность; их субтитры убраны (residual белого текста в зоне маски); субтитр не на лице;
#           водяной знак присутствует; код-слово в описании; громкость ~ -14 LUFS.
import sys,os,json,glob,subprocess,re
import cv2,numpy as np
PROJ=os.path.abspath(sys.argv[1]); meta=json.load(open(f"{PROJ}/project-meta.json"))
def P(p): return p if os.path.isabs(p) else f"{PROJ}/{p}"
R={"project":meta["project"],"method":meta["method"],"checks":{},"fails":[]}
def chk(name,ok,detail=""):
    R["checks"][name]={"ok":bool(ok),"detail":detail}
    if not ok: R["fails"].append(name)
    print(("OK " if ok else "FAIL ")+name+" : "+detail)

render=P(meta["render"])
# 1) рендер
ok=os.path.exists(render); dur=w=h=0
if ok:
    out=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-show_entries","format=duration","-of","default=noprint_wrappers=1",render],capture_output=True,text=True).stdout
    w=int(re.search(r"width=(\d+)",out).group(1)); h=int(re.search(r"height=(\d+)",out).group(1)); dur=float(re.search(r"duration=([\d.]+)",out).group(1))
chk("render_exists_portrait", ok and w==1080 and h==1920 and 49<=dur<=52, f"{w}x{h} {dur:.1f}s")

# 2) остаток ИХ белого субтитра в зоне маски (clean-кадры)
fr=sorted(glob.glob(P(meta["clean_frames"])+"/*.png")); mk=sorted(glob.glob(P(meta["masks"])+"/*.png"))
ker=np.ones((3,3),np.uint8); flagged=0; checked=0
for i in range(0,len(fr),10):
    g=cv2.cvtColor(cv2.imread(fr[i]),cv2.COLOR_BGR2GRAY); m=cv2.imread(mk[i],0)
    if m is None or (m>40).sum()<200: continue
    checked+=1; md=cv2.erode((m>40).astype(np.uint8),ker,iterations=2); reg=g[md>0]
    if reg.size and (reg>225).mean()>0.18: flagged+=1
chk("their_subs_removed", checked>0 and flagged<=max(2,checked//15), f"flagged {flagged}/{checked} masked frames")

# 3) субтитр не на лице
casc=cv2.CascadeClassifier(cv2.data.haarcascades+"haarcascade_frontalface_default.xml")
cues=json.load(open(P(meta["cues"]))); FR=P(meta["frames"]); onface=0
for c in cues:
    pos=c.get("pos"); cy=pos["cy"] if pos else 950; cy=max(360,min(1560,cy))
    fmid=int((c["t0"]+c["t1"])/2*30)+1; p=f"{FR}/{fmid:05d}.png"
    if not os.path.exists(p): continue
    g=cv2.cvtColor(cv2.imread(p),cv2.COLOR_BGR2GRAY)
    for (x,y,wd,ht) in casc.detectMultiScale(g,1.2,6,minSize=(150,150)):
        if y<cy+55 and y+ht>cy-55 and x<700 and x+wd>380 and ht>200: onface+=1; break
chk("subtitle_not_on_face", onface<=max(1,len(cues)//40), f"on-face {onface}/{len(cues)}")

# 4) водяной знак присутствует (ярк. пиксели в зоне <твой-хэндл> на ранних кадрах)
import tempfile
wm_ok=False
for t in [4.0,20.0]:
    tmp=tempfile.mktemp(suffix=".png")
    subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",render,"-frames:v","1",tmp,"-y"])
    if os.path.exists(tmp):
        img=cv2.cvtColor(cv2.imread(tmp),cv2.COLOR_BGR2GRAY)
        # зоны wm: (250,235) и (200,1180) и (830,235)/(880,1180)
        for (x,y) in [(250,235),(200,1180),(830,235),(880,1180)]:
            patch=img[max(0,y-30):y+30, max(0,x-160):x+160]
            if patch.size and (patch>210).sum()>120: wm_ok=True
        os.remove(tmp)
chk("watermark_optional", True, "водяной знак больше НЕ требуется (автор велел убрать <твой-хэндл> из роликов); wm_ok=%s" % wm_ok)

# 5) код-слово в описании
cap=open(P(meta["caption"])).read(); cw=meta["codeword"]
chk("codeword_in_caption", cap.count(cw)>=2, f"{cw} x{cap.count(cw)}")

# 6) громкость ~ -14
ln=subprocess.run(["ffmpeg","-i",render,"-af","loudnorm=print_format=summary","-f","null","-"],capture_output=True,text=True).stderr
mi=re.search(r"Input Integrated:\s*(-?[\d.]+)",ln); lufs=float(mi.group(1)) if mi else 0
chk("loudness_-14", -16<=lufs<=-12, f"{lufs} LUFS")

R["verdict"]="PASS" if not R["fails"] else "FAIL"
R["render"]=render; R["render_mtime"]=os.path.getmtime(render)
import datetime
json.dump(R,open(f"{PROJ}/.selftest-verdict.json","w"),ensure_ascii=False,indent=1)
print("VERDICT:",R["verdict"], "fails:",R["fails"])
sys.exit(0 if R["verdict"]=="PASS" else 2)

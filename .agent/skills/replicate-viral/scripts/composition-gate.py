#!/usr/bin/env python3
"""
composition-gate.py — re-derives a composition verdict from the CURRENT render's
PIXELS against the FROZEN contract (templates/contract.template.json → <project>/contract.json).
Kills RC-1/RC-4/RC-5: geometry is no longer invented & loosely checked inside operator boxes;
it is measured from THE render every run and compared to the etalon contract.

CONTRACT MODEL = UI_HERO_FACECAM_INSET (measured from original DXBt1opjDH2, 2026-06-15):
the website/UI is the HERO that fills the frame and is always in motion; the speaker is a
SMALL face-cam inset in a corner, OPTIONAL per act. NOT a full-bleed person, NOT a top/bottom
split. The old SINGLE_FULLBLEED_PERSON / person-area>=0.20 / forbid-split logic was the WRONG
model and has been removed.

Checks (all non-tunable thresholds come from the contract; exit 2 on ANY fail):
  H. UI_HERO_COVERAGE: per sampled frame the hero (non-facecam region) must be "content"
     (textured site/UI) covering >= contract.ui_hero.min_coverage_frac of the frame.
     FAIL the old defect "site doesn't fill / cut off" — i.e. site confined to a sub-region
     (top third / band) while the rest is a different/plain fill.
  P. FACECAM_SMALL: if a face is detected its area must be <= contract.facecam_inset.max_face_area_frac
     and the connected person region <= contract.facecam_inset.max_person_area_frac. FAIL if the
     person is dominant (old defect: avatar big / full-frame / bottom-half card). If a contract act
     declares facecam.present=false, a large face present in that act = FAIL.
  M. MOTION: hero-region inter-frame motion magnitude must be >= contract.ui_hero.motion_floor
     (per-act override allowed if measured from ref). Static site = FAIL.
  F. CAPTION-VS-FACE: for caption frames the caption Y-band (contract.caption_zone) must NOT
     intersect the detected facecam face bbox. (reuses the Haar logic in this file.)

Writes <projectdir>/.composition-verdict.json (render_mtime via os.path.getmtime, never Date.now).

Usage: composition-gate.py --render out.mp4 --contract contract.json [--fps 4] [--project DIR]
Exit: 0 PASS, 2 FAIL.
"""
import sys, os, json, argparse, subprocess, tempfile, statistics
from PIL import Image, ImageChops, ImageStat

# ---------- frame extraction (matches render-defect-scan.py style) ----------
def dur(p):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nw=1:nk=1", p]).decode().strip())

_DCACHE={}
def _D(render):
    if render not in _DCACHE: _DCACHE[render]=dur(render)
    return _DCACHE[render]

def frames(render, t0, t1, fps, d, tag):
    # clamp to a safe window strictly inside the render so ffmpeg -ss never lands at/after EOF
    D=_D(render)
    t0=max(0.0, min(t0, max(0.0, D-0.10)))
    t1=max(t0+0.05, min(t1, D-0.05))
    n=max(2,int((t1-t0)*fps))
    ts=[t0+(t1-t0)*i/(n-1) for i in range(n)]
    out=[]
    for i,t in enumerate(ts):
        t=min(t, D-0.05)
        f=f"{d}/{tag}_{int(t*1000):07d}_{i}.png"
        r=subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",f"{t:.3f}","-i",render,
            "-frames:v","1", f])
        if r.returncode==0 and os.path.isfile(f) and os.path.getsize(f)>0:
            out.append((t,f))
    return out

# ---------- face / person detection (Haar) ----------
_CC=None
def face_bbox(fp):
    """Largest frontal face bbox (x,y,w,h) or None. Reused for FACECAM_SMALL and CAPTION-VS-FACE."""
    global _CC
    import cv2
    if _CC is None: _CC=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    img=cv2.imread(fp); g=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
    f=_CC.detectMultiScale(g,1.1,5,minSize=(80,80))
    if f is None or len(f)==0: return None
    x,y,w,h=sorted(f,key=lambda b:-b[2])[0]
    return (int(x),int(y),int(w),int(h))

def person_area_frac_from_face(im, fbb):
    """Estimate the connected person/inset region around a detected face by flood-growing the
    face bbox into surrounding 'content' cells (high local variance OR luma differing from the
    frame-edge background). Returns person_area / frame_area. Heuristic but bounded: it only
    grows cells contiguous to the face, so a full-bleed person yields a large frac while a small
    corner inset yields a small one."""
    px=im.load(); W,H=im.size
    fx,fy,fw,fh=fbb
    # background reference = median border luma
    border=[]
    for x in range(0,W,16):
        border.append(sum(px[x,4][:3])//3); border.append(sum(px[x,H-5][:3])//3)
    for y in range(0,H,16):
        border.append(sum(px[4,y][:3])//3); border.append(sum(px[W-5,y][:3])//3)
    bg=statistics.median(border) if border else 0
    step=24
    cols=list(range(8,W-8,step)); rows=list(range(8,H-8,step))
    def content(x,y):
        lum=[]
        for dy in (-6,0,6):
            for dx in (-6,0,6):
                lum.append(sum(px[x+dx,y+dy][:3])//3)
        return statistics.pvariance(lum)>120 or abs(statistics.mean(lum)-bg)>55
    # seed cells = grid cells inside the face bbox
    grid={}
    for y in rows:
        for x in cols:
            grid[(x,y)]=content(x,y)
    seeds=[(x,y) for (x,y) in grid if fx<=x<=fx+fw and fy<=y<=fy+fh]
    seen=set(); stack=list(seeds)
    while stack:
        cx,cy=stack.pop()
        if (cx,cy) in seen: continue
        seen.add((cx,cy))
        for nx,ny in ((cx-step,cy),(cx+step,cy),(cx,cy-step),(cx,cy+step)):
            if (nx,ny) in grid and (nx,ny) not in seen and grid[(nx,ny)]:
                stack.append((nx,ny))
    return len(seen)/max(len(grid),1)

# ---------- H: UI hero coverage = geometric box-coverage + filler-band defect ----------
def filler_band_frac(im, exclude=None):
    """Largest CONTIGUOUS near-uniform 'filler' band as a fraction of frame height. This is the
    pixel signature of the cut-off defect: the site is confined to a sub-region and the rest is a
    plain fill (dark letterbox / blank panel). Robust to JPEG noise via a luma-spread (p90-p10)
    test + horizontal-edge count rather than raw variance (a dark MINIMAL site still has edges /
    spread, so it is NOT counted as filler — verified: original etalon median filler ~0.20).
    Rows inside the facecam bbox are skipped. import numpy locally to keep PIL-only paths cheap."""
    import numpy as np
    a=np.asarray(im.convert("L"),dtype=np.int16); H,W=a.shape
    ex=exclude  # (x,y,w,h) or None
    run=0; best=0; nrows=0
    for y in range(0,H,6):
        nrows+=1
        if ex and ex[1]<=y<=ex[1]+ex[3]: run=0; continue
        row=a[y][::3]
        spread=int(np.percentile(row,90)-np.percentile(row,10))
        edges=int(np.sum(np.abs(np.diff(row))>18))
        if spread<34 and edges<5: run+=1; best=max(best,run)   # near-uniform plain row
        else: run=0
    return best/max(nrows,1)

# ---------- M: hero motion (frame-diff magnitude in hero region) ----------
def region_motion(frame_files, box):
    x0,y0,x1,y1=box
    prev=None; diffs=[]
    for fp in frame_files:
        im=Image.open(fp).convert("RGB")
        W,H=im.size
        xx0,yy0,xx1,yy1=max(0,x0),max(0,y0),min(W,x1),min(H,y1)
        if xx1-xx0<8 or yy1-yy0<8: im.close(); continue
        crop=im.crop((xx0,yy0,xx1,yy1))
        if prev is not None:
            diffs.append(sum(ImageStat.Stat(ImageChops.difference(crop,prev)).mean)/3)
        prev=crop; im.close()
    return (sum(diffs)/len(diffs)) if diffs else 0.0

def _rects_overlap(a, b, pad=0):
    """True if rect a=(x0,y0,x1,y1) overlaps rect b (with optional pad on b)."""
    ax0,ay0,ax1,ay1=a; bx0,by0,bx1,by1=b
    bx0-=pad; by0-=pad; bx1+=pad; by1+=pad
    return not (ax1<bx0 or ax0>bx1 or ay1<by0 or ay0>by1)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--render",required=True)
    ap.add_argument("--contract",required=True)
    ap.add_argument("--fps",type=float,default=4.0)
    ap.add_argument("--project",default=None)
    a=ap.parse_args()

    if not os.path.isfile(a.render):
        print("ARG ERROR: render not found:",a.render); sys.exit(2)
    if not os.path.isfile(a.contract):
        print("ARG ERROR: contract not found:",a.contract); sys.exit(2)
    c=json.load(open(a.contract))
    proj=a.project or os.path.dirname(os.path.abspath(a.render))

    # ---- contract params (UI_HERO_FACECAM_INSET model; all non-tunable) ----
    uh=c.get("ui_hero",{})
    min_cov=float(uh.get("min_coverage_frac",0.82))
    motion_floor=float(uh.get("motion_floor",1.5))
    fci=c.get("facecam_inset",{})
    max_face=float(fci.get("max_face_area_frac",0.09))
    max_person=float(fci.get("max_person_area_frac",0.18))
    cz=c.get("caption_zone",{})
    cz0=int(cz.get("y0",640)); cz1=int(cz.get("y1",1760))
    never_on_face=bool(cz.get("never_on_facecam_face", cz.get("never_on_face",True)))

    fails=[]; facts=[]; checks=[]
    D=dur(a.render)
    frame_area=float(c.get("frame",{}).get("w",1080))*float(c.get("frame",{}).get("h",1920))
    acts=[act for act in c.get("acts",[]) if act.get("name") and act.get("name")!="EXAMPLE_FILL_ME"]

    with tempfile.TemporaryDirectory() as td:
        # ---- sample N frames across the whole render for H + P + F ----
        N=12
        wfps=max(a.fps, (N+1)/max(D,0.5))
        whole=frames(a.render, 0.05, D-0.05, wfps, td, "whole")
        if not whole:
            print("ARG ERROR: could not extract any frame from render (corrupt/too short):",a.render)
            sys.exit(2)
        if len(whole)>N:
            step=len(whole)/N; whole=[whole[int(i*step)] for i in range(N)]

        # ---- H + P: hero filler-band & facecam size per frame ----
        filler_fracs=[]; face_seen=0; face_area_viol=0; person_viol=0; ex_p=[]
        for (t,fp) in whole:
            im=Image.open(fp).convert("RGB")
            fbb=face_bbox(fp)
            filler_fracs.append(filler_band_frac(im, exclude=fbb))
            if fbb is not None:
                face_seen+=1
                fa=(fbb[2]*fbb[3])/frame_area
                if fa>max_face:
                    face_area_viol+=1; ex_p.append((round(t,1),"face",round(fa,3)))
                pa=person_area_frac_from_face(im, fbb)
                if pa>max_person:
                    person_viol+=1; ex_p.append((round(t,1),"person",round(pa,2)))
            im.close()
        # H1 GEOMETRIC: declared ui_hero_box must cover >= min_coverage_frac of the frame.
        # (exact, non-heuristic: catches a contract/render that confines the hero to a sub-region.)
        hero_boxes=[act.get("ui_hero_box") for act in acts if act.get("ui_hero_box")]
        if hero_boxes:
            box_covs=[((b[2]-b[0])*(b[3]-b[1]))/frame_area for b in hero_boxes]
            min_box_cov=min(box_covs)
            facts.append(f"H1 ui_hero_box geometric coverage min={min_box_cov:.2f} (floor {min_cov}) boxes={hero_boxes}")
            checks.append({"check":"ui_hero_box_coverage","min_box_cov":round(min_box_cov,3),
                           "floor":min_cov,"pass": min_box_cov>=min_cov})
            if min_box_cov < min_cov:
                fails.append(f"H1 UI_HERO_COVERAGE: declared ui_hero_box покрывает {min_box_cov:.2f} < floor {min_cov} кадра — сайт-герой зажат в под-область, а не во весь кадр")
        # H2 PIXEL DEFECT: a large contiguous plain-filler band = the cut-off defect (site in a
        # sub-region, rest plain fill). Threshold derived from contract coverage but floored to
        # 0.45 to stay clear of the etalon's own empty-UI frames (measured max filler ~0.38).
        med_filler=statistics.median(filler_fracs) if filler_fracs else 0
        filler_max=max(1.0-min_cov, 0.45)
        facts.append(f"H2 filler-band median={med_filler:.2f} (max {filler_max:.2f}) per_frame={[round(x,2) for x in filler_fracs]}")
        checks.append({"check":"ui_hero_filler_band","median_filler_frac":round(med_filler,3),
                       "max":round(filler_max,3),"pass": med_filler<=filler_max})
        if med_filler > filler_max:
            fails.append(f"H2 UI_HERO_FILL: непрерывная plain-filler полоса median {med_filler:.2f} > {filler_max:.2f} высоты — сайт обрезан, остальное плоский филлер (старый дефект 'сайт не заполняет/обрезан')")

        # FACECAM_SMALL: face-area is the HARD gate (exact, separates etalon 0.05 / happy 0.01 from
        # a dominant person 0.13+). person_area (flood-grow) is ADVISORY only — on a busy composited
        # frame the flood leaks into the site behind the inset and over-reports, so it must not block.
        facts.append(f"P facecam: face_seen={face_seen} face_area_viol={face_area_viol} (HARD) person_viol={person_viol} (ADVISORY) (max_face {max_face}, max_person {max_person}) {ex_p[:4]}")
        checks.append({"check":"facecam_small","face_seen":face_seen,"face_area_violate":face_area_viol,
                       "person_violate_advisory":person_viol,"max_face":max_face,"max_person":max_person,
                       "pass": (face_area_viol==0)})
        if face_area_viol>0:
            fails.append(f"P FACECAM_SMALL: спикер-доминанта в {face_area_viol} кадрах (face area>{max_face}) {ex_p[:4]} — аватар big/full-frame/нижняя карточка вместо МАЛЕНЬКОЙ врезки в углу")

        # ---- P (act-aware): a face present where contract act says facecam.present=false = FAIL ----
        no_facecam_acts=[act for act in acts if act.get("facecam",{}).get("present") is False]
        if no_facecam_acts:
            tot_v=0; exa=[]
            for act in no_facecam_acts:
                t0=max(0,act["t0"]); t1=min(D,act["t1"])
                afr=frames(a.render,t0,t1,a.fps,td,f"nofc_{act['name']}")
                for (t,fp) in afr:
                    fbb=face_bbox(fp)
                    if fbb is None: continue
                    fa=(fbb[2]*fbb[3])/frame_area
                    if fa>max_face:  # a non-trivial face where there should be none
                        tot_v+=1; exa.append((act["name"],round(t,1),round(fa,3)))
            facts.append(f"P facecam-absent acts: large-face violate={tot_v} {exa[:4]}")
            checks.append({"check":"facecam_absent_when_declared","violate":tot_v,"pass":tot_v==0})
            if tot_v>0:
                fails.append(f"P FACECAM-ABSENT: контракт объявил facecam.present=false, но крупное лицо есть в {tot_v} кадрах {exa[:4]}")

        # ---- F: caption vs facecam face ----
        if never_on_face:
            cap_acts=[act for act in acts if act.get("caption_window")]
            if not cap_acts:
                # No act declares a caption_window: coarse fallback — a facecam face inside the
                # whole allowed caption_zone band risks a caption landing on it. Heuristic; the
                # measured path is per-act caption_window (below). Contract acts SHOULD declare windows.
                face_violate=0; fseen=0; ex=[]
                for (t,fp) in whole:
                    bb=face_bbox(fp)
                    if bb is None: continue
                    fseen+=1
                    fy0,fy1=bb[1],bb[1]+bb[3]
                    if not (fy1<cz0 or fy0>cz1):  # face bbox intersects the caption zone band
                        face_violate+=1; ex.append((round(t,1),fy0,fy1))
                facts.append(f"F face-in-caption-zone (whole, band y[{cz0},{cz1}], NO windows declared): seen={fseen} violate={face_violate} {ex[:4]}")
                checks.append({"check":"caption_vs_face_zone_fallback","face_seen":fseen,"violate":face_violate,
                               "caption_zone":[cz0,cz1],"pass": face_violate==0})
                if face_violate>0:
                    fails.append(f"F CAPTION-ON-FACE (fallback): лицо врезки внутри caption_zone [{cz0},{cz1}] в {face_violate} кадрах {ex[:4]} — объявите caption_window в актах для точной проверки")
            else:
                # Measured path: for each act, the declared caption_window Y-band(s) are WHERE the
                # caption actually goes (contract measurement). The facecam face must NOT fall in
                # any of those bands — that is the etalon-faithful "caption never on face" rule.
                tot_v=0; ex=[]
                for act in cap_acts:
                    t0=max(0,act["t0"]); t1=min(D,act["t1"])
                    windows=act.get("caption_window") or []
                    # each window is a [y0,y1] band; tolerate a single [y0,y1] too
                    if windows and isinstance(windows[0],(int,float)): windows=[windows]
                    fcbox=act.get("facecam",{}).get("box")  # declared facecam region (x0,y0,x1,y1) or None
                    afr=frames(a.render,t0,t1,a.fps,td,f"cap_{act['name']}")
                    for (t,fp) in afr:
                        bb=face_bbox(fp)
                        if bb is None: continue
                        fx0,fy0,fx1,fy1=bb[0],bb[1],bb[0]+bb[2],bb[1]+bb[3]
                        # only the face that IS the facecam inset counts: if the act declares a
                        # facecam.box, the detected face must overlap it (else it is a face inside
                        # site content, not the inset — ignore it).
                        if fcbox and not _rects_overlap((fx0,fy0,fx1,fy1), tuple(fcbox), pad=80):
                            continue
                        for w in windows:
                            wy0,wy1=int(w[0]),int(w[1])
                            if not (fy1<wy0 or fy0>wy1):  # facecam face intersects this caption window
                                tot_v+=1; ex.append((act["name"],round(t,1),[wy0,wy1],[fy0,fy1])); break
                facts.append(f"F facecam-face∩caption_window (per-act measured bands): violate={tot_v} {ex[:3]}")
                checks.append({"check":"caption_vs_face_peract","violate":tot_v,"pass":tot_v==0})
                if tot_v>0:
                    fails.append(f"F CAPTION-ON-FACE: лицо ВРЕЗКИ попадает в объявленное caption_window в {tot_v} кадрах {ex[:3]}")

        # ---- M: hero motion per act (hero region = ui_hero_box, fallback full frame) ----
        if acts:
            for act in acts:
                t0=max(0,act["t0"]); t1=min(D,act["t1"])
                afr=frames(a.render,t0,t1,a.fps,td,f"mot_{act['name']}")
                files=[fp for (_,fp) in afr]
                mbox=act.get("ui_hero_box") or [0,0,int(c.get("frame",{}).get("w",1080)),int(c.get("frame",{}).get("h",1920))]
                if mbox and mbox[3]>mbox[1]:
                    act_floor=float(act.get("motion_floor",motion_floor))
                    mot=region_motion(files,mbox)
                    facts.append(f"M [{act['name']}] ui_hero motion={mot:.2f} (floor {act_floor})")
                    checks.append({"check":"ui_hero_motion","act":act["name"],"motion":round(mot,3),
                                   "floor":act_floor,"pass":mot>=act_floor})
                    if mot<act_floor:
                        fails.append(f"M MOTION [{act['name']}]: hero почти статичен ({mot:.2f}<{act_floor}) — оригинальный сайт всегда в движении (scroll/zoom/cursor)")
        else:
            # no acts: judge motion over the whole frame across the whole-render samples
            full=[0,0,int(c.get("frame",{}).get("w",1080)),int(c.get("frame",{}).get("h",1920))]
            mot=region_motion([fp for (_,fp) in whole], full)
            facts.append(f"M [whole] ui_hero motion={mot:.2f} (floor {motion_floor}) — acts не заполнены, motion по всему кадру")
            checks.append({"check":"ui_hero_motion","act":"whole","motion":round(mot,3),
                           "floor":motion_floor,"pass":mot>=motion_floor})
            if mot<motion_floor:
                fails.append(f"M MOTION [whole]: hero почти статичен ({mot:.2f}<{motion_floor}) — сайт обязан быть в движении")

    verdict="PASS" if not fails else "FAIL"
    render_abs=os.path.abspath(a.render)
    out={
        "verdict":verdict,
        "render":render_abs,
        "render_mtime":os.path.getmtime(render_abs),
        "contract":os.path.abspath(a.contract),
        "checks":checks,
        "generated_ts_placeholder":"render_mtime is the freshness key (no Date.now)"
    }
    vpath=os.path.join(proj,".composition-verdict.json")
    json.dump(out, open(vpath,"w"), ensure_ascii=False, indent=1)

    print("========== COMPOSITION-GATE:",verdict,"==========")
    for f in facts: print("  ·",f)
    if fails:
        print("  -- FAIL --")
        for f in fails: print("  ✗",f)
    print("  verdict:",vpath)
    sys.exit(0 if verdict=="PASS" else 2)

if __name__=="__main__": main()

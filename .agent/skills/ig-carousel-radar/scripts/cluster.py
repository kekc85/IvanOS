#!/usr/bin/env python3
"""
Topic cluster classifier for radar skills.

Shared logic, kept as an IDENTICAL copy inside each radar skill's scripts/ dir
so every skill stays self-contained / portable (no cross-skill import coupling).
If you edit one copy, mirror the other (ig-carousel-radar <-> threads-radar).

Zero-LLM keyword matching over a post's caption/text. Reads the cluster taxonomy
from a seed YAML (see ~/.business/growth/clusters-en.yml). Adds a second relevance
layer on top of the source seed-lists: source lists pick WHO/WHAT topic, clusters
pick which FORMAT we actually want surfaced.

Policy per cluster:
    want    -> boosted to the top of the digest
    avoid   -> dropped from the digest (mode=drop_avoid) or sorted to bottom (mode=soft)
    neutral -> kept, below want

Precedence: clusters are evaluated TOP-TO-BOTTOM; first matching cluster wins.
Put want-clusters above avoid-clusters in the seed so a genuine tutorial that merely
mentions "prompt" lands in want, not in avoid.
"""

import re
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


# Fail-open default: if the seed is missing/unreadable, classification is a no-op
# (everything -> "other"/neutral, nothing dropped). The radar must never break
# just because the taxonomy file is absent.
_DEFAULT = {"mode": "off", "clusters": []}


def load_clusters(path: Path) -> dict:
    """Load cluster taxonomy. Returns {'mode': str, 'clusters': [ {name, policy, keywords[]} ]}."""
    if yaml is None or not Path(path).exists():
        return dict(_DEFAULT)
    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return dict(_DEFAULT)
    mode = str(data.get("mode", "off")).strip() or "off"
    clusters = []
    for c in data.get("clusters", []) or []:
        if not isinstance(c, dict):
            continue
        name = str(c.get("name", "")).strip()
        policy = str(c.get("policy", "neutral")).strip().lower()
        kws = [str(k).strip() for k in (c.get("keywords") or []) if str(k).strip()]
        if name and kws and policy in ("want", "avoid", "neutral"):
            clusters.append({"name": name, "policy": policy, "keywords": kws})
    return {"mode": mode, "clusters": clusters}


def _kw_match(text_lc: str, keyword: str) -> bool:
    """Substring match by default; 're:' prefix switches to regex search."""
    if keyword.startswith("re:"):
        try:
            return re.search(keyword[3:], text_lc) is not None
        except re.error:
            return False
    return keyword.lower() in text_lc


def classify(text: str, cfg: dict) -> tuple[str, str]:
    """Return (cluster_name, policy) for a post's caption/text. First match wins."""
    text_lc = (text or "").lower()
    for cluster in cfg.get("clusters", []):
        for kw in cluster["keywords"]:
            if _kw_match(text_lc, kw):
                return cluster["name"], cluster["policy"]
    return "other", "neutral"


def apply_clusters(candidates, get_text, cfg: dict):
    """
    Classify candidates, attach .cluster / .cluster_policy, optionally drop avoid.

    get_text: callable(candidate) -> str (caption for IG, text for Threads).
    Returns (kept, dropped, breakdown) where breakdown = {cluster_name: count} over ALL input.
    When mode != 'drop_avoid', nothing is dropped (avoid is only sorted down later).
    """
    mode = cfg.get("mode", "off")
    breakdown: dict[str, int] = {}
    kept, dropped = [], []
    for c in candidates:
        name, policy = classify(get_text(c), cfg)
        setattr(c, "cluster", name)
        setattr(c, "cluster_policy", policy)
        breakdown[name] = breakdown.get(name, 0) + 1
        if mode == "drop_avoid" and policy == "avoid":
            dropped.append(c)
        else:
            kept.append(c)
    return kept, dropped, breakdown


def policy_rank(policy: str) -> int:
    """Sort key helper: want first, then neutral, then avoid (avoid only present in soft mode)."""
    return {"want": 0, "neutral": 1, "avoid": 2}.get(policy, 1)


# ============================================================
# CTA detection (replicability gate)
# ============================================================
# A carousel is only useful to replicate if it has a CALL TO ACTION (призыв).
# No CTA -> nothing to offer/copy -> useless (автор).
#   strong = lead-magnet CTA (comment WORD / DM for X / link in bio for X) - даёт оффер для реплики
#   weak   = engagement CTA (save / follow / tag / share) - призыв есть, но реплицировать оффер нечего
#   none   = призыва нет -> выкинуть

_CTA_STRONG = [
    r"comment\s+['\"]?[a-z0-9]",      # "comment WORD"
    r"comment\s+(below|the word|to get)",
    r"\bdm\b.{0,20}(me|us|for|to get|and)",
    r"(we'?ll|i'?ll)\s+(dm|send)\s+you",
    r"send\s+you\s+(the|a|my|these)",
    r"link\s+in\s+(my\s+)?bio",
    r"grab\s+(the|it|your|my)",
    r"get\s+(the|it|your|free)\b",
    r"download\s+(the|it|your|free)",
    r"join\s+(the|my|our)\s+(free|waitlist|newsletter)",
]
_CTA_WEAK = [
    r"\bsave\s+(this|it|for later)",
    r"\bfollow\s+(me|us|for|@)",
    r"\btag\s+(a|someone|your|a friend)",
    r"\bshare\s+(this|it|with)",
    r"drop\s+a\s+",
]


def detect_cta(text: str) -> tuple[str, str]:
    """Return (strength, matched) where strength in {'strong','weak','none'}."""
    t = (text or "").lower()
    for pat in _CTA_STRONG:
        m = re.search(pat, t)
        if m:
            return "strong", m.group(0)[:30]
    for pat in _CTA_WEAK:
        m = re.search(pat, t)
        if m:
            return "weak", m.group(0)[:30]
    return "none", ""
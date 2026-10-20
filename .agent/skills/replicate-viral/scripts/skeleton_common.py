#!/usr/bin/env python3
"""
skeleton_common.py — ЕДИНЫЙ ИСТОЧНИК констант «montage skeleton binding».

Раньше списки аватар-несущих блоков / layout-enum / ролей дублировались в
scene-assemble.py И skeleton-match-check.py — рассинхрон при правке одного
файла = дыра (C2: K3 протаскивал говорящую голову на absent-битах, потому что
один файл знал про K3, другой нет). Теперь оба + skeleton-derive.py импортируют
ИМЕННО ОТСЮДА. Менять состав аватар-несущих блоков / enum — ТОЛЬКО здесь.
"""

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from layout_enum import canonical_set as _layout_canonical_set  # ЕДИНЫЙ источник enum (L3)

# layout кадра в enum скелета — берётся ИЗ ЕДИНОГО layout_enum.py (канон full-broll +
# алиас full-demo, оба принимаются). Раньше дублировался здесь как литерал и
# рассинхронивался с deconstruction-стороной. Теперь один источник на весь скилл.
LAYOUT_ENUM = _layout_canonical_set()

# layout спеки, означающий avatar full-screen (говорящую голову на весь кадр)
AVATAR_FULLSCREEN_LAYOUT = {"full-head"}

# Блоки, КОТОРЫЕ НЕСУТ АВАТАР (говорящую голову) в кадре. На absent-бите запрещены ВСЕ
# (не только full-screen O6): K3-overlap-card-avatar = блок говорящей головы (avatar_video
# слот). На absent-бите у эталона контент, не лицо → ни один из этих блоков недопустим.
# C2-фикс: детектор раньше смотрел только full-head/O6 и пропускал K3 на absent.
AVATAR_BEARING_BLOCKS = {"O6-avatar-feathered-fill", "K3-overlap-card-avatar", "K7-avatar-hero-inset"}

# роли скелет-бита, на которых говорящая голова / аватар-несущий блок ЛЕГИТИМНЫ
AVATAR_OK_ROLES = {"bookend", "anchor"}

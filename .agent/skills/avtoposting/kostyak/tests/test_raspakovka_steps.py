"""Номер шага, который называет доктор, обязан существовать в распаковке и вести
именно на свою площадку.

Зачем отдельный тест. Доктор говорит новичку «следующий шаг: шаг N распаковки».
Новичок открывает шаг N и делает то, что там написано. Если номер уехал (а он
уехал: VK жил на шаге 5, доктор слал на шаг 4), человек честно выполняет чужой
шаг и попадает в тупик. Такую ошибку глазами не видно, зато машина ловит её за
миллисекунду - и ловит КАЖДЫЙ раз, когда распаковку переставят местами
"""

from __future__ import annotations

import re

import pytest

from autopost import config
from autopost.config import KOSTYAK_DIR
from autopost.platforms.instagram import InstagramAdapter
from autopost.platforms.telegram import TelegramAdapter
from autopost.platforms.vk import VkAdapter

RASPAKOVKA = KOSTYAK_DIR.parent / "RASPAKOVKA.md"
SHAG_RE = re.compile(r"шаг (\d+) распаковки")
ZAGOLOVOK_RE = re.compile(r"^##\s*Шаг\s+(\d+)\.\s*(.+)$", re.MULTILINE)

# площадка -> слово, которое обязано стоять в заголовке её шага
SLOVO = {"telegram": "телеграм", "instagram": "instagram", "vk": "vk"}


def _adapters(http):
    return {
        "telegram": TelegramAdapter(config.telegram(), http),
        "instagram": InstagramAdapter(config.instagram(), http),
        "vk": VkAdapter(config.vk(), http),
    }


@pytest.fixture
def zagolovki():
    if not RASPAKOVKA.exists():
        pytest.skip("распаковка лежит рядом с костяком, в этой копии её нет")
    text = RASPAKOVKA.read_text(encoding="utf-8")
    return {int(number): title.strip() for number, title in ZAGOLOVOK_RE.findall(text)}


def test_every_step_from_doctor_exists_in_raspakovka(fake_http, monkeypatch, zagolovki):
    for key in ("TELEGRAM_BOT_TOKEN", "IG_ACCESS_TOKEN", "VK_ACCESS_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    http = fake_http()

    proverili = 0
    for name, adapter in _adapters(http).items():
        podskazka = adapter.check().next_step
        found = SHAG_RE.search(podskazka)
        assert found, "площадка %s не называет номер шага распаковки: %s" % (name, podskazka)
        number = int(found.group(1))
        assert number in zagolovki, "доктор шлёт %s на шаг %d, а такого шага в распаковке нет" % (name, number)
        assert SLOVO[name] in zagolovki[number].lower(), (
            "шаг %d называется «%s», а доктор шлёт туда площадку %s" % (number, zagolovki[number], name)
        )
        proverili += 1
    assert proverili == 3, "проверены все три площадки, а не часть"


def test_raspakovka_steps_are_numbered_without_holes(zagolovki):
    """Дыра в нумерации = сдвиг всех ссылок доктора разом"""
    numbers = sorted(zagolovki)
    assert numbers == list(range(numbers[0], numbers[0] + len(numbers))), "номера шагов идут подряд"

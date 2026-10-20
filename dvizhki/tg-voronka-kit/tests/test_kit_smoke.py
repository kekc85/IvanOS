# -*- coding: utf-8 -*-
"""Смоук кита одной командой: pytest.

Тесты кита написаны отдельными скриптами (каждый печатает свой итог и выходит кодом),
так их удобно гонять поштучно на сервере. Но «зелёно ли всё» такой формой не отвечается:
надо помнить список и читать десять хвостов. Здесь на каждый скрипт заведена ОДНА
pytest-функция, которая запускает его подпроцессом и требует нулевой код возврата.

Запуск: python3 -m pytest tests -q
Сеть при этом не используется: ни один из тестов не ходит в Telegram.
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = [
    "test_engine.py",        # машина состояний воронки
    "test_import.py",        # импортёр и валидация чужого JSON
    "test_runtime.py",       # рантайм: переходы, дожим, регистрация
    "test_broadcast.py",     # разбор черновика рассылки, сегменты, курсор
    "test_security.py",      # безопасность
    "test_suppression.py",   # общий реестр исключений
    "test_stats.py",         # счётчики воронки
    "test_clicktrack.py",    # клик-трекинг и редирект
    "test_export.py",        # выгрузка базы
    "test_review_fixes.py",  # закрытые замечания ревью
]


@pytest.mark.parametrize("script", SCRIPTS)
def test_kit_script(script):
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", script)],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, "%s упал:\n%s\n%s" % (script, r.stdout[-2000:], r.stderr[-2000:])


def test_offline_double_runs_funnel():
    """Офлайн-двойник разворачивает воронку целиком: без сети и без токена."""
    env = dict(os.environ)
    env["PYTHONPATH"] = ROOT
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "simulate_klod.py")],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    assert "всего отправок" in r.stdout

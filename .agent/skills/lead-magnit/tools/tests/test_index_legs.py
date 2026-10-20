#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Негативные тесты гейта --index-legs (волна 9, скептик-2 HIGH).

Проверяют, что гейт держится на КОДЕ ВЫХОДА, а не на строке в логе:
  1. несуществующий URL (HEAD не 200) -> exit 1, ни одна нога не трогается
  2. оба эндпоинта IndexNow ответили не 200/202 -> exit 1
  3. один из двух эндпоинтов IndexNow принял (частичный приём) -> exit 0 + WARN в логе
  4. все URL живые, IndexNow принял оба -> exit 0 (baseline, ничего не сломали)

Запуск: python3 tests/test_index_legs.py
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

TOOLS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import ftp_publish as fp  # noqa: E402


def _args(urls, dry_run=False, gsc_queue=None):
    return argparse.Namespace(url=urls, dry_run=dry_run, gsc_queue=gsc_queue)


class IndexLegsGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(
            prefix="gsc-pending-test-", suffix=".json", delete=False)
        self._tmp.close()
        os.unlink(self._tmp.name)  # файла не должно быть - _load_gsc_queue должен завести с нуля
        self.queue_path = self._tmp.name
        self.cfg = {"domain": "https://example.invalid"}

    def tearDown(self):
        if os.path.isfile(self.queue_path):
            os.unlink(self.queue_path)

    # 1. несуществующий URL -----------------------------------------------
    def test_nonexistent_url_exits_1_and_touches_no_leg(self):
        """HEAD-проверка ловит битый URL ДО обеих ног - IndexNow и GSC-очередь
        не должны вызываться вовсе (гейт стоит раньше, не после)."""
        bad_url = "https://example.invalid/definitely-not-a-real-page-xyz-wave9-test"

        with patch.object(fp.sp, "indexnow_ping") as mock_ping:
            buf = io.StringIO()
            with self.assertRaises(SystemExit) as ctx:
                with redirect_stdout(buf):
                    fp.index_legs(self.cfg, "unused-pw",
                                  _args([bad_url], gsc_queue=self.queue_path))
            self.assertEqual(ctx.exception.code, 1)
            mock_ping.assert_not_called()
        # очередь GSC не должна была быть создана - гейт сработал до неё
        self.assertFalse(os.path.isfile(self.queue_path),
                          "очередь GSC не должна писаться, если URL не прошёл HEAD-гейт")

    # 2. оба эндпоинта IndexNow отказали -----------------------------------
    def test_both_indexnow_endpoints_non_200_exits_1(self):
        with patch.object(fp, "_head_check_urls", return_value={"https://example.invalid/x": "200"}), \
             patch.object(fp.sp, "indexnow_ping",
                           return_value={"https://yandex.com/indexnow": "500",
                                         "https://api.indexnow.org/indexnow": "503"}):
            buf = io.StringIO()
            with self.assertRaises(SystemExit) as ctx:
                with redirect_stdout(buf):
                    fp.index_legs(self.cfg, "unused-pw",
                                  _args(["https://example.invalid/x"], gsc_queue=self.queue_path))
            self.assertEqual(ctx.exception.code, 1)
        # GSC-нога независимая - очередь всё равно должна была записаться
        self.assertTrue(os.path.isfile(self.queue_path),
                         "очередь GSC - независимая нога, должна писаться даже при фатале Яндекс-ноги")

    # 3. частичный приём (1 из 2) -> exit 0 + WARN --------------------------
    def test_partial_indexnow_accept_exits_0_with_warn(self):
        with patch.object(fp, "_head_check_urls", return_value={"https://example.invalid/x": "200"}), \
             patch.object(fp.sp, "indexnow_ping",
                           return_value={"https://yandex.com/indexnow": "200",
                                         "https://api.indexnow.org/indexnow": "500"}):
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    code = fp.index_legs(self.cfg, "unused-pw",
                                         _args(["https://example.invalid/x"], gsc_queue=self.queue_path))
            except SystemExit as e:
                self.fail(f"частичный приём (1/2) не должен давать exit != 0, получили {e.code}")
            self.assertEqual(code, 0)
            self.assertIn("WARN", buf.getvalue())

    # 4. baseline: всё живое, оба эндпоинта приняли -> exit 0 ---------------
    def test_all_good_exits_0(self):
        with patch.object(fp, "_head_check_urls", return_value={"https://example.invalid/x": "200"}), \
             patch.object(fp.sp, "indexnow_ping",
                           return_value={"https://yandex.com/indexnow": "200",
                                         "https://api.indexnow.org/indexnow": "202"}):
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    code = fp.index_legs(self.cfg, "unused-pw",
                                         _args(["https://example.invalid/x"], gsc_queue=self.queue_path))
            except SystemExit as e:
                self.fail(f"полностью успешный прогон не должен давать exit != 0, получили {e.code}")
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

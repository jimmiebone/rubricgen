"""rubricgen —— 自检测试。

把自然语言评分标准拆成可机械判定的检查项，并标出仍需人判断的部分。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rubricgen  # noqa: E402


class TestRubricGen(unittest.TestCase):
    def test_machine_criteria_is_detected(self):
        text = "- 输出长度不超过 200 字\n"
        r = rubricgen.generate(text)
        self.assertEqual(r["rows"][0]["mode"], "machine")
        self.assertTrue(r["rows"][0]["rule"])

    def test_subjective_criteria_goes_to_human(self):
        text = "- 回答是否合理贴切\n"
        r = rubricgen.generate(text)
        self.assertEqual(r["rows"][0]["mode"], "human")
        self.assertEqual(r["rows"][0]["rule"], "")

    def test_criteria_without_criterion_is_unknown(self):
        text = "- 回答质量\n"
        r = rubricgen.generate(text)
        self.assertEqual(r["rows"][0]["mode"], "unknown")

    def test_table_rows_are_parsed(self):
        text = "| 判据 | 通过标准 |\n|---|---|\n| 长度 | 不超过 200 字 |\n"
        r = rubricgen.generate(text)
        self.assertEqual(r["total"], 1)
        self.assertEqual(r["rows"][0]["standard"], "不超过 200 字")

    def test_does_not_invent_criteria(self):
        """防呆：不凭空造标准。"""
        text = "这一行没有任何标准\n"
        r = rubricgen.generate(text)
        self.assertEqual(r["total"], 0)

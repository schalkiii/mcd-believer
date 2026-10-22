#!/usr/bin/env python3
"""card.py 单元测试（纯标准库，Python 3.8+）。

运行：python -m unittest discover -s tests -v
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import card  # noqa: E402
import solver  # noqa: E402


def sample_fortune():
    return {
        "sign_no": 7,
        "line": "麦门显灵：你最挂念的那一口，正在锅里。",
        "items": [{"name": "巨无霸", "price_fen": 2350},
                  {"name": "薯条(中)", "price_fen": 1250}],
        "subtotal_fen": 3600,
        "final_fen": 2940,
        "saving_fen": 660,
        "coupon_names": ["满30减6"],
        "note": "测试备注",
    }


def sample_stats():
    return {
        "order_count": 4, "total_fen": 12000, "avg_fen": 3000, "item_count": 10,
        "top_items": [("巨无霸", 3), ("薯条(中)", 2), ("零糖可乐(中)", 1)],
        "channels": [("麦乐送", 3), ("到店自取", 1)],
        "periods": {"早餐": 1, "午餐": 1, "下午茶": 0, "晚餐": 1, "深夜": 1},
        "late_night_ratio": 0.25,
        "max_order_fen": 5200, "latest_order_time": "2026-10-08 21:26",
        "earliest_order_time": "2026-07-12 07:42",
    }


class FortuneCardTest(unittest.TestCase):
    def test_contains_key_data(self):
        html_text = card.render_fortune_card(sample_fortune())
        self.assertIn("第 7 签", html_text)
        self.assertIn("巨无霸", html_text)
        self.assertIn("薯条(中)", html_text)
        self.assertIn("¥36.00", html_text)
        self.assertIn("¥29.40", html_text)
        self.assertIn("满30减6", html_text)

    def test_zero_external_links(self):
        html_text = card.render_fortune_card(sample_fortune())
        self.assertNotIn("http://", html_text)
        self.assertNotIn("https://", html_text)
        self.assertNotIn("<img", html_text)
        self.assertNotIn("<script", html_text)

    def test_html_escaping(self):
        fortune = sample_fortune()
        fortune["items"] = [{"name": "<script>alert(1)</script>", "price_fen": 100}]
        html_text = card.render_fortune_card(fortune)
        self.assertNotIn("<script>alert", html_text)
        self.assertIn("&lt;script&gt;", html_text)

    def test_no_saving_line_when_zero(self):
        fortune = sample_fortune()
        fortune["saving_fen"] = 0
        html_text = card.render_fortune_card(fortune)
        self.assertNotIn("用券省", html_text)


class PersonaCardTest(unittest.TestCase):
    def test_contains_key_data(self):
        html_text = card.render_persona_card(sample_stats(), "2026 年度", 3, "备注")
        self.assertIn("2026 年度", html_text)
        self.assertIn("¥120.00", html_text)
        self.assertIn("巨无霸", html_text)
        self.assertIn("麦乐送", html_text)
        self.assertIn("巨无霸死忠", html_text)
        self.assertIn("零糖特调师", html_text)
        self.assertIn("麦乐送信徒", html_text)

    def test_derive_persona_deterministic(self):
        first = card.derive_persona(sample_stats())
        second = card.derive_persona(sample_stats())
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 3)

    def test_derive_persona_rules(self):
        stats = sample_stats()
        stats["late_night_ratio"] = 0.5
        stats["top_items"] = [("薯条(大)", 5)]
        stats["channels"] = [("得来速", 4)]
        stats["max_order_fen"] = 3000
        stats["avg_fen"] = 4000
        stats["periods"] = {"早餐": 3, "午餐": 0, "下午茶": 0, "晚餐": 0, "深夜": 2}
        self.assertEqual(card.derive_persona(stats),
                         ["深夜麦门徒", "薯条纯爱党", "早餐打卡员"])

    def test_derive_persona_capped_at_three(self):
        stats = sample_stats()
        stats["late_night_ratio"] = 0.5
        stats["top_items"] = [("巨无霸", 5), ("薯条(中)", 2), ("零糖可乐(中)", 1)]
        stats["channels"] = [("麦乐送", 3)]
        stats["max_order_fen"] = 5200
        stats["avg_fen"] = 2000
        stats["periods"] = {"早餐": 3, "午餐": 0, "下午茶": 1, "晚餐": 0, "深夜": 0}
        tags = card.derive_persona(stats)
        self.assertEqual(len(tags), 3)
        self.assertEqual(tags, ["深夜麦门徒", "巨无霸死忠", "零糖特调师"])

    def test_zero_external_links(self):
        html_text = card.render_persona_card(sample_stats(), "2026 年度", 3, "备注")
        self.assertNotIn("http://", html_text)
        self.assertNotIn("https://", html_text)
        self.assertNotIn("<script", html_text)

    def test_html_escaping(self):
        html_text = card.render_persona_card(sample_stats(), "<b>年度</b>", 3, "<i>备注</i>")
        self.assertNotIn("<b>年度</b>", html_text)
        self.assertIn("&lt;b&gt;年度&lt;/b&gt;", html_text)


class RenderToFileTest(unittest.TestCase):
    def test_write_and_read_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = card.render_card_to_file(
                card.render_fortune_card(sample_fortune()), Path(tmp) / "sub" / "card.html")
            self.assertTrue(path.exists())
            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("<!DOCTYPE html>"))
            self.assertIn("第 7 签", content)
            self.assertIn('lang="zh-CN"', content)

    def test_demo_run_generates_two_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            fortune_path, persona_path, stats, fortune = card.run_demo(tmp)
            self.assertTrue(Path(fortune_path).exists())
            self.assertTrue(Path(persona_path).exists())
            self.assertEqual(stats["order_count"], 12)
            self.assertIn("sign_no", fortune)


if __name__ == "__main__":
    unittest.main()

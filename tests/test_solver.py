#!/usr/bin/env python3
"""solver.py 单元测试（纯标准库，Python 3.8+）。

运行：python -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import solver  # noqa: E402

MENU = REPO_ROOT / "fixtures" / "sample_menu.json"
NUTRITION = REPO_ROOT / "fixtures" / "sample_nutrition.json"
COUPONS = REPO_ROOT / "fixtures" / "sample_coupons.json"
ORDERS = REPO_ROOT / "fixtures" / "sample_orders.json"


def make_item(code, name, price_fen, category, tags=(), kcal=100.0, protein=5.0):
    return solver.Item(code=code, name=name, price_fen=price_fen, category=category,
                       tags=tuple(tags), kcal=kcal, protein_g=protein, sodium_mg=100.0)


class SplitAATest(unittest.TestCase):
    def test_sum_equals_total(self):
        for total in (0, 1, 7, 100, 3350, 2590, 999999):
            for people in (1, 2, 3, 6, 11):
                shares = solver.split_aa(total, people)
                self.assertEqual(sum(shares), total)
                self.assertEqual(len(shares), people)
                self.assertLessEqual(max(shares) - min(shares), 1)

    def test_known_distribution(self):
        self.assertEqual(solver.split_aa(1000, 3), [334, 333, 333])
        self.assertEqual(solver.split_aa(3350, 6), [559, 559, 558, 558, 558, 558])
        self.assertEqual(solver.split_aa(2590, 6), [432, 432, 432, 432, 431, 431])
        self.assertEqual(solver.split_aa(0, 4), [0, 0, 0, 0])
        self.assertEqual(solver.split_aa(500, 1), [500])

    def test_invalid_people(self):
        with self.assertRaises(ValueError):
            solver.split_aa(1000, 0)

    def test_negative_total(self):
        with self.assertRaises(ValueError):
            solver.split_aa(-1, 3)


class CouponTest(unittest.TestCase):
    def setUp(self):
        self.burger = make_item("A1", "巨无霸", 2350, "汉堡", tags=["牛肉"], kcal=534, protein=27)
        self.chips = make_item("C1", "薯条(中)", 1250, "小食", tags=["薯条"], kcal=337, protein=3.6)
        self.ice = make_item("E1", "甜筒", 600, "甜品", tags=["冰淇淋"], kcal=153, protein=4)
        self.combo = (self.burger, self.chips, self.ice)

    def test_full_reduction_threshold(self):
        coupon = solver.Coupon("C1", "满30减6", "full_reduction", threshold_fen=3000, reduce_fen=600)
        self.assertEqual(solver.coupon_reduction(self.combo, coupon), 600)
        small = solver.Coupon("C2", "满50减15", "full_reduction", threshold_fen=5000, reduce_fen=1500)
        self.assertEqual(solver.coupon_reduction(self.combo, small), 0)

    def test_discount_scope(self):
        coupon = solver.Coupon("C3", "汉堡7折", "discount", discount=0.7,
                               applies_to_categories=("汉堡",))
        self.assertEqual(solver.coupon_reduction(self.combo, coupon), 705)  # 2350*0.3
        none = solver.Coupon("C4", "饮品5折", "discount", discount=0.5,
                             applies_to_categories=("饮品",))
        self.assertEqual(solver.coupon_reduction(self.combo, none), 0)

    def test_disjoint_scopes_combine(self):
        burger_off = solver.Coupon("B", "汉堡7折", "discount", discount=0.7,
                                   applies_to_categories=("汉堡",))
        dessert_off = solver.Coupon("D", "甜品立减3元", "full_reduction",
                                    threshold_fen=0, reduce_fen=300,
                                    applies_to_categories=("甜品",))
        result = solver.optimize_coupons(self.combo, [burger_off, dessert_off])
        self.assertEqual(result["saving_fen"], 705 + 300)
        self.assertEqual(result["final_fen"], 4200 - 1005)

    def test_overlapping_scopes_excluded(self):
        whole_order = solver.Coupon("W", "满30减6", "full_reduction",
                                    threshold_fen=3000, reduce_fen=600)
        burger_off = solver.Coupon("B", "汉堡7折", "discount", discount=0.7,
                                   applies_to_categories=("汉堡",))
        result = solver.optimize_coupons(self.combo, [whole_order, burger_off])
        self.assertEqual(result["saving_fen"], 705)  # 只能选省得更多的汉堡7折

    def test_same_group_mutual_exclusion(self):
        off_a = solver.Coupon("A", "汉堡7折", "discount", discount=0.7,
                              applies_to_categories=("汉堡",), group="burger")
        off_b = solver.Coupon("B", "汉堡6折", "discount", discount=0.6,
                              applies_to_categories=("汉堡",), group="burger")
        result = solver.optimize_coupons(self.combo, [off_a, off_b])
        self.assertEqual(len(result["coupons"]), 1)
        self.assertEqual(result["coupons"], ("B",))

    def test_tie_break_prefers_fewer_coupons(self):
        one = solver.Coupon("A", "满30减6", "full_reduction", threshold_fen=3000, reduce_fen=600)
        two_a = solver.Coupon("X", "满20减3", "full_reduction", threshold_fen=2000, reduce_fen=300,
                              applies_to_categories=("小食",))
        two_b = solver.Coupon("Y", "甜品立减3元", "full_reduction", threshold_fen=0,
                              reduce_fen=300, applies_to_categories=("甜品",))
        result = solver.optimize_coupons(self.combo, [one, two_a, two_b])
        self.assertEqual(result["coupons"], ("A",))

    def test_no_coupon_applicable(self):
        high = solver.Coupon("H", "满99减50", "full_reduction", threshold_fen=9900, reduce_fen=5000)
        result = solver.optimize_coupons(self.combo, [high])
        self.assertEqual(result["final_fen"], 4200)
        self.assertEqual(result["saving_fen"], 0)


class EnumerateAndSelectTest(unittest.TestCase):
    def setUp(self):
        self.items = solver.load_items(MENU, NUTRITION)
        self.assertTrue(self.items)

    def test_constraints_respected(self):
        budget_fen, kcal_max = 40 * 100, 800
        combos = solver.enumerate_combos(self.items, budget_fen=budget_fen, kcal_max=kcal_max)
        self.assertTrue(combos)
        for combo, totals in combos:
            self.assertLessEqual(totals["price_fen"], budget_fen)
            self.assertLessEqual(totals["kcal"], kcal_max)
            self.assertLessEqual(len(combo), solver.MAX_ITEMS_PER_COMBO)

    def test_determinism(self):
        first = solver.enumerate_combos(self.items, budget_fen=4000, kcal_max=800)
        second = solver.enumerate_combos(self.items, budget_fen=4000, kcal_max=800)
        self.assertEqual([tuple(i.code for i in c) for c, _ in first],
                         [tuple(i.code for i in c) for c, _ in second])

    def test_enumeration_not_truncated_by_expensive_prefix(self):
        # 回归：枚举中途遇到超预算组合，不得剪掉后续合法的更便宜组合
        items = [make_item("T1", "甜筒", 600, "甜品"),
                 make_item("T2", "甜筒二号", 600, "甜品"),
                 make_item("BIG", "超贵套餐", 3900, "套餐"),
                 make_item("TEA", "锡兰红茶", 750, "饮品")]
        combos = solver.enumerate_combos(items, budget_fen=2000, max_items=2)
        sigs = {tuple(i.code for i in c) for c, _ in combos}
        self.assertIn(("T1", "TEA"), sigs)
        self.assertIn(("T2", "TEA"), sigs)
        self.assertNotIn(("BIG",), sigs)

    def test_plan_selection_rules(self):
        candidates = solver.enumerate_combos(self.items, budget_fen=4000, kcal_max=800)
        plans = solver.select_plans(candidates, kcal_max=800)
        self.assertEqual(plans["fullest"]["totals"]["kcal"],
                         max(t["kcal"] for _, t in candidates))
        self.assertEqual(plans["cheapest"]["totals"]["price_fen"],
                         min(t["price_fen"] for _, t in candidates))
        balanced_pool = [c for c in candidates if c[1]["kcal"] >= 400]
        best_ratio = max(t["protein_g"] / t["price_fen"] for _, t in balanced_pool)
        ratio = plans["balanced"]["totals"]["protein_g"] / plans["balanced"]["totals"]["price_fen"]
        self.assertAlmostEqual(ratio, best_ratio, places=6)

    def test_empty_candidates(self):
        self.assertEqual(solver.select_plans([], kcal_max=500), {})

    def test_missing_nutrition_excluded(self):
        menu = {"categories": [{"categoryName": "汉堡", "meals": [
            {"code": "X1", "name": "不存在的餐品", "currentPrice": 10.0, "tags": []}]}]}
        nutrition = {"foods": [{"name": "巨无霸", "energyKcal": 534, "proteinG": 27.0,
                                "fatG": 27.0, "carbG": 45.0, "sodiumMg": 1014}]}
        with tempfile.TemporaryDirectory() as tmp:
            menu_path = Path(tmp) / "menu.json"
            nutrition_path = Path(tmp) / "nutrition.json"
            menu_path.write_text(json.dumps(menu), encoding="utf-8")
            nutrition_path.write_text(json.dumps(nutrition), encoding="utf-8")
            self.assertEqual(solver.load_items(menu_path, nutrition_path), [])


class ParetoTest(unittest.TestCase):
    def test_dominated_removed(self):
        points = [(1000, 300, "a"), (1200, 300, "b"), (900, 250, "c"), (800, 200, "d")]
        front = solver.pareto_front(points)
        labels = [p[2] for p in front]
        self.assertNotIn("b", labels)  # 同热量但更贵，被 a 支配
        self.assertEqual(labels, ["d", "c", "a"])  # d 最便宜、c 次之、a 热量最高，均非支配

    def test_sorted_by_price(self):
        points = [(500, 100, "x"), (300, 90, "y")]
        front = solver.pareto_front(points)
        self.assertEqual([p[0] for p in front], [300, 500])


class SummarizeOrdersTest(unittest.TestCase):
    def setUp(self):
        self.stats = solver.summarize_orders(
            json.loads(ORDERS.read_text(encoding="utf-8"))["orders"])

    def test_totals(self):
        self.assertEqual(self.stats["order_count"], 12)
        self.assertEqual(self.stats["total_fen"], 36490)
        self.assertEqual(self.stats["item_count"], 28)

    def test_top_items(self):
        self.assertEqual(self.stats["top_items"][0], ("巨无霸", 4))

    def test_periods_and_late_night(self):
        self.assertEqual(sum(self.stats["periods"].values()), 12)
        self.assertEqual(self.stats["periods"]["深夜"], 5)
        self.assertEqual(self.stats["late_night_ratio"], 0.417)

    def test_channels(self):
        self.assertEqual(self.stats["channels"][0], ("到店自取", 6))

    def test_extremes(self):
        self.assertEqual(self.stats["max_order_fen"], 5200)
        self.assertEqual(self.stats["earliest_order_time"], "2026-07-12 07:42")
        self.assertEqual(self.stats["latest_order_time"], "2026-10-08 21:26")


if __name__ == "__main__":
    unittest.main()

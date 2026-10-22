#!/usr/bin/env python3
"""
mcd-believer 确定性求解器（离线可跑，零第三方依赖）

定位：把 references/ordering.md 与 references/savings.md 里的文字编排规则
升级为可复现的确定性代码——「取数交给 MCP、算术交给代码、表达交给 Agent」。
本模块只做算术，不联网、不调用 MCP；真实价格一律以 calculate-price 核价为准。

能力：
  - 预算 × 热量双约束组合枚举，输出「最饱 / 最省 / 最均衡」三套方案
  - 券组合枚举（满减 / 折扣 / 品类范围 / 同组互斥），求最优实付
  - 多人拼单零尾差 AA（最大余数法）
  - 价格 × 热量帕累托前沿
  - 历史订单统计（供年报人设卡使用）

用法：
  python scripts/solver.py demo                      # 用 fixtures 跑通完整求解演示
  python scripts/solver.py solve --budget 40 --kcal 800 [--must 汉堡] [--exclude 麦辣]
  python scripts/solver.py aa --total 33.5 --people 6 # 金额为元，内部按分整数运算
"""
import argparse
import json
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

FEN_PER_YUAN = 100
REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"

MAX_ITEMS_PER_COMBO = 4


def fen_to_yuan(fen):
    """分 → 元字符串（内部一律整数分运算，杜绝浮点误差）。"""
    return "{:.2f}".format(fen / FEN_PER_YUAN)


@dataclass(frozen=True)
class Item:
    code: str
    name: str
    price_fen: int
    category: str
    tags: tuple
    kcal: float
    protein_g: float
    sodium_mg: float


@dataclass(frozen=True)
class Coupon:
    coupon_id: str
    name: str
    kind: str                      # full_reduction | discount
    threshold_fen: int = 0
    reduce_fen: int = 0
    discount: float = 1.0
    applies_to_categories: tuple = ()
    applies_to_tags: tuple = ()
    group: str = ""                # 同组互斥
    source: str = "store"


def _read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_items(menu_path, nutrition_path):
    """菜单 × 营养表按 name 连接；缺营养数据的餐品一律剔除（拒绝估算）。"""
    menu = _read_json(menu_path)
    nutrition = _read_json(nutrition_path)
    nutrition_by_name = {f["name"]: f for f in nutrition["foods"]}
    items = []
    for category in menu["categories"]:
        for meal in category["meals"]:
            nut = nutrition_by_name.get(meal["name"])
            if nut is None:
                continue
            items.append(Item(
                code=meal["code"],
                name=meal["name"],
                price_fen=int(round(meal["currentPrice"] * FEN_PER_YUAN)),
                category=category["categoryName"],
                tags=tuple(meal.get("tags", [])),
                kcal=float(nut["energyKcal"]),
                protein_g=float(nut["proteinG"]),
                sodium_mg=float(nut["sodiumMg"]),
            ))
    return items


def load_coupons(coupons_path):
    data = _read_json(coupons_path)
    coupons = []
    for entry in data.get("storeCoupons", []):
        coupons.append(Coupon(
            coupon_id=entry["couponId"], name=entry["name"],
            kind=entry.get("kind", "full_reduction"),
            threshold_fen=int(entry.get("thresholdFen", 0)),
            reduce_fen=int(entry.get("reduceFen", 0)),
            discount=float(entry.get("discount", 1.0)),
            applies_to_categories=tuple(entry.get("appliesToCategories", [])),
            applies_to_tags=tuple(entry.get("appliesToTags", [])),
            group=entry.get("group", ""), source="store",
        ))
    for entry in data.get("myCoupons", []):
        coupons.append(Coupon(
            coupon_id=entry["couponId"], name=entry["name"],
            kind=entry.get("kind", "full_reduction"),
            threshold_fen=int(entry.get("thresholdFen", 0)),
            reduce_fen=int(entry.get("reduceFen", 0)),
            discount=float(entry.get("discount", 1.0)),
            applies_to_categories=tuple(entry.get("appliesToCategories", [])),
            applies_to_tags=tuple(entry.get("appliesToTags", [])),
            group=entry.get("group", ""), source="mine",
        ))
    return coupons


def filter_candidates(items, must_keywords=(), exclude_keywords=()):
    """忌口/必选项过滤。must 命中任一关键词即保留；exclude 命中任一即剔除。"""
    result = []
    for item in items:
        haystack = item.name + " " + " ".join(item.tags)
        if exclude_keywords and any(k in haystack for k in exclude_keywords):
            continue
        if must_keywords and not any(k in haystack for k in must_keywords):
            continue
        result.append(item)
    return result


def combo_totals(combo):
    return {
        "price_fen": sum(i.price_fen for i in combo),
        "kcal": round(sum(i.kcal for i in combo), 1),
        "protein_g": round(sum(i.protein_g for i in combo), 1),
        "sodium_mg": round(sum(i.sodium_mg for i in combo), 1),
        "item_count": len(combo),
    }


def enumerate_combos(items, max_items=MAX_ITEMS_PER_COMBO, budget_fen=None, kcal_max=None):
    """1..max_items 件的组合枚举（按索引升序递归 + 累计价格剪枝，保证完备性）。
    确定性输出：输入有序则输出有序。"""
    ordered = sorted(items, key=lambda i: (i.price_fen, i.name))
    combos = []

    def recurse(start, chosen):
        if chosen:
            totals = combo_totals(chosen)
            if kcal_max is None or totals["kcal"] <= kcal_max:
                combos.append((tuple(chosen), totals))
        if len(chosen) >= max_items:
            return
        chosen_fen = sum(i.price_fen for i in chosen)
        for idx in range(start, len(ordered)):
            if budget_fen is not None and chosen_fen + ordered[idx].price_fen > budget_fen:
                break  # ordered 按价格升序，后续餐品只会更贵，可安全剪枝
            chosen.append(ordered[idx])
            recurse(idx + 1, chosen)
            chosen.pop()

    recurse(0, [])
    return combos


def select_plans(candidates, kcal_max=None, top_n=3):
    """三套确定性方案：最饱 / 最省 / 最均衡。全部带确定性 tie-break。"""
    if not candidates:
        return {}
    by_fullness = sorted(candidates, key=lambda c: (-c[1]["kcal"], c[1]["price_fen"],
                                                    tuple(i.name for i in c[0])))
    by_price = sorted(candidates, key=lambda c: (c[1]["price_fen"], -c[1]["kcal"],
                                                 tuple(i.name for i in c[0])))
    balanced_pool = [c for c in candidates if kcal_max and c[1]["kcal"] >= 0.5 * kcal_max] or candidates
    by_balance = sorted(balanced_pool, key=lambda c: (
        -(c[1]["protein_g"] / max(c[1]["price_fen"], 1)), c[1]["price_fen"],
        tuple(i.name for i in c[0])))
    plans = {}
    for key, ranked, reason in (("fullest", by_fullness, "热量最高（最饱）"),
                                ("cheapest", by_price, "实付最低（最省）"),
                                ("balanced", by_balance, "每元蛋白质最高（最均衡）")):
        plans[key] = {"reason": reason, "combo": ranked[0][0], "totals": ranked[0][1]}
    return plans


def _coupon_scope_indices(combo, coupon):
    """券的适用范围（组合内餐品下标集合）：未限定品类/标签时覆盖整单。"""
    return frozenset(
        idx for idx, item in enumerate(combo)
        if (not coupon.applies_to_categories and not coupon.applies_to_tags)
        or item.category in coupon.applies_to_categories
        or any(t in coupon.applies_to_tags for t in item.tags)
    )


def _coupon_scope_subtotal(combo, coupon):
    return sum(combo[idx].price_fen for idx in _coupon_scope_indices(combo, coupon))


def coupon_reduction(combo, coupon):
    """单张券在给定组合上的可省金额（分）；不满足门槛或范围为空返回 0。"""
    scope_fen = _coupon_scope_subtotal(combo, coupon)
    if scope_fen <= 0:
        return 0
    if coupon.kind == "full_reduction":
        return coupon.reduce_fen if scope_fen >= coupon.threshold_fen else 0
    if coupon.kind == "discount":
        return int(round(scope_fen * (1.0 - coupon.discount)))
    return 0


def _subsets_compatible(pool, scopes):
    """枚举互不冲突的券子集：①同 group 互斥 ②适用范围不重叠（一张餐品最多带一张券）。
    真实可叠性以 calculate-price 返回为准，此处为保守的确定性模型。"""
    for size in range(len(pool), -1, -1):
        for subset in combinations(pool, size):
            groups = [c.group for c in subset if c.group]
            if len(groups) != len(set(groups)):
                continue
            used = set()
            overlap = False
            for coupon in subset:
                if scopes[coupon.coupon_id] & used:
                    overlap = True
                    break
                used |= scopes[coupon.coupon_id]
            if overlap:
                continue
            yield subset


def optimize_coupons(combo, coupons):
    """枚举兼容券子集求最优实付。确定性 tie-break：省更多 > 券更少 > 券 ID 字典序。"""
    subtotal = combo_totals(combo)["price_fen"]
    scopes = {c.coupon_id: _coupon_scope_indices(combo, c) for c in coupons}
    best = None
    for subset in _subsets_compatible(sorted(coupons, key=lambda c: c.coupon_id), scopes):
        reduction = sum(coupon_reduction(combo, c) for c in subset)
        if reduction <= 0:
            continue
        final_fen = max(subtotal - reduction, 0)
        key = (-reduction, len(subset), tuple(c.coupon_id for c in subset))
        if best is None or key < best[0]:
            best = (key, subset, final_fen, reduction)
    if best is None:
        return {"subtotal_fen": subtotal, "coupons": (), "final_fen": subtotal,
                "saving_fen": 0, "per_coupon_fen": {}}
    _, subset, final_fen, reduction = best
    return {
        "subtotal_fen": subtotal,
        "coupons": tuple(c.coupon_id for c in subset),
        "final_fen": final_fen,
        "saving_fen": reduction,
        "per_coupon_fen": {c.coupon_id: coupon_reduction(combo, c) for c in subset},
    }


def split_aa(total_fen, people):
    """多人拼单零尾差 AA：最大余数法，保证分账之和恰等于 total_fen。"""
    if people <= 0:
        raise ValueError("人数必须为正整数")
    if total_fen < 0:
        raise ValueError("总金额不能为负")
    base, remainder = divmod(total_fen, people)
    shares = [base] * people
    for i in range(remainder):
        shares[i] += 1
    return shares


def pareto_front(points):
    """价格 × 热量帕累托前沿。points: [(price_fen, kcal, label), ...] 价格越小越好、热量越高越好。"""
    front = []
    for p in points:
        dominated = any((q[0] <= p[0] and q[1] >= p[1]) and (q[0] < p[0] or q[1] > p[1])
                        for q in points if q is not p)
        if not dominated:
            front.append(p)
    return sorted(front, key=lambda p: (p[0], -p[1]))


def summarize_orders(orders):
    """历史订单统计（确定性聚合，供年报人设卡使用）。只统计真实返回，禁止编造。"""
    total_fen = sum(o["totalFen"] for o in orders)
    item_counter = {}
    for o in orders:
        for entry in o["items"]:
            item_counter[entry["name"]] = item_counter.get(entry["name"], 0) + entry["quantity"]
    channels = {}
    periods = {"早餐": 0, "午餐": 0, "下午茶": 0, "晚餐": 0, "深夜": 0}
    late_night_orders = 0
    for o in orders:
        channels[o["channel"]] = channels.get(o["channel"], 0) + 1
        hour = int(o["orderTime"].split(" ")[1].split(":")[0])
        if 7 <= hour < 11:
            periods["早餐"] += 1
        elif 11 <= hour < 14:
            periods["午餐"] += 1
        elif 14 <= hour < 17:
            periods["下午茶"] += 1
        elif 17 <= hour < 21:
            periods["晚餐"] += 1
        else:
            periods["深夜"] += 1
            late_night_orders += 1
    top_items = sorted(item_counter.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "order_count": len(orders),
        "total_fen": total_fen,
        "avg_fen": total_fen // len(orders) if orders else 0,
        "item_count": sum(item_counter.values()),
        "top_items": top_items,
        "channels": sorted(channels.items(), key=lambda kv: (-kv[1], kv[0])),
        "periods": periods,
        "late_night_ratio": round(late_night_orders / len(orders), 3) if orders else 0.0,
        "max_order_fen": max((o["totalFen"] for o in orders), default=0),
        "latest_order_time": max((o["orderTime"] for o in orders), default=""),
        "earliest_order_time": min((o["orderTime"] for o in orders), default=""),
    }


def _load_default_fixtures():
    return (load_items(FIXTURES_DIR / "sample_menu.json", FIXTURES_DIR / "sample_nutrition.json"),
            load_coupons(FIXTURES_DIR / "sample_coupons.json"))


def _print_plan(name, plan, coupons):
    combo, totals = plan["combo"], plan["totals"]
    print("【{}】{}".format(name, plan["reason"]))
    for item in combo:
        print("  - {}（{}） {}".format(item.name, item.category, fen_to_yuan(item.price_fen)))
    opt = optimize_coupons(combo, coupons)
    print("  合计 {} 元 | {} kcal | 蛋白质 {} g".format(
        fen_to_yuan(totals["price_fen"]), totals["kcal"], totals["protein_g"]))
    if opt["saving_fen"] > 0:
        names = {c.coupon_id: c.name for c in coupons}
        used = " + ".join("{}（省 {} 元）".format(names[cid], fen_to_yuan(fen))
                          for cid, fen in opt["per_coupon_fen"].items())
        print("  用券后实付 {} 元（{}）".format(fen_to_yuan(opt["final_fen"]), used))
    print()


def run_demo():
    items, coupons = _load_default_fixtures()
    budget_fen, kcal_max = 40 * FEN_PER_YUAN, 800
    candidates = enumerate_combos(items, budget_fen=budget_fen, kcal_max=kcal_max)
    plans = select_plans(candidates, kcal_max=kcal_max)
    print("== mcd-believer 求解器演示（fixtures 构造样本，非真实数据）==\n")
    print("约束：预算 ≤ {} 元，热量 ≤ {} kcal，候选组合 {} 套\n".format(
        fen_to_yuan(budget_fen), kcal_max, len(candidates)))
    for key, name in (("fullest", "最饱"), ("cheapest", "最省"), ("balanced", "最均衡")):
        _print_plan(name, plans[key], coupons)
    front = pareto_front([(t["price_fen"], t["kcal"], "+".join(i.name for i in c))
                          for c, t in candidates])
    print("== 价格 × 热量帕累托前沿（前 5）==")
    for price_fen, kcal, label in front[:5]:
        print("  {} 元 / {} kcal  {}".format(fen_to_yuan(price_fen), kcal, label))
    print("\n== 6 人拼单 AA（以「最饱」方案用券后实付为例）==")
    shares = split_aa(optimize_coupons(plans["fullest"]["combo"], coupons)["final_fen"], 6)
    print("  每人：{} 元，合计恰等于实付（零尾差）".format(" / ".join(fen_to_yuan(s) for s in shares)))


def main():
    parser = argparse.ArgumentParser(description="mcd-believer 确定性求解器")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("demo", help="用 fixtures 跑完整求解演示")
    solve = sub.add_parser("solve", help="自定义约束求解")
    solve.add_argument("--budget", type=float, required=True, help="预算上限（元）")
    solve.add_argument("--kcal", type=float, default=None, help="热量上限（kcal）")
    solve.add_argument("--must", default="", help="必含关键词，逗号分隔")
    solve.add_argument("--exclude", default="", help="忌口关键词，逗号分隔")
    solve.add_argument("--max-items", type=int, default=MAX_ITEMS_PER_COMBO)
    aa = sub.add_parser("aa", help="多人拼单零尾差 AA")
    aa.add_argument("--total", type=float, required=True, help="实付总额（元）")
    aa.add_argument("--people", type=int, required=True)
    args = parser.parse_args()

    if args.command == "demo":
        run_demo()
    elif args.command == "solve":
        items, coupons = _load_default_fixtures()
        must = tuple(k for k in args.must.split(",") if k)
        exclude = tuple(k for k in args.exclude.split(",") if k)
        pool = filter_candidates(items, must_keywords=must, exclude_keywords=exclude)
        kcal_max = int(args.kcal) if args.kcal else None
        candidates = enumerate_combos(pool, max_items=args.max_items,
                                      budget_fen=int(round(args.budget * FEN_PER_YUAN)),
                                      kcal_max=kcal_max)
        plans = select_plans(candidates, kcal_max=kcal_max)
        if not plans:
            sys.exit("无解：当前约束下没有可行组合（可放宽预算/热量或忌口）")
        for key, name in (("fullest", "最饱"), ("cheapest", "最省"), ("balanced", "最均衡")):
            _print_plan(name, plans[key], coupons)
    elif args.command == "aa":
        shares = split_aa(int(round(args.total * FEN_PER_YUAN)), args.people)
        print("每人：{} 元".format(" / ".join(fen_to_yuan(s) for s in shares)))
        print("合计：{} 元（与实付一致，零尾差）".format(fen_to_yuan(sum(shares))))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

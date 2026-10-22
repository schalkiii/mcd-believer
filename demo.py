#!/usr/bin/env python3
"""
mcd-believer 一键演示（不需要 MCP Token、不联网、零第三方依赖）

30 秒看完全部核心能力，四条链路一次跑通：
  ① 预算 × 热量双约束求解（最饱 / 最省 / 最均衡）
  ② 券组合枚举（满减 / 折扣 / 品类范围 / 互斥模型）
  ③ 麦门灵签卡（单文件竖屏 HTML，可截图分享）
  ④ 麦门年报人设卡（确定性人设规则 + 时段画像）
  ⑤ 多人拼单零尾差 AA

用法：
    python demo.py

数据为 fixtures/ 下的构造样本（结构对齐 MCP 真实返回），
真实使用时一律以 MCP 实时返回与 calculate-price 核价为准。
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import solver  # noqa: E402
import card as card_module  # noqa: E402

FIXTURES = REPO_ROOT / "fixtures"


def main():
    print("=" * 56)
    print("麦门信徒 mcd-believer · 一键演示（构造样本，非真实数据）")
    print("=" * 56)

    items = solver.load_items(FIXTURES / "sample_menu.json", FIXTURES / "sample_nutrition.json")
    coupons = solver.load_coupons(FIXTURES / "sample_coupons.json")
    budget_fen, kcal_max = 40 * solver.FEN_PER_YUAN, 800

    print("\n■ 链路 ① 预算求解：预算 ≤ {} 元，热量 ≤ {} kcal".format(
        solver.fen_to_yuan(budget_fen), kcal_max))
    candidates = solver.enumerate_combos(items, budget_fen=budget_fen, kcal_max=kcal_max)
    plans = solver.select_plans(candidates, kcal_max=kcal_max)
    print("  候选组合 {} 套，输出三套方案：".format(len(candidates)))
    for key, name in (("fullest", "最饱"), ("cheapest", "最省"), ("balanced", "最均衡")):
        combo, totals = plans[key]["combo"], plans[key]["totals"]
        print("  [{}] {} —— {} 元 / {} kcal / 蛋白质 {} g".format(
            name, " + ".join(i.name for i in combo),
            solver.fen_to_yuan(totals["price_fen"]), totals["kcal"], totals["protein_g"]))

    print("\n■ 链路 ② 券组合优化（以「最均衡」方案为例）")
    combo = plans["balanced"]["combo"]
    opt = solver.optimize_coupons(combo, coupons)
    names = {c.coupon_id: c.name for c in coupons}
    print("  原价 {} 元".format(solver.fen_to_yuan(opt["subtotal_fen"])))
    for coupon_id, fen in opt["per_coupon_fen"].items():
        print("    + {}（省 {} 元）".format(names[coupon_id], solver.fen_to_yuan(fen)))
    print("  最优实付 {} 元，共省 {} 元".format(
        solver.fen_to_yuan(opt["final_fen"]), solver.fen_to_yuan(opt["saving_fen"])))

    print("\n■ 链路 ③④ 分享卡渲染")
    out_dir = REPO_ROOT / "demo_output"
    fortune_path, persona_path, stats, fortune = card_module.run_demo(out_dir)
    print("  灵签：{}".format(fortune["line"]))
    print("  人设标签：{}".format(" / ".join(card_module.derive_persona(stats))))
    print("  已写出：")
    print("    " + str(fortune_path))
    print("    " + str(persona_path))

    print("\n■ 链路 ⑤ 多人拼单 AA（最饱方案实付 ÷ 6 人）")
    fullest_final = solver.optimize_coupons(plans["fullest"]["combo"], coupons)["final_fen"]
    shares = solver.split_aa(fullest_final, 6)
    print("  每人 {} 元，合计恰等于 {} 元（零尾差）".format(
        " / ".join(solver.fen_to_yuan(s) for s in shares), solver.fen_to_yuan(fullest_final)))

    print("\n演示结束。浏览器打开 demo_output/ 下的两张 HTML 即可截图分享。")
    print("真实使用：装载本 Skill（SKILL.md）并接入麦当劳 MCP，直接说人话。")


if __name__ == "__main__":
    main()

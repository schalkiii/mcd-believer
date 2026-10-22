#!/usr/bin/env python3
"""
mcd-believer 分享卡生成器（离线可跑，零第三方依赖）

把求解结果渲染成**单文件竖屏 HTML 分享卡**——品牌配色、零外部链接、
为手机截图分享而设计。两类卡：
  - 麦门灵签卡：抽签结果 + 餐品清单 + 原价/实付对比
  - 麦门年报人设卡：周期消费统计 + 本命餐品 + 人设标签

用法：
  python scripts/card.py demo                 # 用 fixtures 渲染两张卡到 demo_output/
  python scripts/card.py persona --stats X --period "2026 年度" --stores 3
"""
import argparse
import html
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import solver  # noqa: E402

BRAND_RED = "#DA291C"
BRAND_GOLD = "#FFC72C"

PAGE_STYLE = (
    "margin:0;padding:24px 12px;background:#F5F2EA;font-family:-apple-system,"
    "'PingFang SC','Microsoft YaHei',sans-serif;display:flex;"
    "justify-content:center;"
)
CARD_STYLE = (
    "width:100%;max-width:375px;background:#FFFFFF;border-radius:16px;"
    "overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);"
)
HEADER_STYLE = (
    "background:{red};color:#FFFFFF;padding:20px 20px 16px;".format(red=BRAND_RED)
)
FOOTER_STYLE = "padding:12px 20px 16px;color:#8A8578;font-size:11px;line-height:1.6;"

FORTUNE_LINES = [
    "今日麦运在线，宜大口吃肉，忌纠结犹豫。",
    "此签主「饱」——吃什么不重要，吃饱才重要。",
    "麦门显灵：你最挂念的那一口，正在锅里。",
    "签文显示：省钱与好吃今日可兼得，放心点。",
    "命格鉴定：麦门中级长老，餐标务实，眼光独到。",
    "此乃「随心配」上上签——简单点，吃麦的方式简单点。",
]


def _esc(text):
    return html.escape(str(text), quote=True)


def _yuan(fen):
    return solver.fen_to_yuan(fen)


def render_fortune_card(fortune):
    """fortune: {sign_no, line, items:[{name, price_fen}], subtotal_fen, final_fen,
    saving_fen, coupon_names:[str], note}"""
    items_html = "".join(
        "<tr><td style=\"padding:6px 0;color:#2C2C2A;\">{name}</td>"
        "<td style=\"padding:6px 0;text-align:right;color:#2C2C2A;\">¥{price}</td></tr>".format(
            name=_esc(item["name"]), price=_yuan(item["price_fen"]))
        for item in fortune["items"])
    saving_line = ""
    if fortune["saving_fen"] > 0:
        saving_line = (
            "<div style=\"margin-top:10px;color:{red};font-weight:500;\">"
            "用券省 ¥{saving}（{coupons}）</div>".format(
                red=BRAND_RED, saving=_yuan(fortune["saving_fen"]),
                coupons=_esc(" + ".join(fortune["coupon_names"]))))
    return (
        "<div style=\"{page}\"><div style=\"{card}\">"
        "<div style=\"{header}\">"
        "<div style=\"font-size:12px;opacity:.85;letter-spacing:2px;\">麦门灵签</div>"
        "<div style=\"font-size:26px;font-weight:500;margin-top:4px;\">第 {sign} 签</div>"
        "</div>"
        "<div style=\"padding:20px;\">"
        "<div style=\"background:#FFF7E0;border-left:4px solid {gold};padding:12px 14px;"
        "border-radius:6px;color:#633806;font-size:14px;line-height:1.7;\">{line}</div>"
        "<table style=\"width:100%;border-collapse:collapse;margin-top:16px;font-size:14px;\">"
        "{items}</table>"
        "<div style=\"display:flex;justify-content:space-between;align-items:baseline;"
        "margin-top:12px;padding-top:12px;border-top:1px dashed #D3D1C7;\">"
        "<span style=\"color:#8A8578;font-size:12px;\">原价 ¥{subtotal}</span>"
        "<span style=\"font-size:22px;font-weight:500;color:{red};\">实付 ¥{final}</span>"
        "</div>{saving}"
        "</div>"
        "<div style=\"{footer}\">{note}</div>"
        "</div></div>".format(
            page=PAGE_STYLE, card=CARD_STYLE, header=HEADER_STYLE, gold=BRAND_GOLD,
            sign=_esc(fortune["sign_no"]), line=_esc(fortune["line"]), items=items_html,
            subtotal=_yuan(fortune["subtotal_fen"]), final=_yuan(fortune["final_fen"]),
            red=BRAND_RED, saving=saving_line, footer=FOOTER_STYLE,
            note=_esc(fortune.get("note", ""))))


def derive_persona(stats):
    """确定性人设规则：同输入必得同结果，不靠大模型猜测。"""
    tags = []
    top_item = stats["top_items"][0][0] if stats["top_items"] else ""
    top_channel = stats["channels"][0][0] if stats["channels"] else ""
    top_names = [name for name, _ in stats["top_items"][:3]]
    if stats["late_night_ratio"] >= 0.3:
        tags.append("深夜麦门徒")
    if "薯条" in top_item:
        tags.append("薯条纯爱党")
    if top_item == "巨无霸":
        tags.append("巨无霸死忠")
    if any("零糖" in name for name in top_names):
        tags.append("零糖特调师")
    if top_channel == "麦乐送":
        tags.append("麦乐送信徒")
    elif top_channel == "到店自取":
        tags.append("到店老饕")
    if stats["periods"]["早餐"] >= 2:
        tags.append("早餐打卡员")
    if stats["periods"]["下午茶"] >= 1:
        tags.append("下午茶捕手")
    if stats["max_order_fen"] >= 5000:
        tags.append("团餐大家长")
    if stats["avg_fen"] <= 2500:
        tags.append("精打细算派")
    return tags[:3]


def render_persona_card(stats, period, store_count, note):
    """stats: solver.summarize_orders 的返回；period: 如「2026 年度」。"""
    tags = derive_persona(stats)
    tags_html = "".join(
        "<span style=\"background:{gold};color:#633806;border-radius:999px;"
        "padding:4px 12px;font-size:13px;font-weight:500;\">{tag}</span>".format(
            gold=BRAND_GOLD, tag=_esc(tag)) for tag in tags)
    top_items_html = "".join(
        "<div style=\"display:flex;justify-content:space-between;font-size:14px;"
        "padding:5px 0;color:#2C2C2A;\"><span>{rank}. {name}</span>"
        "<span style=\"color:#8A8578;\">×{count}</span></div>".format(
            rank=idx, name=_esc(name), count=count)
        for idx, (name, count) in enumerate(stats["top_items"][:3], start=1))
    channels_html = "".join(
        "<div style=\"display:flex;justify-content:space-between;font-size:13px;"
        "padding:4px 0;color:#5F5E5A;\"><span>{name}</span><span>{count} 单</span></div>".format(
            name=_esc(name), count=count) for name, count in stats["channels"])
    periods = stats["periods"]
    period_bar = "".join(
        "<div style=\"flex:1;text-align:center;\"><div style=\"height:{h}px;"
        "background:{red};border-radius:3px 3px 0 0;margin:0 2px;\"></div>"
        "<div style=\"font-size:10px;color:#8A8578;margin-top:4px;\">{label}</div></div>".format(
            h=max(4, count * 14), red=BRAND_RED, label=label)
        for label, count in periods.items())
    return (
        "<div style=\"{page}\"><div style=\"{card}\">"
        "<div style=\"{header}\">"
        "<div style=\"font-size:12px;opacity:.85;letter-spacing:2px;\">麦门年报</div>"
        "<div style=\"font-size:26px;font-weight:500;margin-top:4px;\">{period}</div>"
        "<div style=\"margin-top:12px;display:flex;flex-wrap:wrap;gap:8px;\">{tags}</div>"
        "</div>"
        "<div style=\"padding:20px;\">"
        "<div style=\"display:flex;justify-content:space-between;text-align:center;\">"
        "<div><div style=\"font-size:22px;font-weight:500;color:{red};\">¥{total}</div>"
        "<div style=\"font-size:11px;color:#8A8578;margin-top:2px;\">总消费</div></div>"
        "<div><div style=\"font-size:22px;font-weight:500;\">{orders}</div>"
        "<div style=\"font-size:11px;color:#8A8578;margin-top:2px;\">订单数</div></div>"
        "<div><div style=\"font-size:22px;font-weight:500;\">{items}</div>"
        "<div style=\"font-size:11px;color:#8A8578;margin-top:2px;\">件数</div></div>"
        "<div><div style=\"font-size:22px;font-weight:500;\">{stores}</div>"
        "<div style=\"font-size:11px;color:#8A8578;margin-top:2px;\">门店数</div></div>"
        "</div>"
        "<div style=\"margin-top:18px;font-size:13px;color:#8A8578;\">本命餐品 TOP3</div>"
        "<div style=\"margin-top:6px;\">{top}</div>"
        "<div style=\"margin-top:18px;font-size:13px;color:#8A8578;\">下单渠道</div>"
        "<div style=\"margin-top:6px;\">{channels}</div>"
        "<div style=\"margin-top:18px;font-size:13px;color:#8A8578;\">时段画像</div>"
        "<div style=\"display:flex;align-items:flex-end;margin-top:8px;height:80px;\">"
        "{period_bar}</div>"
        "</div>"
        "<div style=\"{footer}\">{note}</div>"
        "</div></div>".format(
            page=PAGE_STYLE, card=CARD_STYLE, header=HEADER_STYLE, gold=BRAND_GOLD,
            period=_esc(period), tags=tags_html, red=BRAND_RED,
            total=_yuan(stats["total_fen"]), orders=stats["order_count"],
            items=stats["item_count"], stores=store_count, top=top_items_html,
            channels=channels_html, period_bar=period_bar, footer=FOOTER_STYLE,
            note=_esc(note)))


def render_card_to_file(card_html, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">\n"
        "<title>麦门分享卡</title>\n</head>\n<body style=\"margin:0;\">\n{}\n</body>\n</html>\n".format(
            card_html),
        encoding="utf-8")
    return out_path


def run_demo(out_dir):
    out_dir = Path(out_dir)
    menu = REPO_ROOT / "fixtures" / "sample_menu.json"
    nutrition = REPO_ROOT / "fixtures" / "sample_nutrition.json"
    coupons_path = REPO_ROOT / "fixtures" / "sample_coupons.json"
    orders_path = REPO_ROOT / "fixtures" / "sample_orders.json"

    items = solver.load_items(menu, nutrition)
    coupons = solver.load_coupons(coupons_path)
    candidates = solver.enumerate_combos(items, budget_fen=40 * solver.FEN_PER_YUAN,
                                         kcal_max=800)
    plans = solver.select_plans(candidates, kcal_max=800)
    plan = plans["balanced"]
    combo = plan["combo"]
    opt = solver.optimize_coupons(combo, coupons)
    names = {c.coupon_id: c.name for c in coupons}

    fortune = {
        "sign_no": 42,
        "line": "此乃「随心配」上上签——简单点，吃麦的方式简单点。",
        "items": [{"name": i.name, "price_fen": i.price_fen} for i in combo],
        "subtotal_fen": opt["subtotal_fen"],
        "final_fen": opt["final_fen"],
        "saving_fen": opt["saving_fen"],
        "coupon_names": [names[cid] for cid in opt["coupons"]],
        "note": "mcd-believer · 麦门灵签｜构造样本数据演示，非实时价格；"
                "真实下单价以 calculate-price 核价为准。",
    }
    fortune_path = render_card_to_file(
        render_fortune_card(fortune), out_dir / "麦门灵签卡.html")

    orders_data = json.loads(orders_path.read_text(encoding="utf-8"))
    stats = solver.summarize_orders(orders_data["orders"])
    persona_path = render_card_to_file(
        render_persona_card(
            stats, "2026 年度", 3,
            "mcd-believer · 麦门年报｜构造样本数据演示；真实年报以 order-list "
            "实际返回为准，禁止编造。"),
        out_dir / "麦门年报人设卡.html")
    return fortune_path, persona_path, stats, fortune


def main():
    parser = argparse.ArgumentParser(description="mcd-believer 分享卡生成器")
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "demo_output"),
                        help="输出目录（默认 demo_output/）")
    args = parser.parse_args()
    fortune_path, persona_path, stats, _ = run_demo(args.out_dir)
    print("已生成：")
    print("  " + str(fortune_path))
    print("  " + str(persona_path))
    print("人设标签：" + " / ".join(derive_persona(stats)))


if __name__ == "__main__":
    main()

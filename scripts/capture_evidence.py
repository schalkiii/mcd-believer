#!/usr/bin/env python3
"""
mcd-believer 真实 MCP 返回留证器（只读工具，自动脱敏）

用真实 Token 调用**只读类** MCP 工具，把返回结果脱敏后存档到 evidence/，
作为参赛作品的真实性佐证。绝不调用任何写操作（下单/领券/抽奖/兑换）。

Token 只从环境变量读取，切勿写进代码或提交仓库：
    export MCD_MCP_TOKEN=你的Token        # Linux/macOS
    $env:MCD_MCP_TOKEN="你的Token"        # Windows PowerShell

用法：
    python scripts/capture_evidence.py                     # 留证默认只读工具集
    python scripts/capture_evidence.py --out evidence      # 自定义输出目录

脱敏规则：
  - 键名含 phone/mobile/address/account/token 等敏感词的字段 → 掩码
  - 任意字符串值中的 11 位手机号 → 掩码
  - 留证文件默认被 .gitignore 忽略，确认脱敏干净后可手动 git add
"""
import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

SENSITIVE_KEY_PATTERN = re.compile(
    r"(phone|mobile|tel|address|detail|account|token|secret|openid|userid|idcard)", re.I)
PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")

CAPTURE_PLAN = [
    ("now-time-info", {}),
    ("available-coupons", {}),
    ("query-my-coupons", {}),
    ("query-my-account", {}),
    ("query-lottery-info", {}),
    ("list-nutrition-foods", {}),
    ("campaign-calendar", {}),
    ("mall-points-products", {}),
    ("query-nearby-stores", {"beType": 1, "searchType": 2, "city": "北京市", "keyword": "麦当劳"}),
]


def desensitize(value, key_hint=""):
    """递归脱敏：敏感键掩码 + 11 位手机号掩码。"""
    if isinstance(value, dict):
        return {k: desensitize(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [desensitize(v, key_hint) for v in value]
    if isinstance(value, str):
        if SENSITIVE_KEY_PATTERN.search(key_hint) and value:
            return "***"
        return PHONE_PATTERN.sub("1**********", value)
    return value


def capture_tool(name, arguments):
    """调用只读工具并返回 result（复用 mcp_call 的 JSON-RPC 客户端）。"""
    import mcp_call
    if not mcp_call.TOKEN:
        sys.exit("错误：未设置环境变量 MCD_MCP_TOKEN（见脚本头部说明）")
    session_id = mcp_call.initialize()
    response, _ = mcp_call._post("tools/call", {"name": name, "arguments": arguments},
                                 session_id=session_id)
    return response.get("result", response)


def main():
    parser = argparse.ArgumentParser(description="真实 MCP 只读返回留证器")
    parser.add_argument("--out", default=str(REPO_ROOT / "evidence"), help="输出目录")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    captured_at = datetime.datetime.now().isoformat(timespec="seconds")
    summary = []

    for name, arguments in CAPTURE_PLAN:
        try:
            result = capture_tool(name, arguments)
            payload = {
                "tool": name,
                "arguments": arguments,
                "capturedAt": captured_at,
                "desensitized": True,
                "response": desensitize(result),
            }
            (out_dir / (name + ".json")).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            summary.append((name, "ok"))
            print("  [ok] " + name)
        except SystemExit:
            raise
        except Exception as exc:  # 单个工具失败不中断整体留证
            summary.append((name, "failed: " + str(exc)[:80]))
            print("  [fail] {} —— {}".format(name, str(exc)[:80]))

    ok_count = sum(1 for _, status in summary if status == "ok")
    print("\n留证完成：{}/{} 个工具成功，输出目录 {}".format(
        ok_count, len(CAPTURE_PLAN), out_dir))
    print("注意：留证文件默认被 .gitignore 忽略；提交前请人工复核脱敏是否干净。")


if __name__ == "__main__":
    main()

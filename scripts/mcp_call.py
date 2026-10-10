#!/usr/bin/env python3
"""
mcd-concierge MCP 客户端（独立/兜底用）

在无法原生接入 MCP 的环境下，用本脚本以 JSON-RPC 2.0 over Streamable HTTP
直连麦当劳中国 MCP（https://mcp.mcd.cn）。

Token 只从环境变量读取，切勿写进代码或提交到仓库：
    export MCD_MCP_TOKEN=你的Token        # Linux/macOS
    $env:MCD_MCP_TOKEN="你的Token"        # Windows PowerShell

用法：
    python mcp_call.py list                       # 列出全部工具
    python mcp_call.py call query-meals '{"storeCode":"1234","orderType":1,"beType":1}'
    python mcp_call.py call available-coupons '{}'
    python mcp_call.py call query-my-account '{}'

仅依赖标准库（urllib），无需 pip 安装。
"""
import json
import os
import sys
import urllib.request
import urllib.error

MCP_URL = os.environ.get("MCD_MCP_URL", "https://mcp.mcd.cn")
TOKEN = os.environ.get("MCD_MCP_TOKEN", "")
PROTOCOL_VERSION = "2025-03-26"

_req_id = 0


def _next_id():
    global _req_id
    _req_id += 1
    return _req_id


def _post(method, params=None, session_id=None):
    if not TOKEN:
        sys.exit("错误：未设置环境变量 MCD_MCP_TOKEN")
    body = {"jsonrpc": "2.0", "id": _next_id(), "method": method}
    if params is not None:
        body["params"] = params
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {TOKEN}",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    req = urllib.request.Request(MCP_URL, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            sid = resp.headers.get("mcp-session-id")
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')}")
    return _parse(raw), sid


def _parse(raw):
    """兼容普通 JSON 与 SSE（data: {...}）两种响应。"""
    raw = raw.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    raise ValueError(f"无法解析响应：{raw[:200]}")


def initialize():
    _, sid = _post("initialize", {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "mcd-concierge", "version": "1.0.0"},
    })
    return sid


def list_tools():
    sid = initialize()
    res, _ = _post("tools/list", {}, session_id=sid)
    tools = res.get("result", {}).get("tools", [])
    for t in tools:
        print(f"- {t['name']}: {t['description'].splitlines()[0][:80]}")
    print(f"\n共 {len(tools)} 个工具")


def call_tool(name, arguments):
    sid = initialize()
    res, _ = _post("tools/call", {"name": name, "arguments": arguments}, session_id=sid)
    print(json.dumps(res.get("result", res), ensure_ascii=False, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "list":
        list_tools()
    elif cmd == "call":
        if len(sys.argv) < 3:
            sys.exit("用法：call <tool_name> '<json_arguments>'")
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        call_tool(sys.argv[2], args)
    else:
        sys.exit(f"未知命令：{cmd}（支持 list / call）")


if __name__ == "__main__":
    main()

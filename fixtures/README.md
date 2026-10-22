# fixtures/ — 离线演示与测试样本数据

本目录存放**构造的示例数据**，用于 `demo.py`、`scripts/solver.py`、`scripts/card.py` 的离线演示与单元测试——**不需要 MCP Token、不联网**即可完整体验求解器与分享卡效果。

## ⚠️ 数据性质声明

- 所有 JSON 均为**构造样本**：字段结构对齐麦当劳 MCP 真实返回（`query-meals` / `list-nutrition-foods` / `available-coupons` / `query-my-coupons` / `query-store-coupons` / `order-list` / `query-my-account`），但**价格、编码、营养数值、订单记录均为演示用构造值，不是真实门店数据**。
- 涉及真实使用时，一律以 MCP 实时返回为准（见 `SKILL.md` 全局铁律「不臆造」）。生成留证请用 `scripts/capture_evidence.py`（真实调用 + 自动脱敏）。

## 文件清单

| 文件 | 对应 MCP 工具 | 用途 |
|---|---|---|
| `sample_menu.json` | `query-meals` | 门店菜单（餐品 code、现价、分类、标签） |
| `sample_nutrition.json` | `list-nutrition-foods` | 营养表（热量/蛋白质/钠等） |
| `sample_coupons.json` | `available-coupons` / `query-my-coupons` / `query-store-coupons` | 三路券池 |
| `sample_orders.json` | `order-list` + `query-my-account` | 历史订单 + 积分账户 |

## 如何替换为真实数据

```bash
export MCD_MCP_TOKEN=你的Token
python scripts/mcp_call.py call query-meals '{"storeCode":"1990622","orderType":1,"beType":1}' > fixtures/sample_menu.json
```

（留存前请自行脱敏：去掉手机号、addressId、accountId 等字段。）

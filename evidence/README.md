# evidence/ — 真实 MCP 返回留证

本目录用于存放**真实调用**麦当劳 MCP 只读工具的返回结果（自动脱敏），作为参赛作品真实性的佐证。

## 如何生成

```bash
export MCD_MCP_TOKEN=你的Token        # Linux/macOS
python scripts/capture_evidence.py
```

脚本会依次调用以下**只读**工具并脱敏存档（绝不调用任何写操作）：

| 工具 | 说明 |
|---|---|
| `now-time-info` | 服务时钟 |
| `available-coupons` | 麦麦省可领券 |
| `query-my-coupons` | 我的券包 |
| `query-my-account` | 积分账户 |
| `query-lottery-info` | 抽奖活动 |
| `list-nutrition-foods` | 营养表 |
| `campaign-calendar` | 活动日历 |
| `mall-points-products` | 积分商城目录 |
| `query-nearby-stores` | 附近门店（示例城市：北京） |

## 脱敏与提交策略

- 脚本自动掩码：手机号（11 位）、`phone/address/account/token` 等敏感键。
- **留证 JSON 默认被 `.gitignore` 忽略**（含个人数据）。确认脱敏干净后，可手动 `git add -f evidence/xxx.json` 提交。
- 留证反映「某时间点的真实接口行为」，价格/库存随时效变化，不代表永久数据。

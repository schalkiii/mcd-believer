# WorkBuddy 开发上下文 · workbuddy.md

本文件记录使用 WorkBuddy 开发 `mcd-concierge` Skill 的上下文，用于核验 WorkBuddy 联动活动奖励条件。

## 环境准备

1. 在 https://open.mcd.cn/mcp 申请麦当劳 MCP Token。
2. WorkBuddy 左侧【专家·技能·连接器】→【连接器】→【自定义连接器】→【配置MCP】，粘贴：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer 你的MCP_TOKEN" }
    }
  }
}
```

3. 回到【自定义连接器】将 `mcd-mcp` 启用。

## 开发对话脉络（Prompt → 产物）

在 WorkBuddy 对话框中按以下主线推进，逐步沉淀出本 Skill 的文件：

1. **摸清能力**：要求列出 `mcd-mcp` 全部工具及入参 → 得到 tools/list 的 35 个工具清单（含 `query-survey-coupons`、`query-promotions` 两个隐藏工具），整理为 `references/tools-reference.md`。
2. **点餐主线**：让 AI 用 `query-nearby-stores → query-meals → calculate-price → create-order` 走通一次到店自取，记录 beType/beCode/orderType 的传参铁律与"价格单位为分"的坑 → 沉淀 `references/ordering.md`。
3. **省钱主线**：对比 `available-coupons / auto-bind-coupons / query-my-coupons / query-store-coupons / query-promotions` 的差异 → 沉淀 `references/savings.md`。
4. **营养主线**：用 `list-nutrition-foods` 按目标热量配餐 → 沉淀 `references/nutrition.md`。
5. **积分主线**：`query-my-account → mall-points-products → mall-product-detail → mall-create-order`，以及 `query-lottery-info → draw-lottery`（强调必须先展示 drawDecision 再确认）→ 沉淀 `references/points-mall.md`。
6. **活动/派对主线**：`campaign-calendar` 情报 + `query-party-* → party-order-create` 逐步预约 → 沉淀 `references/activities.md`。
7. **收敛入口**：把六条主线抽象为意图路由表 + 全局铁律 + 默认流程 → 沉淀 `SKILL.md`。

## 关键调试结论（写进 Skill 的硬约束）

- beCode 仅 beType=2/5/6 传；到店自取(beType=1) 不传，否则报错。
- calculate-price 返回金额为分，展示需 ÷100。
- 商城 shopId=2 用 mall-create-order、shopId=5 走派对链路；多商品兑换必须逐个下单且排队。
- 抽奖资格只以 drawDecision 为准，禁止据 availableTimes=0 自行推断；禁止试抽/连抽。
- 工具结果优先读 structuredContent。

## 导出说明

以上脉络可由 WorkBuddy 会话记录导出替换/补充。本文件为人工整理的开发上下文摘要。

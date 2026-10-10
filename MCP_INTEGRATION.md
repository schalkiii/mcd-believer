# MCP 集成说明 · MCP_INTEGRATION.md

## 使用的 MCP Server

本项目基于麦当劳中国官方 MCP Server：

- **服务端点**：`https://mcp.mcd.cn`
- **传输协议**：Model Context Protocol（MCP）over Streamable HTTP
- **认证方式**：请求头 `Authorization: Bearer <MCP Token>`（在 https://open.mcd.cn/mcp 申请）
- **限流**：每个 Token 每分钟最多 600 次请求（超限返回 429）

## 实际使用的 MCP 工具（35 个，全量覆盖）

通过 `tools/list` 实测获取，比官方 README 多识别出 `query-survey-coupons`、`query-promotions` 两个工具。按业务分组：

| 分组 | 工具 | 业务价值 |
|---|---|---|
| 点餐交易 | query-nearby-stores, delivery-query-addresses, delivery-create-address, delivery-query-stores, query-meals, query-meal-detail, query-meal-assistance, calculate-price, create-order, query-order, cancel-order, order-list | 到店/得来速/麦乐送/团餐的选店—选品—算价—下单—跟单闭环 |
| 优惠券/促销 | available-coupons, auto-bind-coupons, query-my-coupons, query-store-coupons, query-promotions | 领券、判断本单可用券、满减满折凑单最优 |
| 营养 | list-nutrition-foods | 按目标热量/偏好配餐 |
| 积分/商城/抽奖 | query-my-account, mall-points-products, mall-product-detail, mall-create-order, mall-order-list, mall-order-detail, query-lottery-info, draw-lottery, query-my-prizes | 积分资产与过期提醒、兑换商品/券、参与抽奖、查中奖 |
| 活动/派对 | now-time-info, campaign-calendar, query-party-city, query-party-store, query-party-store-date, query-party-store-session, party-order-create | 活动日历情报、主题派对逐步预约下单 |
| 售后 | query-survey-coupons | 订单满意度答卷与关联奖券核销状态 |

## 关键调用流程

### 点餐下单
```
选场景(beType/orderType)
  → 选店 query-nearby-stores / (delivery-query-addresses → delivery-create-address → delivery-query-stores)
  → query-meals（取餐品 code、现价）
  →（可选）query-meal-detail 看套餐/特调、query-store-coupons 取可用券
  → calculate-price（带 couponId/特调/随单购，返回单位为分）
  → 用户确认 → create-order（到店带 takeWayCode / 外送带 addressId）→ 返回 payH5Url、pickupCode
  → query-order 跟单 / cancel-order 取消
```

### 积分商城兑换
```
query-my-account → mall-points-products → mall-product-detail(取 skuId, shopId)
  → shopId=2：mall-create-order（多商品逐个下单且排队）
  → shopId=5：转派对链路 party-order-create
```

### 积分抽奖（严格确认）
```
query-lottery-info → 展示 drawDecision.nextConsumption / resourceEligible
  → 用户明确确认 → draw-lottery（禁止试抽/连续抽）→ query-my-prizes
```

### 主题派对（逐步，不跳步）
```
mall-points-products(spuId) → query-party-city → query-party-store → query-party-store-date
  → query-party-store-session → party-order-create
```

## 编排要点（写入 Skill 的硬约束）

- **身份三件套**：`storeCode` 全链路透传；`beCode` 仅在 beType=2/5/6 时传递，来源随场景不同；`orderType` 到店/得来速=1，外送/团餐=2。
- **价格单位**：`calculate-price` 输出为分，展示前 ÷100。
- **返回值解析**：优先读 `structuredContent`，回退解析 `content[].text`。
- **写操作需确认**：下单/兑换/抽奖/领券前必须复述并取得用户确认。

## 业务价值

把分散在 35 个工具上的麦当劳服务能力，收敛成一个可按自然语言驱动的全场景助手，降低普通用户使用 MCP 的门槛，让"吃什么、怎么点省、积分怎么用"这三件事在一轮对话内闭环解决。

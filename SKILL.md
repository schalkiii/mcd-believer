---
name: mcd-believer
description: 麦门信徒 —— 麦当劳中国 MCP 全能助手。基于 mcd.mcp（https://mcp.mcd.cn）35 个工具，覆盖到店/外送/得来速/团餐点餐下单、省钱领券、营养配餐、积分商城兑换、积分抽奖、活动日历、主题派对预约等全场景。Use when 用户想吃麦当劳/点麦乐送/到店取餐/团餐、想找优惠领券、按热量配餐、用积分兑换商品或抽奖、看本月活动、预约生日派对品鉴会，或询问"今天吃什么""我有多少积分""帮我下单这份"等任何麦当劳相关需求。
---

# 麦门信徒 · 麦当劳 MCP 全能助手

一个 Skill 打通麦当劳中国 MCP 的全部能力：**选店 → 选品 → 算价 → 下单 → 跟单**，外加省钱、营养、积分、抽奖、活动、派对六大场景。所有结论必须来自 MCP 工具实时返回，禁止编造价格、门店、券码、订单号。

## 能力路由

先判断用户意图属于哪一类，再按对应 reference 的操作手册执行。只加载需要的那一份。

| 用户意图 | 场景 | 操作手册 |
|---|---|---|
| 点餐 / 下单 / 到店取 / 麦乐送 / 得来速 / 团餐 / 取消订单 / 查订单 | 点餐交易 | [references/ordering.md](references/ordering.md) |
| 领券 / 有什么优惠 / 可用券 / 满减满折 / 省钱搭配 | 省钱顾问 | [references/savings.md](references/savings.md) |
| 热量 / 营养 / 按指定热量配餐 / 低卡 | 营养配餐 | [references/nutrition.md](references/nutrition.md) |
| 积分 / 积分商城 / 兑换商品 / 兑换券 / 抽奖 / 我的奖品 | 积分商城与抽奖 | [references/points-mall.md](references/points-mall.md) |
| 本月活动 / 最近有什么优惠 / 预约生日派对 / 品鉴会 / 体验营 | 活动与派对 | [references/activities.md](references/activities.md) |
| 需要确认某个工具的准确入参 | 任意 | [references/tools-reference.md](references/tools-reference.md) |

## 全局铁律（所有场景通用）

1. **身份三件套传递**：`storeCode` 来自选店；`beCode` 依 `beType` 而定 —— 到店自取(beType=1) **不传** beCode；得来速(beType=5)、麦乐送(beType=2)、团餐(beType=6) **必须**传 beCode（到店来自 `query-nearby-stores`，外送来自 `delivery-query-stores`）。`orderType`：到店/得来速=1，外送/团餐=2。同一链路参数必须一致透传。
2. **价格单位**：`calculate-price` 返回的金额字段单位为**分**，展示给用户前除以 100 转为元。`query-meals` 的 `currentPrice/originalPrice` 已是元，直接用。
3. **预约时间**：仅当用户明确要预约下单时才传 `reservationDate`（`yyyy-MM-dd HH:mm`），即时单不传。
4. **一步步来**：派对、商城兑换等多步链路，每步完成后**必须等用户明确选择再进下一步，禁止跳步**。
5. **确认再花钱**：下单(`create-order`/`mall-create-order`/`party-order-create`)、领券(`auto-bind-coupons`)、抽奖(`draw-lottery`)等会产生真实资产变动的操作，执行前必须向用户复述关键信息并取得明确"确认"。
6. **特调 key 规则**：套餐/单品特调，选中的项用 `selectedKey`，未选中但 `unselectedKey` 非空的项也必须传入并用 `unselectedKey`（详见 ordering.md）。
7. **不臆造**：任何门店、餐品编码、券 ID、订单号、积分、奖品都必须来自工具返回；缺信息就追问用户或调用对应查询工具。

## 交互式默认流程

当用户只说"我想吃麦当劳"这类模糊需求时，按此主线下探：

1. 确认场景：到店自取 / 得来速 / 麦乐送 / 企业团餐？
2. 确认地点：到店→`query-nearby-stores`；外送→`delivery-query-addresses`（无地址则 `delivery-create-address`）→`delivery-query-stores`。
3. 取菜单：`query-meals`（拿到餐品 code、分类、现价、随单购标记）。
4. 想要优惠：叠加 `references/savings.md` 流程领券 + `query-store-coupons`。
5. 选品/配餐：需要看套餐组成或换菜 → `query-meal-detail`；按热量配 → `references/nutrition.md`。
6. 算价：`calculate-price`（带上 couponId / 特调 / 随单购 / 餐具）。
7. 下单：用户确认后 `create-order`，回传 `payH5Url` 支付链接，引导支付。
8. 跟单：支付后 `query-order` 查状态；要退用 `cancel-order`。

## 快速开始

在支持 MCP 的客户端（WorkBuddy / Cursor / Cherry Studio / Trae 等）中配置 `mcd-mcp`（见 `mcp-config.example.json`），直接用自然语言触发，例如：

- "帮我在公司附近的麦当劳点一份麦乐送，预算 40，不要辣的" → 走点餐主线 + 省钱
- "我想吃麦当劳，帮我配一顿 500 大卡以内的" → 走营养配餐
- "我有多少积分？能兑换什么？" → 走积分商城
- "这个月有什么活动？" → 走活动日历

无法原生接入 MCP 的环境，可用 `scripts/mcp_call.py` 以 JSON-RPC 直连（见脚本头部说明）。

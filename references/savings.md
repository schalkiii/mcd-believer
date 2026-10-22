# 省钱顾问手册（领券 / 可用券 / 促销规则 / 凑单）

目标：帮用户**领到能领的券、用对当前门店/订单能用的券、并按满减满折最优凑单**，最终把优惠带进 `calculate-price`。

## 券的四种状态，别混用工具

| 用户想干嘛 | 用哪个工具 | 说明 |
|---|---|---|
| 有什么**可以领**的优惠 | `available-coupons` | 麦麦省可领券列表（券名/图片/状态/标签） |
| 帮我**一键领掉** | `auto-bind-coupons` | 自动领取当前所有可用券；返回成功/失败清单。**执行前需用户确认** |
| 我**已经有哪些券** | `query-my-coupons` | 卡包资产总览；**不做门店/渠道校验**，不保证能用于当前单 |
| 当前**门店/订单能用什么券** | `query-store-coupons` | 需已定门店：传 `storeCode`+`orderType`+`beType`（外送/团餐/得来速带 `beCode`），预约带 `reservationDate` |

要点：真正要下单，以 `query-store-coupons` 返回的 `couponId/couponCode` 为准；`promotionId`、`products[].productCode` 用于关联商品。

## 促销规则（满减/满折）

- **团餐(beType=6)** 专用 `query-promotions`：返回 `promotionType`(31满额减/33订单折扣)、`ruleCategory`(30满折/40满减)、`ruleDetail.orderReduce.reduceInfo[]`（`startDiscountPoint` 门槛 / `reduceAmount` 减免）、`ruleDetail.orderDiscount.orderDiscount`（`startDiscountPoint` 门槛 / `discount` 如 30=7折）、`products`（type=1包含/2不包含/3全部）。
  - **工具只给原始规则，最优方案要你自己算**：把候选餐品按门槛排列，找"再多买一点能跨到更大减免档"的凑单建议。
- 到店/外送的满减多通过券（`query-store-coupons`）体现，没有独立促销工具。

## 标准省钱流程

1. 先问场景与门店（走 ordering.md 第 0–1 步拿到 storeCode/beCode/orderType/beType）。
2. `available-coupons` → 有想领的 → 确认后 `auto-bind-coupons`。
3. `query-store-coupons`（带门店参数）→ 得到本单可用券集合。
4. 让用户选品（`query-meals`）→ 对候选券 × 商品组合，用 `calculate-price`（item 带 `couponId/couponCode`）实测应付。
5. 对比"不用券" vs "用不同券"的 `discount` 与 `price`，把最省的方案报给用户，并说明 `enjoyable.balance`（还差多少可享更大优惠）。
6. 用户认可 → 走 `create-order`。

**确定性实现**：券组合枚举已落地为 `scripts/solver.py` 的 `optimize_coupons`——满减/折扣/品类范围/同组互斥/适用范围不重叠（一张餐品最多带一张券）的保守子集枚举，输出最优实付与每张券的节省明细。这是**候选生成**；真实可叠性以 `calculate-price` 返回为准。

## 输出建议

给用户一句话结论：**"这单原价 X 元，用了【券名】省 Y 元，实付 Z 元；再加一件 A 可跨到更高档再省 W 元。"** 数字全部来自工具返回，价格分→元换算。

## 资产到期倒计时账（券 + 积分 + 抽奖机会）

用户问"我有什么快过期的 / 帮我把资产盘一遍"时，一次拉齐三处数据源做归并：
1. `query-my-coupons` → 券包内每张券的有效期/核销条件；
2. `query-my-account` → `currentMouthExpirePoint`（本月将过期积分）、`nextMouthExpirePoint`（下月）；
3. `query-lottery-info` → 剩余抽奖次数及其有效期字段（若有）。
输出一张**按到期日升序**的倒计时表：`资产 | 面额/数量 | 到期日 | 建议用法（下单用券 / 商城兑换 / 抽奖）`。规则：
- 7 天内到期标🔴"末班车"，30 天内标🟡；已过期的单独列出并告知无法再用。
- 结合 `campaign-calendar` / `query-store-coupons` 给出"本周内用掉它"的具体行动（哪张券配哪单）。
- 到期提醒只陈述工具返回的日期，不自造"还剩 N 天"以外的推断。

## 凑单红线：主动劝退亏本凑单

跨满减档前必算"边际账"：跨档多花的金额 Δ买 对比多省的金额 Δ省。
- Δ买 > Δ省（花了 15 元只多省 8 元）→ **明确建议不要凑**，除非用户本来就需要那件商品。
- 临期券用不上就直说用不上，不为消耗券而推荐不吃的餐品。
- 用户口味/健康约束（profile.md 忌口、nutrition.md 热量目标）优先级高于省钱目标，冲突时先保约束再谈最优。

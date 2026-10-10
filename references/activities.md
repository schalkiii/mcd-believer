# 活动日历与主题派对手册

覆盖两块：**本月营销活动日历**（含优惠券/品鉴会/派对情报），以及**主题派对的逐步预约下单**。

## 1. 活动日历 `campaign-calendar`

- 不传 `specifiedDate` → 返回当月全部活动（进行中/往期/未来）。
- 传 `specifiedDate`（`yyyy-MM-dd`）→ 以该日为锚点，返回当天及时间线上最邻近的前后各一个有活动的日子（共三天）。
- 若用户说的是相对时间（"下周六""国庆那天"）而你不确定今天几号：先 `now-time-info` 拿当前日期，再换算成 `specifiedDate`。
- 返回 `dailyList[].events[]`，`eventType`：0活动 / 1神秘期 / 2优惠券 / 3品鉴会 / 4CMS文章 / 5麦麦省 / 6派对；含 `couponInfo`（券码/核销时间段/周几限制）、`price`、`articleDto`。`subscribedEvents` 为已订阅活动。
- 用法：帮用户做"哪天买最划算 / 最近有什么可参加"的情报式回答，可按日期聚合成行动清单。

## 2. 主题派对预约（生日/主题派对/体验营/品鉴会/读书会/积分兑换活动）

**严格逐步，每步完成后等用户明确选择再进下一步，禁止跳步。** 前提：活动商品来自商城，需先有 `spuId`。

1. 选商品：`mall-points-products` → 让用户选一个 SPU，取 `spuId`（也可 `mall-product-detail`）。确认 `shopId=5` 才是派对链路。
2. 选城市：`query-party-city`（`spuId`）→ 城市列表 `code / name / latitude / longitude`。
3. 选门店：`query-party-store`（`code`+`latitude`+`longitude`+`spuId`）→ 门店列表 `code(餐厅编码)/name/address/distance`。
4. 选日期：`query-party-store-date`（`storeCode`+`spuId`）→ 可预约 `date` 列表。
5. 选场次：`query-party-store-session`（`spuId`+`storeCode`+`dateStr`）→ 场次 `id / timeStart / timeEnd / leftNum / partyMin / partyMax / price`。
6. 下单：`party-order-create`
   - `partyType`：商品 `partyType=1`→包场(1)；`=2`→拼团(2)；`=-1`→需询问用户选 1 还是 2。
   - 携带 `spuId, skuId, code(城市), storeCode, dateStr, id(场次), timeStart, timeEnd, leftNum, count(人数)`。
   - 人数校验**以下单接口返回为准**，不要用 `partyPeople` 展示值前置校验。
   - 下单前向用户复述"城市/门店/日期/场次/类型/人数"确认。

## 输出建议

- 日历类：按日期分组，标注活动类型与可用券、核销时段，给"今天/本周最值得参与"的一句话结论。
- 派对类：每一步都用编号列表呈现候选，明确告诉用户"回复序号选择"，直到进入下单确认。

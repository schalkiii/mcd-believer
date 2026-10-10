# 积分商城与抽奖手册（查询 / 兑换 / 抽奖 / 奖品 / 订单）

目标：帮用户**看清积分资产、用积分兑换商品或券、参与积分抽奖、查兑换与中奖记录**。

## 1. 积分资产

- `query-my-account`：可用积分 `availablePoint`、累计、冻结、**本月/下月将过期积分** `currentMouthExpirePoint/nextMouthExpirePoint`、已过期。
  - 主动提醒"有 X 积分本月到期，要不要用掉"——这是高价值差异化点（对应"积分末班车"需求）。

## 2. 兑换商品/券

标准链路（**每步等用户确认再进下一步**）：

1. `mall-points-products`（可选 `catRuleIds` 类目筛选）→ 列可兑换 SPU：`spuId / spuName / point / price / status / shopId`。
   - 类目码：商品券`1>4`、实物`2`、周边`2>8`、礼品卡`2>9`、生日派对`1>6>20`、主题派对`1>6>21`、体验营`1>6>22`、品鉴会`1>6>25`、读书会`1>6>34`、积分兑换活动`1>6>40`。
   - `status`：1仓库 2上架 3售罄 4下架 5预热 —— 只推 2上架。
2. `mall-product-detail`（`spuId`）→ 取 `skuList[].skuId`、`spuCategory`(1虚拟/2实物)、`shopId`、`note`(购买须知原文展示，**不得从中提取数值做校验**)、限购 `spuLimit`(仅展示)。
3. 按 `shopId` 分流下单：
   - **shopId=2 → 普通兑换** 用 `mall-create-order`（`skuId`,`spuCategory`,count；实物需 `addressId` 来自 `delivery-create-address`）。**多个商品必须逐个下单且排队**，前单成功再下下一单。
   - **shopId=5 → 活动/派对类** 改走 `references/activities.md` 的 `party-order-create` 链路。
4. 兑换成功返回 `orderId / point(消耗积分) / coupons[].couponCodes / payH5Url`；告知"可到麦当劳 APP 查看凭证"。

> ⚠️ `mall-create-order` 仅用于**不需要选门店场次**的商品券/实物；需选城市·门店·日期·场次的活动（生日/主题派对、品鉴会、读书会、积分兑换活动）一律用 `party-order-create`。

## 3. 积分抽奖（严格遵守）

1. `query-lottery-info` → 读 `activityStatusText`、`drawPoint`、`drawTypeText`、`availableTimes`、`availablePoint`、`prizes[]`，以及**权威的 `drawDecision`**。
2. **必须**向用户展示 `drawDecision.nextConsumption`（本次实际消耗：type=NONE/POINTS/CHANCES，points/chances、text 说明）与 `resourceEligible`；若 `fallbackConsumption` 非空，说明"本次优先消耗次数，用完后转为消耗积分"。
3. **只有用户明确确认"要抽"才**调 `draw-lottery`；"试试看""能抽就抽"不算确认。
4. 判断能否抽**只以 `drawDecision` 为准**：不得因为 `availableTimes=0/null` 或 `drawTypeText` 自行推断。混合规则下 `availableTimes=0` 且 `nextConsumption.type=POINTS` 仍可用积分抽。
5. **禁止试抽/自动连续抽**；同一用户短时重复调用会返回"操作太频繁"，不扣积分。
6. `draw-lottery` 返回 `win`、`prizes[]`、`consumePoint`、`remainPoint/remainChance`、`status`；失败时 `status.message` 原样展示，不改写。
7. `query-my-prizes`（pageNum/pageSize）：查历史中奖记录（可用/已用/过期/已领/失效）。

## 4. 兑换订单查询

- `mall-order-list`（lastId,size）：商城近一年订单列表；`mall-order-detail`（orderId）：状态、支付积分/金额、物流、派对预订信息。

## 5. 周边 / 上新 / 末班车联动

- **周边猎人**：用户问"最近有什么新周边/玩具能换" → `mall-points-products` 带 `catRuleIds=2>8`（实物周边），按 `status=2` 上架过滤，重点报 `point`（所需积分）与 `price`；生日/乐园餐玩具类常在 `1>6>20` 派对类目，两处都查。
- **积分末班车**：`query-my-account` 发现 `currentMouthExpirePoint > 0` 时主动提醒，并直接给三条出路：兑换低门槛商品券（`catRuleIds=1>4`）、参加抽奖（§3）、或叠加到近期订单；完整资产倒计时盘法见 savings.md。

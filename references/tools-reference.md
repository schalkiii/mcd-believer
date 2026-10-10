# 麦当劳 MCP 工具速查表（35 个）

服务端点 `https://mcp.mcd.cn`（Streamable HTTP，`Authorization: Bearer <TOKEN>`，限流 600 次/分钟）。以下为 tools/list 实测返回的工具与关键参数。

## 点餐交易

| 工具 | 作用 | 关键入参 |
|---|---|---|
| `query-nearby-stores` | 到店/得来速选店 | beType(1/5), searchType(1收藏/2位置), city, keyword |
| `delivery-query-addresses` | 查配送地址 | 无 |
| `delivery-create-address` | 新增配送地址 | city, address, addressDetail, contactName, phone(11位), gender |
| `delivery-query-stores` | 外送/团餐选店 | addressId, beType(2/6) |
| `query-meals` | 在售菜单 | storeCode, orderType(1/2), beType, beCode?, reservationDate? |
| `query-meal-detail` | 套餐组成/特调 | storeCode, orderType, beType, beCode?, code |
| `query-meal-assistance` | 团餐助餐(仅beType=6) | storeCode, beType=6, orderType, beCode?, reservationDate? |
| `calculate-price` | 算价(含优惠) | storeCode, orderType, beType, beCode?, items[], gmServiceCode?, withOrder?, needTableware? |
| `create-order` | 下单 | storeCode, orderType, beType, beCode?, items[], takeWayCode(到店)/addressId(外送), reservationDate? |
| `query-order` | 订单详情/进度 | orderId |
| `cancel-order` | 取消订单 | orderId, cancelReasonCode(1/2/3/4/5/-1) |
| `order-list` | 历史订单(非商城) | 无 |

## 优惠券 / 促销

| 工具 | 作用 | 关键入参 |
|---|---|---|
| `available-coupons` | 可领券列表(麦麦省) | 无 |
| `auto-bind-coupons` | 一键领取全部可用券 | 无 |
| `query-my-coupons` | 卡包已有券(不做门店校验) | page, pageSize |
| `query-store-coupons` | 当前门店/订单可用券 | storeCode, orderType, beType, beCode?, reservationDate? |
| `query-promotions` | 团餐满减/满折原始规则(仅beType=6) | storeCode, orderType=2, beType=6, beCode?, reservationDate? |

## 营养

| 工具 | 作用 | 关键入参 |
|---|---|---|
| `list-nutrition-foods` | 餐品营养成分(能量/蛋白/脂肪/碳水/钠/钙) | 无 |

## 积分 / 商城 / 抽奖

| 工具 | 作用 | 关键入参 |
|---|---|---|
| `query-my-account` | 积分账户(可用/冻结/将过期) | 无 |
| `mall-points-products` | 可兑换商品列表 | catRuleIds?(逗号分隔类目码) |
| `mall-product-detail` | 商品详情+SKU | spuId |
| `mall-create-order` | 积分兑换下单(仅shopId=2) | skuId, spuCategory(1虚拟/2实物), count?, addressId?(实物) |
| `mall-order-list` | 商城订单列表 | lastId?, size? |
| `mall-order-detail` | 商城订单详情 | orderId |
| `query-lottery-info` | 抽奖活动信息+drawDecision | 无 |
| `draw-lottery` | 执行一次抽奖(需先展示nextConsumption并确认) | 无 |
| `query-my-prizes` | 我的中奖记录 | pageNum?, pageSize? |

## 活动 / 派对

| 工具 | 作用 | 关键入参 |
|---|---|---|
| `now-time-info` | 服务器当前时间 | 无 |
| `campaign-calendar` | 当月活动日历 | specifiedDate?(yyyy-MM-dd) |
| `query-party-city` | 派对可参与城市 | spuId |
| `query-party-store` | 城市下派对门店 | code, latitude, longitude, spuId |
| `query-party-store-date` | 门店可预约日期 | storeCode, spuId |
| `query-party-store-session` | 门店某日场次 | spuId, storeCode, dateStr |
| `party-order-create` | 派对下单(shopId=5, 仅包场/拼团) | partyType, spuId, skuId, code, storeCode, dateStr, id, timeStart, timeEnd, leftNum, count |

## 售后 / 满意度

| 工具 | 作用 | 关键入参 |
|---|---|---|
| `query-survey-coupon` | 订单满意度答卷+关联奖券核销状态 | orderId |

## 通用约定速记

- **读返回值**：工具结果优先取 `structuredContent`（已解析好的 JSON 对象）；没有时再解析 `content[].text`（内含 "## Original Response" 后的 JSON）。`isError=true` 表示失败，把 message 原样告知用户。
- **beCode 传递**：仅 beType=2/5/6 需要；beType=1 不传。来源：到店/得来速→`query-nearby-stores`，外送/团餐→`delivery-stores`。
- **orderType**：到店自取+得来速=1；麦乐送+团餐=2。
- **价格单位**：`calculate-price` 输出为「分」，÷100 展示；`query-meals` 已是「元」。
- **商城 shopId 分流**：=2 走 `mall-create-order`；=5 走 `party-order-create`。
- **抽奖/下单/兑换/领券**：均为写操作，执行前须用户明确确认。

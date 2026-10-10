# 点餐交易手册（到店 / 外送 / 得来速 / 团餐）

目标：把用户从"想吃"带到"拿到取餐码 / 支付链接 / 配送进度"。核心链路：
**选店 → 取菜单 →（看详情/换菜）→（领券）→ 算价 → 下单 → 跟单**。

## 0. 先锁定场景参数（决定后续一切传参）

| 场景 | beType | orderType | beCode | 选店工具 |
|---|---|---|---|---|
| 到店自取 | 1 | 1 | 不传 | `query-nearby-stores` |
| 得来速(DT) | 5 | 1 | 必传 | `query-nearby-stores` |
| 麦乐送到家 | 2 | 2 | 必传 | `delivery-query-stores` |
| 企业团餐 | 6 | 2 | 必传 | `delivery-query-stores` |

一旦选定，`storeCode`（+ 需要时的 `beCode`）在 `query-meals / query-meal-detail / query-store-coupons / calculate-price / create-order` 全链路保持一致。

## 1. 选店

- **到店/得来速** → `query-nearby-stores`
  - `beType`=1 或 5；`searchType`=2 按位置搜（需 `city`+`keyword`），`=1` 搜收藏餐厅。
  - 展示 `storeName / address / businessStatus`；`reservation=true` 时完整列出 `reservationTimeOptions`（`today=true` 标注"今天"）。
  - 得来速(beType=5) 记住返回的 `beCode`。
- **外送/团餐** → 先 `delivery-query-addresses`
  - 无地址 → `delivery-create-address`（需真实 `city/address/addressDetail/contactName/phone`，phone 为 11 位）。
  - 拿到 `addressId` → `delivery-query-stores`（`beType`=2 麦乐送 / 6 团餐）→ 得 `storeCode`+`beCode`+可预约时段。
- **团餐(beType=6)** 额外：引导用户给 **预算金额 + 人数**（算人均），并在算价前调 `query-meal-assistance` 取 `gmServiceCode`。

## 2. 取菜单 `query-meals`

传 `storeCode`（+ 场景需要的 `beCode`、`orderType`、`beType`，预约则带 `reservationDate`）。返回：
- `categories[].meals[].{code, tags}` —— 选品用它，`code` 即下单用的 `productCode`。
- `meals` 映射表含 `name / currentPrice(元) / originalPrice(元) / canWithOrder / withOrder`。
- `frequent` 常点推荐，可用于"不知道吃啥"时提示。

## 3. 看套餐详情 / 换菜 / 特调 `query-meal-detail`

传餐品 `code` + 场景参数。返回 `rounds`（选配轮次）、`choices`（含 `isDefault`、`diffPrice`、`modification`）。
- `supportModify=true` → 商品名后标注 **【可特调】**，但**不要主动展开**特调列表，用户问了再给。
- 总结默认搭配（`isDefault=1` 的 choices），引导"回复'查看特调'"。
- **特调传参规则**（给 calculate-price / create-order 用）：
  - 选中的特调项：`key = selectedKey`；
  - 同组内未选中、但 `unselectedKey` 非空的项：也要传，`key = unselectedKey`；
  - 即"该组全部传入，选中用 selectedKey、未选用 unselectedKey"。

## 4. 算价 `calculate-price`

传 `items[{productCode, quantity, couponId?, couponCode?, modification?, roundList?}]` + 场景参数（+ 团餐 `gmServiceCode`、随单购 `withOrder`、`needTableware`）。
- **返回金额单位是分**：`price/originalPrice/discount/deliveryPrice/packingPrice/tablewarePrice` 全部 ÷100 展示。
- `takeWayList[]` —— 到店/得来速下单前需从里面选 `takeWayCode`。
- `enjoyable/enjoyed` 向用户说明"已享受/还差多少可享"的优惠，引导凑单。
- 算完引导："确认价格后可以说'创建订单'下单"。

## 5. 下单 `create-order`

确认场景参数 + `items`（同算价结构）+ `storeCode`：
- `orderType=1` 必带 `takeWayCode`（来自 calculate-price）。
- `orderType=2` 必带 `addressId`；可引导 `remark`（≤50 字，如"无接触配送"）。
- 团餐带 `gmServiceCode`；预约带 `reservationDate`。
- 返回 `payH5Url`（支付链接）、`orderId`、`pickupCode`（取餐码）、堂食外带柜可能有 `lockerQrCode`（按 `![alt](url)` 展示）。
- 引导用户支付，支付后回复"支付完成/失败"→ 用 `query-order` 复查状态。

## 6. 跟单 / 取消

- `query-order`（`orderId`）：状态 `1待支付 2配餐中-已支付 4配送中 6已完成 7已取消 8已评价 10餐厅确认配餐中`；展示配送、取餐码、金额明细。
- `cancel-order`（`orderId` + `cancelReasonCode`：1改主意/2重复/3点错/4地址电话错/5时间错/-1其它）。
- `order-list`：查近期历史订单（商城订单请用 `mall-order-list`）。
- `query-survey-coupon`（`orderId`）：查该订单的满意度答卷与关联奖券的核销状态/点餐方式。

## 组合策略提示（可选，提升体验）

用户"随便配一份"时，参考官方搭配档位（源自 query-meals 描述）：
- ≤20元：小食；20–30：汉堡+小食 或 汉堡+饮料；30–40：汉堡+薯条/小食+饮料；
- 40–50：汉堡+薯条+小食+饮料；≥50：丰富组合、优先小食不重复。
搭配后一律走 `calculate-price` 核价，再 `create-order`。

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

## 多人拼单 / AA 分账（聚餐、团餐、办公室拼单）

输入：**人数 + 总预算（或人均预算）+ 各自忌口**。流程：
1. 收齐约束：谁不吃什么（忌口取并集过滤候选）、是否有必点项。
2. 用 `query-meals` 现价把预算换算成件数目标：优先套餐/分享装摊薄人均，忌口冲突的品直接剔除。
3. 团餐(beType=6)按人均预算走 `query-meal-assistance` 拿 `gmServiceCode`，再用 `query-promotions` 的满减档做跨档凑单（见 savings.md）。
4. **零尾差 AA**：`calculate-price` 得到实付总额 P（分）。人均 = P ÷ 人数，用**最大余数法**分配：每人先取 floor(P/n)，余数 r 按小数部分从大到小依次 +1 分，换算成元后向用户展示"每人应付"清单，保证合计恰等于 P。
5. 下单人付款后，把 `query-order` 的取餐码/配送状态转给参与者（可用 profile.md 省心模式输出一句话摘要）。

## 异地代点 / 给亲人点一餐

用户在外地给父母/孩子/朋友点餐（对应高频"代送/代点"需求）：
1. 地址用**收件人所在城市**：`delivery-create-address` 传对方真实地址与电话 → `delivery-query-stores` 选可服务门店。
2. 选品时询问对方口味（写入 profile.md 的家人偏好记忆，下次直接复用）；忌口规则照常生效。
3. 下单后把 `payH5Url` 发给用户自己付款（代付场景），或订单支持时把取餐码转交给收件人；用 `query-order` 盯状态，"配餐中/配送中"主动同步给用户。
4. 到店取餐的"交接"场景：`pickupCode` 截图/原文发给取餐人，提醒有效期与取餐窗口。

## 指定预算求解器（"XX 元怎么点最值"）

输入：预算上限 B（元）、场景参数、可选约束（热量≤K / 忌口 / 必选品）。算法（全部基于 `query-meals` 实时现价）：
1. 候选池：在售餐品按"价值密度"排序（主食看 蛋白质÷价格，小食看 份量大÷价格，饮品看 无糖优先）。
2. 组合生成 2–3 套：一套**贴满预算**（件数最多）、一套**最优单品**（质量优先）、一套**保守档**（留出 3–5 元运费/包装费余量；外送记得把 `deliveryPrice/packingPrice` 计入 B）。
3. 每套走 `calculate-price` 实测（单位分÷100），任何一套总价 > B 立即换品重算——**展示给用户的价必须是核价后的实付**。
4. 叠加 savings.md 券链路后再对比一次，把"同预算下最多件数/最优组合"作为结论。
5. 预算不足以跨到满减档时明确告知："再加 X 元可跨档净省 Y 元"由用户决定，**禁止为凑单而凑单**。

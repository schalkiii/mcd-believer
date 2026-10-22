# WorkBuddy 开发上下文 · workbuddy.md

本文件记录使用 WorkBuddy 开发 `mcd-believer` Skill 的上下文，用于核验 WorkBuddy 联动活动奖励条件。

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

## 第二轮迭代：全量调研参赛项目，博采众长

用 GitHub API 分页拉取了大赛报名 Issue 的**全部 296 条**（非仅热门），按主题聚类后识别出高频共识需求与本 Skill 的空白点，逐项落地为可执行的编排规则（均只基于 35 个真实工具，不编造能力）：

| 调研发现的高频主题 | 补强的位置 |
|---|---|
| 口味记忆/老样子复购（麦麦老友记、mac-Buddy、点餐记忆中枢等） | 新增 `references/profile.md`：本地 mcd-profile.json + 一句话复购链路 |
| 年报/人设/分享卡（麦门画像、年度账单、M-TYPE 等） | profile.md §2：真实订单聚合 + 人设标签分享卡 |
| 多人拼单/AA 分账（派对指挥官、拼单大脑、办公拼单等） | ordering.md：零尾差最大余数法 AA |
| 异地代点/给家人点餐（麦麦代送、代点履约等） | ordering.md：收件人地址选店 + 代付/取餐码交接 |
| 指定预算求解（McBudget、预算餐盘、30块能吃什么等） | ordering.md：价值密度候选池 + 三套方案 + 实测核价 |
| 资产到期管理（权益到期管家、末班车、到期清单等） | savings.md：券+积分+抽奖机会一盘清的倒计时表 |
| 凑单劝退（省钱军师"主动劝退亏本凑单"） | savings.md：边际账 Δ买 vs Δ省红线 |
| 健身深度（蛋白质性价比、增肌窗口、减脂不掉队） | nutrition.md：每元蛋白榜单 + 运动后窗口餐 |
| 特殊人群（体检报告白名单、八类人群阈值） | nutrition.md：钠/糖/热量三档白名单 + 量化改配 |
| 扭蛋/求签娱乐（麦麦扭蛋机、薯条签筒、每日签） | SKILL.md：麦门灵签（约束内随机 + 真实核价 + 可换可重抽） |
| 无障碍/大字模式（麦麦读得到、轻松点） | profile.md §3 省心模式：单句输出纪律 |
| 周边/玩具猎人（周边雷达、玩具猎人） | points-mall.md：周边/派对类目双检上新 |

未吸收的候选（无真实工具支撑，宁缺毋滥）：麦金卡回本测算（无卡数据工具）、3D 游戏/点唱机类（超出 MCP 能力边界）、跑步路线规划（需地图服务）。

## 关键调试结论（写进 Skill 的硬约束）

- beCode 仅 beType=2/5/6 传；到店自取(beType=1) 不传，否则报错。
- calculate-price 返回金额为分，展示需 ÷100。
- 商城 shopId=2 用 mall-create-order、shopId=5 走派对链路；多商品兑换必须逐个下单且排队。
- 抽奖资格只以 drawDecision 为准，禁止据 availableTimes=0 自行推断；禁止试抽/连抽。
- 工具结果优先读 structuredContent。

## 导出说明

以上脉络可由 WorkBuddy 会话记录导出替换/补充。本文件为人工整理的开发上下文摘要。

## 第三轮迭代：冲榜补强——星级磁铁四件套（2026-10-22）

背景：官方排行榜按 Star 排名（上榜门槛 32 Star），本项目当时 4 Star 未上榜。全量复盘 TOP10 高星项目后确认四件「星级磁铁」：免 Token 即玩 Demo、确定性算法内核 + 测试、可截图分享卡、营销化 README。本轮全部落地：

| 高星项目打法 | 本项目落地 |
|---|---|
| 在线试算器 / demo.py + fixtures / 离线缓存 | `docs/demo.html` 在线试算页 + `fixtures/` 构造样本 + 根目录 `demo.py` 一键五链路演示 |
| 确定性求解器 + 单测 + CI 徽章 | `scripts/solver.py`（双约束枚举/券优化/AA/帕累托/订单统计）+ `tests/` 36 项 + GitHub Actions CI |
| 可截图分享卡 | `scripts/card.py`：麦门灵签卡 + 年报人设卡（单文件竖屏 HTML，品牌红金、零外链） |
| 营销化 README（数字战报/徽章/Star 引导） | README 重写：602 套候选实测战报、徽章组、30 秒体验、榜单空白定位 |

工程沉淀：
- **修复枚举剪枝 bug**：原 `enumerate_combos` 用「遇超预算即 break」，但组合序列按字典序而非价格序，会漏掉后续更便宜的合法组合（58 套 vs 正确的 602 套）。改为索引递归 + 累计价格剪枝（有序数组上安全），并补回归测试 `test_enumeration_not_truncated_by_expensive_prefix`。JS 版（docs/demo.html）与 Python 版结果逐项对齐（602 套 / 三方案一致）。
- **券互斥保守模型**：同组互斥 + 适用范围不重叠（一张餐品最多带一张券），避免演示中出现 5 券叠加的不实宣传；真实可叠性以 calculate-price 为准。
- **整数分运算**：金额内部一律 int 分，展示才 ÷100，杜绝浮点误差（与 mcd-wrapped 等头部项目同一立场）。
- **拒绝估算**：营养缺失餐品在求解器中自动剔除，与 mcd-budget-bite 的工程纪律对齐。
- 补 MIT LICENSE、`.github/workflows/ci.yml`（3.8/3.12 双版本）、`scripts/capture_evidence.py`（只读脱敏留证）。

新增场景编排（references 同步）：早餐 10:30 压哨流（now-time-info 时钟感知）、特调工坊（民间配方 → 官方 modification 组装，缺组件直说做不了）。

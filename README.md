# 🍔 麦门信徒 · mcd-believer

> 一个基于**麦当劳中国官方 MCP** 的 Agent Skill —— 一个技能打通点餐下单、省钱领券、营养配餐、积分商城、积分抽奖、活动日历、主题派对预约，外加口味记忆/年报人设的**全场景麦当劳管家**。

[![M-CODE](https://img.shields.io/badge/M--CODE-麦当劳程序员创意开发大赛-red)](https://github.com/M-China/mcd-developer-innovation-challenge)
[![MCP](https://img.shields.io/badge/MCP-mcp.mcd.cn-green)](https://open.mcd.cn/mcp)
[![Tools](https://img.shields.io/badge/MCP%20Tools-35-blue)](#-它强在哪覆盖-35-个-mcp-工具)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-yellowgreen)](./SKILL.md)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

解决每天最难的三个选择题：**吃什么、怎么点最省、积分怎么用不浪费**。参赛 290+ 个项目大多只做一个场景，`mcd-believer` 把麦当劳 MCP 的**全部能力 + 全部高频共识需求**收进一个 Skill。

---

## ✨ 它是什么

`mcd-believer` 是一个 **Agent Skill**（`SKILL.md` + 分场景操作手册 + MCP 客户端脚本）。在 WorkBuddy / Cursor / Cherry Studio / Trae 等支持 MCP 的客户端里接入麦当劳 MCP 并装载本 Skill，AI 就能按沉淀好的编排规则，替你完成从"想吃"到"拿到取餐码/支付链接"的完整闭环。

- 🧭 **意图路由**：一句话自动分派到点餐 / 省钱 / 营养 / 积分 / 活动 / 派对 / 画像七大手册。
- 🔗 **端到端下单**：选店 → 选品 → 算价 → 下单 → 跟单/取消，含到店、得来速、麦乐送、企业团餐四种场景；另支持**多人拼单零尾差 AA、异地代点、指定预算求解、一句话复购老样子**。
- 💰 **真·省钱但不劝卖**：领券 → 门店可用券 → 满减凑单 → 实测应付；**亏本凑单主动劝退**，券/积分/抽奖机会一张**到期倒计时表**统一盘。
- 🥗 **按热量配餐**：目标热量凑一餐，另带**蛋白质性价比榜、运动后窗口餐、高血压/糖尿病等特殊人群钠糖阈值三档白名单与量化改配**。
- 🎁 **积分管家**：积分余额 + 末班车主动提醒 + 商城兑换 + 周边/玩具类目检索 + 抽奖（严格先确认后抽）。
- 📅 **活动雷达 + 派对预约**：当月活动日历情报、生日/主题派对逐步下单。
- 🪪 **麦门画像**：本地 `mcd-profile.json` 记住你的店/忌口/预算/习饮；用真实订单数据生成**年报人设分享卡**（薯条纯爱党/深夜麦门徒/精算省钱家…）；还有**省心模式**：给视障、开车、长辈的一句话极简输出。

## 🧩 它强在哪：覆盖 35 个 MCP 工具

比读官方 README（33 个）更全 —— 实测 tools/list 发现两个隐藏工具 `query-survey-coupons`、`query-promotions`，全部纳入编排。

| 场景 | 用到的工具 |
|---|---|
| 点餐交易 | query-nearby-stores · delivery-query-addresses · delivery-create-address · delivery-query-stores · query-meals · query-meal-detail · query-meal-assistance · calculate-price · create-order · query-order · cancel-order · order-list |
| 省钱 | available-coupons · auto-bind-coupons · query-my-coupons · query-store-coupons · query-promotions |
| 营养 | list-nutrition-foods |
| 积分/商城/抽奖 | query-my-account · mall-points-products · mall-product-detail · mall-create-order · mall-order-list · mall-order-detail · query-lottery-info · draw-lottery · query-my-prizes |
| 活动/派对 | now-time-info · campaign-calendar · query-party-city · query-party-store · query-party-store-date · query-party-store-session · party-order-create |
| 售后 | query-survey-coupons |

## 🚀 快速开始

### 1. 申请麦当劳 MCP Token
访问 https://open.mcd.cn/mcp → 手机号登录 → 控制台 → 激活 → 复制 MCP Token。

### 2. 接入 MCP
把 `mcp-config.example.json` 里的 `YOUR_MCP_TOKEN` 换成你的 Token，填入客户端的 MCP 配置：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
    }
  }
}
```

### 3. 装载 Skill
把本仓库目录作为 Skill 装载（`SKILL.md` 为入口）。在对话框直接说人话：

- 「帮我在公司附近的麦当劳点份麦乐送，预算 40，不要辣」
- 「我有多少积分？哪些快过期了？能兑什么？」
- 「配一顿 500 大卡以内的麦当劳」
- 「这个月有什么活动？帮我约个生日派对」
- 「今天吃什么？帮我抽一支麦门灵签」
- 「我们 6 个人聚餐预算 240，两人不吃辣，怎么点？」
- 「按老样子来一份」 / 「给我出张麦门年报」

### 4.（可选）无 MCP 客户端时兜底
`scripts/mcp_call.py` 用标准库直连，Token 走环境变量：

```bash
export MCD_MCP_TOKEN=你的Token
python scripts/mcp_call.py list
python scripts/mcp_call.py call query-my-account '{}'
```

## 👥 目标用户

选择困难症患者、麦门信徒、精打细算的打工人、健身党、手握一堆积分不知怎么花的人、要给孩子订生日派对的家长、组织企业团餐的行政、想给异地爸妈点餐的游子、需要极简语音式点餐的视障/开车/长辈用户。

## 📁 项目结构

```
mcd-believer/
├── SKILL.md                     # 技能入口：意图路由 + 全局铁律 + 默认流程
├── references/
│   ├── ordering.md              # 点餐交易全流程（四种场景 + 特调 + 计价下单）
│   ├── savings.md               # 省钱：领券/可用券/满减满折凑单
│   ├── nutrition.md             # 营养：按热量配餐
│   ├── points-mall.md           # 积分：账户/商城兑换/抽奖/周边检索
│   ├── activities.md            # 活动日历 + 主题派对逐步预约
│   ├── profile.md               # 画像：口味记忆/复购/年报人设卡/省心模式
│   └── tools-reference.md       # 35 工具入参速查表
├── scripts/
│   └── mcp_call.py              # 纯标准库 MCP JSON-RPC 客户端（兜底）
├── README.md
├── MCP_INTEGRATION.md
├── CONTEST_DECLARATION.md       # 参赛声明（官方原文，未改动）
├── workbuddy.md
└── mcp-config.example.json
```

## 🔒 安全与合规

- MCP Token 仅存于本地配置/环境变量，**不写死进代码、不提交仓库**。
- 所有下单 / 兑换 / 抽奖 / 领券等写操作，均**先复述信息、经用户确认**后执行。
- 营养成分、价格、券、订单等一切数据均来自 MCP 实时返回，Skill 不做医疗或绝对省钱承诺。
- 遵守麦当劳中国《使用条款》《麦当劳 MCP 服务规则》，仅限个人非商业用途。

## 🏅 参赛信息

- 大赛：麦当劳程序员创意开发大赛（M-CODE）
- 报名与排名：2026.10.09 10:30 — 2026.10.25 23:59，按公开 Star 排名
- 本项目为原创，未直接盗用他人在赛作品。

## 📄 License

MIT © 2026 mcd-believer contributors

> ⚠️ 声明：本项目为非官方开发者作品，与麦当劳中国无隶属或背书关系。麦当劳相关商标归其权利人所有。

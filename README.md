# Atria — AI 沙盒涌现观察站

> 25 个 AI 居民生活在一个像素小镇上。一桩「邮局包裹错领」事件自然发生、自然传播、自然误解——**没有一行剧本，全部是运行结果**。
>
> 每个居民拥有独占的 512K 全量记忆。14 天实测对照(P1v5)证明：**全量时间线让 agent 能分辨传言在传播中的变异**，而 RAG 检索只能给出「某个版本的答案」。

## 证据图

全部由实跑数据生成，脚本 `atria_figures.py`，逐项与源数据复核 10/10 一致：

| 图 | 内容 |
|---|---|
| ![图1](docs/figures/fig1_spread.png) | 知情扩散曲线 + 三碎片命运分化 |
| ![图2](docs/figures/fig2_cost.png) | 成本实测 vs 推算 + 限速工程 |
| ![图3](docs/figures/fig3_sellpoint.png) | P1v5 卖点对照：全量 3/3 vs RAG 1/3 |
| ![图4](docs/figures/fig4_memory.png) | 记忆规模与 512K 卖点的关系 |

## 交付物

| 产物 | 文件 | 规格 |
|---|---|---|
| 精华版视频 | `renders/atria_highlights.mp4` | 720p / 50s / 3.9MB |
| 完整版视频 | `renders/atria_demo.mp4` | 480p / 282s / 28MB |
| 运行说明 | `说明.md` | 中文，面向评委 |
| 技术方案 | `docs/atria_plan_v1.1.md` | 12 章 / 29 表 / 全部数字标注来源 |
| 涌现报告 | `run/FINAL_REPORT.md` | 14 天运行分析 |

## 实测数字

| 环节 | 结果 |
|---|---|
| 25 人 × 14 天正式跑 | **35 分钟** / 1,106 事件 / 1,413 次调用 / 429 零外泄 |
| P1v5 卖点闸门 | 全量 3/3 vs RAG 1/3（判据完整性判分） |
| P2v2 传播动力学 | S 形扩散 3→5→8 |
| 渲染 | manim 一次性成功，双版本 |

## 涌现亮点（运行产出，零剧本）

1. **三碎片命运分化**：扳指碎片传 40 条、方向碎片 4 条、颜色碎片 **0 条**——不确定措辞被传播链静默丢弃
2. **误解自发涌现**：3 条独立误传把错领者塑造成「目击者」
3. **反派心理转变链**：侥幸 → 烦躁 → 回避
4. **知情扩散 9→20/25 饱和**：剩 5 人永不知情

## 仓库结构

```
├── README.md                      本文件
├── 说明.md                        运行说明(中文)
├── LICENSE                        MIT
├── atria_world.py                 世界:40×30 地图 / 12 地点 / 39 物品
├── atria_personas.py              25 人设(种子结构)
├── atria_engine.py                引擎:令牌桶+断点续跑
├── atria_manim.py / _v2.py        manim 渲染(全版/精华版)
├── renders/                       两版视频
├── run/                           14 天数据+涌现报告
├── docs/
│   ├── atria_plan_v1.1.md         现行方案
│   └── research/                  前期调研与基准(保留)
│       ├── BENCH_REPORT.md        512K 压测(max_tokens≥512 依据)
│       ├── TECH_PLAN.md           初版方案(已归档)
│       ├── RESEARCH_REPORT_v2/v3/v4.md  方向调研链
│       ├── RESEARCH_FACTS.md      官方参赛要求
│       └── bench_*.py             基准脚本
└── sprites/                       25 个程序化角色精灵
```

## 复现

```bash
python3 atria_engine.py --days 14        # 正式跑(约35分钟)
python3 -m manim render atria_manim_v2.py AtriaHighlights   # 精华版
python3 -m manim render atria_manim.py AtriaDemo            # 完整版
```

## 授权

- 代码：MIT
- 图素：Kenney Roguelike RPG Pack（CC0）+ 程序化生成的角色精灵
- **付费图素不在本仓库内**

---

### 前身工作

2026-10-01 的前期调研（方向选择、服务器能力实测、512K 压测、基准脚本）完整保留在 [`docs/research/`](docs/research/README.md)，索引见该目录的 README。

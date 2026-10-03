# Atria — 安镇：LLM 小镇中的受控信息传播实验

> 25 agents · 105 天对照实验 · 8,300+ 起事件 · 运行期零人工干预

**A controlled study of information spread in an LLM town.** Twenty-five agents powered by Atria-Dawn live in a small town with schedules, memories, and social life. We seeded six of them with fragments of an invented event, then ran a 2×2 experiment over *memory anchors* × *prompt guidance* — and measured whether a rumor needs facts to spread, or merely a question.

<div align="center">

**[🎮 在线交互展厅](https://yzml1507.github.io/atria/hall/)** · **[🎬 导览视频](renders/atria_v9.mp4)** (116s) · **[📄 实验报告](docs/REPORT_v4_noprompt.md)**

拖时间轴回放五轮真实运行，点开任意居民看传闻记忆流如何流进他的记忆。

**60 秒看懂本实验**：进展厅 → 点底部「📦 邮局事件」看传闻起点 → 点「🔺 饱和」跳到第 8 天 → 左上角切到「v3 零注入」看同镇 35 天停在 4/25 → 再切「v4 零锚+引」看没有锚点的镇子如何集体编造出同一个包裹案。

</div>

<p align="center">
  <img src="docs/figures/fig8_2x2_curves.png" alt="六轮 run 的知情人数曲线：四格饱和 vs 零注入停滞" width="760">
</p>

---

<p align="center">
  <img src="docs/figures/hall_hero.gif" alt="展厅实拍：等距小镇回放 + 台词气泡 + 传播链路叠加" width="760">
</p>

## 核心结果：2×2 对照

唯一操纵变量：**初始记忆锚点**（包裹错领事件的碎片）× **社交引导句**（prompt 中"如果你记得就告诉他"）。同引擎、同种子、同 25 个人设。

| | 有引导句 | 无引导句 |
|---|---|---|
| **有锚点** | v2：**25/25**，第 9 天饱和 | v4-np：**25/25**，第 8/9 天饱和（两种子复现，n=2） |
| **零锚点** | hint0：**25/25**，第 8/13 天饱和（两种子复现，n=2）—— **全镇集体编造** | v3：**4/25** 停滞（35 天，0 注入报警） |

**引导即播种**：在零锚点 + 引导句条件下，包裹从未存在过，但居民顺着引导语"回忆"出完整的包裹案——查签收底单、对汇款记录、造出"哪是错领，分明是手长"的归因句并被多人转引。**传闻不靠事实传播，靠问题传播。** 这也说明 v2 的 25/25 在相当程度上可归因于每日 prompt 引导，而非纯粹涌现——这是本实验最重要的诚实修正。

<p align="center">
  <img src="docs/figures/fig9_hint0_fabrication.png" alt="hint0 编造词逐日频次：从无到有，第6天起每天40+次" width="640">
</p>

## 三个关键发现

**① 措辞确定性决定碎片存活。** 三位目击者持有同一事件的碎片，措辞确定性不同：

| 碎片 | 措辞 | 14 天后被传递次数（有引导 / 无引导） |
|---|---|---|
| 扳指 | "戴旧扳指"（具体） | 164 / 44 |
| 方向 | "抱纸箱往镇东头走"（半具体） | 30 / 8 |
| 颜色 | "衣裳偏浅，好像灰色"（不确定） | 0 / 0 |

措辞不确定的碎片被传播链**静默丢弃**——在有无引导两种条件下结论一致。最硬的证据是周老师本人：她持有颜色碎片，14 天 35 次发言没有 1 次提颜色，全部追随具体线索。

**② 引导句放大深度而非广度。** 关掉引导句后饱和速度几乎不变（D8/D9 vs D9），但碎片转述量降至约 1/4（164/30/0 → 44/8/0）。引导不是必要条件，是扩音器。

**③ 零注入会产生信息，但长不大。** v3 中居民 D1 即兴虚构"镇中新来了一户人家"——不存在于任何设定。35 天被提及 167 次、触达 4 人，但从未产生实质内容：所有台词都是提问（"你听说没？"），从 D9 起只剩两人重复互问。好奇心真实存在，"看起来在聊"≠"有信息在传"。

<p align="center">
  <img src="docs/figures/fig10_diffusion_network.png" alt="首传链路图：v2/hint0 密网 vs v3 仅 3 条边" width="760"><br>
  <img src="docs/figures/fig11_edge_growth.png" alt="累计首次转述边数：四条曲线长到 78–127 条 vs 零注入 35 天 3 条" width="760"><br>
  <img src="docs/figures/fig1_spread.png" width="45%"> <img src="docs/figures/fig6_rumor_lifecycle.png" width="45%">
</p>

## 方法学

- **引擎**：`atria_engine.py`（~600 行，零框架依赖）——日程作息 + 记忆检索 + 社交对话 + 心事沉淀；Atria-Dawn-Preview 驱动，429 退避与降级
- **世界**：40×30 地图、32 个地点、25 位手写人设（姓名/职业/性格/作息）
- **运行**：每轮 14–35 天、每天 ~75 次 LLM 调用、JSONL 事件流 + 逐日记忆 checkpoint 全量入库
- **口径**：知情判定 = 记忆中出现传闻标志词（`atria_fragments.py` 程序化判定，非人工标注）；碎片计数排除持有者自记
- **对照**：同种子 noise floor 由 v1 基线提供（同种子复跑 D1 得 79 vs 78 事件）

## 复现

```bash
export ATRIA_LLM_KEY=sk-...          # 也可放 ~/.hermes/.env
export ATRIA_LLM_URL=https://...     # 可选，默认 discovery-api.intern-ai.org.cn
export ATRIA_LLM_MODEL=...           # 可选，默认 Atria-Dawn-Preview

python3 atria_engine.py 14 --seed 20261014 --outdir run_x                  # 14 天 ~52 分钟
python3 atria_engine.py 14 --seed 20261014 --outdir run_x --neutral-social # 关闭引导句
python3 atria_verify.py run_v2                                           # 校验数字与数据一致
```

六轮 run 的原始数据全部入库：`run_v2 / run_v3 / run_v4np / run_v4np2 / run_hint0 / run_hint0s2`。展厅数据由 `hall/export_data.py` 从原始事件流重新生成。

## 局限与复现边界

- 本实验**不是零干预**：v2/v4 的初始记忆锚点为作者设定；"零注入"指零信息注入，非零人设注入
- 每格条件样本量 n=1–2：两格关键条件均有双种子复现（v4np D8/D9、hint0 D8/D13），v3 仍为单次运行
- 远程 LLM 端点同种子不逐位确定，复现的是趋势不是数字
- v2 的三碎片结论仅在有锚点条件下成立
- 全部方法学细节与逐 run 数据见 `docs/REPORT_v4_noprompt.md`、`docs/REPORT_v3_unseeded.md`、`FINAL_REPORT.md`

## 与文献的关系

Smallville（Park et al., 2023）谱系实验全部注入种子信息（派对、报道、传闻帖）。**据我们检索，"零注入条件下信息是否自发产生并传播"尚无完全同类工作**——最接近的是 arXiv:2411.03252（无预设身份→社会结构，6 人）与 Inflected Smallville（双分支对照方法学）。本项目的差异点：25 人规模 × 2×2 对照 × 运行期零人工干预 × 105 天总时长。

## 资源

| 资产 | 说明 |
|---|---|
| [在线展厅](https://yzml1507.github.io/atria/hall/)（[✨ 自动导览](https://yzml1507.github.io/atria/hall/index.html?run=v2&tour=1)） | 等距小镇回放 + 6 run 对照 + 传播链路叠加 + 居民记忆面板 |
| `renders/atria_v9.mp4` | 主视频（116s）：展厅实演 + 2×2 结果 + 引导即播种 |
| `renders/` | v3–v8 历代视频（保留溯源） |
| `docs/figures/` | 9 张程序化生成证据图 |
| `docs/` | 设计方案、实验报告、调研归档（15 份） |

## 仓库结构

```
atria_engine.py      涌现引擎（记忆/决策/社交，checkpoint 保护，--neutral-social）
atria_world.py       小镇世界（40×30 地图，32 地点）
atria_personas.py    25 位居民人设
atria_fragments.py   三碎片传播口径锁定（程序化判定）
atria_verify.py      数据一致性校验（所有文档数字可溯源）
atria_video_v7.py    2D 视频渲染管线（v6 弃用保留溯源）
narration_v6/        旁白素材（39 段 mp3 + 音轨 + timeline.json）
hall/                可交互展厅（Canvas 等距渲染 + export_data.py）
run_v2/  run_v3/  run_v4np/  run_v4np2/  run_hint0/  run_hint0s2/   六轮完整实验数据
docs/                报告与图   renders/  视频
```

分支：`main`（交付线）· `experiment/v4-noprompt`（本 PR 工作线，含 v3/v4/hint0 数据与展厅）· `experiment/v1-round1` · `experiment/v2-round2` · `experiment/v3-unseeded`

## 引用与许可

MIT License。素材：Kenney Sketch Town (CC0) + 程序化生成。音乐：Deliberate Thought — Kevin MacLeod (CC BY 4.0)。
若引用本实验，请参考 `FINAL_REPORT.md` 的口径定义。

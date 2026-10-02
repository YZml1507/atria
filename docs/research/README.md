# 前期调研与基准文件索引

本目录是 Atria 项目的前身工作（2026-09-28 ~ 10-01），保留了从方向调研到技术方案再到压测的完整决策链。
**它们不是废物——当前引擎的每一个参数都能在这里找到出处。**

## 1. 达成的关键结论（仍有效）

| 文件 | 结论 | 在当前项目中的位置 |
|---|---|---|
| `RESEARCH_REPORT_v3.md` | 服务器能力实测：manim 可行 / Chromium 截图不可行 / Remotion 近 OOM / MusicGen 出局 | 决定了视频用 manim 离线渲染（`atria_manim.py`） |
| `RESEARCH_REPORT_v4.md` | Smallville 论文精读 + PIMMUR 警告（50.6% 的涌现研究被 prompt 污染）+ 512K 实测确认 | 情景 A 只设信息差不写结局；全量记忆路线 |
| `RESEARCH_FACTS.md` | 官方筛选标准 + 交付物格式（视频 + 说明.md + GitHub 链接） | 投递时要用，**勿删** |
| `BENCH_REPORT.md` | max_tokens≥512 + temp=0 是硬要求；28万/45万 token 尾部读取准确 | 引擎和所有压测脚本的参数依据 |

## 2. 已被取代的部分（保留但标注）

| 文件 | 已过时的内容 | 现行版本 |
|---|---|---|
| `TECH_PLAN.md` | 9×9 网格 / 王婆李四人设 / SIR 传播模型 / 双层记忆 | 40×30 地图 / 25 人真实姓名人设 / LLM 对话传播 / 全量+压缩 |
| `BENCH_REPORT.md` | 核心叙事"RAG 压缩会断片" | **已证伪** → 改为"分辨传言变异"（P1v5 全量 3/3 vs RAG 1/3） |
| `RESEARCH_REPORT_v2.md` | 推荐科研复现/CTF 方向 | 已否决，选沙盒方向 |

## 3. 基准脚本（可直接复跑）

| 脚本 | 测什么 | 结果 |
|---|---|---|
| `bench_memory.py` | 32 智能体内存占用 | — |
| `bench_memory_recall.py` | 512K 记忆有效性压测 | 28万 token 尾部读取准确 |
| `bench_recall2/3/4.py` | None 根因 / 一致性 / max_tokens 解法 | max_tokens=512 + temp=0 → 5/5 |
| `bench_rpm.py` | RPM 上限 | ≈50（52.5 复测） |
| `bench_sandbox.py` | 真实负载 25 人 × 6 步 | — |
| `calc_timeline.py` | 按 RPM 推算各规模耗时 | — |

## 4. 与当前仓库的关系

- 前期调研产物 → 本目录（`docs/research/`）
- 当前方案 → `docs/atria_plan_v1.1.md`
- 正式跑结果 → `run/FINAL_REPORT.md`
- 引擎代码 → `atria_engine.py` 等 5 个根目录 py 文件

---

*历史提交保留在 git log 中，可追溯每个决策的时间点。*

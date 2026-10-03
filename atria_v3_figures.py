#!/usr/bin/env python3.12
# v3 图表生成: 三张图, 补上实验报告的"可视化"缺口
# fig5: 传播动力学对照(v2 S型 vs v3 建台型)
# fig6: 远客传闻生命周期(逐日提及次数, 显示D9衰减+空转)
# fig7: 事件/记忆增长率(v2 vs v3)
import json, glob
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

FP = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
fp = FontProperties(fname=FP)
fpl = FontProperties(fname=FP, size=11)
plt.rcParams["axes.unicode_minus"] = False

RUN3 = "/home/ubuntu/atria_v3/run_v3"
RUN2 = "/home/ubuntu/atria_rerun"

# ---------- 数据 ----------
# v2 知情曲线(回源: run_v2 逐日记忆含扳指/方向/颜色任一者的人数, 排除持有者自记)
def v2_knows(day):
    """D{day} 记忆里含三碎片任一的人数(排除持有者自记)"""
    holders = {"安镇", "孙有财", "周老师", "赵医生", "李大姐"}
    try:
        mem = json.load(open(f"{RUN2}/mem_day{day:02d}.json", encoding="utf-8"))
    except FileNotFoundError:
        return None
    n = 0
    import re
    KEY = re.compile(r"扳指|灰色|镇东头|往东|东头")
    for p, recs in mem.items():
        if p in holders:
            continue
        if any(KEY.search(r[3] or "") for r in recs):
            n += 1
    return n

v2 = [v2_knows(d) for d in range(1, 15)]
v2 = [x if x is not None else 0 for x in v2]

# v3 逐日: 当日提及人数 + 累计触达
daily = defaultdict(set)
cum = set()
v3_daily, v3_cum = [], []
for f in sorted(glob.glob(RUN3 + "/day*.jsonl")):
    day = int(f.split("day")[-1].split(".")[0])
    for line in open(f, encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        s = d.get("say") or ""
        if any(k in s for k in ["远客", "新来", "南边"]):
            daily[day].add(d.get("agent", "?"))
            cum.add(d.get("agent", "?"))
    v3_daily.append((day, len(daily[day])))
    v3_cum.append((day, len(cum)))

# ---------- 图5: 传播动力学对照 ----------
fig, ax = plt.subplots(figsize=(10, 6.5), dpi=140)
ax.plot(range(1, 15), v2, "o-", color="#d7263d", lw=2.4, ms=6,
        label="v2 有锚点: 三枚信息碎片(注入)", zorder=3)
ax.plot([d for d, _ in v3_cum], [c for _, c in v3_cum], "s-", color="#1b6ca8",
        lw=2.4, ms=5, label="v3 零注入: 远客传闻(自发涌现)", zorder=3)
ax.axhline(25, color="#999", ls="--", lw=1.2)
ax.text(1.2, 25.6, "全员 25 人", fontproperties=fpl, color="#666")
ax.axhline(4, color="#1b6ca8", ls=":", lw=1.4)
ax.text(22, 4.6, "传闻上限 4 人", fontproperties=fpl, color="#1b6ca8")
ax.annotate("S 型: 11→25 全员饱和", xy=(6, 19), xytext=(9, 13),
            fontproperties=fpl, color="#d7263d",
            arrowprops=dict(arrowstyle="->", color="#d7263d"))
ax.annotate("D3 到顶后再未上升", xy=(10, 4), xytext=(13, 9),
            fontproperties=fpl, color="#1b6ca8",
            arrowprops=dict(arrowstyle="->", color="#1b6ca8"))
ax.set_xlabel("天数", fontproperties=fp, fontsize=13)
ax.set_ylabel("累计触达人数(去重)", fontproperties=fp, fontsize=13)
ax.set_title("传播动力学对照: 有锚点 vs 零注入", fontproperties=fp, fontsize=16)
ax.set_xlim(0, 36); ax.set_ylim(0, 27)
ax.set_xticks([1, 7, 14, 21, 28, 35])
ax.grid(alpha=0.25)
ax.legend(prop=fpl, loc="center left")
fig.tight_layout()
fig.savefig("/home/ubuntu/atria_repo/docs/figures/fig5_spread_v3_vs_v2.png")
plt.close(fig)
print("fig5 已保存: 传播动力学对照")

# ---------- 图6: 远客传闻生命周期(逐日提及次数) ----------
fig, ax = plt.subplots(figsize=(10, 5.5), dpi=140)
days = [d for d, _ in v3_daily]
counts = [c for _, c in v3_daily]
ax.bar(days, counts, color="#1b6ca8", alpha=0.85, width=0.75)
ax.axvspan(1, 8, color="#d7263d", alpha=0.10)
ax.text(2, max(counts) + 0.4, "扩散期 D1-8\n吕婶→钱老板/许货郎/朱寡妇", fontproperties=fpl, color="#d7263d")
ax.axvspan(9, 35, color="#999", alpha=0.08)
ax.text(19, max(counts) + 0.4, "空转期 D9-35: 只剩许货郎↔朱寡妇重复互问", fontproperties=fpl, color="#555")
ax.set_xlabel("天数", fontproperties=fp, fontsize=13)
ax.set_ylabel("当日提及人数", fontproperties=fp, fontsize=13)
ax.set_title("远客传闻的生命周期: 1 人即兴虚构 → 35 天空转", fontproperties=fp, fontsize=16)
ax.set_xlim(0, 36)
ax.set_xticks([1, 7, 14, 21, 28, 35])
ax.grid(axis="y", alpha=0.25)
fig.tight_layout()
fig.savefig("/home/ubuntu/atria_repo/docs/figures/fig6_rumor_lifecycle.png")
plt.close(fig)
print("fig6 已保存: 远客传闻生命周期")

# ---------- 图7: 事件/记忆增长 ----------
# v2: 逐日事件数; v3: 逐日事件数
def daily_events(run):
    out = []
    for f in sorted(glob.glob(run + "/day*.jsonl")):
        day = int(f.split("day")[-1].split(".")[0])
        out.append((day, sum(1 for _ in open(f, encoding="utf-8"))))
    return out

ev2 = daily_events(RUN2)
ev3 = daily_events(RUN3)
fig, ax = plt.subplots(figsize=(10, 5.5), dpi=140)
ax.plot([d for d, _ in ev2], [c for _, c in ev2], "o-", color="#d7263d", lw=2, ms=5,
        label="v2 有锚点(14 天)")
ax.plot([d for d, _ in ev3], [c for _, c in ev3], "s-", color="#1b6ca8", lw=2, ms=4,
        label="v3 零注入(35 天)")
ax.set_xlabel("天数", fontproperties=fp, fontsize=13)
ax.set_ylabel("当日事件数", fontproperties=fp, fontsize=13)
ax.set_title("社会活跃度对照: 有无锚点不影响日常活跃", fontproperties=fp, fontsize=16)
ax.set_xlim(0, 36)
ax.set_xticks([1, 7, 14, 21, 28, 35])
ax.grid(alpha=0.25)
ax.legend(prop=fpl)
fig.tight_layout()
fig.savefig("/home/ubuntu/atria_repo/docs/figures/fig7_activity.png")
plt.close(fig)
print("fig7 已保存: 活跃度对照")
print("全部完成")

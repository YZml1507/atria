#!/usr/bin/env python3
"""fig14: debunk 辟谣干预 n=3 — 第7天公告前后传闻提及率 vs v2 对照 n=5"""
import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

_fp = os.environ.get("ATRIA_CJK_FONT", "/home/ubuntu/.fonts/NotoSansSC.ttf")
if os.path.exists(_fp): font_manager.fontManager.addfont(_fp)
plt.rcParams["font.family"] = "Noto Sans SC"
plt.rcParams["axes.unicode_minus"] = False
BG, INK, GRID = "#10131a", "#e8e8ee", "#2a2f3d"

MK = ["包裹", "错领", "扳指", "邮局", "纸箱", "旧物"]
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

def daily_mentions(run_dir, days):
    """每日事件中提及传闻关键词的人数(同一agent同一天只算一次)"""
    counts = []
    for d in range(1, days + 1):
        f = os.path.join(run_dir, f"day{d:02d}.jsonl")
        seen = set()
        if os.path.exists(f):
            for line in open(f):
                e = json.loads(line)
                if any(m in (e.get("say") or "") for m in MK):
                    seen.add(e["agent"])
        counts.append(len(seen))
    return counts

fig, ax = plt.subplots(figsize=(11.5, 6), facecolor=BG)
ax.set_facecolor(BG)

# 对照组: v2 五种子(无干预)
ctrl = []
for i, rid in enumerate(["run_v2", "run_v2s2", "run_v2s3", "run_v2s4", "run_v2s5"]):
    cnt = daily_mentions(os.path.join(REPO, rid), 14)
    ctrl.append(cnt)
    ax.plot(range(1, 15), cnt, "-", color="#8ecae6", lw=1.2, alpha=0.4)

import statistics as st
cmean = [st.mean(c[d] for c in ctrl) for d in range(14)]
ax.plot(range(1, 15), cmean, "--", color="#8ecae6", lw=2.2,
        label=f"v2 对照 n=5 均值")

# debunk 三种子
for rid, sname, ls in [("run_debunk", "s1", "-"), ("run_debunk2", "s2", "--"), ("run_debunk3", "s3", "-.")]:
    cnt = daily_mentions(os.path.join(REPO, rid), 14)
    ax.plot(range(1, 15), cnt, ls, color="#ffd166", lw=2.4,
            label=f"debunk·{sname}（D7 公告）")

ax.axvline(7, color="#e07a5f", lw=1.6, ls=":", alpha=0.9)
ax.text(7.15, 24.3, "第 7 天：镇公所布告辟谣", color="#e07a5f", fontsize=10.5)
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("当日提及包裹传闻的居民数", color=INK)
ax.tick_params(colors=INK); ax.set_xlim(1, 14); ax.set_ylim(0, 26)
for s in ax.spines.values(): s.set_color(GRID)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=9.5, loc="lower left")
ax.set_title("辟谣干预（n=3）：公告后提及量减半但不清零，对照组维持高位", color=INK, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(HERE, "..", "docs", "figures", "fig14_debunk.png"), dpi=150, facecolor=BG)
print("fig14 ok")

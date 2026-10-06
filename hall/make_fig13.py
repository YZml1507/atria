#!/usr/bin/env python3
"""fig13: multi 双传闻竞争 n=3 — 包裹(有锚) vs 银元(零锚) 知情数随时间"""
import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

_fp = os.environ.get("ATRIA_CJK_FONT", "/home/ubuntu/.fonts/NotoSansSC.ttf")
if os.path.exists(_fp): font_manager.fontManager.addfont(_fp)
plt.rcParams["font.family"] = "Noto Sans SC"
plt.rcParams["axes.unicode_minus"] = False
BG, INK, GRID = "#10131a", "#e8e8ee", "#2a2f3d"
HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data.json")))

RUNS = [("multi", "s1", "-"), ("multi2", "s2", "--"), ("multi3", "s3", "-.")]
fig, ax = plt.subplots(figsize=(11, 5.8), facecolor=BG)
ax.set_facecolor(BG)

for rid, sname, ls in RUNS:
    R = D["runs"][rid]
    for key, name, c in [("informed_pkg", "包裹错领(有锚)", "#ffd166"),
                         ("informed_silver", "山道银元(零锚)", "#c77dff")]:
        inf = R.get(key, {})
        pts = sorted((d, sum(1 for v in inf.values() if v <= d)) for d in range(1, R["days"] + 1))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], ls, color=c, lw=2.3,
                alpha=0.95 if key == "informed_pkg" else 0.9,
                label=f"{name}·{sname} ({len(inf)}/25)")

ax.axhline(25, color=GRID, lw=1, ls=":")
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("知情居民数", color=INK)
ax.tick_params(colors=INK); ax.set_ylim(0, 27); ax.set_xlim(1, 14)
for s in ax.spines.values(): s.set_color(GRID)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=9.5, loc="center right")
ax.set_title("multi 双传闻并行（n=3）：有锚传闻碾压零锚传闻", color=INK, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(HERE, "..", "docs", "figures", "fig13_dual_rumor.png"), dpi=150, facecolor=BG)
print("fig13 ok")

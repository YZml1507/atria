#!/usr/bin/env python3
"""fig12: 全条件对比 — 每轮最终知情人数散点 + 中位线 (论文式分布图)"""
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

# (条件名, [run ids], 颜色, informed 键)
CONDS = [
    ("v2\n有锚+引导",    ["v2","v2s2","v2s3","v2s4","v2s5"], "#ffd166", "informed"),
    ("v4\n有锚·无引导",  ["v4np","v4np2","v4np3","v4np4","v4np5"], "#8ecae6", "informed"),
    ("hint0\n零锚+引导", ["hint0","hint0s2","hint0s3","hint0s4","hint0s5"], "#ef8354", "informed"),
    ("hint0g\n银元泛化", ["hint0g"], "#f4a261", "informed"),
    ("v3\n零注入",       ["v3","v3s2","v3s3","v3s4","v3s5"], "#7fd17f", "informed"),
    ("multi\n包裹(有锚)", ["multi","multi2","multi3"], "#ffb703", "informed_pkg"),
    ("multi\n银元(零锚)", ["multi","multi2","multi3"], "#c77dff", "informed_silver"),
    ("debunk\n第7天辟谣", ["debunk","debunk2","debunk3"], "#e07a5f", "informed"),
]

import statistics as st
fig, ax = plt.subplots(figsize=(12, 6), facecolor=BG)
ax.set_facecolor(BG)
JITTER = [(-0.16,-0.08,0,0.08,0.16), (-0.22,-0.11,0,0.11,0.22)]
for xi, (name, rids, c, key) in enumerate(CONDS):
    vals = []
    for rid in rids:
        R = D["runs"][rid]
        vals.append(len(R.get(key, R["informed"])))
    jit = JITTER[0] if len(vals) == 5 else JITTER[1]
    for k, (v, j) in enumerate(zip(vals, jit)):
        ax.scatter(xi + j, v, color=c, s=130, alpha=0.92, edgecolors="#10131a",
                   linewidths=0.8, zorder=3)
        yoff = 9 if (v < 24 or k % 2 == 0) else -16
        ax.annotate(str(v), (xi + j, v), textcoords="offset points",
                    xytext=(0, yoff), ha="center", color=INK, fontsize=9)
    med = st.median(vals)
    ax.plot([xi - 0.3, xi + 0.3], [med, med], color=c, lw=3.5, zorder=4,
            solid_capstyle="round", alpha=0.95)
    n = len(vals)
    lab = f"n={n}  中位 {med:g}"
    ax.text(xi, -2.1, lab, ha="center", color="#8b93a3", fontsize=9.5)

ax.axhline(25, color="#5a6478", ls=":", lw=1.2)
ax.text(-0.5, 26.1, "饱和线 (25/25)", color="#8b93a3", fontsize=9, ha="left")
ax.set_xticks(range(len(CONDS)))
ax.set_xticklabels([c[0] for c in CONDS], color=INK, fontsize=10.5)
ax.set_ylim(-3.5, 28.5); ax.set_xlim(-0.6, len(CONDS) - 0.4)
ax.set_ylabel("最终知情居民数（25 人全镇）", color=INK)
ax.tick_params(colors="#8b93a3")
for s in ax.spines.values(): s.set_color(GRID)
ax.set_title("二十七轮 run 按条件汇总：点 = 单轮最终知情数，横杠 = 中位数", color=INK, fontsize=13, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(HERE, "..", "docs", "figures", "fig12_runs_overview.png"), dpi=150, facecolor=BG)
print("fig12 ok")

#!/usr/bin/env python3
"""fig13: multi 双传闻竞争 — 包裹(有锚) vs 银元(零锚) 知情数随时间"""
import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

_fp = os.environ.get("ATRIA_CJK_FONT", "/home/ubuntu/.fonts/NotoSansSC.ttf")
if os.path.exists(_fp): font_manager.fontManager.addfont(_fp)
plt.rcParams["font.family"] = "Noto Sans SC"
plt.rcParams["axes.unicode_minus"] = False
BG, INK, GRID = "#10131a", "#e8e8ee", "#2a2f3d"

D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")))
R = D["runs"]["multi"]

# export_data 里 multi 的双 marker 分两个键: informed_pkg / informed_silver
pkg, sil = R.get("informed_pkg", {}), R.get("informed_silver", {})

fig, ax = plt.subplots(figsize=(10.5, 5.5), facecolor=BG)
ax.set_facecolor(BG)
for d_, name, c in [(pkg, "包裹错领（有锚点）", "#ffd166"), (sil, "山道银元（零锚，全靠引导编造）", "#f4a261")]:
    pts = sorted((d, sum(1 for v in d_.values() if v <= d)) for d in range(1, R["days"] + 1))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=c, lw=2.4,
            label=f"{name} ({len(d_)}/25)")
ax.axhline(25, color=GRID, lw=1, ls=":")
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("知情居民数", color=INK)
ax.tick_params(colors=INK); ax.set_ylim(0, 27); ax.set_xlim(1, R["days"])
for s in ax.spines.values(): s.set_color(GRID)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=10, loc="lower right")
ax.set_title("multi 双传闻并行：有锚传闻 vs 零锚编造传闻 同台竞争", color=INK, fontsize=13)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures", "fig13_dual_rumor.png"), dpi=150, facecolor=BG)
print("ok", len(pkg), len(sil))

#!/usr/bin/env python3
"""fig8(2x2曲线) + fig11(边数增长) 从 hall/data.json 重画 9 轮版"""
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

ORDER = [("v2", "v2 锚+引", "#ffd166"), ("v2s2", "v2 锚+引·s2", "#ffd166"),
         ("v4np", "v4 锚·无引", "#8ecae6"),
         ("v4np2", "v4 锚·无引·s2", "#8ecae6"),
         ("hint0", "hint0 零锚+引", "#ef8354"), ("hint0s2", "hint0 零锚+引·s2", "#ef8354"),
         ("hint0g", "hint0 零锚+引·银元", "#f4a261"),
         ("v3", "v3 零注入·s1", "#7fd17f"), ("v3s2", "v3 零注入·s2", "#7fd17f"),
         ("v3s3", "v3 零注入·s3", "#7fd17f"), ("multi", "multi 双传闻", "#ffb703"), ("debunk", "debunk 辟谣", "#e07a5f")]
DASH = {"v2s2": "--", "v4np2": "--", "hint0s2": "--", "v3s2": "--", "v3s3": ":", "hint0g": "-."}

# fig8: 知情人数随时间 — 2x2 条件分面小图
GROUPS = [
    ("有锚 × 有引导", [("v2", "s1"), ("v2s2", "s2")], "#ffd166"),
    ("有锚 × 无引导", [("v4np", "s1"), ("v4np2", "s2")], "#8ecae6"),
    ("零锚 × 有引导", [("hint0", "s1·包裹"), ("hint0s2", "s2·包裹"), ("hint0g", "银元泛化")], "#ef8354"),
    ("零锚 × 无引导（零注入）", [("v3", "s1"), ("v3s2", "s2"), ("v3s3", "s3")], "#7fd17f"),
]
fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.5), facecolor=BG, sharex=True, sharey=True)
for ax, (gname, rids, c) in zip(axes.flat, GROUPS):
    ax.set_facecolor(BG)
    for rid, sname in rids:
        R = D["runs"][rid]
        pts = sorted((d, sum(1 for v in R["informed"].values() if v <= d)) for d in range(1, R["days"] + 1))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], DASH.get(rid, "-"),
                color=c, lw=2.2, alpha=0.95, label=f"{sname} ({len(R['informed'])}/25)")
    ax.axhline(25, color=GRID, lw=1, ls=":")
    ax.axhline(24, color=GRID, lw=0.7, ls=":")
    ax.set_title(gname, color=INK, fontsize=12)
    ax.tick_params(colors="#8b93a3")
    ax.set_ylim(0, 27); ax.set_xlim(1, 35)
    for s in ax.spines.values(): s.set_color(GRID)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=9, loc="lower right")
for ax in axes[1]: ax.set_xlabel("模拟日", color=INK)
for ax in axes[:, 0]: ax.set_ylabel("知情居民数", color=INK)
fig.suptitle("十轮 run：知情人数随时间（按 2×2 条件分面）", color=INK, fontsize=14, y=0.985)
plt.tight_layout(rect=[0, 0, 1, 0.97]); plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures", "fig8_2x2_curves.png"), dpi=150, facecolor=BG); plt.close()

# fig11: 累计首传边数
fig, ax = plt.subplots(figsize=(10, 5.5), facecolor=BG)
ax.set_facecolor(BG)
for rid, name, c in ORDER:
    if rid not in D["runs"]: continue
    R = D["runs"][rid]
    days = sorted(e[2] for e in R["edges"])
    pts = []
    for d in range(1, R["days"] + 1):
        pts.append((d, sum(1 for x in days if x <= d)))
    ax.plot([p[0] for p in pts], [p[1] for p in pts], DASH.get(rid, "-"),
            color=c, lw=2.2, label=f"{name} ({len(days)} 边)")
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("累计转述边数", color=INK)
ax.tick_params(colors=INK); ax.set_xlim(1, 35)
for s in ax.spines.values(): s.set_color(GRID)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=9, loc="center right")
ax.set_title("十二轮 run：累计转述边数（传闻链路密度）", color=INK, fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures", "fig11_edge_growth.png"), dpi=150, facecolor=BG); plt.close()
print("done", {r: len(D["runs"][r]["edges"]) for r, _, _ in ORDER if r in D["runs"]})

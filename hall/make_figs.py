#!/usr/bin/env python3
"""fig8(2x2 分面曲线, n=5) + fig11(转述边累计, 分面) — 27 轮口径"""
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
FIGDIR = os.path.join(HERE, "..", "docs", "figures")

def cum_informed(R, key="informed"):
    inf = R[key]
    return [(d, sum(1 for v in inf.values() if v <= d)) for d in range(1, R["days"] + 1)]

def cum_edges(R):
    days = sorted(e[2] for e in R["edges"])
    return [(d, sum(1 for x in days if x <= d)) for d in range(1, R["days"] + 1)]

GROUPS = [
    ("有锚 × 有引导 (v2)", ["v2","v2s2","v2s3","v2s4","v2s5"], "#ffd166", []),
    ("有锚 × 无引导 (v4)", ["v4np","v4np2","v4np3","v4np4","v4np5"], "#8ecae6", []),
    ("零锚 × 有引导 (hint0)", ["hint0","hint0s2","hint0s3","hint0s4","hint0s5"], "#ef8354", []),
    ("零锚 × 无引导 (v3 零注入)", ["v3","v3s2","v3s3","v3s4","v3s5"], "#7fd17f", []),
]
LSS = ["-","--","-.",":",(0,(3,1,1,1))]

# ---------- fig8: 知情曲线 2x2 分面 ----------
fig, axes = plt.subplots(2, 2, figsize=(12, 8), facecolor=BG, sharex=True, sharey=True)
for ax, (gname, rids, c, extra) in zip(axes.flat, GROUPS):
    ax.set_facecolor(BG)
    for i, rid in enumerate(rids):
        R = D["runs"][rid]
        pts = cum_informed(R)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], linestyle=LSS[i % 5],
                color=c, lw=1.9, alpha=0.92, label=f"s{i+1} ({len(R['informed'])}/25)")
    for j, (rid, nm) in enumerate(extra):
        if rid not in D["runs"]: continue
        R = D["runs"][rid]
        pts = cum_informed(R)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], linestyle=(0,(1,1)),
                color="#f4a261", lw=2.2, label=f"{nm} ({len(R['informed'])}/25)")
    ax.axhline(25, color=GRID, lw=1, ls=":"); ax.axhline(24, color=GRID, lw=0.7, ls=":")
    ax.set_title(gname, color=INK, fontsize=12)
    ax.tick_params(colors="#8b93a3"); ax.set_ylim(0, 27); ax.set_xlim(1, 35)
    for s in ax.spines.values(): s.set_color(GRID)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=8.5, loc="lower right", ncol=2)
for ax in axes[1]: ax.set_xlabel("模拟日", color=INK)
for ax in axes[:, 0]: ax.set_ylabel("知情居民数", color=INK)
fig.suptitle("2×2 四格 × 5 种子：知情人数随时间", color=INK, fontsize=14, y=0.985)
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(os.path.join(FIGDIR, "fig8_2x2_curves.png"), dpi=150, facecolor=BG); plt.close()

# ---------- fig11: 累计转述边 2x2 分面 ----------
fig, axes = plt.subplots(2, 2, figsize=(12, 8), facecolor=BG, sharex=True)
for ax, (gname, rids, c, extra) in zip(axes.flat, GROUPS):
    ax.set_facecolor(BG)
    for i, rid in enumerate(rids):
        R = D["runs"][rid]
        pts = cum_edges(R)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], linestyle=LSS[i % 5],
                color=c, lw=1.9, alpha=0.92, label=f"s{i+1} ({len(R['edges'])} 边)")
    for j, (rid, nm) in enumerate(extra):
        if rid not in D["runs"]: continue
        R = D["runs"][rid]
        pts = cum_edges(R)
        ax.plot([p[0] for p in pts], [p[1] for p in pts], linestyle=(0,(1,1)),
                color="#f4a261", lw=2.2, label=f"{nm} ({len(R['edges'])} 边)")
    ax.set_title(gname, color=INK, fontsize=12)
    ax.tick_params(colors="#8b93a3"); ax.set_xlim(1, 35)
    for s in ax.spines.values(): s.set_color(GRID)
    ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=8.5, loc="upper left", ncol=2)
for ax in axes[1]: ax.set_xlabel("模拟日", color=INK)
for ax in axes[:, 0]: ax.set_ylabel("累计转述边数", color=INK)
fig.suptitle("二十七轮 run：累计转述边数（传闻链路密度）", color=INK, fontsize=14, y=0.985)
plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(os.path.join(FIGDIR, "fig11_edge_growth.png"), dpi=150, facecolor=BG); plt.close()
print("fig8/fig11 done")

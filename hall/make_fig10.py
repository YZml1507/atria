#!/usr/bin/env python3
"""fig10a: 六轮 run 首传树地理布局对比 (2x3); fig10b: v2 全量传播邻接热图"""
import json, os, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D

_fp = os.environ.get("ATRIA_CJK_FONT", "/home/ubuntu/.fonts/NotoSansSC.ttf")
if os.path.exists(_fp): font_manager.fontManager.addfont(_fp)
plt.rcParams["font.family"] = "Noto Sans SC"
plt.rcParams["axes.unicode_minus"] = False
BG, INK, GRID = "#10131a", "#e8e8ee", "#2a2f3d"

D = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")))
pos = [a["cell"] for a in D["agents"]]
names = [a["name"] for a in D["agents"]]
xs = [p[0] for p in pos]; ys = [-p[1] for p in pos]

def rumor_color(rid, text):
    if rid != "multi":
        return None
    if any(k in text for k in ["银元", "山道", "挖出", "坛子"]):
        return "#c77dff"          # 银元(零锚编造)
    return "#ffd166"              # 包裹(有锚)

panels = [
    ("v2",     "v2 有锚+引导 · 25/25@D9",    "#ffd166"),
    ("hint0",  "hint0 零锚编造 · 25/25@D8",  "#8ecae6"),
    ("hint0g", "hint0g 零锚·银元 · 24/25@D12","#c77dff"),
    ("multi",  "multi 双传闻竞争",            "#ffd166"),
    ("debunk", "debunk D7辟谣 · 25/25@D7",   "#ff8a80"),
    ("v3",     "v3 零注入·s1 · 4/25 停滞",    "#7fd17f"),
]

fig, axes = plt.subplots(2, 3, figsize=(17.5, 11.6), facecolor=BG)
for ax, (rid, title, c) in zip(axes.flat, panels):
    ax.set_facecolor(BG)
    edges = D["runs"][rid]["edges"]
    first = [e for e in edges if e[4] == 1]
    inf = D["runs"][rid]["informed"]
    inf_day = {int(k): v for k, v in inf.items()}
    node_c = ["#ffd166" if inf_day.get(i, 99) <= 3 else "#8ecae6" if inf_day.get(i, 99) <= 8 else "#4a5364" for i in range(len(pos))]
    ax.scatter(xs, ys, s=85, c=node_c, zorder=3, edgecolors="#10131a", linewidths=0.8)
    n_pkg = n_sil = 0
    for e in first:
        col = rumor_color(rid, e[5]) or c
        if rid == "multi":
            if col == "#c77dff": n_sil += 1
            else: n_pkg += 1
        a, b = pos[e[0]], pos[e[1]]
        ax.annotate("", xy=(b[0], -b[1]), xytext=(a[0], -a[1]),
                    arrowprops=dict(arrowstyle="-|>", color=col, lw=1.7, alpha=0.85,
                                    shrinkA=7, shrinkB=7, connectionstyle="arc3,rad=0.18"))
    if rid == "multi":
        title = f"{title}\n包裹 {n_pkg} 边(金) vs 银元 {n_sil} 边(紫)：有锚碾压零锚"
    else:
        title = f"{title}\n{len(first)} 条首传边"
    ax.set_title(title, color=INK, fontsize=12, pad=7)
    ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal")
    for s in ax.spines.values(): s.set_color(GRID)

leg = [Line2D([0], [0], marker="o", color="none", markerfacecolor="#ffd166", markersize=9, label="第1-3天知情"),
       Line2D([0], [0], marker="o", color="none", markerfacecolor="#8ecae6", markersize=9, label="第4-8天知情"),
       Line2D([0], [0], marker="o", color="none", markerfacecolor="#4a5364", markersize=9, label="第9天+ / 未知情")]
fig.legend(handles=leg, loc="lower center", ncol=3, facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=10.5)
fig.suptitle("首次转述链（箭头 = 谁先告诉谁；六轮 run 对比）", color=INK, fontsize=15, y=0.99)
plt.tight_layout(rect=[0, 0.05, 1, 0.96])
plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures", "fig10_diffusion_network.png"), dpi=150, facecolor=BG)
plt.close()

# ---------- fig10b: 25x25 邻接热图 (v2 全量转述次数) ----------
mat = np.zeros((25, 25))
import re
tell = re.compile(r"^(.+?)\s*(?:告诉我|回我说)[:：]")
nidx = {n: i for i, n in enumerate(names)}
for dst, rows in D["runs"]["v2"]["mem_rumor"].items():
    for day, step, kind, text in rows:
        if kind != "对话": continue
        m = tell.match(text)
        if not m: continue
        src = nidx.get(m.group(1).strip())
        if src is not None and src != int(dst):
            mat[src, int(dst)] += 1
order = sorted(range(25), key=lambda i: -mat[i].sum())
M = mat[np.ix_(order, order)]
fig, ax = plt.subplots(figsize=(9.5, 8), facecolor=BG)
ax.set_facecolor(BG)
im = ax.imshow(np.log1p(M), cmap="magma", aspect="equal")
ax.set_xticks(range(25)); ax.set_yticks(range(25))
ax.set_xticklabels([names[i] for i in order], rotation=90, fontsize=6.5, color=INK)
ax.set_yticklabels([names[i] for i in order], fontsize=6.5, color=INK)
ax.set_xlabel("被告知者 →", color=INK, fontsize=11); ax.set_ylabel("转述者 ↓", color=INK, fontsize=11)
cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
cb.set_label("log(1+转述次数)", color=INK); cb.ax.yaxis.set_tick_params(color=INK); plt.setp(cb.ax.yaxis.get_ticklabels(), color=INK)
ax.set_title("v2 全量转述邻接矩阵（行=谁在说，列=谁被告诉，按出度排序）", color=INK, fontsize=12.5, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures", "fig10b_adjacency.png"), dpi=150, facecolor=BG)
print("ok")

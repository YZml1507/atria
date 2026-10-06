#!/usr/bin/env python3
"""重生成早期白底图为深色统一风格:
fig1  三碎片转述分组柱状(有引导/无引导)
fig5  v2 vs v3 知情曲线(归档报告用, s1-s3)
fig6  零注入传闻生命周期双峰: v3s1 停滞 vs v3s4 涌现饱和
fig7  社会活跃度对照: 逐日事件数
fig9  hint0 编造词逐日频次 (5 种子细线+均值)
数据源: hall/data.json + run_*/dayNN.jsonl 原始事件流
"""
import json, os, glob, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

_fp = os.environ.get("ATRIA_CJK_FONT", "/home/ubuntu/.fonts/NotoSansSC.ttf")
if os.path.exists(_fp): font_manager.fontManager.addfont(_fp)
plt.rcParams["font.family"] = "Noto Sans SC"
plt.rcParams["axes.unicode_minus"] = False
BG, INK, GRID = "#10131a", "#e8e8ee", "#2a2f3d"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(ROOT, "docs", "figures")
D = json.load(open(os.path.join(HERE, "data.json")))

def new_ax(w, h):
    fig, ax = plt.subplots(figsize=(w, h), facecolor=BG)
    ax.set_facecolor(BG)
    ax.tick_params(colors="#8b93a3")
    for s in ax.spines.values(): s.set_color(GRID)
    return fig, ax

def save(fig, name):
    fig.savefig(os.path.join(FIG, name), dpi=150, facecolor=BG)
    plt.close(fig); print(name, "ok")

def cum_informed(R):
    by = {}
    for i, d in R["informed"].items():
        if d: by.setdefault(d, 0); by[d] += 1
    acc, out = 0, []
    for d in range(1, R["days"] + 1):
        acc += by.get(d, 0); out.append((d, acc))
    return out

def daily_say_count(run_dir, mk, per_person=False):
    """逐日 say 命中词族的条数, 或(per_person)独立人数"""
    out = []
    for d in range(1, 36):
        f = os.path.join(ROOT, run_dir, f"day{d:02d}.jsonl")
        if not os.path.exists(f): break
        n, ppl = 0, set()
        for line in open(f):
            e = json.loads(line); s = e.get("say") or ""
            if any(k in s for k in mk):
                n += 1; ppl.add(e.get("agent", ""))
        out.append(len(ppl) if per_person else n)
    return out

# ---------- fig1: 三碎片转述次数 分组柱状 ----------
frags = ["扳指(具体)", "方向(半具体)", "颜色(不确定)"]
guided = [164, 30, 0]; unguided = [44, 8, 0]
x = np.arange(3); w = 0.34
fig, ax = new_ax(8.2, 4.4)
b1 = ax.bar(x - w/2, guided, w, color="#ffd166", label="有引导 (v2)")
b2 = ax.bar(x + w/2, unguided, w, color="#8ecae6", label="无引导 (v4)")
for b in list(b1) + list(b2):
    ax.annotate(f"{int(b.get_height())}", (b.get_x() + b.get_width()/2, b.get_height() + 3),
                ha="center", color=INK, fontsize=11)
ax.set_xticks(x); ax.set_xticklabels(frags, color=INK, fontsize=11)
ax.set_ylabel("14 天被传递次数", color=INK)
ax.set_title("措辞确定性决定碎片存活：不确定碎片被静默丢弃", color=INK, fontsize=13, pad=8)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK)
ax.set_ylim(0, 190)
save(fig, "fig1_spread.png")

# ---------- fig5: v2 vs v3(s1-s3) 知情曲线 ----------
fig, ax = new_ax(8.6, 4.6)
R = D["runs"]["v2"]; pts = cum_informed(R)
ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#ffd166", lw=2.4, label="v2 有锚+引导 (25/25)")
for rid, lab, ls in [("v3","v3 s1 (4/25)","-"), ("v3s2","v3 s2 (19/25)","--"), ("v3s3","v3 s3 (9/25)","-.")]:
    R = D["runs"][rid]; pts = cum_informed(R)
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#7fd17f", lw=1.8, ls=ls, label=lab)
ax.axhline(25, color=GRID, lw=1, ls=":")
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("知情居民数", color=INK)
ax.set_title("传播动力学对照：注入曲线 S 型 vs 零注入平台期", color=INK, fontsize=13, pad=8)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=9, loc="center right")
ax.set_xlim(1, 35); ax.set_ylim(0, 27)
save(fig, "fig5_spread_v3_vs_v2.png")

# ---------- fig6: 生命周期双峰 s1 停滞 vs s4 涌现 ----------
MK3 = ["远客","新来的","新来","南边来","本县人","外乡","那户人家","生面孔"]
MK4 = ["磨坊","磨盘","刨开","邪乎","邪性","邪门","底下埋","埋了东西","埋了啥","撬磨盘","磨坊半夜","磨坊响","磨坊里响","磨坊的声响","半夜响","磨坊老有","磨盘松","刨磨盘"]
s1 = daily_say_count("run_v3", MK3, per_person=True)
s4 = daily_say_count("run_v3s4", MK4, per_person=True)
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), facecolor=BG, sharey=True)
for ax in axes:
    ax.set_facecolor(BG); ax.tick_params(colors="#8b93a3")
    for s in ax.spines.values(): s.set_color(GRID)
axes[0].bar(range(1, len(s1)+1), s1, color="#7fd17f", alpha=.85)
axes[0].axvspan(0.5, 8.5, color="#ffd166", alpha=.08)
axes[0].annotate("扩散期 D1–8", (4.5, 3.4), color="#ffd166", ha="center", fontsize=9)
axes[0].annotate("空转期 D9–35", (22, 3.4), color="#8b93a3", ha="center", fontsize=9)
axes[0].set_title("v3·s1 「远客」传闻: 4/25 停滞", color=INK, fontsize=11.5)
axes[1].bar(range(1, len(s4)+1), s4, color="#7fd17f", alpha=.85)
axes[1].axvspan(19, 35.5, color="#ffd166", alpha=.08)
axes[1].annotate("D19 起发酵 → D32 全镇饱和", (27, 21), color="#ffd166", ha="center", fontsize=9)
axes[1].set_title("v3·s4 「磨坊埋物」传闻: 25/25 涌现饱和", color=INK, fontsize=11.5)
for ax in axes:
    ax.set_xlabel("模拟日", color=INK); ax.set_xlim(0.5, 35.5)
axes[0].set_ylabel("当日提及人数", color=INK)
fig.suptitle("零注入传闻的生命周期: 同条件, 相反结局", color=INK, fontsize=13, y=1.0)
plt.tight_layout()
save(fig, "fig6_rumor_lifecycle.png")

# ---------- fig7: 逐日事件数 活跃度对照 ----------
def daily_events(run_dir, days):
    out = []
    for d in range(1, days+1):
        f = os.path.join(ROOT, run_dir, f"day{d:02d}.jsonl")
        out.append(sum(1 for _ in open(f)) if os.path.exists(f) else 0)
    return out
ev2 = daily_events("run_v2", 14); ev3 = daily_events("run_v3", 35)
fig, ax = new_ax(9, 4.2)
ax.plot(range(1,15), ev2, color="#ffd166", lw=2.2, label="v2 有锚+引导 (14 天)")
ax.plot(range(1,36), ev3, color="#7fd17f", lw=2.2, label="v3 零注入 (35 天)")
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("当日事件数", color=INK)
ax.set_title("社会活跃度对照：两条件日常活跃相当 — 传播差异不是活跃度造成的", color=INK, fontsize=12, pad=8)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=9)
save(fig, "fig7_activity.png")

# ---------- fig9: hint0 编造词频次 (5 种子+均值) ----------
runs = ["run_hint0","run_hint0s2","run_hint0s3","run_hint0s4","run_hint0s5"]
MK = ["包裹","错领","扳指","邮局","纸箱","旧物"]
series = [daily_say_count(r, MK)[:14] for r in runs]
fig, ax = new_ax(9, 4.4)
lss = ["-","--","-.",":",(0,(3,1,1,1))]
for i, s in enumerate(series):
    ax.plot(range(1, len(s)+1), s, color="#ef8354", lw=1.4, ls=lss[i], alpha=.75, label=f"s{i+1}")
mean = [sum(s[d] for s in series)/len(series) for d in range(14)]
ax.plot(range(1,15), mean, color="#ffd166", lw=2.6, label="五种子均值")
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("编造词出现次数(台词)", color=INK)
ax.set_title("hint0: 「包裹/错领/扳指/邮局」词族逐日频次 — 引导语从无到有造出谈资 (n=5)", color=INK, fontsize=12, pad=8)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=8.5, ncol=3)
ax.set_xlim(1, 14)
save(fig, "fig9_hint0_fabrication.png")

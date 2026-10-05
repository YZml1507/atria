#!/usr/bin/env python3
"""fig12: 十轮实验对比总表 — 知情人数条形 + 饱和天数标注"""
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

# (rid, 显示名, 颜色, 条件分组)
ROWS = [("v2",   "v2 锚+引·s1",   "#ffd166", "有锚×有引导"),
        ("v2s2", "v2 锚+引·s2",   "#ffd166", "有锚×有引导"),
        ("v4np", "v4 锚·无引·s1", "#8ecae6", "有锚×无引导"),
        ("v4np2","v4 锚·无引·s2", "#8ecae6", "有锚×无引导"),
        ("hint0","hint0 零锚+引·s1","#ef8354","零锚×有引导"),
        ("hint0s2","hint0 零锚+引·s2","#ef8354","零锚×有引导"),
        ("hint0g","hint0 零锚+引·银元","#f4a261","零锚×有引导(泛化)"),
        ("v3",   "v3 零注入·s1",  "#7fd17f", "零锚×无引导"),
        ("v3s2", "v3 零注入·s2",  "#7fd17f", "零锚×无引导"),
        ("v3s3", "v3 零注入·s3",  "#7fd17f", "零锚×无引导"),
        ("multi","multi 双传闻·包裹侧","#ffb703","有锚×双引"),
        ("debunk","debunk 辟谣·s1","#e07a5f","有锚×有引导+辟谣")]

fig, ax = plt.subplots(figsize=(11, 6), facecolor=BG)
ax.set_facecolor(BG)
yi = len(ROWS)
for i, (rid, name, c, grp) in enumerate(ROWS):
    if rid not in D["runs"]: continue
    R = D["runs"][rid]
    inf_d = R.get("informed_pkg", R["informed"])
    inf = len(inf_d)
    last = max(inf_d.values()) if inf else 0
    sat_day = last if inf >= 25 else None
    yi -= 1
    extra = ""
    if "informed_silver" in R:
        extra = f"（银元 {len(R['informed_silver'])}/25）"
    ax.barh(yi, inf, color=c, alpha=0.85, height=0.68)
    txt = f"{inf}/25{extra}"
    if sat_day: txt += f"  ·  第{sat_day}天饱和"
    elif inf >= 24: txt += f"  ·  第{last}天达峰(未饱和)"
    else: txt += f"  ·  {R['days']}天未饱和"
    ax.text(inf + 0.35, yi, txt, va="center", color=INK, fontsize=10.5)
    ax.text(-0.4, yi, name, va="center", ha="right", color=INK, fontsize=10.5)
ax.set_yticks([])
ax.set_xlim(0, 32); ax.set_xlabel("最终知情人数（25 人全镇）", color=INK, fontsize=11)
ax.axvline(25, color="#5a6478", ls=":", lw=1)
ax.text(25.15, -0.9, "饱和线", color="#8b93a3", fontsize=9, va="top")
ax.set_title("全部 run 对比：注入/引导条件全体饱和，零注入三种子无一饱和", color=INK, fontsize=13, pad=10)
ax.tick_params(colors="#8b93a3")
for s in ax.spines.values(): s.set_color(GRID)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures", "fig12_runs_overview.png"), dpi=150, facecolor=BG)
print("ok")

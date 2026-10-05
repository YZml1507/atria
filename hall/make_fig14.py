#!/usr/bin/env python3
"""fig14: debunk 辟谣干预 — 第7天公告前后, 传闻提及率 vs 对照组(v2/v2s2)"""
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
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def daily_mentions(run_dir, days):
    """每日事件中提及传闻关键词的人次(同一agent同一天只算一次)"""
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

fig, ax = plt.subplots(figsize=(11, 5.8), facecolor=BG)
ax.set_facecolor(BG)

for rid, name, c, ls in [("run_v2", "v2 对照·s1", "#8ecae6", "--"),
                          ("run_v2s2", "v2 对照·s2", "#8ecae6", ":"),
                          ("run_debunk", "debunk 第7天辟谣", "#ffd166", "-")]:
    cnt = daily_mentions(os.path.join(REPO, rid), 14)
    ax.plot(range(1, 15), cnt, ls, color=c, lw=2.4 if ls == "-" else 1.6,
            alpha=1 if ls == "-" else 0.65, label=name)

ax.axvline(7, color="#ef8354", lw=1.6, ls="-", alpha=0.9)
ax.text(7.15, ax.get_ylim()[1] * 0.92, "第7天 镇公所辟谣公告", color="#ef8354", fontsize=10.5)
ax.set_xlabel("模拟日", color=INK); ax.set_ylabel("当日提及传闻的居民数", color=INK)
ax.tick_params(colors=INK); ax.set_xlim(1, 14); ax.set_ylim(bottom=0)
for s in ax.spines.values(): s.set_color(GRID)
ax.legend(facecolor=BG, edgecolor=GRID, labelcolor=INK, fontsize=10)
ax.set_title("辟谣干预：公告注入后传闻提及率是否衰减（对照 = 无干预双种子）", color=INK, fontsize=12.5)
plt.tight_layout()
plt.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "figures", "fig14_debunk.png"), dpi=150, facecolor=BG)
print("ok")

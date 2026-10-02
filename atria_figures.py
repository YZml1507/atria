"""Atria Demo — 证据图生成
输出 4 张静态图到 atri­a_repo/docs/figures/:
  fig1_spread.png   知情扩散曲线 + 三碎片命运分化
  fig2_cost.png     成本实测 vs 推算(墙钟/调用/429 吸收)
  fig3_sellpoint.png P1v5 判据完整性对照(全量 vs RAG)
  fig4_memory.png   记忆规模增长 + 与 Smallville/512K 卖点的关系
"""
import json, os, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

# 中文字体
font_manager.fontManager.addfont("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
plt.rcParams["font.family"] = ["WenQuanYi Zen Hei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

C = {"bg":"#fafafa", "ink":"#2b2b2b", "grey":"#9a9a9a",
     "red":"#d64545", "blue":"#3366cc", "green":"#4a9d5e",
     "amber":"#d99a2b", "purple":"#7a5ea8", "teal":"#2a9d8f"}

OUT = "/home/ubuntu/atria_repo/docs/figures"
os.makedirs(OUT, exist_ok=True)

# ---------- 数据加载 ----------
def daily_events():
    return [(d, sum(1 for _ in open(f"/home/ubuntu/atria_run/day{d:02d}.jsonl"))) for d in range(1,15)]

def know_curve():
    """1-4 天用事件 say 回填, 5-14 天用记忆 checkpoint"""
    pts=[]
    for d in range(1,5):
        know=set()
        for l in open(f"/home/ubuntu/atria_run/day{d:02d}.jsonl"):
            e=json.loads(l)
            if any(k in str(e.get("say","")) for k in ["包裹","错领","领走","扳指"]): know.add(e["agent"])
        pts.append((d,len(know)))
    for d in range(5,15):
        m=json.load(open(f"/home/ubuntu/atria_run/mem_day{d:02d}.json"))
        know=set()
        for p,recs in m.items():
            for r in recs:
                if any(k in str(r) for k in ["包裹","错领","领走","扳指"]): know.add(p); break
        pts.append((d,len(know)))
    return pts

def llm_daily():
    """从 full.log 解析每日累计 calls/r429"""
    import re
    pts=[]
    for l in open("/home/ubuntu/atria_run/full.log",encoding="utf-8",errors="replace"):
        m=re.search(r"第(\d+)天完成.*?累计墙钟 (\d+)s.*?LLM \{[^}]*'calls': (\d+)[^}]*'r429': (\d+)", l)
        if m:
            pts.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))))
    # day1-4 用比例补(从总量按事件数摊)
    return pts

def mem_growth():
    pts=[]
    for d in range(5,15):
        p=f"/home/ubuntu/atria_run/mem_day{d:02d}.json"
        if os.path.exists(p):
            m=json.load(open(p))
            pts.append((d, sum(len(v) for v in m.values())))
    return pts

# ---------- 图1: 知情扩散 + 碎片分化 ----------
def fig1():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), facecolor="white")
    kc = know_curve()
    xs, ys = zip(*kc)
    ax1.plot(xs, ys, "-o", color=C["blue"], lw=2.2, ms=6, zorder=3)
    ax1.fill_between(xs, ys, color=C["blue"], alpha=0.10)
    ax1.axhline(25, color=C["grey"], ls="--", lw=1.2)
    ax1.text(13.6, 23.6, "全镇 25 人", fontsize=9, color=C["grey"])
    ax1.annotate(f"饱和于 {ys[-1]}/25\n3 名中性居民永不知情",
                 xy=(12, ys[-1]), xytext=(8.2, 13), fontsize=9.5,
                 arrowprops=dict(arrowstyle="->", color=C["ink"], lw=1))
    ax1.annotate("第2天引爆\n(错领事件)", xy=(2, ys[1]), xytext=(2.6, 4.5), fontsize=9.5,
                 arrowprops=dict(arrowstyle="->", color=C["red"], lw=1.2))
    # 口径切换标记
    ax1.axvline(4.5, color=C["grey"], ls=":", lw=1.5)
    ax1.text(4.7, 2.5, "← 事件口径 | 记忆口径 →", fontsize=8, color=C["grey"])
    for x,y in zip(xs,ys):
        if x in (1,4,14): ax1.annotate(str(y), (x,y), textcoords="offset points", xytext=(0,8), fontsize=9, ha="center")
    ax1.set_xlabel("游戏日", fontsize=11); ax1.set_ylabel("知情人数", fontsize=11)
    ax1.set_xticks(range(1,15)); ax1.set_ylim(0,26); ax1.grid(alpha=.25)
    ax1.set_title("a. 知情扩散曲线(记忆流实测, 非统计推断)", fontsize=12, fontweight="bold")

    # 右: 三碎片条形
    frags = [("扳指碎片\n(具体·可验证)", 40, C["green"]),
             ("方向碎片\n(中等)", 8, C["amber"]),
             ("颜色碎片\n(措辞不确定)", 0, C["grey"])]
    names=[f[0] for f in frags]; vals=[f[1] for f in frags]; cols=[f[2] for f in frags]
    bars=ax2.bar(names, vals, color=cols, width=.55, zorder=3)
    for b,(n,v,c) in zip(bars, frags):
        label = f"{v} 条" if v>0 else "0 条 · 无人传播"
        ax2.text(b.get_x()+b.get_width()/2, max(v,1)+1.2, label, ha="center", fontsize=10.5, fontweight="bold")
    ax2.set_ylim(0, 48); ax2.grid(axis="y", alpha=.25)
    ax2.set_ylabel("14 天后终局记忆条数", fontsize=11)
    ax2.set_title("b. 三碎片命运分化: 不确定细节被传播链静默丢弃", fontsize=12, fontweight="bold")
    fig.suptitle("图 1  信息扩散与保真度分化 — 全部来自 25 人 × 14 天实跑数据", fontsize=13.5, fontweight="bold", y=1.02)
    fig.tight_layout()
    p=f"{OUT}/fig1_spread.png"; fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved", p)

# ---------- 图2: 成本 ----------
def fig2():
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), facecolor="white")
    # a 墙钟
    ax=axes[0]
    ax.bar(["实测","方案推算\n(1.6–2.5h 区间)"], [35, 123], color=[C["green"], C["grey"]], width=.5, zorder=3,
           yerr=[[0],[27]], error_kw=dict(ecolor=C["ink"], lw=1.2, capsize=4, capthick=1.2))
    ax.text(0, 38, "35 分钟\n(快 2.7–4.3 倍)", ha="center", fontsize=10, fontweight="bold")
    ax.text(1, 155, "误差棒: 96–150 分钟\n(推算区间)", ha="center", fontsize=9)
    ax.set_ylim(0,185); ax.grid(axis="y", alpha=.25)
    ax.set_ylabel("墙钟(分钟)", fontsize=10)
    ax.set_title("a. 墙钟: 25 人 × 14 天", fontsize=11.5, fontweight="bold")

    # b LLM 调用构成
    ax=axes[1]
    labels=["成功","429 重试\n(全部吸收)","fallback","其他错误"]
    vals=[834,77,37,1]
    cols=[C["green"], C["amber"], C["grey"], C["red"]]
    bars=ax.bar(labels, vals, color=cols, width=.55, zorder=3)
    for b,v in zip(bars,vals):
        ax.text(b.get_x()+b.get_width()/2, v+18, f"{v}\n({v/1413*100:.1f}%)", ha="center", fontsize=9.5)
    ax.set_ylim(0,1000); ax.grid(axis="y", alpha=.25)
    ax.set_title(f"b. LLM 调用 1,413 次: 零失败外泄", fontsize=11.5, fontweight="bold")

    # c 调用速率 vs 限额
    ax=axes[2]
    ax.bar(["令牌桶设定","端点实测限额","裸线程池\n(会超限)"], [40, 52.5, 65.9],
           color=[C["blue"], C["green"], C["red"]], width=.5, zorder=3)
    for i,v in enumerate([40,52.5,65.9]):
        ax.text(i, v+1.5, f"{v} RPM", ha="center", fontsize=10, fontweight="bold")
    ax.set_ylim(0,78); ax.grid(axis="y", alpha=.25)
    ax.set_title("c. 限速: 令牌桶 40 RPM\n429 零外泄的工程原因", fontsize=11.5, fontweight="bold")
    fig.suptitle("图 2  运行成本 — 推算被实测推翻, 实际远好于预期", fontsize=13.5, fontweight="bold", y=1.04)
    fig.tight_layout()
    p=f"{OUT}/fig2_cost.png"; fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved", p)

# ---------- 图3: P1v5 卖点对照 ----------
def fig3():
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), facecolor="white", gridspec_kw={"width_ratios":[1,1.25]})
    # a: 判据完整性
    ax=axes[0]
    cats=["答案正确\n(事实回忆)","指出矛盾\n/来源","分辨一手\nvs 转述"]
    full=[1,1,1]; rag=[1,0,0]
    x=range(3); w=.32
    b1=ax.bar([i-w/2 for i in x], full, w, color=C["green"], label="全量 512K 窗口", zorder=3)
    b2=ax.bar([i+w/2 for i in x], rag, w, color=C["grey"], label="RAG top-30 检索", zorder=3)
    for i in x:
        ax.text(i-w/2, 1.03, "✓", ha="center", fontsize=13, color=C["green"], fontweight="bold")
        ax.text(i+w/2, rag[i]+1.03, "✓" if rag[i] else "✗", ha="center", fontsize=13,
                color=C["green"] if rag[i] else C["red"], fontweight="bold")
    ax.set_xticks(list(x)); ax.set_xticklabels(cats, fontsize=9.5)
    ax.set_ylim(0,1.35); ax.set_yticks([0,1]); ax.set_yticklabels(["","1 分"])
    ax.legend(fontsize=9.5, loc="lower right")
    ax.grid(axis="y", alpha=.25)
    ax.set_title("a. 判据完整性: 全量 3/3 vs RAG 1/3", fontsize=11.5, fontweight="bold")

    # b: token 规模对数图
    ax=axes[1]
    labels=["RAG top-30\n(检索结果)","全量窗口\n(P1v5 实灌)","512K\n窗口上限"]
    vals=[830/1000, 138.5, 512]  # K token
    cols=[C["grey"], C["green"], C["blue"]]
    bars=ax.bar(labels, vals, color=cols, width=.5, zorder=3)
    txts=["0.83K token\n(覆盖率 0.48%)","138K token\n(6,304 条记忆)","512K"]
    for b,t,v in zip(bars,txts,vals):
        ax.text(b.get_x()+b.get_width()/2, v*1.35, t, ha="center", fontsize=9, fontweight="bold")
    ax.set_yscale("log"); ax.set_ylim(.3, 3000); ax.set_ylabel("prompt token (K, 对数轴)", fontsize=10)
    ax.grid(True, which="both", alpha=.2)
    ax.set_title("b. 记忆规模差 167 倍, 判据完整性差 3 倍", fontsize=11.5, fontweight="bold")
    fig.suptitle("图 3  卖点验证: 全量时间线分辨传言变异 (P1v5 对照实验)", fontsize=13.5, fontweight="bold", y=1.04)
    fig.tight_layout()
    p=f"{OUT}/fig3_sellpoint.png"; fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved", p)

# ---------- 图4: 记忆规模 ----------
def fig4():
    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor="white")
    mg = mem_growth()
    xs, ys = zip(*mg)
    ax.plot(xs, ys, "-o", color=C["purple"], lw=2.2, ms=6, label="Atria 正式跑(25 人合计)", zorder=3)
    ax.fill_between(xs, ys, color=C["purple"], alpha=.10)

    # Smallville 对照: 912 条/人/日 x 25 人
    sb=[912*25*(d-4) for d in xs]
    ax.plot(xs, sb, "--", color=C["grey"], lw=1.8, label="Smallville 密度(912 条/人/日, 含 63% idle 噪声)")
    # 512K 卖点所需规模: 单人 6304 条才测出差异(P1v5), 25 人 = 157,600 条
    ax.axhline(6304, color=C["blue"], ls=":", lw=2)
    ax.text(13.6, 6304*1.8, "P1v5 测出差异\n所需单人规模\n6,304 条", fontsize=8.5, color=C["blue"], ha="right")

    ax.set_xlabel("游戏日", fontsize=11); ax.set_ylabel("记忆总条数", fontsize=11)
    ax.set_yscale("log"); ax.set_ylim(100, 3_000_000)
    ax.set_xticks(range(5,15)); ax.grid(True, which="both", alpha=.2)
    ax.legend(fontsize=9.5, loc="upper left")
    ax.set_title("图 4  记忆规模: 正式跑仅 709 条(诚实记录 idle 压缩的代价)\n512K 卖点由独立实验 P1v5 验证, 不依赖正式跑密度", fontsize=12.5, fontweight="bold")
    p=f"{OUT}/fig4_memory.png"; fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig)
    print("saved", p)

fig1(); fig2(); fig3(); fig4()
print("\n全部完成")

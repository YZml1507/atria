#!/usr/bin/env python3.12
"""Atria 视频 v6 渲染 — 按调研结论的四幕结构

[已弃用] 已知缺陷: -shortest 截掉结尾旁白 / 句标与 mp3 顺序错位导致提示抢跑 /
        结尾大字叠穿 / 全程无小镇画面。请改用 atria_video_v7.py。本文件保留供溯源。

四幕时间轴(从旁白时间轴读, 不硬编码):
  HOOK      0 - ~9s    : 第二人称 + 常识→矛盾
  SETUP     ~9 - ~28s  : 纸箱事件 + 三碎片
  PROGRESSION ~28 - ~84s: 三阶梯递进(扳指→方向→颜色) + 误传/反派
  REVEAL    ~84 - 155s : v3 零注入对照 + 收尾问句
"""
import os, json, glob
import pygame

HERE = os.path.dirname(os.path.abspath(__file__))
RUN2 = os.environ.get("ATRIA_RUN2", os.path.join(HERE, "run_v2"))
RUN3 = os.environ.get("ATRIA_RUN3", os.path.join(HERE, "run_v3"))
NARR_DIR = os.environ.get("ATRIA_NARR", os.path.join(HERE, "narration_v6"))
W, H = 1280, 720
FPS = 30

# 四幕的句子分割点(按文案结构, 时间从 timeline 读)
ACT_Hook = ["n00","n01","n02","n03"]
ACT_Setup = ["n04","n05","n06","n07","n08","n09"]
ACT_Prog = ["n10","n11","n12","n13","n14","n15","n16","n17","n18","n19","n20","n21","n22"]
ACT_Reveal = ["n23","n24","n25","n26","n27","n28","n29","n30","n31","n32","n33","n34","n35","n36","n37","n38"]

pygame.init()
pygame.display.set_mode((W, H), pygame.HIDDEN)
screen = pygame.Surface((W, H))

def font(sz, bold=False):
    return pygame.font.Font("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", sz)

f_title = font(34, True)
f_big = font(64, True)
f_sub = font(24)
f_small = font(20)

TL = json.load(open(f"{NARR_DIR}/timeline.json"))["timeline"]
TOTAL = json.load(open(f"{NARR_DIR}/timeline.json"))["total"]

# ---------- 数据(回源核验过的常量) ----------
KNOWS = [11, 16, 17, 19, 22, 22, 23, 24, 25, 25, 25, 25, 25, 25]
FRAGS = [("扳指", 164, (90, 200, 90)), ("方向", 30, (230, 180, 60)), ("颜色", 0, (150, 150, 150))]
V3_CUM = [1, 3] + [4]*33
RUMOR4 = ["吕婶", "钱老板", "许货郎", "朱寡妇"]

def text(s, f, color, x, y, anchor="midtop"):
    surf = f.render(s, True, color)
    r = surf.get_rect()
    setattr(r, anchor, (x, y))
    screen.blit(surf, r)

def act_of(t):
    """当前在哪一幕"""
    def start(name):
        return TL[name]["start"]
    if t < start("n04"):  return "hook"
    if t < start("n10"):  return "setup"
    if t < start("n23"):  return "prog"
    return "reveal"

def day_of(t, ndays, nstart, nend):
    """把 [nstart, nend] 句的时段线性映射到 1..ndays"""
    s0, s1 = TL[nstart]["start"], TL[nend]["start"] + TL[nend]["dur"]
    if s1 <= s0: return 1
    frac = max(0, min(1, (t - s0) / (s1 - s0)))
    return max(1, min(ndays, int(frac * ndays) + 1))

# ---------- 精灵 ----------
sprites = {}
for f in glob.glob(f"{HERE}/sprites/*.png"):
    n = os.path.basename(f).replace(".png", "")
    try: sprites[n] = pygame.transform.scale(pygame.image.load(f), (44, 58))
    except Exception: pass
names25 = sorted(sprites.keys())[:25]

# ---------- 各幕画面 ----------
def draw_common():
    screen.fill((22, 22, 32))

def frame_hook(t):
    draw_common()
    # hook: 全黑 + 大字句, 不露小镇(悬念)
    # n02 时amping: 二十五
    if t >= TL["n02"]["start"]:
        a = min(1.0, (t - TL["n02"]["start"]) / 0.8)
        c = (int(180*a), int(200*a), int(255*a))
        text("25 个居民", f_big, c, W/2, H/2 - 60)
        text("没有一个是人类", f_sub, (int(150*a), int(160*a), int(180*a)), W/2, H/2 + 20)
    return

def frame_setup(t):
    draw_common()
    # 邮局场景: 左侧事件描述, 右侧三个目击者
    text("安镇 · 邮局", f_title, (255, 220, 140), 40, 30, "topleft")
    day = day_of(t, 1, "n04", "n09")
    text("第 1 天", f_sub, (200, 200, 210), 40, 74, "topleft")
    # 三碎片逐条出现
    frags = [("旧扳指", "李大姐", (90, 200, 90), "n06"),
             ("往镇东头走", "赵医生", (230, 180, 60), "n07"),
             ("好像是灰色", "周老师", (150, 150, 160), "n08")]
    for i, (frag, who, c, n) in enumerate(frags):
        if t >= TL[n]["start"]:
            a = min(1.0, (t - TL[n]["start"]) / 0.6)
            col = tuple(int(x*a) for x in c)
            y = 160 + i * 130
            text(frag, f_big, col, W/2 - 200, y, "midleft")
            text(f"— {who}", f_sub, (int(140*a), int(140*a), int(150*a)), W/2 + 80, y + 18, "midleft")
    # 底部问题句
    if t >= TL["n09"]["start"]:
        text("哪个会传遍全镇？", f_title, (255, 255, 255), W/2, H - 110)

def frame_prog(t):
    draw_common()
    text("安镇 · 14 天", f_title, (255, 220, 140), 40, 30, "topleft")
    day = day_of(t, 14, "n10", "n22")
    text(f"第 {day} / 14 天", f_sub, (200, 200, 210), 40, 74, "topleft")
    # 碎片柱状图(动态生长, 按 day)
    bx, by = W - 460, 150
    text("转述条数", f_small, (210, 210, 220), bx, by - 34, "topleft")
    # 柱子高度按 day 增长(D14 达到最终值)
    grow = min(1.0, day / 14)
    for i, (name, v, c) in enumerate(FRAGS):
        y = by + i * 90
        h = max(3, int(v / 170 * 64 * grow))
        pygame.draw.rect(screen, c, (bx, y, 26 + int(v * 0.55 * grow), 26))
        text(f"{name} {int(v*grow)}", f_small, c, bx + 180, y + 2, "topleft")
    # 左侧: 知情计数器 + 进度
    knows = KNOWS[day - 1]
    text(f"知情 {knows} / 25", f_big, (120, 200, 255), 60, 170, "topleft")
    pygame.draw.rect(screen, (60, 60, 70), (60, 260, 600, 14))
    pygame.draw.rect(screen, (120, 200, 255), (60, 260, int(knows / 25 * 600), 14))
    # 周老师证据(n14 起)
    if t >= TL["n14"]["start"]:
        a = min(1.0, (t - TL["n14"]["start"]) / 0.8)
        text("周老师 35 次发言 · 0 次提颜色", f_title, (int(255*a), int(120*a), int(120*a)), 60, 330, "topleft")
    # 精灵阵
    for i, n in enumerate(names25):
        cx = 60 + (i % 8) * 74
        cy = 400 + (i // 8) * 96
        screen.blit(sprites[n], (cx, cy))

def frame_reveal(t):
    draw_common()
    # 灰蓝调
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((12, 16, 34, 120))
    screen.blit(ov, (0, 0))
    text("另一座镇子 · 35 天 · 零注入", f_title, (160, 190, 255), 40, 30, "topleft")
    day = day_of(t, 35, "n23", "n38")
    text(f"第 {day} / 35 天", f_sub, (170, 180, 200), 40, 74, "topleft")
    # 底部进度条(填补下半屏空旷)
    pygame.draw.rect(screen, (50, 56, 76), (70, H - 120, 720, 12))
    pygame.draw.rect(screen, (120, 170, 255), (70, H - 120, int(day / 35 * 720), 12))
    text(f"day {day} / 35", f_small, (150, 165, 200), 70, H - 96, "topleft")
    # 双曲线对照(左大图)
    gx, gy, gw, gh = 70, 140, 720, 280
    pygame.draw.rect(screen, (38, 42, 58), (gx, gy, gw, gh))
    text("累计触达人数", f_small, (210, 210, 220), gx, gy - 30, "topleft")
    # v2 红线
    pts2 = []
    for d in range(1, 15):
        x = gx + int((d - 1) / 34 * gw)
        y = gy + gh - int(KNOWS[d - 1] / 27 * (gh - 20))
        pts2.append((x, y))
    if len(pts2) > 1:
        pygame.draw.lines(screen, (230, 120, 120), False, pts2, 3)
    # v3 蓝线(按 day 只画到当天)
    upto = min(day, 35)
    pts3 = []
    for d in range(1, upto + 1):
        x = gx + int((d - 1) / 34 * gw)
        y = gy + gh - int(V3_CUM[d - 1] / 27 * (gh - 20))
        pts3.append((x, y))
    if len(pts3) > 1:
        pygame.draw.lines(screen, (120, 170, 255), False, pts3, 3)
    # 图例
    text("红 = v2 有锚点 → 25/25", f_small, (230, 120, 120), gx, gy + gh + 16, "topleft")
    text("蓝 = v3 零注入 → 4/25", f_small, (120, 170, 255), gx + 240, gy + gh + 16, "topleft")
    # 右侧: 4 人
    text("传闻触达", f_small, (200, 200, 210), gx + gw + 40, gy + 60, "topleft")
    for i, p in enumerate(RUMOR4):
        c = (255, 200, 120) if day >= i * 2 + 1 else (90, 90, 100)
        text(p, f_small, c, gx + gw + 40, gy + 96 + i * 32, "topleft")
    # 收尾大数字(n23/n24 起)
    if t >= TL["n24"]["start"]:
        text("167 次提及", f_big, (255, 200, 120), gx + gw + 36, gy + 240, "topleft")
        text("4 人知晓", f_big, (120, 170, 255), gx + gw + 36, gy + 310, "topleft")
    # 结尾问句: 补足画面 — 双曲线保留 + 全宽对照大字
    if t >= TL["n34"]["start"]:
        a = min(1.0, (t - TL["n34"]["start"]) / 1.2)
        c1 = (int(255*a), int(220*a), int(140*a))
        text("有故事  25/25", f_big, c1, W/2 - 180, H - 190)
        text("没故事  4/25", f_big, (int(120*a), int(170*a), int(255*a)), W/2 + 180, H - 190)
    if t >= TL["n38"]["start"]:
        text("会自己长出内容吗？", f_title, (255, 255, 255), W/2, H - 70)

# ---------- 渲染 ----------
out = "/home/ubuntu/atria_repo/renders/atria_v6.mp4"
import subprocess
ffmpeg_cmd = ("ffmpeg -y -v error -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {fps} -i - "
              "-i {narr} -c:v libx264 -pix_fmt yuv420p -crf 23 -c:a aac -b:a 128k "
              "-shortest {out}").format(W=W, H=H, fps=FPS,
              narr=f"{NARR_DIR}/narration_track_v6.mp3", out=out)
pipe = subprocess.Popen(ffmpeg_cmd.split(), stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

t = 0.0
while t < TOTAL:
    for ev in pygame.event.get():
        pass
    act = act_of(t)
    if act == "hook":
        frame_hook(t)
    elif act == "setup":
        frame_setup(t)
    elif act == "prog":
        frame_prog(t)
    else:
        frame_reveal(t)
    pipe.stdin.write(pygame.image.tostring(screen, "RGB"))
    t += 1.0 / FPS

pipe.stdin.close()
pipe.wait()
print("v6 渲染完成:", out, os.path.getsize(out) // 1024, "KB")

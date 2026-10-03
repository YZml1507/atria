#!/usr/bin/env python3.12
"""Atria 视频渲染 v5 — v2 画面 + 新时间轴 + v3 尾段对照画面

结构:
  Part A (0-84.7s): 与 v4 相同的 v2 画面(精灵+地图+知情计数器+碎片柱状图), 挂新旁白时间轴
  Part B (84.7-112.2s): v3 尾段
    - 灰蓝色调(零注入氛围)
    - 远客传闻逐日触达曲线(1→4 人平台) + v2 的 25 人 S 曲线对照
    - 吕婶/许货郎/朱寡妇/钱老板 4 人高亮
    - 收尾大字: 有锚点 25/25  零注入 4/25
"""
import os, sys, json, glob
import pygame

HERE = "/home/ubuntu/atria_repo"
RUN = "/home/ubuntu/atria_rerun"
RUN3 = "/home/ubuntu/atria_v3/run_v3"
NARR_DIR = "/home/ubuntu/atria_repo/narration_v5"
W, H = 1280, 720
FPS = 30

pygame.init()
pygame.display.set_mode((W, H), pygame.HIDDEN)
screen = pygame.Surface((W, H))

# ---------- 字体(直加载 ttc, 禁 SysFont) ----------
def font(sz, bold=False):
    return pygame.font.Font("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", sz)

f_title = font(30, True)
f_sub = font(22)
f_small = font(18)

# ---------- 旁白时间轴 ----------
TL = json.load(open(f"{NARR_DIR}/timeline.json"))
TL = TL["timeline"]
TOTAL = 112.2

# ---------- 事件流 ----------
def load_events(run, ndays):
    evs = []
    for d in range(1, ndays+1):
        p = f"{run}/day{d:02d}.jsonl"
        if os.path.exists(p):
            for l in open(p, encoding="utf-8"):
                try: evs.append(json.loads(l))
                except Exception: pass
    return evs

evs2 = load_events(RUN, 14)

# v2 知情曲线 + v3 远客触达曲线
KNOWS = [11, 16, 17, 19, 22, 22, 23, 24, 25, 25, 25, 25, 25, 25]
FRAGS = [("扳指碎片", 164, (90, 200, 90)), ("方向碎片", 30, (230, 180, 60)),
         ("颜色碎片", 0, (150, 150, 150))]
V3_CUM = [1, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
          4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4]
RUMOR_PEOPLE = ["吕婶", "钱老板", "许货郎", "朱寡妇"]

# ---------- 精灵 ----------
def load_sprites():
    sp = {}
    pdir = f"{HERE}/sprites"
    for f in glob.glob(f"{pdir}/*.png"):
        n = os.path.basename(f).replace(".png", "")
        try: sp[n] = pygame.transform.scale(pygame.image.load(f), (48, 64))
        except Exception: pass
    return sp

sprites = load_sprites()

def text(s, f, color, x, y, anchor="midtop"):
    surf = f.render(s, True, color)
    r = surf.get_rect()
    setattr(r, anchor, (x, y))
    screen.blit(surf, r)

def draw_bg(day_bg=False):
    screen.fill((24, 22, 34))

# ---------- Part A: v2 画面 ----------
def frame_a(t):
    draw_bg()
    # 按 t 落到 v2 天数(0-84.7s 映射 1-14 天)
    day = min(14, max(1, int(t / (84.72 / 14)) + 1))
    text("安镇 · v2 有锚点", f_title, (255, 220, 140), 40, 30, "topleft")
    text(f"第 {day} / 14 天", f_sub, (200, 200, 210), 40, 72, "topleft")
    # 知情计数器
    knows = KNOWS[day-1]
    text(f"知情人数  {knows} / 25", f_title, (120, 200, 255), W/2, H-90)
    # 进度条
    pw = int((day / 14) * (W - 80))
    pygame.draw.rect(screen, (60, 60, 70), (40, H-40, W-80, 12))
    pygame.draw.rect(screen, (120, 200, 255), (40, H-40, pw, 12))
    # 碎片柱状图(右侧)
    bx, by, bw = W - 420, 130, 90
    text("三碎片传播(条)", f_small, (210, 210, 220), bx, by - 30, "topleft")
    for i, (name, v, c) in enumerate(FRAGS):
        y = by + i * 74
        h = max(2, int(v / 170 * 60))
        pygame.draw.rect(screen, c, (bx, y, bw, 20))
        pygame.draw.rect(screen, c, (bx, y+20, bw, 8))  # 底座
        text(f"{name} {v}", f_small, c, bx + bw + 14, y, "midleft")
    # 精灵排布(图标阵)
    names = sorted(sprites.keys())[:25]
    for i, n in enumerate(names):
        cx = 60 + (i % 8) * 90
        cy = 130 + (i // 8) * 110
        sp = sprites[n]
        screen.blit(sp, (cx, cy))
        text(n[:2], f_small, (160, 160, 170), cx + 24, cy + 66)
    # 安镇高亮(中央)
    text("安镇", f_small, (255, 220, 140), 60 + 24, 130 + 66 + 22)

# ---------- Part B: v3 尾段画面 ----------
def frame_b(t, frame):
    draw_bg()
    # 灰蓝调 overlay
    ov = pygame.Surface((W, H), pygame.SRCALPHA)
    ov.fill((10, 14, 30, 90))
    screen.blit(ov, (0, 0))
    text("v3 零注入 · 35 天", f_title, (160, 190, 255), 40, 30, "topleft")
    # 在尾段内落到 v3 天数
    local = t - 84.72
    day = min(35, int(local / (27.5 / 35)) + 1)
    text(f"第 {day} / 35 天", f_sub, (170, 180, 200), 40, 72, "topleft")
    # 远客触达曲线(左大图)
    gx, gy, gw, gh = 80, 150, 700, 260
    pygame.draw.rect(screen, (40, 44, 60), (gx, gy, gw, gh))
    text("远客传闻 · 累计触达人数", f_small, (210, 210, 220), gx, gy - 30, "topleft")
    # v3 曲线(蓝, 到4)
    pts = []
    for d in range(1, 36):
        x = gx + int((d-1) / 34 * gw)
        y = gy + gh - int(V3_CUM[d-1] / 27 * (gh - 20))
        pts.append((x, y))
    if len(pts) > 1:
        pygame.draw.lines(screen, (120, 170, 255), False, pts, 3)
    # v2 曲线(红, 到25, 虚拟对照)
    pts2 = []
    for d in range(1, 15):
        x = gx + int((d-1) / 34 * gw)
        y = gy + gh - int(KNOWS[d-1] / 27 * (gh - 20))
        pts2.append((x, y))
    if len(pts2) > 1:
        pygame.draw.lines(screen, (230, 120, 120), False, pts2, 3)
    text(f"触达 {V3_CUM[min(day,35)-1]} / 25 人", f_title, (120, 170, 255), gx + gw + 30, gy + 100, "topleft")
    # 右侧 4 人
    text("传闻触达:", f_small, (200, 200, 210), gx + gw + 30, gy + 150, "topleft")
    for i, p in enumerate(RUMOR_PEOPLE):
        c = (255, 200, 120) if day >= 1 + i else (90, 90, 100)
        text(p, f_small, c, gx + gw + 30, gy + 180 + i * 30, "topleft")
    text("红色 = v2 有锚点(S 型到 25 人)", f_small, (230, 120, 120), gx, gy + gh + 18, "topleft")
    # 收尾大字
    if t > 104.81:
        a = min(1.0, (t - 104.81) / 1.5)
        text("有锚点 25/25    零注入 4/25", f_title, (int(255*a), int(220*a), int(140*a)), W/2, H - 70)

# ---------- 主渲染 ----------
out = "/home/ubuntu/atria_repo/renders/atria_v5.mp4"
pipe = None
import subprocess
ffmpeg_cmd = ("ffmpeg -y -v error -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {fps} -i - "
             "-i {narr} -c:v libx264 -pix_fmt yuv420p -crf 23 -c:a aac -b:a 128k "
             "-shortest {out}").format(W=W, H=H, fps=FPS, narr=f"{NARR_DIR}/narration_track_v5.mp3", out=out)
pipe = subprocess.Popen(ffmpeg_cmd.split(), stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

clock = pygame.time.Clock()
t = 0.0
frame = 0
while t < TOTAL:
    for ev in pygame.event.get():
        pass
    if t < 84.72:
        frame_a(t)
    else:
        frame_b(t, frame)
    # 事件流字幕(尾段前)
    if t < 84.72:
        ei = min(len(evs2) - 1, int(t / TOTAL * len(evs2)))
        e = evs2[ei] if evs2 else None
        if e:
            say = (e.get("say") or e.get("text") or "")[:34]
            who = e.get("agent") or ""
            if say:
                text(f"{who}: {say}", f_small, (190, 190, 200), 40, H - 70, "topleft")
    pipe.stdin.write(pygame.image.tostring(screen, "RGB"))
    t += 1.0 / FPS
    frame += 1

pipe.stdin.close()
pipe.wait()
print("v5 渲染完成:", out, os.path.getsize(out)//1024, "KB")

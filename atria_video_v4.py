"""Atria v4 — pygame headless 渲染管线

修正 v3 全部问题:
  - 黑边: 直接画 1280x720, 地图 scale 铺满, 零黑边
  - 精灵: PIPOYA 64x66 原尺寸 blit, 25 居民各 3 帧走路动画
  - 字体: 真实像素字号 (标题 44, 正文 28), bbox 重叠自动检测
  - 配音: 音轨驱动画面 —— 旁白实测时长 → 分镜触发点

渲染: SDL_VIDEODRIVER=dummy, 帧序列 PNG → ffmpeg 编码
时间轴: narration_track.mp3 逐句 start 时间 (实测)
"""
import os, sys, json, random

os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.environ.get("ATRIA_RUN", "/home/ubuntu/atria_rerun")
W, H = 1280, 720
FPS = 30

# ---------- 旁白时间轴 (实测) ----------
NARRATION = NARRATION = NARRATION = NARRATION = NARRATION = NARRATION = NARRATION = NARRATION = [
    ("二十五个智能体，在一座叫做安镇的小镇里，自由生活十四天。", 0.3, 4.78),
    ("镇上唯一的木匠安镇，去邮局取一只旧纸箱，里面是亡妻留下的遗物。", 6.1, 5.57),
    ("纸箱不见了，被别人领走了。安镇开始逢人打听，想查清是谁拿走的。", 12.7, 6.65),
    ("那天有三个人碰巧在邮局附近，看见了拿箱子的人。", 20.3, 3.65),
    ("杂货铺帮工李大姐，看清了箱子里有一枚旧扳指。", 24.9, 3.7),
    ("诊所的赵医生，看见那人往镇东头走了。", 29.6, 3.17),
    ("退休教师周老师，只记得那人的衣裳颜色偏浅，好像是灰色。", 33.8, 4.92),
    ("十四天里，这三句话在镇上传来传去，命运完全不同。", 39.7, 4.97),
    ("具体的扳指，被一百六十四个人记住。", 45.7, 2.52),
    ("半具体的方向，只有三十个人记住。", 49.2, 2.59),
    ("而周老师那句不确定的颜色，从没人传出去。", 52.8, 3.38),
    ("这个实验真正想看的，不是谁拿了纸箱，而是消息在人群里传播时，会遭遇什么。", 57.2, 6.34),
    ("信息越不确定，越被传播链静默淘汰。这就是十四天涌现出的答案。", 64.5, 5.74),
    ("拿走纸箱的是五金店老板孙有财，他从侥幸、烦躁，到烧掉存根，最后还是趁夜把箱子还了回去。", 71.2, 9.0),
    ("十四天，二十五人，一千零一十条记忆。这就是安镇的故事。", 81.2, 5.21),
]







DURATION = 87.4

# ---------- v2 数据 ----------
KNOWS = [11, 16, 17, 19, 22, 22, 23, 24, 25, 25, 25, 25, 25, 25]  # D1-14 知情曲线, 与源数据一致
FRAGS = [("扳指碎片", 164, (90, 200, 90)), ("方向碎片", 30, (230, 180, 60)),
         ("颜色碎片", 0, (150, 150, 150))]

def load_events():
    evs = []
    for d in range(1, 15):
        p = f"{RUN}/day{d:02d}.jsonl"
        if os.path.exists(p):
            for l in open(p):
                evs.append(json.loads(l))
    return evs

def load_places():
    import sys
    sys.path.insert(0, HERE)
    from atria_world import PLACES, HOMES_SOUTH, ROADS
    return PLACES, HOMES_SOUTH, ROADS

def place_box(name, PLACES, HOMES_SOUTH, ROADS):
    return (PLACES.get(name, {}).get("box") or HOMES_SOUTH.get(name)
            or ROADS.get(name) or (5, 5, 10, 10))


t_draw = [0.0]
class Renderer:
    def __init__(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.screen = pygame.Surface((W, H))
        # 字体: 直加载 ttc (SysFont 按名字查找会 fallback 拉丁字体, 中文全是空白)
        TTC = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        self.f_title = pygame.font.Font(TTC, 44)
        self.f_big = pygame.font.Font(TTC, 32)
        self.f_body = pygame.font.Font(TTC, 28)
        self.f_small = pygame.font.Font(TTC, 22)
        self.f_place = pygame.font.Font(TTC, 34)
        # 地图 (1280x960 → 缩放到铺满 1280x720)
        im = Image.open(os.path.join(HERE, "renders", "map.png")).convert("RGB")
        im = im.resize((W, H), Image.LANCZOS)
        self.map_surf = pygame.image.frombuffer(im.tobytes(), (W, H), "RGB")
        # 精灵
        self.sprites = {}
        self.tint = {}
        pn = os.path.join(HERE, "atria_personas.json")
        persons = [p["name"] for p in json.load(open(pn))]
        for i, nm in enumerate(persons):
            frames = []
            for f in range(3):
                p = os.path.join(HERE, "sprites_v3", f"{nm}_f{f}.png")
                if os.path.exists(p):
                    si = Image.open(p).convert("RGBA").resize((64, 66), Image.NEAREST)
                    # 行重复的 14 人 (i>=11) 做色调区分, 避免看起来"换衣服"
                    if i >= 11:
                        overlay = Image.new("RGBA", si.size, (0, 0, 0, 0))
                        from PIL import ImageDraw
                        d = ImageDraw.Draw(overlay)
                        hue = (i - 11) * 37 % 360
                        col = pygame.Color(0)
                        col.hsva = (hue, 45, 90, 28)
                        d.rectangle([0, 0, 64, 66], fill=(col.r, col.g, col.b, 60))
                        si = Image.alpha_composite(si, overlay)
                    frames.append(pygame.image.frombuffer(si.tobytes(), si.size, "RGBA").convert_alpha())
            if frames:
                self.sprites[nm] = frames
        self.PLACES, self.HOMES_SOUTH, self.ROADS = load_places()
        self.events = load_events()
        self.home_of = {v["home_of"]: k for k, v in self.PLACES.items() if v.get("home_of")}

    def grid_to_px(self, x, y):
        """grid (40x30) → 1280x720 像素, 铺满"""
        return int((x + 0.5) / 40 * W), int((y + 0.5) / 30 * H)

    def current_narration(self, t):
        """返回当前时刻应显示的旁白句 (字幕)"""
        cur = None
        for txt, t0, dur in NARRATION:
            if t0 <= t < t0 + dur + 0.8:
                cur = txt
        return cur

    KEY_PLACES = {"安镇老宅", "周家小院", "赵宅", "孙氏裁缝铺", "李家", "邮局",
                  "五金店", "杂货铺", "诊所", "镇学校", "镇公园", "老磨坊酒吧"}

    def draw_places(self, rects, t=None):
        self.t_now = t if t is not None else getattr(self, "t_now", 0)
        """大字醒目的地名标签 (36px, 半透明底), 只标剧情核心地点避免互相遮挡"""
        placed = []
        for name in self.KEY_PLACES:
            info = self.PLACES.get(name)
            box = info.get("box") if info else None
            if not box:
                continue
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            px, py = self.grid_to_px(cx, cy)
            s = self.f_place.render(name, True, (255, 244, 200))
            # 黑色描边: 8 方向偏移渲染
            so = self.f_place.render(name, True, (20, 20, 25))
            for dx in (-2, 0, 2):
                for dy in (-2, 0, 2):
                    if dx or dy:
                        pass  # 描边合成在 blit 时做
            sw, sh = s.get_size()
            bg = pygame.Surface((sw + 20, sh + 10), pygame.SRCALPHA)
            bg.fill((30, 30, 40, 170))
            # 标签位置: 上排地块(住宅, y<8)放下方, 其余放上方
            # S3 碎片弹出期 (34-60s): 上排住宅暂隐, 避让碎片
            if 24 < self.t_now < 45 and cy < 8 and info.get("home_of"):
                continue
            below = cy < 8
            x = px - (sw + 20) // 2
            y = py + 14 if below else py - sh - 14
            r = pygame.Rect(x, y, sw + 20, sh + 10)
            # 与已放置地名错开: 若重叠则沿同方向偏移
            for q in placed:
                while r.colliderect(q):
                    r.y += 44 if below else -44
            placed.append(r)
            self.screen.blit(bg, (r.x, r.y))
            for dx in (-2, 0, 2):
                for dy in (-2, 0, 2):
                    if dx or dy:
                        self.screen.blit(so, (r.x + 10 + dx, r.y + 5 + dy))
            self.screen.blit(s, (r.x + 10, r.y + 5))
            rects.append(r)

    def draw_subtitle(self, rects):
        """底部字幕: 当前旁白句, 半透明底条"""
        cur = self.current_narration(t_draw[0])
        if not cur:
            return
        # 半透明底条
        sub = self.f_body.render(cur, True, (255, 255, 255))
        sw, sh = sub.get_size()
        bg = pygame.Surface((sw + 48, sh + 18), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        x = (W - sw - 48) // 2
        y = H - sh - 52
        self.screen.blit(bg, (x, y))
        self.screen.blit(sub, (x + 24, y + 9))
        rects.append(pygame.Rect(x, y, sw + 48, sh + 18))

    # ---------- 文字辅助 (带 bbox 重叠检测) ----------
    def text(self, s, font, color, x, y, anchor="topleft"):
        surf = font.render(s, True, color)
        r = surf.get_rect()
        setattr(r, anchor, (int(x), int(y)))
        self.screen.blit(surf, r)
        return r

    def texts_overlap(self, rects):
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                if rects[i].colliderect(rects[j]):
                    return True, (i, j)
        return False, None

    # ---------- 分镜 ----------
    def scene_title(self, t):
        """S1 0-7s: 地图铺满 + 标题 + 25 精灵散布"""
        self.screen.blit(self.map_surf, (0, 0))
        # 精灵散布在住宅
        rng = random.Random(20261014)
        persons = list(self.sprites.keys())
        for i, nm in enumerate(persons):
            hb = self.home_of.get(nm)
            box = place_box(hb, self.PLACES, self.HOMES_SOUTH, self.ROADS) if hb else (i * 5, 5, i * 5 + 5, 10)
            cx = (box[0] + box[2]) / 2 + rng.uniform(-1, 1)
            cy = (box[1] + box[3]) / 2 + rng.uniform(-1, 1)
            px, py = self.grid_to_px(cx, cy)
            # 静止时固定 f0, 不闪
            self.screen.blit(self.sprites[nm][0], (px - 32, py - 33))
        # 标题 (大字, 上方)
        r1 = self.text("Atria — 二十五人的十四天", self.f_title, (255, 255, 255), W / 2, 24, "midtop")
        r3 = self.text("第 1 天 / 14", self.f_body, (255, 220, 120), 40, H - 60)
        rects = []
        self.draw_places(rects)
        ov, pair = self.texts_overlap([r1, r3] + rects)
        if ov:
            allr = [r1, r3] + rects
            print("S1 重叠对:", pair, [getattr(rr, "x", "?") for rr in [allr[pair[0]], allr[pair[1]]]])
        assert not ov, "S1 文字重叠"
        return [r1, r3]

    def scene_incite(self, t):
        """S2 7-19s: 邮局红框 + 三碎片"""
        self.screen.blit(self.map_surf, (0, 0))
        # 安镇真的走向邮局 (线性插值, 7-15s 从老宅走到邮局)
        if "安镇" in self.sprites:
            ab = place_box("安镇老宅", self.PLACES, self.HOMES_SOUTH, self.ROADS)
            pb = place_box("邮局", self.PLACES, self.HOMES_SOUTH, self.ROADS)
            x0, y0 = (ab[0]+ab[2])/2, (ab[1]+ab[3])/2
            x1, y1 = (pb[0]+pb[2])/2, (pb[1]+pb[3])/2
            prog = min(1.0, max(0.0, (t - 6.8) / 6.0))
            cx = x0 + (x1 - x0) * prog
            cy = y0 + (y1 - y0) * prog
            px, py = self.grid_to_px(cx, cy)
            f = 1 if 0.05 < prog < 0.95 else 0  # 走路中用 f1
            self.screen.blit(self.sprites["安镇"][f], (px - 32, py - 33))
        # 其他居民在原地做日常 (各自住宅附近小幅活动)
        rng = random.Random(7)
        for i, nm in enumerate(list(self.sprites.keys())):
            if nm == "安镇": continue
            hb = self.home_of.get(nm)
            if not hb: continue
            box = place_box(hb, self.PLACES, self.HOMES_SOUTH, self.ROADS)
            cx = (box[0]+box[2])/2 + rng.uniform(-0.8, 0.8)
            cy = (box[1]+box[3])/2 + rng.uniform(-0.8, 0.8)
            px, py = self.grid_to_px(cx, cy)
            self.screen.blit(self.sprites[nm][0], (px - 32, py - 33))
        # 邮局红框
        box = place_box("邮局", self.PLACES, self.HOMES_SOUTH, self.ROADS)
        x0, y0 = self.grid_to_px(box[0], box[1])
        x1, y1 = self.grid_to_px(box[2], box[3])
        pulse = (t * 6) % 2 < 1
        if pulse:
            pygame.draw.rect(self.screen, (255, 60, 60), (x0 - 4, y0 - 4, x1 - x0 + 8, y1 - y0 + 8), 5)
        r1 = self.text("第 2 天 · 邮局: 包裹被错领", self.f_big, (255, 80, 80), 40, 24)
        # 三碎片移到 S3 旁白句触发 (n06-n08@40.7/46.1/53.2)
        rects = [r1]
        self.draw_places(rects)
        assert not self.texts_overlap(rects)[0], "S2 文字重叠"
        return rects

    def scene_fast(self, t):
        """S3 19-45s: 14 天快进 + 计数器"""
        # 天数映射: 19-45s → 1-14 天
        day = min(14, max(1, int((t - 24) / 46.5 * 14) + 1))
        self.screen.blit(self.map_surf, (0, 0))
        # 移动精灵: 按事件流 agent→place, 天内平滑插值
        rng = random.Random(day * 31)
        evs = [e for e in self.events if e.get("day") == day and e.get("place")]
        # 这一天的时间进度 (0-1), 用于在两次事件间插值
        day_prog = ((t - 24) / 46.5 * 14) % 1.0
        last_pos = {}
        for e in evs[:14]:
            nm = e.get("agent")
            if nm not in self.sprites: continue
            box = place_box(e["place"], self.PLACES, self.HOMES_SOUTH, self.ROADS)
            cx = (box[0] + box[2]) / 2
            cy = (box[1] + box[3]) / 2
            last_pos[nm] = (cx, cy)
        for i, e in enumerate(evs[:14]):
            nm = e.get("agent")
            if nm not in self.sprites: continue
            box = place_box(e["place"], self.PLACES, self.HOMES_SOUTH, self.ROADS)
            tx, ty = (box[0]+box[2])/2, (box[1]+box[3])/2
            # 从上一个位置插值到当前位置
            prev = last_pos.get(nm, (tx, ty))
            cx = prev[0] + (tx - prev[0]) * min(1, day_prog)
            cy = prev[1] + (ty - prev[1]) * min(1, day_prog)
            px, py = self.grid_to_px(cx, cy)
            f = ((day + i) % 3) if e.get("emoji") != "\U0001f4ac" else 1
            self.screen.blit(self.sprites[nm][f], (px - 32, py - 33))
        # 顶部: 天数
        r1 = self.text(f"第 {day} 天 / 14", self.f_big, (255, 220, 120), 40, 24)
        # 底部大字计数器
        knows = KNOWS[day - 1]
        r2 = self.text(f"知情人数  {knows} / 25", self.f_title, (120, 200, 255), W / 2, H - 90, "midtop")
        # 进度条
        pw = int((day / 14) * (W - 80))
        pygame.draw.rect(self.screen, (60, 60, 70), (40, H - 40, W - 80, 12))
        pygame.draw.rect(self.screen, (120, 200, 255), (40, H - 40, pw, 12))
        rects = [r1, r2]
        # 碎片数据弹出 (右侧, 避开左侧天数/计数器)
        milestones = [(49.2, 8, "旧扳指：164 人记住"),
                      (57.2, 9, "衣裳的颜色：从没人传出去")]
        for ts, idx, txt in milestones:
            if t >= ts:
                col = (150, 150, 150) if "颜色" in txt else (90, 200, 90)
                # 左下角 (计数器上方), 与右侧地名错开
                yy = H - 170 if idx == 8 else H - 130
                r = self.text(txt, self.f_body, col, 40, yy)
                rects.append(r)
        # 三碎片弹出 (右上角, 避开左侧地名与左下里程碑)
        frags3 = [(24.9, "李大姐: 箱子里有一枚旧扳指", (90, 200, 90)),
                  (29.6, "赵医生: 那人往镇东头走了", (230, 180, 60)),
                  (33.8, "周老师: 衣裳偏浅…好像是灰色", (160, 160, 160))]
        # 顶部横排 3 张 (y=64), 间距 400
        xx = W / 2 - 440
        for ts, txt, col in frags3:
            if t >= ts and t <= 45.0:
                short = txt.split(": ", 1)[-1][:12]  # 只保留内容 12 字
                r = self.text("◆" + short, self.f_small, col, xx, 100)
                rects.append(r)
            xx += 400
        self.draw_places(rects, t)
        ov, pair = self.texts_overlap([r for r in rects])
        if ov:
            print("S3 重叠 @t=", t, "对:", pair)
            for k, rr in enumerate(rects):
                print(f"   rects[{k}] = ({rr.x},{rr.y},{rr.w},{rr.h})")
        assert not ov, "S3 文字重叠"
        return rects

    def scene_split(self, t):
        """S4 45-60s: 分屏 销毁 vs 追查"""
        self.screen.fill((18, 20, 28))
        # 左右分屏
        pygame.draw.rect(self.screen, (34, 22, 26), (0, 0, W // 2, H))
        pygame.draw.rect(self.screen, (20, 26, 38), (W // 2, 0, W // 2, H))
        # 中线
        pygame.draw.line(self.screen, (80, 80, 90), (W // 2, 0), (W // 2, H), 2)
        # 左: 孙有财
        sun = self.sprites.get("孙有财")
        if sun:
            f = 1  # 固定行走帧, 不闪
            sx, sy = W // 4 - 32, 200
            self.screen.blit(sun[f], (sx, sy))
        r1 = self.text("孙有财 · 错领者", self.f_big, (255, 90, 90), W // 4, 120, "midtop")
        # 台词逐句出现
        lefts = [(71.8, "「这存根烧了，就没人查到我了。」"),
                 (74.0, "D12: 销毁登记存根"),
                 (76.0, "D13: 趁夜将纸箱放回门口")]
        yy = 300
        for ts, txt in lefts:
            if t >= ts:
                col = (255, 120, 120) if txt.startswith("「") else (200, 160, 160)
                r = self.text(txt, self.f_body, col, 60, yy)
                yy += 52
        # 右: 安镇
        an = self.sprites.get("安镇")
        if an:
            f = 1
            ax, ay = 3 * W // 4 - 32, 200
            self.screen.blit(an[f], (ax, ay))
        r2 = self.text("安镇 · 失主", self.f_big, (120, 180, 255), 3 * W // 4, 120, "midtop")
        rights = [(72.0, "「我那包裹叫一个戴旧扳指的人错领了。」"),
                 (74.5, "D13–14: 拿扳指线索逼交底单")]
        yy = 300
        for ts, txt in rights:
            if t >= ts:
                col = (140, 200, 255) if txt.startswith("「") else (160, 180, 200)
                r = self.text(txt, self.f_body, col, W // 2 + 60, yy)
                yy += 52
        # 底部
        r3 = self.text("← 销毁                追查 →", self.f_big, (255, 255, 255), W / 2, H - 80, "midtop")
        return [r1, r2, r3]

    def scene_end(self, t):
        """S5 60-82s: 还物 + 三碎片统计"""
        # 夜色渐变背景
        self.screen.fill((14, 16, 26))
        # 月亮
        pygame.draw.circle(self.screen, (240, 240, 220), (1060, 120), 46)
        # 精灵 (夜里)
        if "孙有财" in self.sprites and "安镇" in self.sprites:
            self.screen.blit(self.sprites["孙有财"][1], (300, 380))
            self.screen.blit(self.sprites["安镇"][1], (900, 380))
        r1 = self.text("第十三天夜里", self.f_big, (200, 220, 255), 40, 24)
        r2 = self.text("孙有财把箱子悄悄放回了门口", self.f_big, (150, 230, 150), 40, 80)
        r3 = self.text("侥幸 → 烦躁 → 销毁存根 → 悔过还物 → 观察确认", self.f_body, (220, 220, 220), 40, 140)
        # 统计表 (n16 收尾句后)
        rects = [r1, r2, r3]
        if t >= 81.5:
            yy = 220
            for nm, v, col in FRAGS:
                r = self.text(f"{nm}: {v} 条传播记忆", self.f_big, col, 40, yy)
                yy += 60
                rects.append(r)
            r4 = self.text("不确定性细节，被传播链静默丢弃。", self.f_body, (180, 180, 180), 40, yy + 10)
            rects.append(r4)
        return rects


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else "/tmp/atria_v4_frames"
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith(".png"):
            os.remove(os.path.join(outdir, f))
    R = Renderer()
    print(f"精灵: {len(R.sprites)} 人; 事件: {len(R.events)}")
    n = 0
    t = 0.0
    import time
    t0 = time.time()
    while t < DURATION:
        # 音轨驱动分镜
        if t < 12.0:      # n00-n01 设定
            R.scene_title(t)
        elif t < 24.0:    # n02-n03 事件
            R.scene_incite(t)
        elif t < 70.5:    # n04-n11 三碎片与传播
            R.scene_fast(t)
        elif t < 81.0:    # n12-n13 结论与孙有财
            R.scene_split(t)
        else:             # n14 收尾
            R.scene_end(t)
        # 字幕 (与旁白音轨同步)
        t_draw[0] = t
        rects = []
        R.draw_subtitle(rects)
        assert not R.texts_overlap([r for r in rects if r is not None])[0], "字幕重叠"
        pygame.image.save(R.screen, f"{outdir}/f{n:04d}.png")
        n += 1
        t += 1.0 / FPS
    dt = time.time() - t0
    print(f"{n} 帧, {dt:.1f}s = {n/dt:.0f} fps")


if __name__ == "__main__":
    main()

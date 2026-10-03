#!/usr/bin/env python3.12
"""Atria 视频 v7 渲染 — v6 的四幕叙事 + v4 的像素小镇画面

修复 v6 全部实测问题:
  - 音轨结尾被 -shortest 截断 → 视频帧数 = 音轨实际时长 + 0.4s 淡出, 不用 -shortest
  - 画面提示抢跑旁白 2~6 句 → 全部提示点按重排后的 n00..n38 键位校准
  - 全程零小镇画面 → setup/prog 两幕在像素地图上演(邮局红框+精灵走位+气泡)
  - 结尾大字互相叠穿 → 全部文案块做矩形避让
  - 无字幕 → 底部旁白字幕条回归(v4 同款)

用法: python3 atria_video_v7.py
依赖: pygame, Pillow, ffmpeg, 文泉驿正黑; 素材全在仓库内
"""
import os, sys, json, random
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RUN2 = os.environ.get("ATRIA_RUN2", os.path.join(HERE, "run_v2"))
NARR_DIR = os.environ.get("ATRIA_NARR", os.path.join(HERE, "narration_v6"))
OUT = os.environ.get("ATRIA_OUT", os.path.join(HERE, "renders", "atria_v7.mp4"))
W, H = 1280, 720
FPS = 30

# ---------- 旁白文本 + 时间轴 ----------
sys.path.insert(0, HERE)
from atria_narration_v6_text import NARRATION_V6
TEXTS = {n: t for n, t in NARRATION_V6}
TL = json.load(open(os.path.join(NARR_DIR, "timeline.json")))["timeline"]
TRACK = os.path.join(NARR_DIR, "narration_track_v6.mp3")
ORDER = [f"n{i:02d}" for i in range(39)]

def T(n):  # 句子的开始时刻
    return TL[n]["start"]

def Tend(n):
    return TL[n]["start"] + TL[n]["dur"]

# ---------- 数据(回源核验过的常量, 见 atria_verify.py / REPORT_v3) ----------
KNOWS = [11, 16, 17, 19, 22, 22, 23, 24, 25, 25, 25, 25, 25, 25]
FRAGS = [("扳指", 164, (90, 200, 90)), ("方向", 30, (230, 180, 60)), ("颜色", 0, (150, 150, 150))]
V3_CUM = [1, 3] + [4] * 33
RUMOR4 = ["吕婶", "钱老板", "许货郎", "朱寡妇"]


class Renderer:
    def __init__(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.screen = pygame.Surface((W, H))
        TTC = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        self.f_title = pygame.font.Font(TTC, 44)
        self.f_big = pygame.font.Font(TTC, 40)
        self.f_body = pygame.font.Font(TTC, 28)
        self.f_small = pygame.font.Font(TTC, 22)
        self.f_place = pygame.font.Font(TTC, 30)
        # 地图
        im = Image.open(os.path.join(HERE, "renders", "map.png")).convert("RGB")
        im = im.resize((W, H), Image.LANCZOS)
        self.map_surf = pygame.image.frombuffer(im.tobytes(), (W, H), "RGB")
        # 精灵 3 帧
        self.sprites = {}
        persons = [p["name"] for p in json.load(open(os.path.join(HERE, "atria_personas.json")))]
        for i, nm in enumerate(persons):
            frames = []
            for f in range(3):
                p = os.path.join(HERE, "sprites_v3", f"{nm}_f{f}.png")
                if os.path.exists(p):
                    si = Image.open(p).convert("RGBA").resize((52, 54), Image.NEAREST)
                    if i >= 11:
                        overlay = Image.new("RGBA", si.size, (0, 0, 0, 0))
                        from PIL import ImageDraw
                        hue = (i - 11) * 37 % 360
                        col = pygame.Color(0); col.hsva = (hue, 45, 90, 28)
                        ImageDraw.Draw(overlay).rectangle([0, 0, 52, 54], fill=(col.r, col.g, col.b, 60))
                        si = Image.alpha_composite(si, overlay)
                    frames.append(pygame.image.frombuffer(si.tobytes(), si.size, "RGBA").convert_alpha())
            if frames:
                self.sprites[nm] = frames
        # 世界几何
        from atria_world import PLACES, HOMES_SOUTH, ROADS
        self.PLACES, self.HOMES_SOUTH, self.ROADS = PLACES, HOMES_SOUTH, ROADS
        self.home_of = {v["home_of"]: k for k, v in PLACES.items() if v.get("home_of")}
        for nm, box in HOMES_SOUTH.items():
            owner = nm.replace("宅2", "宅").replace("宅", "")
            self.home_of.setdefault(owner, nm)
        # run_v2 事件(精灵走位依据)
        self.events = []
        for d in range(1, 15):
            p = os.path.join(RUN2, f"day{d:02d}.jsonl")
            if os.path.exists(p):
                for l in open(p):
                    self.events.append(json.loads(l))

    def grid_to_px(self, x, y):
        return int((x + 0.5) / 40 * W), int((y + 0.5) / 30 * H)

    def place_box(self, name):
        return (self.PLACES.get(name, {}).get("box") or self.HOMES_SOUTH.get(name)
                or self.ROADS.get(name) or (5, 5, 10, 10))

    def text(self, s, font, color, x, y, anchor="topleft"):
        surf = font.render(s, True, color)
        r = surf.get_rect()
        setattr(r, anchor, (int(x), int(y)))
        self.screen.blit(surf, r)
        return r

    def subtitle(self, t):
        """底部旁白字幕条; 末句让位给结尾大字"""
        if t >= T("n38"):
            return
        cur = None
        for n in ORDER:
            if T(n) <= t < Tend(n) + 0.15:
                cur = TEXTS[n]
        if not cur:
            return
        sub = self.f_body.render(cur, True, (255, 255, 255))
        sw, sh = sub.get_size()
        bg = pygame.Surface((sw + 48, sh + 18), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 165))
        x = (W - sw - 48) // 2
        y = H - sh - 40
        self.screen.blit(bg, (x, y))
        self.screen.blit(sub, (x + 24, y + 9))

    def sprite_at(self, name, px, py, frame=0):
        if name in self.sprites:
            self.screen.blit(self.sprites[name][frame % len(self.sprites[name])], (px - 26, py - 27))

    def label(self, s, x, y, color=(255, 244, 200)):
        """带描边底的地名标签"""
        s1 = self.f_place.render(s, True, color)
        so = self.f_place.render(s, True, (20, 20, 25))
        sw, sh = s1.get_size()
        bg = pygame.Surface((sw + 18, sh + 8), pygame.SRCALPHA)
        bg.fill((30, 30, 40, 175))
        r = pygame.Rect(x - (sw + 18) // 2, y, sw + 18, sh + 8)
        self.screen.blit(bg, r)
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                if dx or dy:
                    self.screen.blit(so, (r.x + 9 + dx, r.y + 4 + dy))
        self.screen.blit(s1, (r.x + 9, r.y + 4))
        return r

    # ---------- 幕 1: hook (0 ~ n05) ----------
    def act_hook(self, t):
        self.screen.fill((14, 15, 22))
        # 第二人称短句, 逐行淡入中央
        lines = [("n00", "如果把你丢进一座小镇"), ("n01", "十四天"),
                 ("n02", "你记不清每个人说了什么"), ("n03", "但你记得哪句是真的")]
        y = H / 2 - 110
        for n, s in lines:
            if t >= T(n):
                a = min(1.0, (t - T(n)) / 0.7)
                c = (int(235 * a),) * 3
                self.text(s, self.f_big, c, W / 2, y, "midtop")
            y += 76
        # n04 揭晓: 切入小镇全景(像素地图 + 25 精灵)
        if t >= T("n04"):
            a = min(1.0, (t - T("n04")) / 0.9)
            self.screen.blit(self.map_surf, (0, 0))
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((14, 15, 22, int(255 * (1 - a))))
            self.screen.blit(ov, (0, 0))
            rng = random.Random(20261014)
            for nm in self.sprites:
                box = self.place_box(self.home_of.get(nm, "镇公园"))
                cx = (box[0] + box[2]) / 2 + rng.uniform(-0.6, 0.6)
                cy = (box[1] + box[3]) / 2 + rng.uniform(-0.6, 0.6)
                px, py = self.grid_to_px(cx, cy)
                self.sprite_at(nm, px, py, 0)
            self.text("25 个居民 · 全是语言模型", self.f_title, (255, 255, 255), W / 2, 26, "midtop")

    # ---------- 幕 2: setup (n05 ~ n12) ----------
    def act_setup(self, t):
        self.screen.blit(self.map_surf, (0, 0))
        self.label("安镇 · 邮局事件 · 第 1 天", 240, 26)
        # 邮局红框脉冲 (n05 起)
        box = self.place_box("邮局")
        x0, y0 = self.grid_to_px(box[0], box[1]); x1, y1 = self.grid_to_px(box[2], box[3])
        if t >= T("n05") and (t * 5) % 2 < 1:
            pygame.draw.rect(self.screen, (255, 60, 60), (x0 - 5, y0 - 5, x1 - x0 + 10, y1 - y0 + 10), 5)
        # 安镇 sprite 走向邮局 (n05 期间)
        ab = self.place_box("安镇老宅"); pb = self.place_box("邮局")
        prog = min(1.0, max(0.0, (t - T("n05")) / max(1.0, T("n06") - T("n05"))))
        cx = (ab[0] + ab[2]) / 2 + ((pb[0] + pb[2]) / 2 - (ab[0] + ab[2]) / 2) * prog
        cy = (ab[1] + ab[3]) / 2 + ((pb[1] + pb[3]) / 2 - (ab[1] + ab[3]) / 2) * prog
        px, py = self.grid_to_px(cx, cy)
        self.sprite_at("安镇", px, py, 1 if 0.05 < prog < 0.95 else 0)
        self.label("安镇", px, py - 70)
        # 三个目击者 + 碎片台词, 各随自己的句子出现 (n08/n09/n10)
        witnesses = [("n08", "李大姐", "旧扳指", (90, 200, 90), "杂货铺"),
                     ("n09", "赵医生", "往镇东头走", (230, 180, 60), "诊所"),
                     ("n10", "周老师", "好像是灰色", (170, 170, 170), "周家小院")]
        for n, who, frag, col, home in witnesses:
            if t >= T(n):
                box2 = self.place_box(home)
                wx, wy = self.grid_to_px((box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2)
                self.sprite_at(who, wx, wy, 0)
                self.label(who, wx, wy - 70)
                a = min(1.0, (t - T(n)) / 0.5)
                self.text(f"「{frag}」", self.f_body, tuple(int(c * a) for c in col),
                          wx, wy + 34, "midtop")
        # 问题句 (n11)
        if t >= T("n11"):
            self.text("哪个会传遍全镇？", self.f_title, (255, 255, 255), W / 2, H - 120, "midtop")

    # ---------- 幕 3: progression (n12 ~ n26, v2 14 天快进) ----------
    def act_prog(self, t):
        self.screen.blit(self.map_surf, (0, 0))
        # 天数: n12-n25 段线性映射 1-14
        s0, s1 = T("n12"), Tend("n25")
        day = max(1, min(14, int((t - s0) / max(0.01, s1 - s0) * 14) + 1))
        # 精灵按当天事件走位
        rng = random.Random(day * 31)
        evs = [e for e in self.events if e.get("day") == day and e.get("place")]
        seen = set()
        for i, e in enumerate(evs):
            nm = e.get("agent")
            if nm not in self.sprites or nm in seen:
                continue
            seen.add(nm)
            box = self.place_box(e["place"])
            bx = (box[0] + box[2]) / 2 + rng.uniform(-0.7, 0.7)
            by = (box[1] + box[3]) / 2 + rng.uniform(-0.7, 0.7)
            px, py = self.grid_to_px(bx, by)
            self.sprite_at(nm, px, py, (day + i) % 3)
        # 没事件的在家
        for nm in self.sprites:
            if nm in seen:
                continue
            box = self.place_box(self.home_of.get(nm, "镇公园"))
            px, py = self.grid_to_px((box[0] + box[2]) / 2 + rng.uniform(-0.5, 0.5),
                                     (box[1] + box[3]) / 2 + rng.uniform(-0.5, 0.5))
            self.sprite_at(nm, px, py, 0)
        # 左上: 天数 + 知情计数 + 进度条
        self.label(f"第 {day} / 14 天", 150, 24)
        knows = KNOWS[day - 1]
        self.text(f"知情 {knows} / 25", self.f_big, (120, 200, 255), 40, 84, "topleft")
        pygame.draw.rect(self.screen, (60, 60, 70), (40, 136, 340, 12))
        pygame.draw.rect(self.screen, (120, 200, 255), (40, 136, int(knows / 25 * 340), 12))
        # 右上: 三碎片转述计数 (随天数生长)
        grow = min(1.0, day / 14)
        for i, (nm, v, c) in enumerate(FRAGS):
            yy = 24 + i * 46
            self.text(f"{nm}  {int(v * grow)} 条", self.f_body, c, W - 330, yy, "topleft")
        # 周老师证据 (n18 起)
        if t >= T("n18"):
            a = min(1.0, (t - T("n18")) / 0.6)
            self.text("周老师 35 次发言 · 0 次提颜色", self.f_body,
                      (int(255 * a), int(110 * a), int(110 * a)), 40, 160, "topleft")
        # 孙有财反派弧 (n24/n25): 精灵高亮 + 事件卡
        if t >= T("n24"):
            box = self.place_box("五金店")
            sx, sy = self.grid_to_px((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)
            pygame.draw.circle(self.screen, (255, 90, 90), (sx, sy - 14), 34, 3)
            self.sprite_at("孙有财", sx, sy, 1)
            self.label("孙有财 · 无人怀疑", sx, sy - 96, color=(255, 140, 140))
        if t >= T("n25"):
            self.text("D12 烧掉登记存根 · D13 趁夜还回纸箱", self.f_small,
                      (255, 170, 170), 40, 196, "topleft")

    # ---------- 幕 4: reveal (n26 ~ 结尾, v3 零注入对照) ----------
    def act_reveal(self, t):
        self.screen.fill((14, 16, 26))
        self.label("另一座镇子 · 35 天 · 零注入", 200, 24, color=(160, 190, 255))
        # 天数 n27-n35 → 1-35
        s0, s1 = T("n27"), Tend("n35")
        day = max(1, min(35, int((t - s0) / max(0.01, s1 - s0) * 35) + 1))
        self.text(f"第 {day} / 35 天", self.f_body, (170, 180, 200), 40, 64, "topleft")
        # 左: 双曲线
        gx, gy, gw, gh = 60, 150, 700, 300
        pygame.draw.rect(self.screen, (30, 34, 48), (gx, gy, gw, gh))
        self.text("累计触达人数", self.f_small, (200, 205, 220), gx, gy - 30, "topleft")
        pts2 = [(gx + int((d - 1) / 34 * gw), gy + gh - int(KNOWS[d - 1] / 27 * (gh - 24)))
                for d in range(1, 15)]
        if len(pts2) > 1:
            pygame.draw.lines(self.screen, (230, 120, 120), False, pts2, 3)
            self.text("v2 有锚点 → 25/25", self.f_small, (230, 120, 120), pts2[-1][0] + 12, pts2[-1][1] - 12, "topleft")
        upto = min(day, 35)
        pts3 = [(gx + int((d - 1) / 34 * gw), gy + gh - int(V3_CUM[d - 1] / 27 * (gh - 24)))
                for d in range(1, upto + 1)]
        if len(pts3) > 1:
            pygame.draw.lines(self.screen, (120, 170, 255), False, pts3, 3)
            self.text("v3 零注入 → 4/25", self.f_small, (120, 170, 255), pts3[-1][0] + 12, pts3[-1][1] + 8, "topleft")
        # 右: 传闻触达 4 人 sprite 头像
        self.text("传闻触达", self.f_small, (200, 200, 210), gx + gw + 60, gy + 10, "topleft")
        for i, p in enumerate(RUMOR4):
            yy = gy + 56 + i * 74
            col = (255, 200, 120) if day >= i * 2 + 1 else (90, 90, 100)
            if p in self.sprites and day >= i * 2 + 1:
                self.screen.blit(self.sprites[p][0], (gx + gw + 60, yy - 20))
            self.text(p, self.f_small, col, gx + gw + 124, yy, "topleft")
        # 大数字 (n30=167次 / n31=4人)
        if t >= T("n30"):
            a = min(1.0, (t - T("n30")) / 0.7)
            self.text("167 次提及", self.f_big, (int(255 * a), int(200 * a), int(120 * a)),
                      gx + gw + 60, gy + 360, "topleft")
        if t >= T("n31"):
            a = min(1.0, (t - T("n31")) / 0.7)
            self.text("4 人知晓", self.f_big, (int(120 * a), int(170 * a), int(255 * a)),
                      gx + gw + 60, gy + 420, "topleft")
        # 对照结论 (n35/n36) — 靠图表一侧居中, 与右侧大数字避让
        ccx = gx + gw // 2
        if t >= T("n35"):
            a = min(1.0, (t - T("n35")) / 0.8)
            self.text("有故事的小镇：25 / 25 全部知情", self.f_big,
                      (int(255 * a), int(215 * a), int(140 * a)), ccx, H - 210, "midtop")
        if t >= T("n36"):
            a = min(1.0, (t - T("n36")) / 0.8)
            self.text("没故事的小镇：传闻停在 4 个人", self.f_big,
                      (int(120 * a), int(170 * a), int(255 * a)), ccx, H - 150, "midtop")
        # 结尾问句 (n38) — 此时字幕条隐去, 让位给大字
        if t >= T("n38"):
            a = min(1.0, (t - T("n38")) / 1.0)
            self.text("会自己长出内容吗？", self.f_title, (int(255 * a),) * 3, W / 2, H - 100, "midtop")

    def draw(self, t, total):
        if t < T("n05"):
            self.act_hook(t)
        elif t < T("n12"):
            self.act_setup(t)
        elif t < T("n26"):
            self.act_prog(t)
        else:
            self.act_reveal(t)
        self.subtitle(t)
        # 结尾淡出
        if t > total - 1.0:
            a = min(1.0, (t - (total - 1.0)) / 1.0)
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(200 * a)))
            self.screen.blit(ov, (0, 0))


def audio_dur(p):
    import subprocess
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True, timeout=60)
    return float(r.stdout.strip())


def main():
    import subprocess
    a_dur = audio_dur(TRACK)
    video_len = a_dur + 0.4   # 视频帧覆盖整条音轨 + 0.4s 尾帧 — 不用 -shortest
    print(f"音轨 {a_dur:.2f}s → 视频 {video_len:.2f}s")
    R = Renderer()
    print(f"精灵 {len(R.sprites)} 人, 事件 {len(R.events)} 条")
    ffmpeg_cmd = ("ffmpeg -y -v error -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {fps} -i - "
                  "-i {narr} -c:v libx264 -pix_fmt yuv420p -crf 22 -c:a aac -b:a 128k "
                  "{out}").format(W=W, H=H, fps=FPS, narr=TRACK, out=OUT)
    pipe = subprocess.Popen(ffmpeg_cmd.split(), stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t, n = 0.0, 0
    while t < video_len:
        for ev in pygame.event.get():
            pass
        R.draw(t, video_len)
        pipe.stdin.write(pygame.image.tostring(R.screen, "RGB"))
        n += 1
        t += 1.0 / FPS
    pipe.stdin.close()
    pipe.wait()
    print(f"v7 渲染完成: {OUT} ({os.path.getsize(OUT)//1024} KB, {n} 帧)")


if __name__ == "__main__":
    main()

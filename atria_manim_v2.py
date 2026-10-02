"""Atria Demo — 精华版视频 (~90 秒)
结构:
  1. 开场: 镇子全景 + 标题 (5s)
  2. 第2天: 引爆(邮局红框) + 三碎片出场 (10s)
  3. 第3-11天: 传播快放(精灵移动+知情计数器爬升) (30s)
  4. 第12天: 安镇当面找孙有财(核心对白) (15s)
  5. 第13-14天: 孙有财心理转变链 (10s)
  6. 片尾: 三碎片命运分化统计 + 卖点 slogan (15s)
"""
from manim import *
import json, os, random, subprocess
from PIL import Image

RUN_DIR = "/home/ubuntu/atria_run"
MAP_PNG = "/home/ubuntu/atria_render_map_half.png"
SPRITE_DIR = "/home/ubuntu/atria_sprites"
GW, GH, PX = 40, 30, 16.0

events = []
for d in range(1, 15):
    p = f"{RUN_DIR}/day{d:02d}.jsonl"
    if os.path.exists(p):
        for l in open(p):
            events.append(json.loads(l))

# 知情曲线(实测算出)
KNOWS = [9, 11, 14, 16, 16, 16, 17, 17, 18, 18, 19, 20, 20, 20]

sys_path_added = False
def grid_to_manim(x, y):
    mx = (x + 0.5) * PX - 640 / 2
    my = 480 / 2 - (y + 0.5) * PX
    return mx * 0.0125, my * 0.0125


def place_box(name):
    import sys
    sys.path.insert(0, "/home/ubuntu")
    from atria_world import PLACES, HOMES_SOUTH, ROADS
    return PLACES.get(name, {}).get("box") or HOMES_SOUTH.get(name) or ROADS.get(name)


class AtriaHighlights(Scene):
    def construct(self):
        rng = random.Random(7)
        FONT = "WenQuanYi Zen Hei"

        # ---------- 1. 开场 ----------
        map_img = ImageMobject(MAP_PNG).scale(1.07)
        self.add(map_img)
        title = Text("Atria 小镇：一个包裹错领的 14 天", font=FONT, font_size=26)
        title.to_edge(UP)
        sub = Text("25 个 AI 居民 · 全部行为涌现 · 无剧本", font=FONT, font_size=16)
        sub.next_to(title, DOWN, buff=0.1)
        self.play(FadeIn(title), FadeIn(sub))
        self.wait(1.5)
        self.remove(sub)

        # ---------- 2. 第2天引爆 ----------
        day_label = Text("第 2 天 · 邮局", font=FONT, font_size=22)
        day_label.to_edge(UP)
        self.play(Transform(title, day_label))

        bx = place_box("邮局")
        gx, gy = grid_to_manim((bx[0]+bx[2])/2, (bx[1]+bx[3])/2)
        flash = RoundedRectangle(width=2.2, height=1.5, color=RED, stroke_width=4)
        flash.move_to([gx, gy, 0])
        self.play(Create(flash))
        blast = Text("◆ 包裹被错领", font=FONT, font_size=18, color=RED)
        blast.next_to(flash, UP, buff=0.1)
        self.play(Write(blast))
        self.wait(1.5)
        self.remove(flash, blast)

        # 三碎片出场
        frags = [("周老师", "瞥见衣裳颜色偏浅…好像灰色", place_box("周家小院")),
                 ("赵医生", "远远瞧见往镇东头走", place_box("赵宅")),
                 ("李大姐", "瞧见手上戴着个旧扳指", place_box("李家"))]
        frag_texts = []
        for name, txt, box in frags:
            gx, gy = grid_to_manim((box[0]+box[2])/2, (box[1]+box[3])/2)
            d = Dot(radius=0.09, color=YELLOW).move_to([gx, gy, 0])
            t = Text(f"{name}: {txt}", font=FONT, font_size=13)
            t.next_to(d, UP, buff=0.05)
            self.play(FadeIn(d), Write(t), run_time=0.7)
            frag_texts.append((d, t))
        self.wait(1.5)
        for d, t in frag_texts:
            self.play(FadeOut(t), run_time=0.3)

        # ---------- 3. 传播快放 ----------
        counter = VGroup(*[Text(f"知情 0/25", font=FONT, font_size=18)])
        counter.to_corner(DR)
        self.add(counter)

        ev_by_day = {}
        for e in events:
            ev_by_day.setdefault(e["day"], []).append(e)

        dots = {}
        for day in range(3, 12):
            new_day = Text(f"第 {day} 天", font=FONT, font_size=22)
            new_day.to_edge(UP)
            self.play(Transform(title, new_day), run_time=0.15)
            day_evs = ev_by_day.get(day, [])
            # 每天挑最多 5 个事件
            for e in day_evs[:5]:
                name = e["agent"]
                box = place_box(e["place"])
                if box:
                    gx, gy = grid_to_manim((box[0]+box[2])/2 + rng.uniform(-1,1),
                                            (box[1]+box[3])/2 + rng.uniform(-1,1))
                    if name not in dots:
                        dots[name] = Dot(radius=0.07, color=BLUE).move_to([gx, gy, 0])
                        self.add(dots[name])
                    self.play(dots[name].animate.move_to([gx, gy, 0]), run_time=0.12)
                    say = e.get("say", "")
                    if say and say != "无" and rng.random() < 0.3:
                        b = Text(f"{name}:{say[:12]}", font=FONT, font_size=11)
                        b.next_to(dots[name], UP, buff=0.04)
                        self.add(b)
                        self.wait(0.1)
                        self.remove(b)
            new_ct = Text(f"知情 {KNOWS[day-1]}/25", font=FONT, font_size=18)
            new_ct.to_corner(DR)
            self.play(Transform(counter, new_ct), run_time=0.15)

        # ---------- 4. 第12天核心对白 ----------
        d12 = Text("第 12 天 · 抉择", font=FONT, font_size=22)
        d12.to_edge(UP)
        self.play(Transform(title, d12))

        box = place_box("五金店")
        gx, gy = grid_to_manim((box[0]+box[2])/2, (box[1]+box[3])/2)
        sun = Dot(radius=0.09, color=RED).move_to([gx, gy, 0])
        self.add(sun)
        # 安镇走过去
        bx2 = place_box("邮局")
        ax, ay = grid_to_manim((bx2[0]+bx2[2])/2, (bx2[1]+bx2[3])/2)
        an = Dot(radius=0.09, color=BLUE).move_to([ax, ay, 0])
        self.add(an)
        self.play(an.animate.move_to([gx-0.4, gy, 0]), run_time=1.2)

        conv = Text("安镇: 孙老板，我那包裹被人从邮局错领了，\n里头是我亡妻留下的旧物。十二天了…",
                    font=FONT, font_size=15, color=YELLOW)
        conv.to_edge(LEFT).shift(DOWN*0.5)
        self.play(Write(conv), run_time=1.5)
        self.wait(2)
        self.remove(conv)

        # ---------- 5. 孙有财心理链 ----------
        d1314 = Text("第 13–14 天 · 孙有财", font=FONT, font_size=22)
        d1314.to_edge(UP)
        self.play(Transform(title, d1314))
        chain = ["他亡妻的遗物…这可怎么还，先躲躲",
                 "亡妻遗物…惹上这档子事，晦气！",
                 "还是别惹事，先躲着"]
        prev = None
        for i, line in enumerate(chain):
            t = Text(f"孙有财: {line}", font=FONT, font_size=15, color=RED)
            t.to_edge(LEFT).shift(DOWN*0.5)
            if prev:
                self.play(Transform(prev, t), run_time=0.8)
            else:
                self.play(Write(t), run_time=0.8)
                prev = t
            self.wait(0.8)
        self.remove(prev)

        # ---------- 6. 片尾 ----------
        end_title = Text("14 天后的信息生态", font=FONT, font_size=24)
        end_title.to_edge(UP)
        self.play(Transform(title, end_title))
        self.play(FadeOut(counter))

        stats = [
            ("李大姐的扳指碎片", "36 人次传播", GREEN),
            ("赵医生的方向碎片", "4 人次传播", YELLOW),
            ("周老师的颜色碎片", "0 人次 · 不确定措辞被传播链静默丢弃", RED),
        ]
        lines = VGroup()
        for name, val, col in stats:
            t = Text(f"{name}  →  {val}", font=FONT, font_size=16, color=col)
            lines.add(t)
        lines.arrange(DOWN, aligned_edge=LEFT, buff=0.25)
        lines.shift(LEFT*2.5 + UP*0.3)
        self.play(Write(lines), run_time=2.5)
        self.wait(2)

        slogan = Text("每个居民拥有 512K 全量记忆，\n全量时间线让 agent 分辨传言的变异",
                      font=FONT, font_size=20, color=BLUE)
        slogan.to_edge(DOWN)
        self.play(Write(slogan))
        self.wait(3)
        self.play(FadeOut(slogan), FadeOut(lines))

        fin = Text("—— Atria · 涌现观察站 ——", font=FONT, font_size=30)
        self.play(Write(fin))
        self.wait(2)


if __name__ == "__main__":
    r = subprocess.run(["/usr/bin/python3.12", "-m", "manim", "render", "-qm",
                        "--media_dir", "/home/ubuntu/media",
                        "/home/ubuntu/atria_manim_v2.py", "AtriaHighlights",
                        "-o", "atria_highlights"], capture_output=True, text=True,
                       timeout=580, cwd="/home/ubuntu")
    print("rc:", r.returncode)
    print(r.stdout[-1000:])
    if r.returncode:
        print("ERR:", r.stderr[-1500:])

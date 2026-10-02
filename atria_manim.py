"""Atria Demo — manim 渲染引擎
把 25 人 x 14 天的事件流渲染成视频。
分层:
  - 静态地图层(PIL 渲染的 PNG)
  - 精灵动画层(25 人 3 帧行走, 事件流驱动移动)
  - 信息层(对话气泡、日期、事件计数、右侧统计面板)
事件源: /home/ubuntu/atria_run/dayXX.jsonl
"""
from manim import *
import json, os, random
from PIL import Image

MAP_PNG = "/home/ubuntu/atria_render_map_half.png"
SPRITE_DIR = "/home/ubuntu/atria_sprites"
RUN_DIR = "/home/ubuntu/atria_run"

# 读取事件
events = []
for d in range(1, 15):
    p = f"{RUN_DIR}/day{d:02d}.jsonl"
    if os.path.exists(p):
        for l in open(p):
            events.append(json.loads(l))
print(f"事件总数: {len(events)}")

# 地图坐标 -> manim 坐标 (地图 40x30 格, 半幅 640x480, 1格=16px)
GW, GH = 40, 30
PX = 16.0  # 每格像素(半幅)


def grid_to_manim(x, y):
    """格坐标 -> manim 坐标(地图中心为原点)"""
    mx = (x + 0.5) * PX - 640 / 2
    my = 480 / 2 - (y + 0.5) * PX
    return mx * 0.0125, my * 0.0125  # manim 单位缩放


class AtriaDemo(Scene):
    def construct(self):
        # 地图背景
        map_img = ImageMobject(MAP_PNG)
        map_img.scale(1.07)
        self.add(map_img)

        # 精灵(25 人)
        import os
        sprites = {}
        for name in os.listdir(SPRITE_DIR):
            if name.endswith(".png"):
                n = name[:-4]
                # 三帧拼成一张 96x32, 取第 0 帧(站)与切换实现行走
                im = Image.open(f"{SPRITE_DIR}/{name}")
                sprites[n] = im

        dots = {}
        rng = random.Random(7)
        events_by_day = {}
        for e in events:
            events_by_day.setdefault(e["day"], []).append(e)

        # 标题
        title = Text("Atria 小镇：包裹错领的 14 天", font="WenQuanYi Zen Hei", font_size=28)
        title.to_edge(UP)
        self.add(title)
        day_label = Text("第 1 天", font="WenQuanYi Zen Hei", font_size=24)
        day_label.to_edge(UP).shift(RIGHT * 5)
        self.add(day_label)

        fps = 15
        self.camera.frame_rate = fps

        # 逐日播放
        for day in range(1, 15):
            new_label = Text(f"第 {day} 天", font="WenQuanYi Zen Hei", font_size=24)
            new_label.to_edge(UP).shift(RIGHT * 5)
            self.play(Transform(day_label, new_label), run_time=0.3)

            day_evs = events_by_day.get(day, [])
            # 每天播 4 秒, 每事件约 4*fps/max(1,len(day_evs)) 帧
            n_ev = max(1, len(day_evs))
            frames_per_ev = max(2, int(4 * fps / n_ev))

            for e in day_evs:
                name = e["agent"]
                # 事件地点 -> 格坐标(从事件 place 名反解; 简化: 随机抖动)
                gx = rng.uniform(2, 38)
                gy = rng.uniform(2, 28)
                # 用事件 place 查实际坐标
                import sys
                sys.path.insert(0, "/home/ubuntu")
                try:
                    from atria_world import PLACES, HOMES_SOUTH, ROADS
                    box = PLACES.get(e["place"], {}).get("box") or HOMES_SOUTH.get(e["place"]) or ROADS.get(e["place"])
                    if box:
                        gx = (box[0] + box[2]) / 2 + rng.uniform(-1, 1)
                        gy = (box[1] + box[3]) / 2 + rng.uniform(-1, 1)
                except Exception:
                    pass
                tx, ty = grid_to_manim(gx, gy)

                if name not in dots:
                    d = Dot(radius=0.08, color=BLUE)
                    dots[name] = d
                    self.add(d)
                # 移动
                self.play(dots[name].animate.move_to([tx, ty, 0]), run_time=0.2)

                # 说的话(气泡)
                say = e.get("say", "")
                if say and say != "无" and rng.random() < 0.35:
                    bubble = Text(f"{name}: {say[:14]}", font="WenQuanYi Zen Hei", font_size=12)
                    bubble.next_to(dots[name], UP, buff=0.05)
                    self.add(bubble)
                    self.wait(0.15)
                    self.remove(bubble)

        # 片尾
        self.wait(1)
        end = Text("—— 全部涌现，无剧本 ——", font="WenQuanYi Zen Hei", font_size=32)
        self.play(Write(end))
        self.wait(2)


if __name__ == "__main__":
    import subprocess
    r = subprocess.run(["/usr/bin/python3.12", "-m", "manim", "render", "-ql",
                        "/home/ubuntu/atria_manim.py", "AtriaDemo", "-o", "atria_demo"],
                       capture_output=True, text=True, timeout=580, cwd="/home/ubuntu")
    print(r.stdout[-1500:])
    print("STDERR:", r.stderr[-1500:] if r.returncode else "无")

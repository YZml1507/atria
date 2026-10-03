#!/usr/bin/env python3
"""Atria 视频 v8 — 3D 小镇开场/邮局事件(Three.js 帧序列) + v7 的 2D 传播/对照幕

结构:
  0 - 46.7s  : 3D 渲染帧(atria3d/index.html 捕获) — 黎明亮相 + 邮局推近 + 大俯瞰
  46.7s 起   : v7 的 act_prog / act_reveal(2D 像素地图 + 数据幕)
  合成层     : hook 文字卡、25人标题、三碎片卡、字幕、46.7-47.1s 交叉淡入

素材:
  ATRIA_FRAMES  3D PNG 帧序列目录(默认 ../atria3d/frames)
  narration_v6/ 旁白音轨 + timeline.json
用法: python3 atria_video_v8.py
"""
import os, sys, json, random
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
RUN2 = os.environ.get("ATRIA_RUN2", os.path.join(HERE, "run_v2"))
NARR_DIR = os.environ.get("ATRIA_NARR", os.path.join(HERE, "narration_v6"))
FRAMES = os.environ.get("ATRIA_FRAMES", os.path.join(HERE, "..", "atria3d", "frames"))
OUT = os.environ.get("ATRIA_OUT", os.path.join(HERE, "renders", "atria_v8.mp4"))
W, H = 1280, 720
FPS = 30
CUT = 46.7          # 3D → 2D 切换点
NF3D = 1401         # 3D 帧数(46.7s*30)

sys.path.insert(0, HERE)
from atria_narration_v6_text import NARRATION_V6
TEXTS = {n: t for n, t in NARRATION_V6}
TL = json.load(open(os.path.join(NARR_DIR, "timeline.json")))["timeline"]
TRACK = os.path.join(NARR_DIR, "narration_track_v6.mp3")
ORDER = [f"n{i:02d}" for i in range(39)]
def T(n): return TL[n]["start"]
def Tend(n): return TL[n]["start"] + TL[n]["dur"]

KNOWS = [11, 16, 17, 19, 22, 22, 23, 24, 25, 25, 25, 25, 25, 25]
FRAGS = [("扳指", 164, (90, 200, 90)), ("方向", 30, (230, 180, 60)), ("颜色", 0, (150, 150, 150))]
V3_CUM = [1, 3] + [4] * 33
RUMOR4 = ["吕婶", "钱老板", "许货郎", "朱寡妇"]

from atria_video_v7 import Renderer as _R7      # 复用 v7 的 act_prog/act_reveal/subtitle/工具


class Renderer(_R7):
    def __init__(self):
        super().__init__()
        # 3D 帧懒加载缓存
        self._f3d = {}

    def frame3d(self, t):
        i = min(int(t * FPS), NF3D - 1)
        if i not in self._f3d:
            p = os.path.join(FRAMES, f"f{i:05d}.png")
            if len(self._f3d) > 6:                       # 只保留少量缓存, 省内存
                self._f3d.clear()
            self._f3d[i] = pygame.image.load(p).convert()
        return self._f3d[i]

    def card(self, s, x, y, font=None, color=(240, 240, 245), anchor="midtop", pad=14):
        """半透明底文字卡"""
        f = font or self.f_big
        surf = f.render(s, True, color)
        w, h = surf.get_size()
        bg = pygame.Surface((w + pad * 2, h + pad), pygame.SRCALPHA)
        bg.fill((10, 12, 18, 150))
        r = bg.get_rect()
        setattr(r, anchor, (x, y))
        self.screen.blit(bg, r)
        self.screen.blit(surf, (r.x + pad, r.y + pad // 2))
        return r

    def draw3d_overlay(self, t):
        """3D 段上的文字合成层"""
        # hook 四行 (n00-n03)
        lines = [("n00", "如果把你丢进一座小镇"), ("n01", "十四天"),
                 ("n02", "你记不清每个人说了什么"), ("n03", "但你记得哪句是真的")]
        if t < T("n04"):
            y = H / 2 - 110
            for n, s in lines:
                if t >= T(n):
                    a = min(1.0, (t - T(n)) / 0.7)
                    self.card(s, W / 2, y, color=(int(240 * a),) * 3)
                y += 76
        # n04→n05: 全镇亮相标题
        elif t < T("n05"):
            a = min(1.0, (t - T("n04")) / 0.9)
            self.card("25 个居民 · 全是语言模型", W / 2, 30,
                      font=self.f_title, color=(int(255 * a),) * 3)
        # setup 段小标注
        elif t < T("n08"):
            self.card("安镇 · 邮局事件 · 第 1 天", 120, 26, font=self.f_place,
                      color=(255, 244, 200), anchor="midleft")
        # 三碎片卡 (n08/n09/n10 起, 右下竖排, 常驻到切幕)
        frags = [("n08", "李大姐 看见「旧扳指」", (90, 220, 110)),
                 ("n09", "赵医生 看见「往镇东头走」", (240, 200, 90)),
                 ("n10", "周老师 看见「好像灰色」", (200, 200, 215))]
        for i, (n, txt, c) in enumerate(frags):
            if t >= T(n):
                a = min(1.0, (t - T(n)) / 0.5)
                yy = H - 300 + i * 52
                self.card(txt, W - 60, yy, font=self.f_body,
                          color=tuple(int(v * a) for v in c), anchor="midright")

    def draw(self, t, total):
        if t < CUT:
            self.screen.blit(self.frame3d(t), (0, 0))
            self.draw3d_overlay(t)
        elif t < T("n26"):
            self.act_prog(t)
        else:
            self.act_reveal(t)
        # 46.7-47.1s 交叉淡入: 3D 末帧叠在 2D 首帧上淡出
        if CUT <= t < CUT + 0.45:
            last = self.frame3d(CUT).copy()
            last.set_alpha(int(255 * (1 - (t - CUT) / 0.45)))
            self.screen.blit(last, (0, 0))
        self.subtitle(t)
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
    video_len = a_dur + 0.4
    print(f"音轨 {a_dur:.2f}s → 视频 {video_len:.2f}s")
    R = Renderer()
    assert os.path.exists(os.path.join(FRAMES, "f00000.png")), f"缺 3D 帧: {FRAMES}"
    ffmpeg_cmd = ("ffmpeg -y -v error -f rawvideo -pix_fmt rgb24 -s {W}x{H} -r {fps} -i - "
                  "-i {narr} -c:v libx264 -pix_fmt yuv420p -crf 22 -c:a aac -b:a 128k "
                  "{out}").format(W=W, H=H, fps=FPS, narr=TRACK, out=OUT)
    pipe = subprocess.Popen(ffmpeg_cmd.split(), stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t, n = 0.0, 0
    while t < video_len:
        R.draw(t, video_len)
        pipe.stdin.write(pygame.image.tostring(R.screen, "RGB"))
        n += 1
        t += 1.0 / FPS
    pipe.stdin.close()
    pipe.wait()
    print(f"v8 渲染完成: {OUT} ({os.path.getsize(OUT)//1024} KB, {n} 帧)")


if __name__ == "__main__":
    main()

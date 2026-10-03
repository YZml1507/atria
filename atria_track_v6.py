#!/usr/bin/env python3.12
# v6/v7 音轨合成: 句间停顿按"结构角色"分配(不是统一 0.8s)
#  - 句内断句(拆开的短句): 0.35s
#  - 段落内: 0.7s
#  - 幕与幕之间(hook→setup→progression→reveal): 1.2s (调研: reveal 前停 0.5-1.0s)
#
# 用法: python3 atria_track_v6.py [逐句mp3目录] [输出目录]
#   默认: ./narration_v6/segments -> ./narration_v6/{narration_track_v6.mp3, timeline.json}
#   逐句目录需含 n00.mp3 .. n38.mp3 (由 tts_gen_v2.py 生成)
import subprocess, os, json, sys

NARR_DIR = sys.argv[1] if len(sys.argv) > 1 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "narration_v6", "segments")
OUT_DIR = sys.argv[2] if len(sys.argv) > 2 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "narration_v6")
GAP_INNER = 0.35   # 句内拆碎的短句
GAP_PARA = 0.70    # 段落内
GAP_ACT = 1.20     # 幕之间 / reveal 前

# 39 句的停顿标记, 长度必须 = 38 (每句后一个停顿, 末句除外)
# i=句内断句, p=段落内, a=幕切换/reveal前停顿
# 键序 = n00..n38 (与 atria_narration_v6_text.py 一一对应)
#   hook n00-04 / setup n05-11 / prog n12-25 / reveal n26-38
# 历史 bug: 旧表只有 29 项, n29 之后全部无停顿背靠背连读。
GAPS = [
    "i","i","i","i","a",              # n00-04: hook 4短句 + hook→setup
    "p","p","i","i","i","p","a",      # n05-11: setup 事件+三碎片+问题 + setup→prog
    "i","p","p","i","i","p","i","i","p","i","i","p","i","a",  # n12-25: prog 递进+误传+反派 + prog→reveal
    "p","i","i","p","p","i","p","i","p","i","p","a",  # n26-38: reveal 对照+结论+问句前停顿
]
assert len(GAPS) == 38, f"GAPS 长度 {len(GAPS)} != 38 (每句后一个停顿, 末句除外)"

def dur(p):
    r = subprocess.run(["bash","-c",f"ffprobe -v error -show_entries format=duration -of csv=p=0 {p}"],
                       capture_output=True, text=True, timeout=60)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0

# 生成不同时长的静音片
def silence(t, name):
    p = f"{NARR_DIR}/sil_{name}.mp3"
    if not os.path.exists(p):
        subprocess.run(["bash","-c",
            f"ffmpeg -y -v error -f lavfi -i anullsrc=r=24000:cl=mono -t {t} -q:a 9 {p}"],
            capture_output=True, timeout=120)
    return p

sil_map = {"i": silence(GAP_INNER, "i"), "p": silence(GAP_PARA, "p"), "a": silence(GAP_ACT, "a")}

# concat 列表 — n38 后补 0.8s 尾静音, 防止混流时末句尾音被截
ORDER = [f"n{i:02d}" for i in range(39)]
listf = f"{NARR_DIR}/concat.txt"
with open(listf, "w") as f:
    for i, n in enumerate(ORDER):
        p = f"{NARR_DIR}/{n}.mp3"
        assert os.path.exists(p), f"缺逐句音频 {p} — 先跑 tts_gen_v2.py"
        f.write(f"file '{p}'\n")
        if i < len(GAPS):
            f.write(f"file '{sil_map[GAPS[i]]}'\n")
    f.write(f"file '{silence(0.8, 'tail')}'\n")

track = os.path.join(OUT_DIR, "narration_track_v6.mp3")
os.makedirs(OUT_DIR, exist_ok=True)
r = subprocess.run(["bash","-c",f"ffmpeg -y -v error -f concat -safe 0 -i {listf} -c copy {track}"],
                   capture_output=True, text=True, timeout=300)
print("合并 rc:", r.returncode, os.path.getsize(track)//1024, "KB")

# 时间轴
timeline = {}
t = 0.0
for i, n in enumerate(ORDER):
    d = dur(f"{NARR_DIR}/{n}.mp3")
    timeline[n] = {"start": round(t, 2), "dur": round(d, 2)}
    t += d
    if i < len(GAPS):
        t += {"i": GAP_INNER, "p": GAP_PARA, "a": GAP_ACT}[GAPS[i]]
print(f"总时长: {t:.1f}s")
json.dump({"total": round(t,2), "timeline": timeline},
          open(os.path.join(OUT_DIR, "timeline.json"),"w"), ensure_ascii=False, indent=1)

#!/usr/bin/env python3.12
# v6 音轨合成: 句间停顿按"结构角色"分配(不是统一 0.8s)
#  - 句内断句(拆开的短句): 0.35s
#  - 段落内: 0.7s
#  - 幕与幕之间(hook→setup→progression→reveal): 1.2s (调研: reveal 前停 0.5-1.0s)
#  - reveal 句(n19/n22/n23): 前面留 1.0s
import subprocess, os, json

NARR_DIR = "/tmp/v6_narr"
GAP_INNER = 0.35   # 句内拆碎的短句
GAP_PARA = 0.70    # 段落内
GAP_ACT = 1.20     # 幕之间 / reveal 前

# 39 句的结构标记: i=句内, p=段落, a=幕切换/reveal停顿
GAPS = [
    "p","i",        # n00->n01 句内, n01->n02 句内? 实际 n00/n01/n02 是 hook 内
    "i","a",        # n02->n03 句内, n03->n04 幕(hook->setup)
    "i","i","i","p",# setup 内
    "a",            # n09->n10 setup->progression
    "i","p","i","i","p","i","p","p",   # progression 阶梯
    "a",            # n18->n19 progression->reveal
    "p","i","p","i","i","p","p","p",   # reveal 内
    "a",            # n28->n29 结论重击前
    "i","a",        # n29->n30->n31 结尾问句
]

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

# concat 列表
ORDER = [f"n{i:02d}" for i in range(39)]
listf = f"{NARR_DIR}/concat.txt"
with open(listf, "w") as f:
    for i, n in enumerate(ORDER):
        f.write(f"file '{NARR_DIR}/{n}.mp3'\n")
        if i < len(GAPS):
            f.write(f"file '{sil_map[GAPS[i]]}'\n")

track = "/home/ubuntu/atria_repo/narration_v6/narration_track_v6.mp3"
os.makedirs(os.path.dirname(track), exist_ok=True)
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
          open("/home/ubuntu/atria_repo/narration_v6/timeline.json","w"), ensure_ascii=False, indent=1)

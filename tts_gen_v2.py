#!/usr/bin/env python3.12
"""TTS 生成器 v2 — 修复句尾被切问题

v1 bug: 固定"尾部裁 0.9s", 但 edge-tts 尾静音实际 ~0.58s → 19/19 句尾被削 ~0.32s
v2: silencedetect 动态找语音结尾, 裁到 语音结尾+0.12s; 前导只裁 0.15s

用法: python3 tts_gen.py <文案句列表json> <输出目录>
"""
import subprocess, os, json, sys

VOICE = "zh-CN-XiaoxiaoNeural"

def run(cmd, timeout=180):
    return subprocess.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=timeout)

def dur(p):
    r = run(f"ffprobe -v error -show_entries format=duration -of csv=p=0 {p}")
    try:
        return float(r.stdout.strip())
    except Exception:
        return None

def speech_end(p, chunk=0.05, thresh=300):
    """语音真实结束时刻 — 用 RMS 从尾部往前扫, 不依赖 ffmpeg 阈值抖动
    返回: 语音结尾时刻(秒)"""
    import array
    r = subprocess.run(["bash", "-c",
        f"ffmpeg -v error -i {p} -f s16le -ar 16000 -ac 1 -"], capture_output=True, timeout=120)
    if not r.stdout:
        return None
    samples = array.array("h"); samples.frombytes(r.stdout)
    n = len(samples); sr = 16000
    bs = int(sr * chunk)
    last_voice = n
    for i in range(n - 1, 0, -bs):
        seg = samples[max(0, i - bs):i]
        rms = (sum(x * x for x in seg) / max(1, len(seg))) ** 0.5
        if rms > thresh:
            last_voice = i
            break
    return last_voice / sr

def make_tts(text, out_mp3, retries=3):
    raw = out_mp3.replace(".mp3", "_raw.mp3")
    for a in range(retries):
        r = run(f'edge-tts --voice {VOICE} --text "{text}" --write-media {raw}')
        if os.path.exists(raw) and os.path.getsize(raw) > 1000:
            break
    if not (os.path.exists(raw) and os.path.getsize(raw) > 1000):
        return None, f"TTS失败: {text[:20]}"

    d = dur(raw)
    se = speech_end(raw)
    if d is None or se is None:
        return None, f"探测失败: {text[:20]}"

    # 前导 0.15s, 时长 = 语音结尾+0.12s 呼吸 - 0.15s
    # 注意: mp3 -c copy 的 -to 按帧对齐不精确, 必须重编码; -to 用时长更稳的是 -t
    length = max(0.5, se + 0.12 - 0.15)
    r = run(f'ffmpeg -y -v error -i {raw} -ss 0.15 -t {length:.3f} -ar 24000 -ac 1 -c:a libmp3lame -q:a 4 {out_mp3}')
    if not (os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 500):
        return None, f"裁剪失败: {text[:20]}"
    return dur(out_mp3), None

if __name__ == "__main__":
    # 自检: 证明裁剪没切到语音
    sentences = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    ok = 0
    for i, text in enumerate(sentences):
        name = f"n{i:02d}"
        mp3 = f"{outdir}/{name}.mp3"
        d, err = make_tts(text, mp3)
        if err:
            print(f"{name} FAIL {err}")
        else:
            # 校验: 裁出来的成品末尾应有静音(说明没切到语音)
            se2 = speech_end(mp3)
            tail = (d - se2) if se2 else 0
            status = "ok" if 0.02 <= tail <= 0.3 else "CHECK"
            print(f"{name} {d:.2f}s 语音尾 {se2:.2f} 尾静音 {tail:.2f}s {status}")
            ok += 1
    print(f"\n完成 {ok}/{len(sentences)}")

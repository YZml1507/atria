"""RPM 复测: 排除 P0 里的混淆因素。
P0 的 24.7 RPM 可能被三件事拉低:
  1. 串行 for 循环里夹着 Python 逻辑(拼 prompt/状态更新), 不全是网络时间
  2. 没有并发——纯串行, 吞吐被单次延迟拖死, 不是端点真实容量
  3. emoji 那类任务 reasoning 特别重, 拉高平均延迟
复测方法: (a) 纯调用死循环测串行上限, (b) 4 线程并发测真实容量。
每次调用都是最小请求(hi, max_tokens=8), 排除任务差异。
"""
import json, urllib.request, time, subprocess, threading, os

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"


def one_call(i):
    body = json.dumps({"model": MODEL,
                       "messages": [{"role": "user", "content": f"reply OK {i}"}],
                       "max_tokens": 8, "temperature": 0})
    req = urllib.request.Request(
        URL, data=body.encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read())
        ok = d["choices"][0].get("message", {}).get("content") is not None
        return time.time() - t, ok, None
    except Exception as e:
        return time.time() - t, False, str(e)[:60]


# (a) 串行 20 次
print("=== (a) 串行 20 次最小请求 ===")
t0 = time.time()
lat, oks = [], 0
for i in range(20):
    dt, ok, err = one_call(i)
    lat.append(dt)
    oks += ok
    if err: print(f"  #{i} err: {err}")
tot = time.time() - t0
print(f"  成功 {oks}/20, 总时 {tot:.1f}s, 串行 RPM = {20/tot*60:.1f}")
print(f"  延迟: min={min(lat):.2f}s med={sorted(lat)[10]:.2f}s max={max(lat):.2f}s")

# (b) 4 线程并发, 各 15 次
print("=== (b) 4 线程 x 15 次并发 ===")
res = []
def worker(wid):
    for i in range(15):
        dt, ok, err = one_call(wid*100+i)
        res.append((dt, ok, err))
threads = [threading.Thread(target=worker, args=(w,)) for w in range(4)]
t0 = time.time()
for t in threads: t.start()
for t in threads: t.join()
tot = time.time() - t0
oks = sum(1 for _, ok, _ in res if ok)
errs = [e for _, _, e in res if e]
print(f"  成功 {oks}/60, 总时 {tot:.1f}s, 并发 RPM = {60/tot*60:.1f}")
if errs:
    print(f"  错误 {len(errs)}: {errs[:5]}")

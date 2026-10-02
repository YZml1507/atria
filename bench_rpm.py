"""探测真实 RPM 上限：并发2 + 自动退避，跑100秒"""
import os, time, threading, statistics
from openai import OpenAI
key = os.environ["HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY"]
client = OpenAI(base_url="https://discovery-api.intern-ai.org.cn/v1", api_key=key)

t_end = time.time() + 100
lat, ok, fail, lock = [], 0, 0, threading.Lock()

def worker():
    global ok, fail
    while time.time() < t_end:
        t0 = time.time()
        try:
            r = client.chat.completions.create(model="Atria-Dawn-Preview",
                messages=[{"role":"user","content":"说\"在\""}], max_tokens=5)
            dt = time.time()-t0
            with lock: lat.append(dt); ok += 1
        except Exception as e:
            with lock: fail += 1
            if "429" in str(e): time.sleep(8)   # 限流就退避
        time.sleep(0.3)

ts=[threading.Thread(target=worker,daemon=True) for _ in range(2)]
[t.start() for t in ts]; time.sleep(105)
print(f"100秒内 成功{ok} 失败{fail}")
print(f"推算RPM上限 ≈ {ok} 请求/分钟")
if lat: print(f"时延 中位{statistics.median(lat):.2f}s")

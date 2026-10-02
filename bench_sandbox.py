"""真实负载实测：25 智能体 x 6 步，测时延/并发/内存/费用"""
import os, time, json, threading, statistics
from openai import OpenAI

key = os.environ["HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY"]
client = OpenAI(base_url="https://discovery-api.intern-ai.org.cn/v1", api_key=key)

N_AGENTS, STEPS, CONC = 25, 6, 5
lat, errs, lock = [], [], threading.Lock()

def step(aid, s):
    msgs = [{"role":"system","content":f"你是小镇居民#{aid}，有自己性格。第{s}小时，根据记忆决定下一步动作，30字内。"},
            {"role":"user","content":"照做"}]
    t0=time.time()
    try:
        r = client.chat.completions.create(model="Atria-Dawn-Preview", messages=msgs, max_tokens=60)
        dt=time.time()-t0
        with lock: lat.append(dt)
        return r.choices[0].message.content
    except Exception as e:
        with lock: errs.append(str(e)[:120])
        return None

t0 = time.time(); sem = threading.Semaphore(CONC)
def job(aid):
    for s in range(1, STEPS+1):
        with sem: step(aid, s)
ts = [threading.Thread(target=job, args=(a,)) for a in range(N_AGENTS)]
[t.start() for t in ts]; [t.join() for t in ts]
total = time.time()-t0

print(f"== {N_AGENTS} Agent x {STEPS} 步 = {N_AGENTS*STEPS} 次调用（并发{CONC}）")
print(f"总耗时 {total:.1f}s  成功 {len(lat)}  失败 {len(errs)}")
if lat:
    print(f"单次时延 中位{statistics.median(lat):.1f}s 均{statistics.mean(lat):.1f}s max{max(lat):.1f}s")
    print(f"外推: 25A x 24步(600次) = {total*4/60:.1f} 分钟; token≈600x900=54万 ≈ ¥{600*900*2/1e6*0.5:.1f}(混合)")
if errs: print("首错:", errs[0])

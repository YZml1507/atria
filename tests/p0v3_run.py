"""令牌桶限速器 + P0v3。
修复 P0v2 的问题: 裸线程池打到 65.9 RPM 超过 52.5 限额, 17/72 步 429。
方案: 在 chat() 外面包一个全局令牌桶, 速率 48 RPM(留余量), 桶容量 8。
"""
import json, urllib.request, time, subprocess, os, re, threading, queue
from concurrent.futures import ThreadPoolExecutor

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"


class TokenBucket:
    """速率 rate 个/秒, 桶容量 cap。 acquire() 阻塞到有令牌为止。"""
    def __init__(self, rate, cap):
        self.rate = rate
        self.cap = cap
        self.tokens = cap
        self.ts = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self):
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.cap, self.tokens + (now - self.ts) * self.rate)
            self.ts = now
            if self.tokens >= 1:
                self.tokens -= 1
                return 0.0
            wait = (1 - self.tokens) / self.rate
            self.tokens = 0
            return wait


# 48 RPM = 0.8 个/秒, 桶容量 8 允许小突发
bucket = TokenBucket(rate=48/60.0, cap=8)
stats = {"calls": 0, "ok": 0, "r429": 0, "other_err": 0, "wait_total": 0.0}
lock = threading.Lock()


def chat(messages, max_tokens=2048, temperature=0, retries=4):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature})
    for attempt in range(retries):
        wait = bucket.acquire()
        if wait > 0:
            with lock:
                stats["wait_total"] += wait
            time.sleep(wait)
        req = urllib.request.Request(
            URL, data=body.encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            with lock:
                stats["calls"] += 1
                stats["ok"] += 1
            return d["choices"][0]["message"].get("content")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                with lock:
                    stats["r429"] += 1
                if attempt < retries - 1:
                    time.sleep(min(60, 2 ** attempt * 2))  # 2,4,8s
                    continue
            with lock:
                stats["calls"] += 1
                stats["other_err"] += 1
            return None
        except Exception:
            with lock:
                stats["calls"] += 1
                stats["other_err"] += 1
            return None
    return None


world = json.load(open("/home/ubuntu/p0_world.json"))
personas = json.load(open("/home/ubuntu/p0_personas.json"))
SEC = list(world["sectors"].keys())


def extract(raw, valid):
    if not raw:
        return None
    try:
        d = json.loads(raw)
        for k in valid:
            if d.get(k):
                return d[k]
    except Exception:
        pass
    for pat in [r"\*\*Answer[:：]\s*([^*\n{]+)", r"\{([^}\n]+)\}"]:
        m = re.search(pat, raw)
        if m:
            v = m.group(1).strip().rstrip("}").strip()
            if v in valid:
                return v
    for v in valid:
        if v in raw:
            return v
    return None


def merged_prompt(p, act):
    cur_sec = p["loc"].split(":")[0]
    cur_arenas = list(world["sectors"][cur_sec]["arenas"].keys())
    return f"""你是游戏里的角色 {p['name']}。当前要执行: {act}

当前在 {cur_sec}（子区域: {', '.join(cur_arenas)}）。
可去地点: {', '.join(SEC)}。

输出一个 JSON, 字段如下, 只能从给定候选里选, 不要任何其他文字:
{{
  "sector": "从 {', '.join(SEC)} 选一个",
  "arena": "从该地点的子区域选一个",
  "object": "从该子区域的物品选一个",
  "emoji": "1-3 个 emoji 表示动作",
  "action": "{act}"
}}

地点-子区域-物品参照:
{json.dumps({s: {a: v['objects'] for a, v in world['sectors'][s]['arenas'].items()} for s in SEC}, ensure_ascii=False)}
"""


def step_one(p, step):
    act = p["daily_plan_req"].split("，")[0] if step < 12 else "休息"
    raw = chat([{"role": "user", "content": merged_prompt(p, act)}])
    if raw is None:
        return p["name"], step, False, "LLM 失败"
    val = None
    try:
        val = json.loads(raw)
    except Exception:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                val = json.loads(m.group(0))
            except Exception:
                pass
    okfields = {k: v for k, v in (val or {}).items() if isinstance(v, str)}
    sec = okfields.get("sector") or extract(raw, SEC)
    if sec not in SEC:
        sec = p["loc"].split(":")[0]
        okfields["sector"] = sec
    arenas = list(world["sectors"][sec]["arenas"].keys())
    arena = okfields.get("arena") or extract(raw, arenas)
    if arena not in arenas:
        arena = arenas[0]
        okfields["arena"] = arena
    p["loc"] = f"{sec}:{arena}"
    return p["name"], step, True, raw[:80]


STEPS = 24
for p in personas:
    p["loc"] = p["living_area"]
t0 = time.time()
results = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for step in range(STEPS):
        futs = [ex.submit(step_one, p, step) for p in personas]
        for f in futs:
            results.append(f.result())
tot = time.time() - t0

ok = sum(1 for r in results if r[2])
print(f"== P0v3 结果(令牌桶) ==")
print(f"步数 {STEPS} x {len(personas)} 人 = {len(results)}")
print(f"成功 {ok} / {len(results)}")
print(f"stats: {stats}")
print(f"墙钟 {tot:.0f}s -> 等效 RPM {stats['calls']/tot*60:.1f}(含限速等待)")

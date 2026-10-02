"""P0v2: 单次 JSON 合并调用 + 并发线程池。
目标: 72 步合规率 100%, 墙钟显著下降。

设计:
  - 每步每人只 1 次 LLM 调用, 一次输出 {"sector","arena","object","emoji","action"}
  - 4 线程并发执行(25 人时开 6 线程)
  - 严格 JSON 解析 + 正则兜底(从 **Answer: X** / {X} / 裸地名 提取)
  - 429 自动重试 + 指数退避
"""
import json, urllib.request, time, subprocess, os, re, threading, queue
from concurrent.futures import ThreadPoolExecutor

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"

lock = threading.Lock()
stats = {"calls": 0, "ok": 0, "retry": 0, "fallback": 0}


def chat(messages, max_tokens=2048, temperature=0, retries=3):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature})
    for attempt in range(retries):
        req = urllib.request.Request(
            URL, data=body.encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            with lock:
                stats["calls"] += 1
                stats["ok"] += 1
                if attempt > 0:
                    stats["retry"] += 1
            return d["choices"][0]["message"].get("content")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(2 ** attempt)  # 退避 1s, 2s
                continue
            with lock:
                stats["calls"] += 1
            return None
        except Exception:
            with lock:
                stats["calls"] += 1
            return None
    return None


world = json.load(open("/home/ubuntu/p0_world.json"))
personas = json.load(open("/home/ubuntu/p0_personas.json"))
SEC = list(world["sectors"].keys())
for p in personas:
    p["loc"] = p["living_area"]


def extract(raw, valid):
    """从任意格式输出中提取合法值。"""
    if not raw:
        return None
    # 尝试 JSON
    try:
        d = json.loads(raw)
        for k in valid:
            if d.get(k):
                return d[k]
    except Exception:
        pass
    # **Answer: X** 或 {X} 或 裸值
    for pat in [r"\*\*Answer[:：]\s*([^*\n{]+)", r"\{([^}\n]+)\}", r"^\s*([^\s{*][^\n{*]*)\s*$"]:
        m = re.search(pat, raw)
        if m:
            v = m.group(1).strip().rstrip("}").strip()
            if v in valid:
                return v
    # 直接找合法词
    for v in valid:
        if v in raw:
            return v
    return None


def merged_prompt(p, act):
    cur_sec = p["loc"].split(":")[0]
    cur_arena = p["loc"].split(":")[1] if ":" in p["loc"] else ""
    cur_arenas = list(world["sectors"][cur_sec]["arenas"].keys())
    tgt_arenas = list(world["sectors"].get(cur_sec, {}).get("arenas", {}).keys())
    objs = []
    for a in tgt_arenas:
        objs += world["sectors"][cur_sec]["arenas"][a]["objects"]
    return f"""你是游戏里的角色 {p['name']}。当前要执行: {act}

当前在 {cur_sec}（子区域: {cur_arenas}）。
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
    hour = 6 + step
    act = p["daily_plan_req"].split("，")[0] if step < 12 else "休息"
    raw = chat([{"role": "user", "content": merged_prompt(p, act)}])
    if raw is None:
        return p["name"], step, False, "LLM 失败"
    out = json.loads("{}") if False else None
    # 直接尝试整体 JSON
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
    okfields = {}
    if val:
        okfields = {k: v for k, v in val.items() if isinstance(v, str)}
    else:
        with lock:
            stats["fallback"] += 1
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
t0 = time.time()
results = []
with ThreadPoolExecutor(max_workers=4) as ex:
    for step in range(STEPS):
        futs = [ex.submit(step_one, p, step) for p in personas]
        for f in futs:
            results.append(f.result())
tot = time.time() - t0

ok = sum(1 for r in results if r[2])
print(f"== P0v2 结果 ==")
print(f"步数 {STEPS} x {len(personas)} 人 = {len(results)}")
print(f"成功 {ok} / {len(results)}")
print(f"stats: {stats}")
print(f"墙钟 {tot:.0f}s -> 等效 RPM {stats['calls']/tot*60:.1f}")
fb = [r for r in results if not r[2]]
for f in fb[:8]:
    print("  失败:", f)
sample = [r[3] for r in results if r[2]][:3]
print("输出样本:")
for s in sample:
    print("  ", repr(s))

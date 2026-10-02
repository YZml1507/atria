"""P0 机制冒烟: 3 人 / 1 游戏日 / 3 地点小图。
模拟 Smallville 的每步决策链: sector→arena→object→emoji→triple,
但不引入它的全部代码, 自己写最小世界模拟。
通过标准: 144 步(24 步/日 x 6 ? 不——这里 1 日 = 24 步粗粒度) 零崩溃 + 地址合法 + 完成一轮对话。

注意 sec_per_step=60s -> 1 日 = 1440/60 = 24 步。
3 人 x 24 步 x 每步 3-4 次调用。
"""
import json, urllib.request, time, subprocess, os, re, sys

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"

call_log = []  # (step, who, kind, tokens, ok)


def chat(messages, max_tokens=2048, temperature=0):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature})
    req = urllib.request.Request(
        URL, data=body.encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.loads(r.read())
    msg = d["choices"][0]["message"]
    return msg.get("content"), d["usage"], time.time() - t


world = json.load(open("/home/ubuntu/p0_world.json"))
personas = json.load(open("/home/ubuntu/p0_personas.json"))
SEC = list(world["sectors"].keys())


def sector_prompt(p, act):
    cur_sec = p["loc"].split(":")[0]
    cur_arenas = list(world["sectors"][cur_sec]["arenas"].keys())
    return f"""Task -- choose an appropriate area from the area options for a task at hand.

{p['name']} lives in {p['living_area'].split(':')[0]} that has {p['living_area'].split(':')[1]}.
{p['name']} is currently in {cur_sec} that has {', '.join(cur_arenas)}.
Area options: {', '.join(SEC)}.
* Stay in the current area if the activity can be done there. Only go out if the activity needs to take place in another place.
* Must be one of the "Area options," verbatim.
{p['name']} is {act}. {p['name']} should go to the following area: {{"""


STEPS_PER_DAY = 24
t_start = time.time()
errors = []
steps_ok = 0

# 简单的逐步循环: 每个 agent 每 step 生成一个动作
for step in range(STEPS_PER_DAY):
    for p in personas:
        if "loc" not in p:
            p["loc"] = p["living_area"]
        # 1) 生成动作描述(简化: 从每天计划里取)
        hour = 6 + step  # 6am 起, 每 step = 1 小时
        act = p["daily_plan_req"].split("，")[0] if step < 12 else "休息"
        # 2) sector 选择
        try:
            c, u, dt = chat([{"role": "user", "content": sector_prompt(p, act)}])
            sec = (c or "").strip().rstrip("}").strip()
            if sec not in SEC:
                errors.append(("sector", step, p["name"], repr(c)))
                sec = p["loc"].split(":")[0]
            call_log.append((step, p["name"], "sector", u["completion_tokens"], True))
            # 3) arena 选择
            arenas = list(world["sectors"][sec]["arenas"].keys())
            ar_prompt = f"""{p['name']} is in {p['loc'].split(':')[1] if ':' in p['loc'] else arenas[0]} in {p['loc'].split(':')[0]}.
{p['name']} is going to {sec} that has the following areas: {{{', '.join(arenas)}}}
Stay in the current area if the activity can be done there. Never go into other people's rooms unless necessary.
For {act}, {p['name']} should go to the following area in {sec}: {{"""
            c2, u2, _ = chat([{"role": "user", "content": ar_prompt}])
            arena = (c2 or "").strip().rstrip("}").strip()
            if arena not in arenas:
                errors.append(("arena", step, p["name"], repr(c2)))
                arena = arenas[0]
            call_log.append((step, p["name"], "arena", u2["completion_tokens"], True))
            # 4) emoji
            em_prompt = f"""Convert an action description to an emoji (important: use three or less emojis).

Action description: waking up and starting her morning routine (taking a shower)
Emoji: 🛁🧖‍♀️
Action description: having breakfast (making coffee)
Emoji: ☕️🥐
Action description: {act}
Emoji:"""
            c3, u3, _ = chat([{"role": "user", "content": em_prompt}])
            call_log.append((step, p["name"], "emoji", u3["completion_tokens"], True))
            p["loc"] = f"{sec}:{arena}"
            steps_ok += 1
        except Exception as e:
            errors.append(("exception", step, p["name"], str(e)[:100]))
            call_log.append((step, p["name"], "error", 0, False))

tot = time.time() - t_start
n_ok = sum(1 for x in call_log if x[4])
toks = sum(x[3] for x in call_log)
print(f"== P0 结果 ==")
print(f"步数 {STEPS_PER_DAY} x {len(personas)} 人 = {STEPS_PER_DAY*len(personas)} 步")
print(f"成功 {steps_ok} / {STEPS_PER_DAY*len(personas)}")
print(f"LLM 调用 {len(call_log)} 次, 成功 {n_ok}, 总 completion token {toks}")
print(f"墙钟 {tot:.0f}s -> 等效 RPM {len(call_log)/tot*60:.1f}")
print(f"错误 {len(errors)}")
for e in errors[:10]:
    print("  ", e)

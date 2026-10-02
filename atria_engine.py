"""Atria 正式引擎 — 主循环
25 人 x 14 天。
架构(全部由实测数据决定):
  - sec_per_step=30s -> 48 步/日; 每日 3 个决策步 + 1 个社交步(非每步调用)
  - 单次 JSON 合并调用出 {place, activity, emoji, say} (P0v2/v3 实测格式 0 失败)
  - 令牌桶 40 RPM + 指数退避 (P0v3 实测 72/72 零外泄)
  - 记忆: idle 不入流 + 5 分钟去重 (方案 6.7 必需项); 对话记忆 "X 告诉我: ..."
  - 情景 A: 第 2 天引爆(错领发生, 3 目击者存碎片), 不写结局
输出: 每日 JSONL 事件流 + 记忆文件, 供 manim 渲染
"""
import json, urllib.request, time, subprocess, os, re, threading, random, sys
from collections import deque, defaultdict
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/home/ubuntu")
from atria_world import World

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"

DAYS = 14  # 默认 14 天; main() 会按命令行参数覆盖
STEPS_PER_DAY = 48            # sec_per_step=30s
DECISION_STEPS = [10, 22, 34]  # 早/中/晚各 1 次决策调用
SOCIAL_STEP = 44              # 傍晚社交(对话)

# ---------- 令牌桶 40 RPM (P0v3 实测) ----------
lock = threading.Lock()
bucket = {"tok": 40.0, "last": time.time()}
RATE = 40 / 60.0
CAP = 40.0
stats = {"calls": 0, "ok": 0, "r429": 0, "err": 0, "fallback": 0}


def take(n=1):
    with lock:
        while True:
            now = time.time()
            bucket["tok"] = min(CAP, bucket["tok"] + (now - bucket["last"]) * RATE)
            bucket["last"] = now
            if bucket["tok"] >= n:
                bucket["tok"] -= n
                return
            need = n - bucket["tok"]
            time.sleep(need / RATE + 0.05)


def chat(messages, max_tokens=1024, tries=4):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": 0})
    for a in range(tries):
        take()
        stats["calls"] += 1
        req = urllib.request.Request(
            URL, data=body.encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            c = d["choices"][0]["message"].get("content")
            if c:
                stats["ok"] += 1
                return c
        except urllib.error.HTTPError as e:
            if e.code == 429:
                stats["r429"] += 1
                time.sleep(2 ** a + 1)
            else:
                stats["err"] += 1
                return None
        except Exception:
            stats["err"] += 1
            time.sleep(2 ** a)
    return None


# ---------- 记忆(方案 6.7: idle 不入流 + 去重) ----------
class Memory:
    def __init__(self):
        self.records = []              # (day, step, kind, text)
        self._recent = deque(maxlen=8)  # 5 分钟去重窗(约 10 步)

    def add(self, day, step, kind, text):
        # 去重: 8 步内相同文本不入
        if text in self._recent:
            return False
        self._recent.append(text)
        self.records.append((day, step, kind, text))
        return True

    def narrative(self, limit=None):
        recs = self.records if limit is None else self.records[-limit:]
        return "\n".join(f"[第{d}天{s}步] {t}" for d, s, k, t in recs)


class Agent:
    def __init__(self, scratch, world):
        self.s = scratch
        self.name = scratch["name"]
        self.mem = Memory()
        self.pos = world.spawn.get(scratch["living_area"], (20, 20))
        self.home = scratch["living_area"]
        # 种子记忆: 人设 + 钩子 + 日常基线
        self.mem.add(1, 0, "设定", f"我是{self.name}。{scratch['learned']}")
        if scratch["currently"]:
            self.mem.add(1, 0, "心事", scratch["currently"])
        self.mem.add(1, 0, "作息", scratch["daily_plan"])

    def __repr__(self):
        return f"<{self.name}@{self.pos}>"


# ---------- LLM 决策: 单次 JSON 合并调用 ----------
JSON_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)
BARE_RE = re.compile(r"(\{[^{}]*\"place\"[^{}]*\})", re.S)


def decide(agent, world, day, step, others_here):
    place_now = world.place_of(*agent.pos)
    # 候选地点 = 全部公共地点 + 自己家 (方案 3.2: 12 地点 + 20 住宅)
    candidates = [n for n in world.places if not n.endswith("宅") or n == agent.home or n in ("安镇老宅","周家小院","赵宅","李家","孙氏裁缝铺")]
    cand_str = "、".join(candidates[:20])
    items_here = world.items_near(place_now)
    mem = agent.mem.narrative(limit=40)
    others = "、".join(o.name for o in others_here) if others_here else "无人"

    prompt = f"""你是 {agent.name}，{agent.s['learned'][:60]}
今天是在这个镇上生活的第 {day} 天。
你现在的位置: {place_now}。身边: {others}。

你最近的经历:
{mem}

请决定你接下来去哪里、做什么。从以下地点中选: {cand_str}
可用物品(当前位置): {items_here if items_here else '无'}

只输出一个 JSON 对象，格式:
{{"place": "地点名", "activity": "你在那里做什么(15字内)", "emoji": "一个表情", "say": "你脱口而出的一句话(20字内,没有就写'无')"}}
不要输出其他任何内容。"""
    raw = chat([{"role": "user", "content": prompt}], max_tokens=600)
    if not raw:
        stats["fallback"] += 1
        return None
    # 三级兜底抽取 (方案 5.4)
    m = JSON_RE.search(raw) or BARE_RE.search(raw)
    if m:
        try:
            d = json.loads(m.group(1))
            return d
        except Exception:
            pass
    try:
        d = json.loads(raw)
        return d
    except Exception:
        stats["fallback"] += 1
        return None


# ---------- 对话(复用 P2v2 验证机制) ----------
def converse(a, b, day, step):
    """a 主动找 b 聊一句。a 从全量记忆生成转述, b 记入。"""
    mem = a.mem.narrative()
    prompt = f"""你是 {a.name}。这是你从第1天到第{day}天的全部记忆:

{mem}

你现在遇到 {b.name}({b.s['occupation']}), 闲聊几句。
如果你清楚记得镇上那件"邮局包裹被错领"的事, 就把它告诉 {b.name}, 讲出你记忆里最详细的情形。
只输出你当面说的话(不超过60字), 不要加引号和解释。"""
    utt = chat([{"role": "user", "content": prompt}], max_tokens=300)
    if utt:
        b.mem.add(day, step, "对话", f"{a.name} 告诉我: {utt.strip()}")
        # 双向: b 回一句, a 也记
        r2 = chat([{"role": "user", "content":
            f"你是 {b.name}。{a.name} 刚对你说: \"{utt.strip()}\"\n你顺口回一句(20字内)。只输出那句话。"}], max_tokens=200)
        if r2:
            a.mem.add(day, step, "对话", f"{b.name} 回我说: {r2.strip()}")
        return utt.strip()
    return None


# ---------- 移动(简单: 朝目标地点中心走 3 格) ----------
def move_toward(agent, world, target_place):
    cells = world.places.get(target_place, {}).get("cells")
    if not cells:
        return
    tx, ty = min(cells, key=lambda c: abs(c[0]-agent.pos[0])+abs(c[1]-agent.pos[1]))
    dx = (tx - agent.pos[0])
    dy = (ty - agent.pos[1])
    for _ in range(3):
        if dx == 0 and dy == 0:
            break
        if abs(dx) >= abs(dy) and dx != 0:
            nx = agent.pos[0] + (1 if dx > 0 else -1)
            if world.is_walkable(nx, agent.pos[1]):
                agent.pos = (nx, agent.pos[1]); dx = tx - nx
            elif dy != 0:
                ny = agent.pos[1] + (1 if dy > 0 else -1)
                if world.is_walkable(agent.pos[0], ny):
                    agent.pos = (agent.pos[0], ny); dy = ty - ny
        elif dy != 0:
            ny = agent.pos[1] + (1 if dy > 0 else -1)
            if world.is_walkable(agent.pos[0], ny):
                agent.pos = (agent.pos[0], ny); dy = ty - ny
            elif dx != 0:
                nx = agent.pos[0] + (1 if dx > 0 else -1)
                if world.is_walkable(nx, agent.pos[1]):
                    agent.pos = (nx, agent.pos[1]); dx = tx - nx


# ---------- 主循环 ----------
def main():
    DAYS = 14
    start_day = 1
    if len(sys.argv) > 1 and sys.argv[1] == "--start":
        start_day = int(sys.argv[2])
        if len(sys.argv) > 3:
            DAYS = int(sys.argv[3])
    elif len(sys.argv) > 1 and sys.argv[1].isdigit():
        DAYS = int(sys.argv[1])
    rng = random.Random(20261014)
    world = World()
    scratches = json.load(open("/home/ubuntu/atria_personas.json"))
    agents = [Agent(s, world) for s in scratches]
    # 断点续跑: 载入前一天的记忆
    if start_day > 1:
        ck = f"/home/ubuntu/atria_run/mem_day{start_day-1:02d}.json"
        if os.path.exists(ck):
            saved = json.load(open(ck))
            for a in agents:
                for rec in saved.get(a.name, []):
                    a.mem.records.append(tuple(rec))
            print(f"从第{start_day}天续跑: 已载入 {ck}")
    print(f"引擎启动: {len(agents)} 人 x {DAYS} 天(从第{start_day}天起), {STEPS_PER_DAY} 步/日, 决策步 {DECISION_STEPS}, 社交步 {SOCIAL_STEP}", flush=True)

    outdir = "/home/ubuntu/atria_run"
    os.makedirs(outdir, exist_ok=True)
    events = []

    t0 = time.time()
    for day in range(start_day, DAYS + 1):
        day_events = []
        for step in range(STEPS_PER_DAY):
            is_decision = step in DECISION_STEPS
            is_social = step == SOCIAL_STEP
            if not (is_decision or is_social):
                continue  # 其余步只移动(零调用)

            # 并行决策(25 人独立)
            if is_decision:
                def do_decide(a):
                    here = [o for o in agents if o is not a and o.pos == a.pos]
                    d = decide(a, world, day, step, here)
                    if d:
                        target = d.get("place") or world.place_of(*a.pos)
                        move_toward(a, world, target)
                        place_now = world.place_of(*a.pos)
                        ev = {"day": day, "step": step, "agent": a.name,
                              "place": place_now, "activity": d.get("activity", ""),
                              "emoji": d.get("emoji", ""), "say": d.get("say", "")}
                        a.mem.add(day, step, "行动", f"在{place_now}{d.get('activity','')}; 说: {d.get('say','')}")
                        return ev
                    return None
                with ThreadPoolExecutor(max_workers=6) as ex:
                    evs = list(ex.map(do_decide, agents))
                for e in evs:
                    if e:
                        day_events.append(e)

            # 社交: 随机配对对话
            if is_social:
                order = agents[:]
                rng.shuffle(order)
                pairs = [(order[i], order[i+1]) for i in range(0, len(order)-1, 2)]
                for a, b in pairs:
                    utt = converse(a, b, day, step)
                    if utt:
                        day_events.append({"day": day, "step": step, "agent": a.name,
                                           "place": world.place_of(*a.pos), "activity": "与"+b.name+"交谈",
                                           "emoji": "💬", "say": utt[:40]})
                # 社交后各回各家
                for a in agents:
                    move_toward(a, world, a.home)

        # 每日存档 + 记忆 checkpoint
        events.extend(day_events)
        with open(f"{outdir}/day{day:02d}.jsonl", "w") as f:
            for e in day_events:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
        mem_ck = {a.name: [list(r) for r in a.mem.records] for a in agents}
        json.dump(mem_ck, open(f"{outdir}/mem_day{day:02d}.json", "w"), ensure_ascii=False)
        memsize = {a.name: len(a.mem.records) for a in agents}
        top3 = sorted(memsize.items(), key=lambda x: -x[1])[:3]
        print(f"第{day}天完成: {len(day_events)} 事件, 累计墙钟 {time.time()-t0:.0f}s, LLM {stats}"
              f" | 记忆最多: {top3}", flush=True)

    # 记忆存档
    mem_out = {a.name: a.mem.records for a in agents}
    json.dump(mem_out, open(f"{outdir}/memories.json", "w"), ensure_ascii=False, indent=1)
    json.dump(events, open(f"{outdir}/events.json", "w"), ensure_ascii=False, indent=1)
    print(f"\n=== 完成: {len(events)} 总事件, 墙钟 {time.time()-t0:.0f}s ===")
    print(f"stats: {stats}")
    print(f"记忆条数: 均值 {sum(len(a.mem.records) for a in agents)/len(agents):.0f}, "
          f"max {max(len(a.mem.records) for a in agents)}")


if __name__ == "__main__":
    main()

"""P2v2 传播动力学: 修复 P2 的两个 bug。
bug1: knows 判断宽松("不知道邮局"也命中) -> 改严格(必须含 纸箱/包裹 + 动词)
bug2: 知情者被 prompt 引导说"我不知道" -> 知情者主动谈论细节
另: 每天两轮配对(早/午), 老王第3天固定先遇周老师
指标: 真实知情人数扩散, 颜色变异, 最终判分
"""
import json, urllib.request, time, subprocess, os, re, threading, random
from concurrent.futures import ThreadPoolExecutor

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"

lock = threading.Lock()
bucket = {"tok": 40.0, "last": time.time()}
RATE = 40 / 60.0
CAP = 40.0


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


def chat(messages, max_tokens=768, tries=4):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": 0})
    for a in range(tries):
        take()
        req = urllib.request.Request(
            URL, data=body.encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                d = json.loads(r.read())
            c = d["choices"][0]["message"].get("content")
            if c:
                return c
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 ** a + 1)
            else:
                return None
        except Exception:
            time.sleep(2 ** a)
    return None


AGENTS = ["老王", "周老师", "赵医生", "孙裁缝", "李大姐", "钱老板", "吴怀疑", "郑 neutral"]
ROLES = {
    "老王": "唯一目击者(第2天亲眼看见)",
    "周老师": "转述者(爱聊天)",
    "赵医生": "转述者(诊所闲聊)",
    "孙裁缝": "好奇心放大器(爱打听)",
    "李大姐": "好奇心放大器(传话快)",
    "钱老板": "好奇心放大器(消息灵通)",
    "吴怀疑": "怀疑论者(不信传出的话)",
    "郑 neutral": "中性(不主动传播)",
}
EVENT = "邮局门口取走旧纸箱的那个人"
TRUTH = "那人穿一件灰色粗呢外套, 抱着纸箱朝镇子东头的五金店方向走了"

rng = random.Random(42)
memory = {a: [] for a in AGENTS}
knows = {a: False for a in AGENTS}

memory["老王"].append((2, f"老王在邮局门口晒太阳时看见: 一个人从邮局柜台取走一只用胶带缠了好几道的旧纸箱, {TRUTH}。"))
knows["老王"] = True

pool = json.load(open("/home/ubuntu/p1v3_noise.json"))
for a in AGENTS:
    p = [l for l in pool.get(a, pool["老王"]) if not any(w in l for w in ["灰", "外套", "纸箱", "东头", "黑色", "蓝色"])][:80]
    for day in range(1, 6):
        for k in range(16):
            memory[a].append((day, p[(day * 16 + k) % len(p)]))


def real_knows(utt):
    """严格判断: 转述含 纸箱/包裹 + 取/拿/搬 动词才算传播成功"""
    if not utt:
        return False
    has_obj = any(w in utt for w in ["纸箱", "包裹"])
    has_verb = any(w in utt for w in ["取", "拿", "搬", "抱"])
    return has_obj and has_verb


def gen_utterance(speaker, listener, day):
    mem = "\n".join(f"[第{d}天] {t}" for d, t in memory[speaker])
    if knows[speaker]:
        prompt = f"""你是 {speaker}({ROLES[speaker]})。以下是你从第1天到第{day}天的全部记忆:

{mem}

今天(第{day}天)你遇到 {listener}({ROLES[listener]})。你清楚记得镇上那件事: "{EVENT}"。
闲聊时你把这件事告诉 {listener}, 讲出你记忆里最详细的情形(若记得来源就提到是谁告诉你的或是否亲眼所见)。
只输出你当面说的那一句话(不超过80字), 不要加引号和解释。"""
    else:
        prompt = f"""你是 {speaker}({ROLES[speaker]})。以下是你从第1天到第{day}天的全部记忆:

{mem}

今天(第{day}天)你遇到 {listener}({ROLES[listener]}) 闲聊。你的记忆里没有 "{EVENT}" 的任何信息。
只输出你当面说的那一句话(不超过60字), 不要加引号和解释。"""
    return chat([{"role": "user", "content": prompt}], max_tokens=300)


def final_quiz(a):
    mem = "\n".join(f"[第{d}天] {t}" for d, t in memory[a])
    prompt = f"""以下是 {a} 从第1天到第5天的全部记忆:

{mem}

现在有人问你: "{EVENT}, 他穿什么颜色的外套? 一句话回答。
注意: 记忆里若有互相矛盾的说法, 请分辨哪个是更可信的一手描述。"""
    return chat([{"role": "user", "content": prompt}], max_tokens=300)


def judge(ans):
    if not ans:
        return -1, []
    marks = []
    if "灰" in ans:
        marks.append("答灰")
    if any(w in ans for w in ["矛盾", "但", "而", "转述", "听说", "告诉", "亲眼"]):
        marks.append("指出来源差异")
    if "灰" in ans and any(w in ans for w in ["亲眼", "原始", "亲眼所见", "转述", "告诉"]):
        marks.append("分辨一手")
    score = 0
    if "灰" in ans:
        score = 1
    if len(marks) >= 2 and "答灰" in marks:
        score = 2
    if len(marks) >= 3:
        score = 3
    return score, marks


stats = {"calls": 0}
t0 = time.time()
spread_log = []

# 第3天: 老王固定先遇周老师(种子传播)
utt = gen_utterance("老王", "周老师", 3)
stats["calls"] += 1
if utt:
    memory["周老师"].append((3, f"老王 告诉我: {utt.strip()}"))
    if real_knows(utt):
        knows["周老师"] = True
print(f"第3天 种子: 老王->周老师: {(utt or '(失败)')[:60]}")

for day in range(3, 6):
    for rnd in range(2):  # 每天两轮
        order = [a for a in AGENTS]  # 全员参与(含老王)
        rng.shuffle(order)
        pairs = [(order[i], order[i + 1]) for i in range(0, len(order), 2)]
        for sp, li in pairs:
            if sp == "老王" and day == 3 and rnd == 0 and li == "周老师":
                continue  # 已单独传过
            utt = gen_utterance(sp, li, day)
            stats["calls"] += 1
            if utt:
                memory[li].append((day, f"{sp} 告诉我: {utt.strip()}"))
                if not knows[li] and real_knows(utt):
                    knows[li] = True
    n = sum(knows.values())
    spread_log.append({"day": day, "knows": n, "who": [a for a in AGENTS if knows[a]]})
    print(f"第{day}天结束: 真知情 {n}/8")

print("\n=== 第5天全员考核 ===")
with ThreadPoolExecutor(max_workers=2) as ex:
    answers = dict(zip(AGENTS, ex.map(final_quiz, AGENTS)))

rows = []
for a in AGENTS:
    s, m = judge(answers[a])
    rows.append((a, ROLES[a], answers[a], s, m, knows[a]))

for a, role, ans, s, m, k in rows:
    print(f"{a}({role[:6]}): {'知情' if k else '不知'} 分={s} {m}")
    print(f"    {(ans or '(无)')[:110]}")

ok = [r for r in rows if r[3] >= 1]
hi = [r for r in rows if r[3] >= 2]
print(f"\n墙钟 {time.time()-t0:.0f}s  LLM调用 {stats['calls']}")
print(f"传播: {sum(knows.values())}/8 知情, {len(ok)}/8 答对, {len(hi)}/8 带判据")
# 变异检测: 非"灰"颜色出现次数
colors = {"黑": 0, "蓝": 0, "灰": 0}
for a, _, ans, _, _, _ in rows:
    if ans:
        for c in colors:
            if c in ans:
                colors[c] += 1
print(f"最终答案颜色分布: {colors}")
verd = "传播+变异可观测" if len(ok) >= 4 else ("传播部分成功" if len(ok) >= 2 else "传播失败")
print(f">>> 结论: {verd}")

out = {"spread": spread_log, "rows": [{"a": r[0], "role": r[1], "ans": r[2], "score": r[3], "marks": r[4], "knows": r[5]} for r in rows],
       "stats": stats, "colors": colors, "verdict": verd}
json.dump(out, open("/home/ubuntu/p2v2_result.json", "w"), ensure_ascii=False, indent=1, default=str)
print("结果已存 /home/ubuntu/p2v2_result.json")

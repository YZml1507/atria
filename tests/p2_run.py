"""P2 传播动力学: 8 人 x 5 日。
核心问题: 信息能否通过对话在镇上传播? 传播中是否变异?
设计:
  - 8 agent: 老王(唯一目击者), 周老师, 赵医生, 3 好奇心放大器, 1 怀疑论者, 1 中性
  - 每天随机配对, 每对对话 1 次(1 次 LLM: 说话者从全量记忆生成转述句)
  - 听者把 "X 告诉我: <转述>" 记入记忆
  - 第5天全员考核 "邮局那个人穿什么颜色", 判据完整性判分
指标: 每天知情人数(扩散曲线), 颜色变异, 最终判分分布
"""
import json, urllib.request, time, subprocess, os, re, threading, random
from concurrent.futures import ThreadPoolExecutor

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"

# ---------- 令牌桶(40 RPM) ----------
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


# ---------- 8 个 agent ----------
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

rng = random.Random(42)
memory = {a: [] for a in AGENTS}          # (day, text)
knows = {a: False for a in AGENTS}        # 是否听说过包裹事件

# 老王第 2 天的一手记忆
memory["老王"].append((2, "老王在邮局门口晒太阳时看见: 一个人从邮局柜台取走一只用胶带缠了好几道的旧纸箱, 那人穿一件灰色粗呢外套, 抱着纸箱朝镇子东头的五金店方向走了。"))
knows["老王"] = True

# 每个 agent 的日常噪声(80 条, 从 P1v3 池子)
pool = json.load(open("/home/ubuntu/p1v3_noise.json"))
for a in AGENTS:
    p = [l for l in pool.get(a, pool["老王"]) if not any(w in l for w in ["灰", "外套", "纸箱", "东头", "黑色", "蓝色"])][:80]
    for day in range(1, 6):
        for k in range(16):
            memory[a].append((day, p[(day * 16 + k) % len(p)]))

EVENT = "邮局门口取走旧纸箱的那个人"


def gen_utterance(speaker, listener, day):
    """说话者从全量记忆生成一句转述(只说 1 句, 模拟闲聊)。"""
    mem = "\n".join(f"[第{d}天] {t}" for d, t in memory[speaker])
    prompt = f"""你是 {speaker}({ROLES[speaker]})。以下是你从第1天到第{day}天的全部记忆:

{mem}

今天(第{day}天)你遇到了 {listener}({ROLES[listener]}), 闲聊中你提到了最近镇上的事:
"{EVENT}" —— 如果你知道细节就告诉他, 不知道就说你不知道。
只输出你当面说的那一句话(不超过60字), 不要加引号和其他解释。"""
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
    if any(w in ans for w in ["矛盾", "但", "而", "转述", "听说", "告诉"]):
        marks.append("指出来源差异")
    if "灰" in ans and any(w in ans for w in ["亲眼", "原始", "亲眼所见", "转述", "告诉"]):
        marks.append("分辨一手")
    score = 0
    if "灰" in ans:
        score = 1
    if marks and marks[0] == "答灰" and len(marks) >= 2:
        score = 2
    if len(marks) >= 3:
        score = 3
    return score, marks


# ---------- 5 天循环 ----------
stats = {"calls": 0, "conv": 0}
t0 = time.time()
spread_log = []

for day in range(3, 6):  # 第3-5天传播(第2天目击, 第1天纯噪声)
    # 随机配对,每人每天说 1 次
    order = AGENTS[:]
    rng.shuffle(order)
    pairs = [(order[i], order[i + 1]) for i in range(0, len(order), 2)]
    for sp, li in pairs:
        utt = gen_utterance(sp, li, day)
        stats["calls"] += 1
        stats["conv"] += 1
        if utt:
            memory[li].append((day, f"{sp} 告诉我: {utt.strip()}"))
            if not knows[li] and any(w in utt for w in ["纸箱", "包裹", "邮局"]):
                knows[li] = True
    n = sum(knows.values())
    spread_log.append({"day": day, "knows": n, "who": [a for a in AGENTS if knows[a]]})
    print(f"第{day}天结束: 知情 {n}/8")

# ---------- 第5天考核 ----------
print("\n=== 第5天全员考核 ===")
with ThreadPoolExecutor(max_workers=2) as ex:
    answers = dict(zip(AGENTS, ex.map(final_quiz, AGENTS)))

rows = []
for a in AGENTS:
    s, m = judge(answers[a])
    rows.append((a, ROLES[a], answers[a], s, m, knows[a]))

for a, role, ans, s, m, k in rows:
    print(f"{a}({role[:4]}): {'知情' if k else '不知'} 分={s} {m}")
    print(f"    {ans[:100] if ans else '(无)'}")

ok = [r for r in rows if r[3] >= 1]
hi = [r for r in rows if r[3] >= 2]
print(f"\n墙钟 {time.time()-t0:.0f}s  LLM调用 {stats['calls']}")
print(f"传播: {sum(knows.values())}/8 知情, {len(ok)}/8 答对, {len(hi)}/8 带判据")
verd = "传播+变异可观测" if len(ok) >= 4 and len(hi) >= 1 else "传播不足"
print(f">>> 结论: {verd}")

out = {"spread": spread_log, "rows": [{"a": r[0], "role": r[1], "ans": r[2], "score": r[3], "marks": r[4], "knows": r[5]} for r in rows],
       "stats": stats, "verdict": verd}
json.dump(out, open("/home/ubuntu/p2_result.json", "w"), ensure_ascii=False, indent=1, default=str)
print("结果已存 /home/ubuntu/p2_result.json")

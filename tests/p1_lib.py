"""P1 记忆卖点生死闸门: 5 人 x 7 日。
第2天给老王埋碎片, 第7天考问。同一 agent 跑两遍:
  A) 全量时间窗口(把全部记忆按序灌进 prompt)
  B) RAG top-30(关键词重合 + 时间近因打分, 近似 Smallville retrieve.py)
判分: 答案是否说出"灰色"和"东"两个细节。
"""
import json, urllib.request, time, subprocess, os, re, threading
from concurrent.futures import ThreadPoolExecutor

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"


class TokenBucket:
    def __init__(self, rate, cap):
        self.rate, self.cap, self.tokens, self.ts = rate, cap, cap, time.monotonic()
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


bucket = TokenBucket(rate=40/60.0, cap=8)
stats = {"calls": 0, "ok": 0, "r429": 0, "err": 0}


def chat(messages, max_tokens=2048, temperature=0, retries=4):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": temperature})
    for attempt in range(retries):
        w = bucket.acquire()
        if w > 0:
            time.sleep(w)
        req = urllib.request.Request(
            URL, data=body.encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                d = json.loads(r.read())
            return d["choices"][0]["message"].get("content")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                with threading.Lock():
                    stats["r429"] += 1
                if attempt < retries - 1:
                    time.sleep(min(60, 2 ** attempt * 2))
                    continue
            with threading.Lock():
                stats["calls"] += 1
                stats["err"] += 1
            return None
        except Exception:
            with threading.Lock():
                stats["calls"] += 1
                stats["err"] += 1
            return None
    return None


# ---------- 世界与人设 ----------
world = {
  "sectors": {
    "Hobbs Cafe": {"arenas": {"cafe": {"objects": ["cafe customer seating", "coffee machine"]}}},
    "邮局": {"arenas": {"柜台": {"objects": ["邮局柜台", "邮票展架"]}, "休息区": {"objects": ["休息区长椅"]}}},
    "镇公所": {"arenas": {"办公室": {"objects": ["办公桌", "档案柜"]}}},
    "诊所": {"arenas": {"候诊室": {"objects": ["候诊长椅", "挂号台"]}}},
    "学校": {"arenas": {"教室": {"objects": ["课桌", "黑板"]}}}
  }
}
SEC = list(world["sectors"].keys())
OBJ = {s: [o for a in world["sectors"][s]["arenas"].values() for o in a["objects"]] for s in SEC}

personas = [
 {"name":"林阿姨","age":52,"innate":"friendly, hardworking, observant",
  "learned":"林阿姨是 Hobbs Cafe 的老板，喜欢和客人聊天。",
  "daily_plan_req":"林阿姨每天在咖啡馆柜台后工作。","living_area":"Hobbs Cafe:cafe"},
 {"name":"小陈","age":28,"innate":"careful, honest, anxious",
  "learned":"小陈是邮局职员，负责柜台收件。",
  "daily_plan_req":"小陈每天在邮局柜台后工作。","living_area":"邮局:柜台"},
 {"name":"老王","age":61,"innate":"nosy, talkative, kind",
  "learned":"老王是退休邮递员，整天在镇上溜达打听消息。",
  "daily_plan_req":"老王每天在镇上散步。","living_area":"镇公所:办公室"},
 {"name":"赵医生","age":45,"innate":"calm, methodical, busy",
  "learned":"赵医生是镇上诊所的医生。",
  "daily_plan_req":"赵医生每天在诊所候诊室接诊。","living_area":"诊所:候诊室"},
 {"name":"周老师","age":38,"innate":"patient, curious, cheerful",
  "learned":"周老师是学校教师。",
  "daily_plan_req":"周老师每天在学校教室上课。","living_area":"学校:教室"},
]
for p in personas:
    p["loc"] = p["living_area"]
    p["memory"] = []   # list of (day, text)

# ---------- 脚本注入(情景A的种子, 只注入不写结局) ----------
def inject(day):
    """按弧线在指定日子给特定 agent 注入记忆。"""
    if day == 2:
        # 引爆点: 老王目睹取件(低频措辞, 降低与日后提问的词汇重合)
        personas[2]["memory"].append((2, "老王在邮局门口晒太阳时看见: 一个人从邮局柜台取走一只用胶带缠了好几道的旧纸箱, 那人穿一件灰色粗呢外套, 抱着纸箱朝镇子东头的五金店方向走了。"))
        personas[0]["memory"].append((2, "林阿姨听说邮局昨天走了一只旧纸箱包裹。"))
    if day == 3:
        personas[2]["memory"].append((3, "老王跟周老师聊天时提到: 前天邮局那个人穿的不是常见的黑外套, 颜色偏浅。"))
    if day == 5:
        personas[1]["memory"].append((5, "小陈发现登记册上有一个包裹的取件记录存疑, 取件人特征栏写着: 外套颜色很特别。"))

NOISE = ["{n} is idle at the {obj}", "{n} 正在 {obj} 旁发呆", "{n} 擦了擦 {obj}"]
def add_noise(day):
    import random
    rng = random.Random(day * 7)
    for p in personas:
        for _ in range(6):
            obj = OBJ[p["loc"].split(":")[0]][0]
            p["memory"].append((day, rng.choice(NOISE).format(n=p["name"], obj=obj)))

def merged_prompt(p, act):
    cur_sec = p["loc"].split(":")[0]
    cur_arenas = list(world["sectors"][cur_sec]["arenas"].keys())
    return f"""你是游戏里的角色 {p['name']}。当前要执行: {act}
当前在 {cur_sec}（子区域: {', '.join(cur_arenas)}）。可去地点: {', '.join(SEC)}。
输出一个 JSON, 字段如下, 只能从给定候选里选, 不要任何其他文字:
{{"sector":"从候选选一个","arena":"从该地点子区域选一个","object":"从该子区域物品选一个","emoji":"1-3个emoji","action":"{act}"}}
地点-子区域-物品参照:
{json.dumps({s: {a: v['objects'] for a, v in world['sectors'][s]['arenas'].items()} for s in SEC}, ensure_ascii=False)}
"""

def extract(raw, valid):
    if not raw: return None
    try:
        d = json.loads(raw)
        for k in valid:
            if d.get(k): return d[k]
    except Exception: pass
    for pat in [r"\*\*Answer[:：]\s*([^*\n{]+)", r"\{([^}\n]+)\}"]:
        m = re.search(pat, raw)
        if m:
            v = m.group(1).strip().rstrip("}").strip()
            if v in valid: return v
    for v in valid:
        if v in raw: return v
    return None

# ---------- RAG 检索: 近似 Smallville retrieve ----------
def rag_top(memlist, query, n=30):
    """score = 2.0*关键词重合(字符bigram) + 0.5*近因。gw=[0.5,3,2] 的本机近似。"""
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s)-1))
    qb = bigrams(query)
    scored = []
    for i, (day, text) in enumerate(memlist):
        tb = bigrams(text)
        overlap = len(qb & tb)
        recency = 1.0 / (7 - day + 1)   # 越近越高
        score = 2.0 * overlap + 0.5 * recency
        scored.append((score, i, day, text))
    scored.sort(key=lambda x: -x[0])
    return scored[:n]


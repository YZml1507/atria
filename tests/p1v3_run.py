"""P1v3 记忆卖点生死闸门 - 时间线分辨版。
核心改动(对 P1v2 失败的诊断):
  1. 任务从"事实回忆"改为"矛盾信息分辨" - 3 个互相矛盾的颜色版本, 只有全量时间线能分辨
  2. 噪声池真撑到 6400 条(P1v2 只到 842)
  3. 清除 '灰' 字污染(P1v2 噪声含'落了点灰', 词频 156 次)
  4. RAG 严格按 Smallville gw=[0.5,3,2]
判分: 答"灰色"(第2天原始目击)=对; 答黑/蓝=被变异版本带偏
"""
import json, urllib.request, time, subprocess, os, re, threading, random
from concurrent.futures import ThreadPoolExecutor

exec(open("/home/ubuntu/p1_lib.py").read())

# ---------- 噪声池: 真实规模 ----------
NOISE_CACHE = "/home/ubuntu/p1v3_noise.json"


def gen_noise_prompt(p, n=60):
    return f"""你在模拟 {p['name']} 的一天。写 {n} 条他当天会记录的日常记忆, 每条一行。
要求: 像日记一样自然, 长度 15-40 字, 动作/地点/物品多样。
禁用这些词: 灰 外套 纸箱 东头 黑色 蓝色 颜色 (留给剧情)。
只输出 {n} 行, 每行一条, 不要编号不要解释。 {p['name']} 的身份: {p['learned']}"""


def build_pool(cache=NOISE_CACHE, batches_per_agent=4):
    """每 agent 4 批 x 60 = 240 条, 5 人 = 1200, 程序化复读 + 变体扩到 6400。"""
    if os.path.exists(cache):
        return json.load(open(cache))
    pool = {}
    futs = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for p in personas:
            for b in range(batches_per_agent):
                def do(p=p):
                    raw = chat([{"role": "user", "content": gen_noise_prompt(p, 60)}], max_tokens=3000)
                    if not raw:
                        return p["name"], []
                    return p["name"], [l.strip("- ").strip() for l in raw.split("\n") if l.strip()][:60]
                futs.append(ex.submit(do))
        for f in futs:
            name, lines = f.result()
            pool.setdefault(name, []).extend(lines)
    json.dump(pool, open(cache, "w"), ensure_ascii=False, indent=1)
    return pool


print("=== P1v3 阶段1: 噪声池 ===")
t0 = time.time()
pool = build_pool()
print(f"LLM 噪声: " + ", ".join(f"{k}={len(v)}" for k, v in pool.items()))
print(f"墙钟 {time.time()-t0:.0f}s")

# ---------- 构造记忆流: 目标 6400 ----------
print("\n=== P1v3 阶段2: 构造记忆 ===")
rng = random.Random(7)
BANNED = ["灰", "外套", "纸箱", "东头", "黑色", "蓝色"]
lw_pool = [l for l in pool["老王"] if not any(w in l for w in BANNED)]
print(f"老王可用噪声(已过滤禁词): {len(lw_pool)} 条")

mem = []
for day in range(1, 8):
    # 每天 ~900 条 (912/日 实测)
    target = 900
    day_mem = []
    # 6 条决策
    for k in range(6):
        sec = rng.choice(SEC)
        arenas = list(world["sectors"][sec]["arenas"].keys())
        arena = rng.choice(arenas)
        day_mem.append(f"老王 在 {sec} 的 {arena} 散步打听消息 🚶‍♂️")
    # LLM 噪声(去重复读)
    if lw_pool:
        need = target - 6
        while len(day_mem) < target:
            for line in lw_pool:
                if len(day_mem) >= target:
                    break
                # 复读 + 轻微变体
                day_mem.append(line)
                v = line + rng.choice(["", " (又看了一眼)", " (顺便]", " 第二次经过", ""])
                if len(day_mem) < target:
                    day_mem.append(v)
    mem.extend((day, t) for t in day_mem)

# ---------- 注入 3 个矛盾版本 ----------
mem.append((2, "老王在邮局门口晒太阳时看见: 一个人从邮局柜台取走一只用胶带缠了好几道的旧纸箱, 那人穿一件灰色粗呢外套, 抱着纸箱朝镇子东头的五金店方向走了。"))
mem.append((3, "老王跟周老师聊天时提到: 前天邮局那个人穿的不是常见的黑外套, 颜色偏浅, 好像是灰色。"))
mem.append((4, "周老师后来跟别人说: 老王讲的那个人穿的是黑色大衣, 挺长的。"))       # 变异A
mem.append((6, "赵医生在诊所听人闲聊: 邮局那天取包裹的人穿蓝色工作服来着。"))      # 变异B

print(f"老王总记忆: {len(mem)} 条")
for w in ["灰", "黑", "蓝"]:
    print(f"  '{w}' 出现 {sum(1 for d,t in mem if w in t)} 次")

# ---------- RAG: 严格 gw=[0.5,3,2] ----------
def rag_top_strict(memlist, query, n=30):
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))
    qb = bigrams(query)
    scored = []
    for i, (day, text) in enumerate(memlist):
        overlap = len(qb & bigrams(text))
        recency = 1.0 / (8 - day)
        score = 0.5 * recency + 3.0 * overlap + 2.0 * 0.1
        scored.append((score, i, day, text))
    scored.sort(key=lambda x: -x[0])
    return scored[:n]

QUESTION = "老王, 五天前你在邮局门口看到取包裹的那个人, 他穿什么颜色的外套? 一句话回答。"
top = rag_top_strict(mem, QUESTION, n=30)
print(f"\ntop-30 覆盖率: {30/len(mem)*100:.2f}%")
print("top-6:")
for rank, (s, i, day, text) in enumerate(top[:6]):
    tag = "原始" if day == 2 else ("复述" if day == 3 else ("变异A" if day == 4 else ("变异B" if day == 6 else "噪声")))
    print(f"  #{rank+1} score={s:5.1f} day={day} [{tag}] {text[:55]}")

# ---------- 考问 ----------
print("\n=== P1v3 阶段3: 考问 ===")
def ask_full(memlist):
    m = "\n".join(f"[第{d}天] {t}" for d, t in memlist)
    prompt = f"""以下是 老王 从第1天到第7天的全部记忆, 按时间顺序排列:

{m}

现在有人问你: {QUESTION}
注意: 记忆里有几个互相矛盾的说法, 请你分辨哪个是第2天你亲眼所见的原始记忆(后续天的说法可能是以讹传讹)。如实回答。"""
    return chat([{"role": "user", "content": prompt[:120000]}], max_tokens=1024)


def ask_rag(top_hits):
    m = "\n".join(f"[第{d}天] {t}" for _, _, d, t in top_hits)
    prompt = f"""以下是 老王 的记忆检索结果(按相关性排序):

{m}

现在有人问你: {QUESTION}
注意: 记忆里有几个互相矛盾的说法, 请你分辨哪个是你亲眼所见的原始记忆。如实回答。"""
    return chat([{"role": "user", "content": prompt[:120000]}], max_tokens=1024)

ans_full = ask_full(mem)
print(f"[A 全量 {len(mem)}条] {ans_full!r}")
ans_rag = ask_rag(top)
print(f"[B RAG top-30] {ans_rag!r}")

def score(ans):
    if not ans: return 0, ["无输出"]
    a = ans.replace(" ", "")
    if "灰" in a and "黑" not in a.replace("灰色","") and "蓝" not in a:
        return 2, ["灰色(正确)"]
    if "灰" in a: return 1, ["提到灰但混入其他色"]
    if "黑" in a or "蓝" in a: return 0, ["被变异版本带偏"]
    return 0, ["未答出颜色"]

sf, gf = score(ans_full)
sr, gr = score(ans_rag)
print(f"\n判分: 全量={sf}/2 {gf}  RAG={sr}/2 {gr}")
verd = "卖点成立" if (sf == 2 and sr < 2) else ("卖点被证伪/不显著" if (sf == 2 and sr == 2) else ("全量也失败-需查" if sf < 2 else "异常"))
print(f">>> 结论: {verd}")

out = {"n_memory": len(mem), "ans_full": ans_full, "ans_rag": ans_rag,
       "score_full": sf, "score_rag": sr, "verdict": verd,
       "stats": stats}
json.dump(out, open("/home/ubuntu/p1v3_result.json", "w"), ensure_ascii=False, indent=1)
print("结果已存 /home/ubuntu/p1v3_result.json")

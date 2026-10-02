"""P1v5: 判据完整性对照实验。
继承 P1v3 的记忆构造(6304 条, 3 个矛盾版本), 但:
  1. 判分改为 0-3 分的判据完整性(方案 v1.1 6.5)
  2. 全量调用绕过令牌桶(单次大请求, 与 RPM 无关), timeout=600s
  3. RAG 调用照常
  4. 两个调用并行发起
判据:
  0=只给答案无判据  1=答案正确  2=+指出矛盾版本  3=+分辨一手vs转述失真
"""
import json, urllib.request, time, subprocess, os, re, threading, random
from concurrent.futures import ThreadPoolExecutor

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"


def chat_raw(messages, max_tokens=1024, timeout=600):
    """不带令牌桶, 用于大请求。"""
    body = json.dumps({"model": MODEL, "messages": messages,
                       "max_tokens": max_tokens, "temperature": 0})
    req = urllib.request.Request(
        URL, data=body.encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        return d["choices"][0]["message"].get("content"), d.get("usage", {}), time.time() - t
    except Exception as e:
        return None, {"error": str(e)[:120]}, time.time() - t


# ---------- 构造与 P1v3 相同的记忆 ----------
rng = random.Random(7)
pool = json.load(open("/home/ubuntu/p1v3_noise.json"))
lw_pool = [l for l in pool["老王"] if not any(w in l for w in ["灰", "外套", "纸箱", "东头", "黑色", "蓝色"])]
print(f"老王可用噪声: {len(lw_pool)} 条")

mem = []
for day in range(1, 8):
    day_mem = []
    for k in range(6):
        day_mem.append(f"老王 在 镇上 散步打听消息 🚶‍♂️ {day}-{k}")
    while len(day_mem) < 900:
        for line in lw_pool:
            if len(day_mem) >= 900:
                break
            day_mem.append(line)
    mem.extend((day, t) for t in day_mem)

# 3 个矛盾版本
mem.append((2, "老王在邮局门口晒太阳时看见: 一个人从邮局柜台取走一只用胶带缠了好几道的旧纸箱, 那人穿一件灰色粗呢外套, 抱着纸箱朝镇子东头的五金店方向走了。"))
mem.append((3, "老王跟周老师聊天时提到: 前天邮局那个人穿的不是常见的黑外套, 颜色偏浅, 好像是灰色。"))
mem.append((4, "周老师后来跟别人说: 老王讲的那个人穿的是黑色大衣, 挺长的。"))
mem.append((6, "赵医生在诊所听人闲聊: 邮局那天取包裹的人穿蓝色工作服来着。"))
print(f"总记忆: {len(mem)} 条")

QUESTION = "老王, 五天前你在邮局门口看到取包裹的那个人, 他穿什么颜色的外套? 一句话回答。"


def rag_top_strict(memlist, query, n=30):
    def bigrams(s):
        return set(s[i:i+2] for i in range(len(s) - 1))
    qb = bigrams(query)
    scored = []
    for i, (day, text) in enumerate(memlist):
        overlap = len(qb & bigrams(text))
        recency = 1.0 / (8 - day)
        score = 0.5 * recency + 3.0 * overlap + 0.2
        scored.append((score, i, day, text))
    scored.sort(key=lambda x: -x[0])
    return scored[:n]


top = rag_top_strict(mem, QUESTION, n=30)
print(f"top-30 覆盖率: {30/len(mem)*100:.2f}%")

# ---------- 两个 prompt ----------
def full_prompt():
    m = "\n".join(f"[第{d}天] {t}" for d, t in mem)
    return f"以下是 老王 从第1天到第7天的全部记忆, 按时间顺序排列:\n\n{m}\n\n现在有人问你: {QUESTION}\n注意: 记忆里有几个互相矛盾的说法, 请分辨哪个是第2天你亲眼所见的原始记忆(后续天的说法可能是以讹传讹)。如实回答。"

def rag_prompt():
    m = "\n".join(f"[第{d}天] {t}" for _, _, d, t in top)
    return f"以下是 老王 的记忆检索结果(按相关性排序):\n\n{m}\n\n现在有人问你: {QUESTION}\n注意: 记忆里有几个互相矛盾的说法, 请分辨哪个是你亲眼所见的原始记忆。如实回答。"


print("\n=== P1v5: 并行发起两个调用 ===")
results = {}


def do_full():
    results["full"] = chat_raw([{"role": "user", "content": full_prompt()[:500000]}])


def do_rag():
    results["rag"] = chat_raw([{"role": "user", "content": rag_prompt()}])


t0 = time.time()
with ThreadPoolExecutor(max_workers=2) as ex:
    ex.submit(do_full)
    ex.submit(do_rag)
print(f"墙钟 {time.time()-t0:.0f}s")

ans_full, u_full, dt_full = results.get("full", (None, {}, 0))
ans_rag, u_rag, dt_rag = results.get("rag", (None, {}, 0))

print(f"\n[A 全量窗口] {dt_full:.0f}s")
print(f"  usage: {u_full}")
print(f"  回答: {ans_full!r}")
print(f"\n[B RAG top-30] {dt_rag:.0f}s")
print(f"  usage: {u_rag}")
print(f"  回答: {ans_rag!r}")


# ---------- 判据完整性判分 ----------
def judge(ans):
    """0=只给答案 1=答案对 2=+指出矛盾 3=+分辨一手vs转述"""
    if not ans:
        return -1, "无输出"
    a = ans
    marks = []
    if "灰" in a:
        marks.append("答案=灰")
    has_conflict = any(w in a for w in ["矛盾", "但第", "而第", "转述", "失真", "以讹传讹", "听说", "后来"])
    if has_conflict:
        marks.append("指出矛盾/来源")
    has_source = any(w in a for w in ["亲眼", "原始", "亲眼所见", "转述", "失真", "第2天"])
    if has_source and has_conflict and "灰" in a:
        marks.append("分辨一手vs转述")
    score = 0
    if "灰" in a:
        score = 1
    if has_conflict and score >= 1:
        score = 2
    if has_source and has_conflict and "灰" in a:
        score = 3
    return score, marks


sf, mf = judge(ans_full)
sr, mr = judge(ans_rag)
print(f"\n=== 判据完整性判分 ===")
print(f"全量: {sf}/3  {mf}")
print(f"RAG : {sr}/3  {mr}")
verd = "卖点成立(全量分辨传言变异)" if sf >= 3 and sr <= 1 else \
       ("两者都能分辨" if sf >= 3 and sr >= 3 else ("全量也失败" if sf < 2 else "差异不显著"))
print(f">>> 结论: {verd}")

out = {"n_memory": len(mem), "ans_full": ans_full, "ans_rag": ans_rag,
       "judge_full": sf, "judge_rag": sr, "marks_full": mf, "marks_rag": mr,
       "verdict": verd, "usage_full": u_full, "usage_rag": u_rag}
json.dump(out, open("/home/ubuntu/p1v5_result.json", "w"), ensure_ascii=False, indent=1, default=str)
print("结果已存 /home/ubuntu/p1v5_result.json")

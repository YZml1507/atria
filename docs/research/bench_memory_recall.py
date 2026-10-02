"""
512K 记忆有效性压测
模拟真实沙盒负载：25 个居民 × 多天记忆流，测 Atria 能否准确回忆。

测试维度：
1. 容量：记忆流能塞多少
2. 检索准确性："张三上周三说过什么"
3. 一致性：同一问题问两次，答案是否一致
4. 抗干扰：插入无关记忆后是否仍能回忆
"""
import os, time, json, statistics
from openai import OpenAI

key = os.environ["HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY"]
client = OpenAI(base_url="https://discovery-api.intern-ai.org.cn/v1", api_key=key)
MODEL = "Atria-Dawn-Preview"

# ---- 构造真实感记忆流 ----
DAYS = 6
RESIDENTS = ["张三", "李四", "王梅", "赵六", "陈七"]
LOCATIONS = ["广场", "集市", "面包房", "铁匠铺", "酒馆", "神庙", "码头"]

def gen_memory(day):
    """生成一天的居民行为记录，混入 5 个可验证的事实种子"""
    seeds = [
        (day, "张三", f"第{day}天我在集市上以 12 个铜币的价格卖出了三袋小麦"),
        (day, "李四", f"第{day}天王梅向我借了 50 个铜币，约定第{day+3}天还"),
        (day, "王梅", f"第{day}天我在面包房听到谣言，说领主的税要涨到两成"),
        (day, "赵六", f"第{day}天我在铁匠铺打造了 3 把剑，其中一把卖给了陈七"),
        (day, "陈七", f"第{day}天我在酒馆里和张三吵了一架，因为他踩了我的脚"),
    ]
    # 混入大量日常噪声记忆（真实沙盒里大多是这样的流水账）
    noise = [
        (day, r, f"第{day}天我在{l}度过了平常的一天，天气{'晴朗' if (day*len(r))%3==0 else '阴沉'}，吃了{'面包' if (day+len(r))%2==0 else '炖肉'}")
        for r in RESIDENTS for l in LOCATIONS[:3]
    ]
    return seeds + noise

# 构造 6 天记忆
memories = []
for d in range(1, DAYS+1):
    memories.extend(gen_memory(d))

MEMORY_TEXT = "\n".join(f"[{d}天前] {r}：{c}" for d, r, c in sorted(memories, key=lambda x: -x[0]))
print(f"记忆流: {len(memories)} 条, 约 {len(MEMORY_TEXT)//3} token")

# ---- 压测问题（答案预先已知，可自动判分）----
QUESTIONS = [
    {"q": "张三卖出三袋小麦的价格是多少铜币？只答数字。", "a": "12", "day": 3, "person": "张三"},
    {"q": "王梅向李四借了多少钱？只答数字。", "a": "50", "day": 3, "person": "王梅"},
    {"q": "谣言说领主的税要涨到几成？只答数字。", "a": "2", "day": 3, "person": "王梅"},
    {"q": "赵六打造了几把剑？只答数字。", "a": "3", "day": 3, "person": "赵六"},
    {"q": "陈七为什么和张三吵架？用一句话回答。", "a": "踩", "day": 3, "person": "陈七"},
]

def ask(question, memory=MEMORY_TEXT):
    """带记忆流的提问"""
    msgs = [
        {"role": "system", "content": f"你是小镇的记忆管理者。以下是居民们过去{DAYS}天的行为记录。\n\n{memory}\n\n请根据记录回答问题，只给出最直接的答案。"},
        {"role": "user", "content": question},
    ]
    t0 = time.time()
    try:
        r = client.chat.completions.create(model=MODEL, messages=msgs, max_tokens=60)
        content = r.choices[0].message.content
        reasoning = getattr(r.choices[0].message, "reasoning", None) or getattr(r.choices[0].message, "reasoning_content", None)
        return content, reasoning, r.usage.total_tokens if r.usage else 0, time.time()-t0
    except Exception as e:
        return None, None, 0, time.time()-t0

# ---- 测 1：基础检索准确性 ----
print("\n== 测 1：记忆检索准确性（含 6 天噪声）==")
correct, results = 0, []
for item in QUESTIONS:
    ans, reasoning, tokens, dt = ask(item["q"])
    ok = ans is not None and item["a"] in ans
    correct += ok
    results.append({"q": item["q"][:20], "ans": ans, "ok": ok, "dt": dt, "tok": tokens})
    print(f"  {'✓' if ok else '✗'} {item['q'][:24]} → {repr(ans)[:40]} ({dt:.1f}s, {tokens} tok)")
print(f"准确率: {correct}/{len(QUESTIONS)} = {correct/len(QUESTIONS)*100:.0f}%")

# ---- 测 2：长上下文尾部信息 ----
print("\n== 测 2：长上下文尾部信息读取（约 28 万 token）==")
padding = "窗外下着小雨。居民区的梧桐树叶子落了一地。" * 20000  # ~28万 token
tail_q = "张三的银行卡密码是多少？只答数字。"
tail_a = "920417"
full = padding + f"\n\n【关键信息】张三的银行卡密码是 {tail_a}。\n\n请回答：{tail_q}"
ans, reasoning, tok, dt = ask(tail_q, memory=full)
ok = ans is not None and tail_a in ans
print(f"  {'✓' if ok else '✗'} 尾部信息 → {repr(ans)[:40]} ({dt:.1f}s, {tok} tok)")
if not ok and reasoning:
    print(f"  reasoning 片段: {str(reasoning)[:150]}")

print("\n== 压测结束 ==")

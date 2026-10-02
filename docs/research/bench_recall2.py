"""补充压测：None 是否偶发 / 一致性 / 接近 512K 上限"""
import os, time
from openai import OpenAI
key = os.environ["HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY"]
client = OpenAI(base_url="https://discovery-api.intern-ai.org.cn/v1", api_key=key)
MODEL = "Atria-Dawn-Preview"

def ask(q, memory):
    msgs = [{"role":"system","content":f"以下是居民们过去6天的行为记录。\n\n{memory}\n\n请根据记录回答，只给最直接的答案。"},
            {"role":"user","content":q}]
    t0=time.time()
    try:
        r = client.chat.completions.create(model=MODEL, messages=msgs, max_tokens=60)
        return r.choices[0].message.content, time.time()-t0
    except Exception as e:
        return f"ERR:{str(e)[:80]}", time.time()-t0

MEMORY = """[6天前] 张三：第1天我在集市上以 12 个铜币的价格卖出了三袋小麦
[6天前] 李四：第1天王梅向我借了 50 个铜币，约定第4天还
[6天前] 王梅：第1天我在面包房听到谣言，说领主的税要涨到两成
[6天前] 赵六：第1天我在铁匠铺打造了 3 把剑，其中一把卖给了陈七
[6天前] 陈七：第1天我在酒馆里和张三吵了一架，因为他踩了我的脚"""

# 1) 重试之前返回 None 的题 x3
print("== 补测 1：None 是否偶发（同一题 3 次）==")
for i in range(3):
    ans, dt = ask("王梅向李四借了多少钱？只答数字。", MEMORY)
    print(f"  第{i+1}次 → {repr(ans)[:40]} ({dt:.1f}s)")

# 2) 一致性：同一问题间隔问 2 次
print("\n== 补测 2：答案一致性 ==")
a1,_ = ask("张三卖出三袋小麦的价格是多少铜币？只答数字。", MEMORY)
a2,_ = ask("张三三袋小麦卖了多少钱？只答数字。", MEMORY)
print(f"  问法A → {repr(a1)[:30]} | 问法B → {repr(a2)[:30]} | 一致: {a1==a2}")

# 3) 接近上限：约 45 万 token
print("\n== 补测 3：约 45 万 token 尾部读取 ==")
padding = "窗外下着小雨。居民区的梧桐树叶子落了一地。" * 32000  # ~45万
full = padding + "\n\n【关键信息】李四的仓库密码是 7291。\n\n请回答：李四的仓库密码是多少？只答数字。"
t0=time.time()
ans, dt = ask("李四的仓库密码是多少？只答数字。", full)
ok = ans is not None and "7291" in str(ans)
print(f"  {'✓ 成功' if ok else '✗ 失败'} → {repr(ans)[:40]} ({dt:.1f}s)")

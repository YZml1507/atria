"""验证解法：max_tokens 拔高 + temperature=0，看 None 与一致性是否解决"""
import os, time
from openai import OpenAI
key = os.environ["HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY"]
client = OpenAI(base_url="https://discovery-api.intern-ai.org.cn/v1", api_key=key)
MODEL = "Atria-Dawn-Preview"

MEMORY = """[6天前] 张三：第1天我在集市上以 12 个铜币的价格卖出了三袋小麦
[6天前] 李四：第1天王梅向我借了 50 个铜币，约定第4天还
[6天前] 王梅：第1天我在面包房听到谣言，说领主的税要涨到两成
[6天前] 赵六：第1天我在铁匠铺打造了 3 把剑，其中一把卖给了陈七
[6天前] 陈七：第1天我在酒馆里和张三吵了一架，因为他踩了我的脚"""

def ask(q, max_tok=512, temp=0.0):
    msgs = [{"role":"system","content":"以下是居民日记。\n\n"+MEMORY+"\n\n根据记录回答，只给最直接的答案。"},
            {"role":"user","content":q}]
    t0=time.time()
    r = client.chat.completions.create(model=MODEL, messages=msgs, max_tokens=max_tok, temperature=temp)
    m = r.choices[0].message
    return m.content, getattr(r.choices[0], "finish_reason", None), time.time()-t0

print("== 解法验证：max_tokens=512 + temperature=0 ==")
qs = [
    "王梅向李四借了多少钱？只答数字。",
    "张三卖出三袋小麦的价格是多少铜币？只答数字。",
    "张三三袋小麦一共卖了几个铜币？只答数字。",
    "王梅借李四的钱约定第几天还？只答数字。",
    "赵六打造了几把剑？只答数字。",
]
for q in qs:
    c, fin, dt = ask(q)
    print(f"  {q[:26]} → {repr(c)[:32]} fin={fin} ({dt:.1f}s)")

print("\n== 一致性复测（同题 2 次，temp=0）==")
a1,_,_ = ask("王梅向李四借了多少钱？只答数字。")
a2,_,_ = ask("王梅向李四借了多少钱？只答数字。")
print(f"  第1次={repr(a1)[:20]} 第2次={repr(a2)[:20]} 一致={a1==a2}")

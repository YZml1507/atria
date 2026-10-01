"""深挖 None 机制 + 一致性失败根因"""
import os, time
from openai import OpenAI
key = os.environ["HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY"]
client = OpenAI(base_url="https://discovery-api.intern-ai.org.cn/v1", api_key=key)
MODEL = "Atria-Dawn-Preview"

MEMORY = """[6天前] 张三：第1天我在集市上以 12 个铜币的价格卖出了三袋小麦
[6天前] 李四：第1天王梅向我借了 50 个铜币，约定第4天还
[6天前] 王梅：第1天我在面包房听到谣言，说领主的税要涨到两成"""

def ask(q, memory=MEMORY, label=""):
    msgs = [{"role":"system","content":f"以下是居民日记。\n\n{memory}\n\n根据记录回答，只给最直接的答案。"},
            {"role":"user","content":q}]
    t0=time.time()
    r = client.chat.completions.create(model=MODEL, messages=msgs, max_tokens=60)
    m = r.choices[0].message
    content = m.content
    # 试探 reasoning 字段
    reasoning = None
    for attr in ("reasoning_content", "reasoning"):
        v = getattr(m, attr, None)
        if v: reasoning = v; break
    fin_reasons = getattr(r, "choices", [{}])[0].finish_reason if r.choices else None
    print(f"  {label or q[:22]} → content={repr(content)[:30]} | fin={fin_reasons} | reasoning={repr(str(reasoning))[:80] if reasoning else 'None'} ({time.time()-t0:.1f}s)")
    return content

print("== A：视角转换题（李四日记里的'我'）==")
ask("王梅向李四借了多少钱？只答数字。", label="原问法(3连None)")
ask("李四借给王梅多少钱？只答数字。", label="改成李四视角")
ask("日记里李四说'王梅向我借了50个铜币'，请问王梅向李四借了多少？只答数字。", label="明示引文")

print("\n== B：一致性失败根因（12 vs 36）==")
ask("张三卖出三袋小麦的价格是多少铜币？只答数字。", label="问单价")
ask("张三三袋小麦一共卖了几个铜币？只答数字。", label="问总价(原文是总价12)")

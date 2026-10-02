"""P1v4: 复现 P1v3 的全量调用, 但带完整错误捕获。
P1v3 的 ask_full 返回 None 且 stats 没记录, 需要看到真实错误。
"""
import json, urllib.request, time, subprocess, urllib.error

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"

# 用真实记忆(P1v3 的构造)而非假句
import random
rng = random.Random(7)
mem = []
for day in range(1, 8):
    for k in range(900):
        mem.append((day, f"老王在镇上散步, 经过了邮局和咖啡馆, 看到了熟悉的街景和邻居, 日子一天天过去 {day}-{k}"))
# 注入 3 个矛盾版本(与 P1v3 完全一致)
mem.append((2, "老王在邮局门口晒太阳时看见: 一个人从邮局柜台取走一只用胶带缠了好几道的旧纸箱, 那人穿一件灰色粗呢外套, 抱着纸箱朝镇子东头的五金店方向走了。"))
mem.append((3, "老王跟周老师聊天时提到: 前天邮局那个人穿的不是常见的黑外套, 颜色偏浅, 好像是灰色。"))
mem.append((4, "周老师后来跟别人说: 老王讲的那个人穿的是黑色大衣, 挺长的。"))
mem.append((6, "赵医生在诊所听人闲聊: 邮局那天取包裹的人穿蓝色工作服来着。"))

m = "\n".join(f"[第{d}天] {t}" for d, t in mem)
prompt = f"以下是老王从第1天到第7天的全部记忆, 按时间顺序排列:\n\n{m}\n\n问: 五天前老王在邮局门口看到取包裹的那个人, 他穿什么颜色的外套? 注意记忆里有互相矛盾的说法, 请分辨哪个是第2天亲眼所见的原始记忆。一句话回答。"
print(f"记忆条数: {len(mem)}")
print(f"prompt 字符数: {len(prompt)}")

body = json.dumps({"model": "Atria-Dawn-Preview",
                   "messages": [{"role": "user", "content": prompt}],
                   "max_tokens": 1024, "temperature": 0}).encode()
print(f"请求体: {len(body)/1e6:.2f} MB")

req = urllib.request.Request(
    URL, data=body,
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
t = time.time()
try:
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.loads(r.read())
    print(f"HTTP {r.status}  {time.time()-t:.1f}s")
    msg = d["choices"][0]["message"]
    print("content:", repr(msg.get("content"))[:300])
    print("finish_reason:", d["choices"][0].get("finish_reason"))
    u = d.get("usage", {})
    print(f"prompt_tokens: {u.get('prompt_tokens'):,}  completion: {u.get('completion_tokens')}  reasoning: {u.get('completion_tokens_details',{}).get('reasoning_tokens')}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}  {time.time()-t:.1f}s")
    print(e.read()[:600].decode(errors="replace"))
except Exception as e:
    print(f"异常: {type(e).__name__}: {str(e)[:300]}  {time.time()-t:.1f}s")

"""P1 记忆卖点生死闸门: 5 人 x 7 日。清晰版。
第2天给老王埋碎片, 第7天考问。同一 agent 跑两遍:
  A) 全量时间窗口  B) RAG top-30
判分: 答案是否说出"灰色"和"东"两个细节。
"""
import json, urllib.request, time, subprocess, os, re, threading, random
from concurrent.futures import ThreadPoolExecutor

exec(open("/home/ubuntu/p1_lib.py").read())  # chat, bucket, world, personas, inject, noise, rag_top, extract

# ---------- 主循环 ----------
DAYS = 7
STEPS_PER_DAY = 6
t0 = time.time()

for day in range(1, DAYS + 1):
    inject(day)
    add_noise(day)
    futs = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        for p in personas:
            for s_i in range(STEPS_PER_DAY):
                def do(p=p):
                    act = p["daily_plan_req"].split("，")[0]
                    raw = chat([{"role": "user", "content": merged_prompt(p, act)}])
                    if raw is None:
                        return
                    val = None
                    try:
                        val = json.loads(raw)
                    except Exception:
                        m = re.search(r"\{[\s\S]*\}", raw)
                        if m:
                            try:
                                val = json.loads(m.group(0))
                            except Exception:
                                pass
                    okf = {k: v for k, v in (val or {}).items() if isinstance(v, str)}
                    sec = okf.get("sector") or extract(raw, SEC) or p["loc"].split(":")[0]
                    if sec not in SEC:
                        sec = p["loc"].split(":")[0]
                    arenas = list(world["sectors"][sec]["arenas"].keys())
                    arena = okf.get("arena") or extract(raw, arenas) or arenas[0]
                    if arena not in arenas:
                        arena = arenas[0]
                    p["loc"] = f"{sec}:{arena}"
                    p["memory"].append((day, f"{p['name']} 在 {sec} 的 {arena} {okf.get('action', act)} {okf.get('emoji', '')}"))
                futs.append(ex.submit(do))
        for f in futs:
            f.result()
    print(f"第{day}天完成: 记忆总数 " + ", ".join(f"{p['name']}={len(p['memory'])}" for p in personas))

tot = time.time() - t0
print(f"模拟墙钟 {tot:.0f}s stats={stats}")

# ---------- 第7天考问 ----------
QUESTION = "老王, 五天前你在邮局门口看到取包裹的那个人, 他穿什么颜色的外套? 往哪个方向走的? 请回忆具体细节。"

def ask_full_window(p):
    mem = "\n".join(f"[第{d}天] {t}" for d, t in p["memory"])
    prompt = f"""以下是 {p['name']} 从第1天到第7天的全部记忆, 按时间顺序排列:

{mem}

现在有人问你: {QUESTION}
请根据记忆如实回答, 只说事实, 不确定就说不确定。一句话回答。"""
    return chat([{"role": "user", "content": prompt}], max_tokens=1024)

def ask_rag(p):
    hits = rag_top(p["memory"], QUESTION, n=30)
    mem = "\n".join(f"[第{d}天] {t}" for _, _, d, t in hits)
    prompt = f"""以下是 {p['name']} 的记忆检索结果(按相关性排序):

{mem}

现在有人问你: {QUESTION}
请根据记忆如实回答, 只说事实, 不确定就说不确定。一句话回答。"""
    return chat([{"role": "user", "content": prompt}], max_tokens=1024)

laowang = personas[2]
print("\n== P1 生死闸门结果 ==")
print(f"老王总记忆: {len(laowang['memory'])} 条")
ans_full = ask_full_window(laowang)
print(f"[A 全量窗口] {ans_full!r}")
ans_rag = ask_rag(laowang)
print(f"[B RAG top30] {ans_rag!r}")

def score(ans):
    if not ans:
        return 0, "无输出"
    s = 0
    got = []
    if ("灰色" in ans or "灰" in ans):
        s += 1; got.append("灰色")
    if ("东" in ans and ("东头" in ans or "往东" in ans or "朝东" in ans or "东边的" in ans)):
        s += 1; got.append("东")
    return s, got

sf, gf = score(ans_full)
sr, gr = score(ans_rag)
print(f"\n判分: 全量={sf}/2 {gf}  RAG={sr}/2 {gr}")
if sf == 2 and sr < 2:
    print(">>> 结论: 卖点成立 (全量赢 RAG)")
elif sf < 2:
    print(">>> 结论: 危险 - 全量也没答对, 模型可能 lost-in-the-middle 或注入失败")
else:
    print(">>> 结论: RAG 也答对了, 卖点被证伪或差异不显著")

# 保存全部数据
out = {
    "stats": stats, "wall_s": time.time() - t0,
    "ans_full": ans_full, "ans_rag": ans_rag,
    "score_full": sf, "score_rag": sr,
    "n_memory": len(laowang["memory"]),
    "laowang_memory": laowang["memory"],
}
json.dump(out, open("/home/ubuntu/p1_result.json", "w"), ensure_ascii=False, indent=1)
print("结果已存 /home/ubuntu/p1_result.json")

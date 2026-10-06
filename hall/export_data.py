#!/usr/bin/env python3
"""导出 atria 运行数据 -> hall/data.json (展厅用)"""
import json, os, re, sys

REPO = os.path.expanduser("~/repos/atria")
RUNS = {
    "v2":   dict(dir=os.path.join(REPO, "run_v2"),   days=14, label="v2 有锚点+有引导",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v2s2": dict(dir=os.path.join(REPO, "run_v2s2"), days=14, label="v2 有锚+引·种子2",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v4np": dict(dir=os.path.join(REPO, "run_v4np"), days=14, label="v4 有锚点+无引导",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v4np2": dict(dir=os.path.join(REPO, "run_v4np2"), days=14, label="v4 无引导·种子2",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "hint0": dict(dir=os.path.join(REPO, "run_hint0"), days=14, label="v4 零锚点+有引导",
                 markers=["包裹","错领","扳指","邮局","纸箱","旧物"]),
    "hint0s2": dict(dir=os.path.join(REPO, "run_hint0s2"), days=14, label="v4 零锚+引·种子2",
                 markers=["包裹","错领","扳指","邮局","纸箱","旧物"]),
    "v3":   dict(dir=os.path.join(REPO, "run_v3"),                  days=35, label="v3 零注入",
                 markers=["远客","新来的","新来","南边来","本县人","外乡","那户人家","生面孔"]),
    "v3s2": dict(dir=os.path.join(REPO, "run_v3s2"),                days=35, label="v3 零注入·种子2",
                 markers=["远客","新来的","新来","南边来","本县人","外乡","那户人家","生面孔"]),
    "v3s3": dict(dir=os.path.join(REPO, "run_v3s3"),                days=35, label="v3 零注入·种子3",
                 markers=["喜事","婚事","出嫁","花轿","亲事","说媒","新娘","嫁衣","聘礼"]),
    "hint0g": dict(dir=os.path.join(REPO, "run_hint0g"),            days=14, label="v4 零锚+引·银元",
                 markers=["银元","山道","挖出","坛子","古墓","一坛","银圆"]),
    "multi": dict(dir=os.path.join(REPO, "run_multi"),              days=14, label="multi 双传闻并行",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"],
                 markers2=["银元","山道","挖出","坛子","古墓","一坛","银圆"]),
    "debunk": dict(dir=os.path.join(REPO, "run_debunk"),            days=14, label="debunk 第7天辟谣",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    # n=5 扩展轮 (seed 20261201-20261215)
    "v2s3": dict(dir=os.path.join(REPO, "run_v2s3"), days=14, label="v2 有锚+引·种子3",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v2s4": dict(dir=os.path.join(REPO, "run_v2s4"), days=14, label="v2 有锚+引·种子4",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v2s5": dict(dir=os.path.join(REPO, "run_v2s5"), days=14, label="v2 有锚+引·种子5",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v4np3": dict(dir=os.path.join(REPO, "run_v4np3"), days=14, label="v4 无引导·种子3",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v4np4": dict(dir=os.path.join(REPO, "run_v4np4"), days=14, label="v4 无引导·种子4",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v4np5": dict(dir=os.path.join(REPO, "run_v4np5"), days=14, label="v4 无引导·种子5",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "hint0s3": dict(dir=os.path.join(REPO, "run_hint0s3"), days=14, label="v4 零锚+引·种子3",
                 markers=["包裹","错领","扳指","邮局","纸箱","旧物"]),
    "hint0s4": dict(dir=os.path.join(REPO, "run_hint0s4"), days=14, label="v4 零锚+引·种子4",
                 markers=["包裹","错领","扳指","邮局","纸箱","旧物"]),
    "hint0s5": dict(dir=os.path.join(REPO, "run_hint0s5"), days=14, label="v4 零锚+引·种子5",
                 markers=["包裹","错领","扳指","邮局","纸箱","旧物"]),
    "v3s4": dict(dir=os.path.join(REPO, "run_v3s4"),                days=35, label="v3 零注入·种子4",
                 markers=["磨坊半夜","磨坊响","磨坊里响","磨坊的声响","半夜响","磨坊老有",
                          "磨盘松","磨盘底下","埋了东西","底下埋","埋了啥","刨开","刨磨盘",
                          "撬磨盘","邪乎","邪性","邪门"]),
    "v3s5": dict(dir=os.path.join(REPO, "run_v3s5"),                days=35, label="v3 零注入·种子5",
                 markers=["没影","失踪","找不着","找着了","下落","音信","他娘","急坏",
                          "不在铺里","进山几天"]),
    "multi2": dict(dir=os.path.join(REPO, "run_multi2"),            days=14, label="multi 双传闻·种子2",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"],
                 markers2=["银元","山道","挖出","坛子","古墓","一坛","银圆"]),
    "multi3": dict(dir=os.path.join(REPO, "run_multi3"),            days=14, label="multi 双传闻·种子3",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"],
                 markers2=["银元","山道","挖出","坛子","古墓","一坛","银圆"]),
    "debunk2": dict(dir=os.path.join(REPO, "run_debunk2"),          days=14, label="debunk 辟谣·种子2",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "debunk3": dict(dir=os.path.join(REPO, "run_debunk3"),          days=14, label="debunk 辟谣·种子3",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
}
sys.path.insert(0, REPO)
from atria_world import PLACES, HOMES_SOUTH, ROADS, GRID_W, GRID_H

personas = json.load(open(os.path.join(REPO, "atria_personas.json")))
agents = []
for p in personas:
    la = p["living_area"]
    box = PLACES.get(la, {}).get("box") or HOMES_SOUTH.get(la) or HOMES_SOUTH.get(la+"2")
    cx, cy = ((box[0]+box[2])/2, (box[1]+box[3])/2) if box else (20, 15)
    agents.append(dict(name=p["name"], role=p["occupation"], home=la,
                       cell=[cx, cy], persona=p["currently"], seed_role=p.get("seed_role","")))
aidx = {a["name"]: i for i, a in enumerate(agents)}

out = dict(
    grid=[GRID_W, GRID_H],
    places=[dict(name=n, box=s["box"]) for n, s in PLACES.items()],
    homes=[dict(name=n, box=b) for n, b in HOMES_SOUTH.items()],
    roads=[dict(name=n, box=b) for n, b in ROADS.items()],
    agents=agents,
    runs={},
)

for rid, spec in RUNS.items():
    d = spec["dir"]
    if not os.path.isdir(d):
        print(f"!! {rid}: {d} 不存在, 跳过"); continue
    events, pidx = [], {}
    for n in [x["name"] for x in out["places"]] + [x["name"] for x in out["homes"]]:
        pidx[n] = len(pidx)
    for day in range(1, spec["days"] + 1):
        f = os.path.join(d, f"day{day:02d}.jsonl")
        if not os.path.exists(f): continue
        for line in open(f):
            e = json.loads(line)
            pl = e.get("place", "")
            if pl not in pidx: pidx[pl] = len(pidx)
            events.append([day, e.get("step", 0), aidx.get(e["agent"], -1),
                           pidx[pl], e.get("say", ""), e.get("emoji", ""), e.get("activity", "")])
    # informed: 首个含 marker 的记忆出现日 (markers2 = 第二传闻, multi 用)
    all_markers = spec["markers"] + spec.get("markers2", [])
    informed, informed2, mem_rumor = {}, {}, {}
    for ai, a in enumerate(agents):
        mem_rumor[ai] = []
        for day in range(1, spec["days"] + 1):
            f = os.path.join(d, f"mem_day{day:02d}.json")
            if not os.path.exists(f): break
            recs = json.load(open(f)).get(a["name"], [])
            for r in recs:
                rd, rs, kind, text = r[0], r[1], r[2], r[3]
                hit1 = any(m in text for m in spec["markers"])
                hit2 = spec.get("markers2") and any(m in text for m in spec["markers2"])
                if hit1 or hit2:
                    mem_rumor[ai].append(r)
                    if ai not in informed and rd == day:
                        informed[ai] = day
                    if hit2 and ai not in informed2 and rd == day:
                        informed2[ai] = day
            if ai in informed and (not spec.get("markers2") or ai in informed2):
                break
        # rumor 记忆全量收集(不等 informed 提前 break)
        for day in range(informed.get(ai, 1), spec["days"] + 1):
            f = os.path.join(d, f"mem_day{day:02d}.json")
            if not os.path.exists(f): break
            for r in json.load(open(f)).get(a["name"], []):
                if any(m in r[3] for m in all_markers):
                    mem_rumor[ai].append(r)
        # checkpoint 逐日累积 → 同一记忆在多天的 checkpoint 里重复出现, 按内容去重保序
        seen, dedup = set(), []
        for r in mem_rumor[ai]:
            k = tuple(r)
            if k not in seen: seen.add(k); dedup.append(r)
        mem_rumor[ai] = dedup[:80]
    # 传播链路: 从 'X 告诉我/回我说: ...' 对话记忆提取 src->dst 边
    tell = re.compile(r"^(.+?)\s*(?:告诉我|回我说)[:：]")
    edges, ebest = [], {}
    for ai, rows in mem_rumor.items():
        for day, step, kind, text in rows:
            if kind != "对话":
                continue
            m = tell.match(text)
            if not m:
                continue
            src = aidx.get(m.group(1).strip())
            if src is None or src == ai:
                continue
            k = (src, ai)
            if k not in ebest or (day, step) < ebest[k][:2]:
                ebest[k] = (day, step, text[:60])
    for (src, dst), (day, step, txt) in sorted(ebest.items()):
        # first=该边发生的当天正好是 dst 的知情日(疑似首传)
        edges.append([src, dst, day, step, 1 if informed.get(dst) == day else 0, txt])
    out["runs"][rid] = dict(label=spec["label"], days=spec["days"], events=events,
                            informed=informed, place_index=pidx, mem_rumor=mem_rumor,
                            edges=edges)
    if informed2:
        out["runs"][rid]["informed_silver"] = informed2
        # informed 此时是"两传闻任一知情", 单独保留包裹口径供 fig13 用
        pkg_only = {}
        for ai, a in enumerate(agents):
            for day in range(1, spec["days"] + 1):
                f = os.path.join(d, f"mem_day{day:02d}.json")
                if not os.path.exists(f): break
                recs = json.load(open(f)).get(a["name"], [])
                if any(any(m in r[3] for m in spec["markers"]) and r[0] == day for r in recs):
                    pkg_only[ai] = day; break
        out["runs"][rid]["informed_pkg"] = pkg_only
    print(rid, len(events), "events; informed:", len(informed))

json.dump(out, open(os.path.join(os.path.dirname(__file__), "data.json"), "w"),
          ensure_ascii=False, separators=(",", ":"))
print("data.json:", os.path.getsize(os.path.join(os.path.dirname(__file__), "data.json")) // 1024, "KB")

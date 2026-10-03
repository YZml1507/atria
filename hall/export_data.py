#!/usr/bin/env python3
"""导出 atria 运行数据 -> hall/data.json (展厅用)"""
import json, os, re, sys

REPO = os.path.expanduser("~/repos/atria")
RUNS = {
    "v2":   dict(dir=os.path.join(REPO, "run_v2"),   days=14, label="v2 有锚点+有引导",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v4np": dict(dir=os.path.join(REPO, "run_v4np"), days=14, label="v4 有锚点+无引导",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "v4np2": dict(dir=os.path.join(REPO, "run_v4np2"), days=14, label="v4 无引导·种子2",
                 markers=["错领","包裹","扳指","旧物","纸箱","邮局"]),
    "hint0": dict(dir=os.path.join(REPO, "run_hint0"), days=14, label="v4 零锚点+有引导",
                 markers=["包裹","错领","扳指","邮局","纸箱","旧物"]),
    "v3":   dict(dir="/tmp/run_v3",                  days=35, label="v3 零注入",
                 markers=["远客","新来的","新来","南边来","本县人","外乡","那户人家","生面孔"]),
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
    # informed: 首个含 marker 的记忆出现日
    informed, mem_rumor = {}, {}
    for ai, a in enumerate(agents):
        mem_rumor[ai] = []
        for day in range(1, spec["days"] + 1):
            f = os.path.join(d, f"mem_day{day:02d}.json")
            if not os.path.exists(f): break
            recs = json.load(open(f)).get(a["name"], [])
            for r in recs:
                rd, rs, kind, text = r[0], r[1], r[2], r[3]
                if any(m in text for m in spec["markers"]):
                    mem_rumor[ai].append(r)
                    if ai not in informed and rd == day:
                        informed[ai] = day
            if ai in informed: break
        # rumor 记忆全量收集(不等 informed 提前 break)
        for day in range(informed.get(ai, 1), spec["days"] + 1):
            f = os.path.join(d, f"mem_day{day:02d}.json")
            if not os.path.exists(f): break
            for r in json.load(open(f)).get(a["name"], []):
                if any(m in r[3] for m in spec["markers"]):
                    mem_rumor[ai].append(r)
        mem_rumor[ai] = mem_rumor[ai][:80]
    out["runs"][rid] = dict(label=spec["label"], days=spec["days"], events=events,
                            informed=informed, place_index=pidx, mem_rumor=mem_rumor)
    print(rid, len(events), "events; informed:", len(informed))

json.dump(out, open(os.path.join(os.path.dirname(__file__), "data.json"), "w"),
          ensure_ascii=False, separators=(",", ":"))
print("data.json:", os.path.getsize(os.path.join(os.path.dirname(__file__), "data.json")) // 1024, "KB")

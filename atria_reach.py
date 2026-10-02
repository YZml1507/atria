# v3 终态测量: 远客传闻的记忆触达 (D21/D35)
import json, sys, re
run = sys.argv[1]
day = int(sys.argv[2])
KEY = re.compile(r"远客|新来|来了客|外来|不是本县|外乡|南边来")
mem = json.load(open(f"{run}/mem_day{day:02d}.json", encoding="utf-8"))
print(f"=== D{day} 记忆触达测量 ===")
reached = []
for person, recs in mem.items():
    hits = [r for r in recs if KEY.search(r[3] or "")]
    said = []
    for line in open(f"{run}/day{day:02d}.jsonl", encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("agent") == person and KEY.search(d.get("say") or ""):
            said.append(d.get("say")[:30])
    if hits or said:
        reached.append(person)
        kinds = {}
        for h in hits:
            kinds[h[2]] = (h[3] or "")[:50]
        print(f"[触达] {person}: 记忆{len(hits)}条 | 当日台词{len(said)}句")
        for k, v in list(kinds.items())[:3]:
            print(f"    {k}: {v}")
    else:
        print(f"[未触] {person}")
print(f"\n触达: {len(reached)}/25")

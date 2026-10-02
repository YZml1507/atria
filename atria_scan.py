# v3 话题扫描器 v4 (语料库式: 通用称呼自动剔除)
import json, re, sys
from collections import defaultdict

def phrases(say):
    return [m.group(0) for m in re.finditer(r"[一-龥]{2,6}", say)]

INJECT = re.compile(r"扳指|灰色|镇东头|错领|亡妻|旧纸箱|遗物")

def scan_day(path, freq_all=None):
    inject = 0
    ph_people = defaultdict(set)
    people_all = defaultdict(set)
    for line in open(path, encoding="utf-8"):
        try:
            d = json.loads(line)
        except Exception:
            continue
        say = d.get("say") or ""
        ag = d.get("agent", "?")
        if INJECT.search(say):
            inject += 1
        for p in phrases(say):
            ph_people[p].add(ag)
    # 回填通用词基线
    if freq_all:
        for p, ppl in freq_all.items():
            people_all[p] = set(ppl)
    rep = {}
    for p, ppl in ph_people.items():
        if len(ppl) < 2:
            continue
        # 通用词过滤: 该短语若出现在全镇语料里 >8 人, 是称呼/常用语, 剔除
        n_all = len(freq_all.get(p, [])) if freq_all else 0
        if n_all > 8:
            continue
        rep[p] = len(ppl)
    return rep, inject

if __name__ == "__main__":
    run_dir, day = sys.argv[1], sys.argv[2]
    # 基线: 全部天数里每个短语被多少人说过
    import glob
    base = defaultdict(set)
    for f in sorted(glob.glob(run_dir + "/day*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                d = json.loads(line)
            except Exception:
                continue
            for p in phrases(d.get("say") or ""):
                base[p].add(d.get("agent", "?"))
    rep, inj = scan_day(f"{run_dir}/day{int(day):02d}.jsonl", base)
    print(json.dumps({"day": int(day), "topics": rep, "inject_alarm": inj}, ensure_ascii=False))

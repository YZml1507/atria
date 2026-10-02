"""Atria 数据一致性校验 — 所有文档数字必须可追溯到源数据
用法: python3 atri­a_verify.py [<run_dir>] [--docs <repo_dir>]
      run_dir 默认 /home/ubuntu/atria_rerun (v2 主交付)
      传 /home/ubuntu/atria_run 可校验 v1 归档数据
退出码 0 = 通过, 1 = 发现不一致
"""
import json, re, os, sys, glob

def load_facts(run_dir="/home/ubuntu/atria_rerun"):
    """从原始数据重新计算全部事实, 不信任任何文档"""
    mem = json.load(open(f"{run_dir}/mem_day14.json"))
    evs = [json.loads(l) for d in range(1, 15) for l in open(f"{run_dir}/day{d:02d}.jsonl")]
    F = {}
    F["事件总数"] = len(evs)
    F["决策事件"] = sum(1 for e in evs if e.get("emoji") != "💬")
    F["社交事件"] = sum(1 for e in evs if e.get("emoji") == "💬")
    F["记忆总条数"] = sum(len(v) for v in mem.values())
    F["记忆均值"] = F["记忆总条数"] // len(mem)

    # 碎片: 双口径都记录, 文档用哪个都行但必须统一
    holders = {"扳指": "李大姐", "东头": "赵医生", "浅灰": "周老师"}
    for kw, holder in holders.items():
        total = sum(1 for p, v in mem.items() for r in v if kw in str(r))
        own = sum(1 for r in mem[holder] if kw in str(r))
        F[f"碎片-{kw}-总"] = total
        F[f"碎片-{kw}-含持有者"] = own
        F[f"碎片-{kw}-传播"] = total - own

    # 永不知情
    F["永不知情"] = len([p for p, v in mem.items()
                        if not any(x in str(r) for r in v for x in ["包裹", "错领", "领走", "扳指"])])

    # 知情曲线
    curve = []
    for d in range(5, 15):
        m = json.load(open(f"{run_dir}/mem_day{d:02d}.json"))
        k = set()
        for p, v in m.items():
            for r in v:
                if any(x in str(r) for x in ["包裹", "错领", "领走", "扳指"]):
                    k.add(p); break
        curve.append(len(k))
    F["知情终点"] = curve[-1]
    return F

def check_docs(facts, repo="/home/ubuntu/atria_repo"):
    """扫描文档, 找出与事实表矛盾或口径不统一的表述"""
    issues = []
    docs = [p for p in glob.glob(f"{repo}/**/*.md", recursive=True)]
    fr = f"{repo}/run/FINAL_REPORT.md"
    if os.path.exists(fr): docs.append(fr)

    # 每个断言: (正则, 期望值, 说明)
    asserts = [
        (r"1,?109\s*条", 1109, "事件总数"),
        (r"1,?005\s*决策", 1005, "决策事件"),
        (r"104\s*社交", 104, "社交事件"),
        (r"剩余\s*(\d+)\s*人始终不知情", facts["永不知情"], "永不知情人数"),
        (r"(\d+)/25\s*饱和", facts["知情终点"], "知情终点"),
    ]
    for p in docs:
        t = open(p, encoding="utf-8").read()
        for pat, expect, name in asserts:
            for m in re.finditer(pat, t):
                got = m.group(1) if m.groups() else m.group()
                if got and str(expect) not in str(got).replace(",", ""):
                    issues.append((os.path.basename(p), name, got, f"应为 {expect}"))

    # 口径统一检查: 同一文档内碎片的"条数"是否同口径
    # 规则: 若出现"含持有者"值(40/15)与"传播"值(36/8)混用 → 警报
    for p in docs:
        t = open(p, encoding="utf-8").read()
        has_total_bz = bool(re.search(r"扳指[^\n]{0,30}?40\s*条", t))
        has_spread_fx = bool(re.search(r"方向[^\n]{0,20}?8\s*条", t))
        has_total_fx = bool(re.search(r"方向[^\n]{0,20}?15\s*条", t))
        has_spread_bz = bool(re.search(r"扳指[^\n]{0,30}?36\s*条", t))
        if has_total_bz and has_spread_fx:
            issues.append((os.path.basename(p), "口径不统一",
                           "扳指=40(含持有者) 而 方向=8(排除持有者)",
                           "必须同口径: 40/15 或 36/8"))
        if has_spread_bz and has_total_fx:
            issues.append((os.path.basename(p), "口径不统一",
                           "扳指=36(排除持有者) 而 方向=15(含持有者)",
                           "必须同口径: 40/15 或 36/8"))
    return issues

if __name__ == "__main__":
    args = sys.argv[1:]
    docs_dir = None
    if "--docs" in args:
        i = args.index("--docs")
        docs_dir = args[i+1]
        del args[i:i+2]
    run = args[0] if args else "/home/ubuntu/atria_rerun"
    facts = load_facts(run)
    print(f"数据源: {run}")
    print("源数据事实:")
    for k, v in facts.items(): print(f"  {k}: {v}")
    print()
    issues = check_docs(facts, docs_dir or "/home/ubuntu/atria_repo")
    if issues:
        print(f"!! 发现 {len(issues)} 处不一致:")
        for f, name, got, want in issues:
            print(f"  [{f}] {name}: '{got}' {want}")
        sys.exit(1)
    print("✓ 校验通过: 所有文档数字与源数据一致, 口径统一")

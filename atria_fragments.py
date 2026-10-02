"""三碎片传播口径锁定脚本 (v2, D14 记忆)

判定规则 (程序化, 唯一结果):
  - 扳指: 名词, grep 无歧义
  - 颜色: 须同时排除"丝线颜色正/彩线颜色正"类日常记忆
  - 方向: 短语碎片, 须区分"碎片转述"与"地名日常提及"
         转述 = 方向词 (东头/往东) + 包裹语境词 (纸箱/包裹/抱/错领) 双条件

输出: 唯一三个数 + 逐条传播者清单, 供 verify 与文档引用
"""
import json, re, sys, os

HOLDERS = {"扳指": "李大姐", "方向": "赵医生", "颜色": "周老师"}

def is_ring(s):
    return "扳指" in s

def is_color(s):
    # 碎片内容: "衣裳颜色偏浅, 好像是灰色"
    return bool(re.search(r'(灰色|偏浅|衣裳.{0,6}(灰|浅)|浅色衣|浅色)', s))

def is_direction_spread(s):
    # 碎片原话: "抱纸箱往镇东头走"
    has_dir = bool(re.search(r'(镇东头|往东|东头|朝东)', s))
    has_ctx = bool(re.search(r'(纸箱|包裹|抱|错领|领走)', s))
    return has_dir and has_ctx

RULES = {"扳指": is_ring, "方向": is_direction_spread, "颜色": is_color}

def main(run_dir="/home/ubuntu/atria_rerun", verbose=True):
    mem = json.load(open(os.path.join(run_dir, "mem_day14.json"), encoding="utf-8"))
    out = {}
    for frag, fn in RULES.items():
        holder = HOLDERS[frag]
        spread_counts = {}
        own = 0
        for agent, mems in mem.items():
            if agent == holder:
                own = sum(1 for m in mems if fn(str(m)))
                continue
            k = sum(1 for m in mems if fn(str(m)))
            if k:
                spread_counts[agent] = k
        total_spread = sum(spread_counts.values())
        out[frag] = {"传播": total_spread, "持有者自记": own,
                     "总计": total_spread + own, "传播者": spread_counts}
    if verbose:
        for frag, r in out.items():
            p = ", ".join(f"{a}({n})" for a, n in sorted(r["传播者"].items(), key=lambda x: -x[1]))
            print(f"{frag}: 传播 {r['传播']} / 持有者自记 {r['持有者自记']} / 总 {r['总计']}")
            print(f"  传播者: {p}")
    # 机器可读
    facts = {f"碎片-{frag}-传播": out[frag]["传播"] for frag in out}
    facts["碎片-口径"] = "D14记忆 | 排除持有者自记 | 方向=转述双条件 | 颜色=排除日常"
    return out, facts

if __name__ == "__main__":
    run = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/atria_rerun"
    main(run)

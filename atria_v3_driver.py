# v3 三段式预设终点驱动
# 规则(跑之前定死, 不根据结果调整):
#   1) 基准 21 天, 跑满
#   2) 每日扫描: 若出现"实体话题跨>=2人" -> 标记为"有蔓延", 续跑到 35 天
#   3) 若 D15-21 连续 7 天无任何新跨人话题 -> 冻结, 停止
import subprocess, sys, os, json, time, glob

HERE = "/home/ubuntu/atria_v3"
RUN = "/home/ubuntu/atria_v3/run_v3"
BASE_DAYS = 21
EXT_DAYS = 35
FROZEN_WINDOW = 7  # 连续 N 天无新话题 -> 冻结

def scan(day):
    r = subprocess.run(["/usr/bin/python3.12", f"{HERE}/atria_scan.py", RUN, str(day)],
                       capture_output=True, text=True, timeout=120,
                       env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/home/ubuntu"})
    try:
        return json.loads(r.stdout.strip())
    except Exception:
        return {"day": day, "topics": {}, "inject_alarm": 0, "err": r.stdout[:200]}

def main():
    phase = "base"
    days_done = 0
    spread_days = []     # 出现跨人话题的天
    new_topic_streak = 0 # 连续无新话题天数
    total = BASE_DAYS
    day = 1
    while day <= total:
        # 引擎每天单独跑(断点续跑), 防止一次跑 21 天被 OOM 杀
        start = day
        r = subprocess.run(["/usr/bin/python3.12", f"{HERE}/" + glob.glob("*engine*.py")[0].split("/")[-1],
                            "1", "--seed", "20261014", "--outdir", RUN,
                            "--start", str(day), str(day)],
                           capture_output=True, text=True, timeout=3600,
                           env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/home/ubuntu",
                                "ATRIA_OUT": RUN})
        print(f"[D{day}]", r.stdout[-200:].replace("\n", " | "), flush=True)
        if r.returncode != 0:
            print(f"!! D{day} 引擎返回 {r.returncode}", r.stderr[-300:], flush=True)
            break
        s = scan(day)
        topics = s.get("topics", {})
        alarm = s.get("inject_alarm", 0)
        if alarm:
            print(f"!!!! 注入泄漏报警 D{day}: {alarm} 处 -- 注入没清干净", flush=True)
        if topics:
            spread_days.append(day)
            new_topic_streak = 0
            print(f"[D{day}] 跨人话题: {topics}", flush=True)
        else:
            new_topic_streak += 1
        # 续跑判定: 基准期末
        if phase == "base" and day == BASE_DAYS:
            if spread_days:
                print(f"[判定] 基准期 {BASE_DAYS} 天内出现跨人话题 (D{spread_days}) -> 续跑到 {EXT_DAYS} 天", flush=True)
                phase = "ext"; total = EXT_DAYS
            else:
                # 冻结判定: 后段 D15-21 无新话题
                late = [d for d in spread_days if d >= BASE_DAYS - FROZEN_WINDOW + 1]
                if not late:
                    print(f"[判定] 基准期后段连续 {FROZEN_WINDOW} 天无新跨人话题 -> 冻结, 停止于 D{day}", flush=True)
                    break
                else:
                    print(f"[判定] 后段仍有话题 D{late} -> 续跑到 {EXT_DAYS}", flush=True)
                    phase = "ext"; total = EXT_DAYS
        day += 1
    print(f"[结束] phase={phase} days={day-1} spread_days={spread_days}", flush=True)

if __name__ == "__main__":
    main()

"""按 RPM=50 精确推导各规模所需时间"""
import math
def hours(calls, rpm=50, conc=4):
    # 限流是账号级，并发不能突破 RPM；有效速率 = rpm
    return calls / rpm / 60

scenarios = [
    ("极简版  8人 x 12步",   8*12,   96),
    ("标准版 25人 x 24步",  25*24,  600),
    ("豪华版 32人 x 48步",  32*48, 1536),
    ("旗舰版 40人 x 72步",  40*72, 2880),
]
print(f"{'规模':22} {'调用数':>6} {'RPM=50 纯调用':>14} {'+渲染/编排预估':>14}")
for name, calls, _ in scenarios:
    h = hours(calls)
    print(f"{name:22} {calls:>6} {h*60:>10.1f} 分 {h*60*1.35:>10.1f} 分")
print()
print("外推到 2 小时视频素材(约 300k tokens):")
print(f"  纯调用 {hours(2000)*60:.0f} 分钟，含渲染/编排约 {hours(2000)*60*1.35:.0f} 分钟")

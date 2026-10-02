"""RPM 复测 2: 排除推理开销的干扰,直接测 requests-per-minute 限额。
最小请求(max_tokens=8,content 会因 reasoning 变 null,但 HTTP 200/429 是真实的)。
持续 2 分钟, 每 1.15 秒发 1 个(=52 RPM), 看是否触发 429。
"""
import json, urllib.request, time, subprocess, urllib.error

KEY = subprocess.run(
    ["bash", "-c",
     "grep '^HERMES_CUSTOM_DISCOVERY_API_INTERN_AI_ORG_CN_API_KEY=' /home/ubuntu/.hermes/.env | head -1 | cut -d= -f2-"],
    capture_output=True, text=True, timeout=60).stdout.strip()
URL = "https://discovery-api.intern-ai.org.cn/v1/chat/completions"
MODEL = "Atria-Dawn-Preview"


def one_call():
    body = json.dumps({"model": MODEL,
                       "messages": [{"role": "user", "content": "OK"}],
                       "max_tokens": 8, "temperature": 0})
    req = urllib.request.Request(
        URL, data=body.encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + KEY})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return time.time() - t, r.status, None
    except urllib.error.HTTPError as e:
        return time.time() - t, e.code, e.read()[:120].decode(errors="replace")
    except Exception as e:
        return time.time() - t, -1, str(e)[:80]


DURATION = 120.0
INTERVAL = 1.15  # = 52 RPM
results = []
t_end = time.time() + DURATION
i = 0
while time.time() < t_end:
    dt, code, err = one_call()
    results.append((time.time(), code, dt, err))
    i += 1
    if i % 20 == 0:
        ok = sum(1 for _, c, _, _ in results if c == 200)
        r429 = sum(1 for _, c, _, _ in results if c == 429)
        print(f"  [{time.time()-t_end+DURATION:5.0f}s] 已发 {i}: 200={ok} 429={r429} lat={dt:.2f}s")
    # 按节拍等
    elapsed = time.time() - (t_end - DURATION)
    target = i * INTERVAL
    if elapsed < target:
        time.sleep(target - elapsed)

ok = sum(1 for _, c, _, _ in results if c == 200)
r429 = sum(1 for _, c, _, _ in results if c == 429)
other = [r for r in results if r[1] not in (200, 429)]
print(f"== 2 分钟节流测试结果 ==")
print(f"  总请求 {len(results)}: 200={ok} 429={r429} 其他={len(other)}")
print(f"  实际 achieved RPM = {len(results)/2:.1f}")
if other:
    for t, c, dt, e in other[:5]:
        print(f"   {c}: {e}")
lat_ok = [dt for _, c, dt, _ in results if c == 200]
if lat_ok:
    print(f"  200 延迟: min={min(lat_ok):.2f} med={sorted(lat_ok)[len(lat_ok)//2]:.2f} max={max(lat_ok):.2f}")

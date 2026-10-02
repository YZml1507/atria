import subprocess, sys, os, glob, json, time
HERE = "/home/ubuntu/atria_v3"
RUN = "/home/ubuntu/atria_v3/run_v3"
eng = glob.glob(HERE + "/*engine*.py")[0]
for day in range(22, 36):
    print(f"[D{day}] 启动...", flush=True)
    r = subprocess.run(["/usr/bin/python3.12", eng, "1", "--seed", "20261014",
                        "--outdir", RUN, "--start", str(day), str(day)],
                       capture_output=True, text=True, timeout=1800,
                       env={"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": "/home/ubuntu",
                            "ATRIA_OUT": RUN})
    tail = r.stdout[-160:].replace("\n", " | ")
    print(f"[D{day}] rc={r.returncode} {tail}", flush=True)
    if r.returncode != 0:
        print(f"!! D{day} 失败: {r.stderr[-300:]}", flush=True)
        break
print("[完成] D22-35", flush=True)

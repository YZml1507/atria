#!/usr/bin/env python3
"""用 Git Data API 把本地 main 分支推送到远端 (绕过 github.com 间歇不通)
流程: create blob (新增+修改) → build tree → create commit → update ref
"""
import subprocess, json, base64, os, time, sys

REPO = "/home/ubuntu/atria_repo"
API = "https://api.github.com/repos/YZml1507/atria"

def get_token():
    return open("/home/ubuntu/.github_token", "r", encoding="utf-8").read().strip()

TOKEN = get_token()
ENV = dict(os.environ)
ENV["GH_TOKEN"] = TOKEN

def curl(method, endpoint, data=None, timeout=180):
    import tempfile
    payload = json.dumps(data) if data is not None else "{}"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        f.write(payload)
        tmp = f.name
    try:
        r = subprocess.run(
            ["bash", "-c",
             f'curl -s -X {method} -H "Authorization: Bearer $GH_TOKEN" '
             f'-H "Content-Type: application/json" -d @{tmp} {API}{endpoint}'],
            capture_output=True, text=True, timeout=timeout, env=ENV)
        try:
            return json.loads(r.stdout)
        except Exception:
            return {"error": r.stdout[:300]}
    finally:
        os.unlink(tmp)

def git(*args):
    r = subprocess.run(["git", "-C", REPO, "-c", "core.quotepath=false"] + list(args),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()

def main():
    # 1) 远端 main 当前 tree
    r = curl("GET", "/git/trees/main?recursive=1")
    remote = {t["path"]: t for t in r.get("tree", [])}
    print(f"远端 main: {len(remote)} 文件")

    local_paths = git("ls-tree", "-r", "main", "--name-only").split("\n")
    local_paths = [p for p in local_paths if p]
    print(f"本地 main: {len(local_paths)} 文件")

    # 2) 计算差异
    tree_entries = []  # 保留的 + 新增的
    n_blob = 0
    for path in local_paths:
        local_sha = git("rev-parse", f"main:{path}")
        remote_entry = remote.get(path)
        if remote_entry and remote_entry.get("sha") == local_sha:
            # 未变 → 直接用 blob sha
            tree_entries.append({"path": path, "mode": remote_entry["mode"],
                                 "type": "blob", "sha": local_sha})
            continue
        # 新增或修改 → create blob
        full = os.path.join(REPO, path)
        if not os.path.exists(full):
            print(f"  跳过(文件不存在): {path}")
            continue
        is_bin = path.endswith((".mp4", ".mp3", ".png", ".ttf"))
        if is_bin:
            with open(full, "rb") as f:
                content = base64.b64encode(f.read()).decode()
            br = curl("POST", "/git/blobs", {"content": content, "encoding": "base64"})
        else:
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
            br = curl("POST", "/git/blobs", {"content": content, "encoding": "utf-8"})
        if not br.get("sha"):
            print(f"  blob 失败: {path} → {str(br)[:120]}")
            return False
        tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": br["sha"]})
        n_blob += 1
        if n_blob % 20 == 0:
            print(f"  已建 {n_blob} blob...")
        time.sleep(0.15)  # 避免 rate limit

    print(f"新建 blob: {n_blob}, 直接引用: {len(tree_entries)-n_blob}")

    # 3) build tree
    tr = curl("POST", "/git/trees", {"tree": tree_entries})
    if not tr.get("sha"):
        print("build tree 失败:", str(tr)[:300])
        return False
    print(f"新 tree: {tr['sha'][:10]}")

    # 4) create commit (parent = 远端 main 当前头)
    r2 = curl("GET", "/branches/main")
    parent_sha = r2["commit"]["sha"]
    cm = curl("POST", "/git/commits", {
        "message": "v2 主交付: 三碎片口径锁定 + 强校验 + v4 视频",
        "tree": tr["sha"],
        "parents": [parent_sha],
    })
    if not cm.get("sha"):
        print("create commit 失败:", str(cm)[:300])
        return False
    print(f"新 commit: {cm['sha'][:10]}")

    # 5) update ref
    ur = curl("PATCH", "/git/refs/heads/main", {"sha": cm["sha"]})
    if not ur.get("object", {}).get("sha"):
        print("update ref 失败:", str(ur)[:300])
        return False
    print(f"✓ 远端 main 已更新: {ur['object']['sha'][:10]}")
    return True

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)

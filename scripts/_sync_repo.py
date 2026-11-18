# -*- coding: utf-8 -*-
"""同步 nahan-tea-blog 全部可寫檔案到 GitHub（Contents API，中文/二進位皆可）。"""
import os, base64, json, urllib.request, urllib.error, urllib.parse, time

TOKEN = os.environ.get("GH_TOKEN", "")
REPO = "hanchaoqun8/dazi-tea-blog"
BASE = f"https://api.github.com/repos/{REPO}"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "logs", "node_modules", "__pycache__"}
SKIP_FILES = {"_ghkey.json", "_blob.json", "_tree.json"}
# 同步 images-final(文章配圖，CI 部署需要) 與 site 靜態檔；不同步原始大圖 images-source
EXTRA_SKIP_PREFIX = ("images-source/",)


def api(path, method="GET", data=None, retries=4):
    for attempt in range(retries):
        req = urllib.request.Request(BASE + path, method=method,
            data=json.dumps(data).encode() if data else None,
            headers={"Authorization": "Bearer " + TOKEN, "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=40)
            return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            return 0, {"message": str(e)}
    return 0, {"message": "retry exhausted"}


# 遠端現有檔案 sha（避免重複 PUT 報錯）
_, tree = api("/git/trees/main?recursive=1")
remote = {t["path"]: t["sha"] for t in tree.get("tree", []) if t["type"] == "blob"}

files = []
for root, dirs, fnames in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    for fn in fnames:
        if fn in SKIP_FILES or fn.endswith(".pyc"): continue
        full = os.path.join(root, fn)
        rel = os.path.relpath(full, ROOT).replace("\\", "/")
        if rel.startswith(EXTRA_SKIP_PREFIX): continue
        files.append((rel, full))

# 進度記錄（斷點續傳）
progress_path = os.path.join(ROOT, "docs", "_sync_progress.json")
done = set(json.load(open(progress_path, encoding="utf-8"))) if os.path.exists(progress_path) else set()

ok = fail = 0
for rel, full in files:
    if rel in done:
        ok += 1
        continue
    data = open(full, "rb").read()
    payload = {"message": f"sync {rel}", "content": base64.b64encode(data).decode(), "branch": "main"}
    if rel in remote:
        payload["sha"] = remote[rel]
    enc_path = urllib.parse.quote(rel, safe="/")
    code, res = api(f"/contents/{enc_path}", "PUT", payload)
    if code in (200, 201):
        ok += 1
        done.add(rel)
        json.dump(sorted(done), open(progress_path, "w", encoding="utf-8"))
    else:
        fail += 1
        print(f"FAIL {rel}: {code} {res.get('message')}")
print(f"[sync] ok={ok} fail={fail} total={len(files)}")

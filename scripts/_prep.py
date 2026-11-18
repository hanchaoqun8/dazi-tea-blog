# -*- coding: utf-8 -*-
"""一次性准备：建骨架 + 测 API + 归集图片素材"""
import os, shutil, json, urllib.request, urllib.error

ROOT = r"F:/Sites/nahan-tea-blog"
for d in ["notes", "images-source", "images-final", "published",
          "used-notes", "scripts", "site/assets/img", ".github/workflows", "docs"]:
    os.makedirs(os.path.join(ROOT, d), exist_ok=True)
print("[dirs] ok")

# ---------- API 测试 ----------
def test_api(url, token, body, label):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8",
    })
    try:
        r = urllib.request.urlopen(req, timeout=40)
        txt = r.read().decode("utf-8", "replace")
        print(f"[api:{label}] HTTP {r.status} :: {txt[:300]}")
    except urllib.error.HTTPError as e:
        print(f"[api:{label}] HTTP {e.code} :: {e.read().decode('utf-8','replace')[:300]}")
    except Exception as e:
        print(f"[api:{label}] ERR :: {type(e).__name__} {str(e)[:200]}")

zp = os.environ.get("ZP_TOKEN", "")
ms = os.environ.get("MS_TOKEN", "")
if zp:
    test_api("https://open.bigmodel.cn/api/paas/v4/chat/completions", zp,
             {"model": "glm-4-flash", "messages": [{"role": "user", "content": "Reply OK"}], "max_tokens": 10}, "zhipu")
if ms:
    test_api("https://api-inference.modelscope.cn/v1/chat/completions", ms,
             {"model": "deepseek-ai/DeepSeek-V4-Flash-0731", "messages": [{"role": "user", "content": "Reply OK"}], "max_tokens": 10}, "modelscope")

# ---------- 归集图片 ----------
src_clip = r"C:/Users/哪罕/.workbuddy/clipboard-images"
src_puh = r"F:/茶图片/朴衡"
dst = os.path.join(ROOT, "images-source")
n_clip = n_puh = 0
if os.path.isdir(src_clip):
    for f in sorted(os.listdir(src_clip)):
        if "2026-11-18T10-14" in f and f.lower().endswith((".jpg", ".jpeg", ".png")):
            shutil.copy2(os.path.join(src_clip, f), os.path.join(dst, f))
            n_clip += 1
if os.path.isdir(src_puh):
    for f in sorted(os.listdir(src_puh)):
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
            shutil.copy2(os.path.join(src_puh, f), os.path.join(dst, f))
            n_puh += 1
print(f"[images] clipboard={n_clip} puhneg={n_puh} total={len(os.listdir(dst))}")

# ---------- 视频清单 ----------
vdir = r"F:/茶图片/哪罕视频"
if os.path.isdir(vdir):
    vids = [f for f in os.listdir(vdir) if f.lower().endswith((".mp4", ".mov"))]
    with open(os.path.join(ROOT, "docs", "videos-inventory.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(sorted(vids)))
    print(f"[videos] {len(vids)} -> docs/videos-inventory.txt")

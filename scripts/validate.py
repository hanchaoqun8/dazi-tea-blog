# -*- coding: utf-8 -*-
"""文章合格性校验：繁体、结构、禁令、配图存在性、字数。"""
import os, re, sys
from opencc import OpenCC

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "published")
IMGF = os.path.join(ROOT, "images-final")
s2t = OpenCC("s2t")
t2s = OpenCC("t2s")

BANNED = ["頂級", "天花板", "神茶", "名貴", "稀缺", "降血壓", "減肥", "排毒", "抗癌", "增強免疫力", "理財茶"]
# 這些詞僅在「肯定/推薦」語境才違規；在「不碰/不炒/反對」批判語境屬合法表態
CONTEXT_BANNED = ["投資茶", "保值茶", "金融茶"]
CRITIQUE_MARKERS = ["不碰", "不玩", "不炒", "不鼓勵", "從不", "反對", "不做", "不搞"]
# 繁簡同形/異體字，OpenCC 會誤判，加入白名單（這些字在繁體中亦通用）
VARIANT_OK = {"峰": "峯", "干": "幹", "欲": "慾", "里": "裡", "后": "后"}
REQUIRED_H2 = ["一、產地真實風土", "二、茶農做茶本心", "三、禪茶一味", "四、百姓日常飲茶真義"]
REQUIRED_FM = ["title", "slug", "date", "description", "keywords", "cover", "image_caption"]


def check(path):
    errs, warns = [], []
    txt = open(path, encoding="utf-8").read()
    fn = os.path.basename(path)
    # 繁体检测：把简体字转繁体后若与原文差异大 => 含简体
    conv = s2t.convert(txt)
    # 忽略标点/空白差异，只比较汉字；逐字符找被转换的简字
    simplified = []
    for a, b in zip(txt, conv):
        if a != b and "\u4e00" <= a <= "\u9fff" and "\u4e00" <= b <= "\u9fff":
            if a in VARIANT_OK: continue
            simplified.append(f"{a}->{b}")
    if simplified:
        errs.append("簡體字: " + " ".join(sorted(set(simplified))[:25]))
    # front matter
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", txt, re.S)
    if not m:
        errs.append("缺少 front matter"); return errs, warns
    fm, body = m.group(1), m.group(2)
    for k in REQUIRED_FM:
        if not re.search(rf"^{k}:", fm, re.M): errs.append(f"缺 front matter 欄位 {k}")
    # 字数（中文字符）
    words = len(re.findall(r"[\u4e00-\u9fff]", body))
    if not (750 <= words <= 1250): warns.append(f"字數 {words}（目標800-1100）")
    for h in REQUIRED_H2:
        if h not in body: errs.append(f"缺章節 {h}")
    if "常見問題" not in body and "FAQ" not in body: errs.append("缺 FAQ")
    if "配圖" not in body: warns.append("無配圖佔位")
    # 禁令（绝对词）
    for b in BANNED:
        if b in txt: errs.append(f"禁用詞 [{b}]")
    # 語境詞：整句含批判標記才合法
    for line in body.splitlines():
        for b in CONTEXT_BANNED:
            if b in line and not any(mk in line for mk in CRITIQUE_MARKERS):
                errs.append(f"禁用詞(非批判語境) [{b}] :: {line.strip()[:40]}")
    if "哪罕村" in body: errs.append("出現禁用地名 哪罕村")
    # 配图存在
    covers = re.findall(r"images-final/([A-Za-z0-9_-]+\.jpg)", txt)
    for c in covers:
        if not os.path.exists(os.path.join(IMGF, c)): errs.append(f"配圖不存在 {c}")
    warns.insert(0, f"正文約{words}字, 配圖{len(set(covers))}張")
    return errs, warns


def main():
    total_err = 0
    for f in sorted(os.listdir(PUB)):
        if not f.endswith(".md"): continue
        errs, warns = check(os.path.join(PUB, f))
        print(f"\n=== {f} ===")
        for w in warns: print("  i", w)
        for e in errs: print("  X", e); total_err += 1
        if not errs: print("  OK 通過")
    print(f"\n[validate] 錯誤總數={total_err}")
    return total_err


if __name__ == "__main__":
    sys.exit(1 if main() else 0)

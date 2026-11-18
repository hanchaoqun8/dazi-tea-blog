# -*- coding: utf-8 -*-
"""把 474 篇普洱茶知識鏡像轉成精簡後備資料庫（供每日寫作檢索，不照抄）。"""
import os, re, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
s = open(os.path.join(ROOT, "docs", "_knowledge_data.js"), encoding="utf-8").read()
d = json.loads(re.search(r"=\s*(\{.*\})", s, re.S).group(1))
items = d["items"]
meta = d["meta"]

# 1) 完整索引（標題+摘要+分類+來源），供 API 檢索
slim = [{"t": x.get("title", ""), "s": x.get("summary", "")[:200],
         "c": x.get("category", ""), "u": x.get("url", "")} for x in items]
with open(os.path.join(ROOT, "docs", "knowledge-library.json"), "w", encoding="utf-8") as f:
    json.dump({"meta": {k: meta.get(k) for k in ("total", "categories", "source", "fetchedAt")},
               "items": slim}, f, ensure_ascii=False, indent=1)

# 2) 分類統計 + 與哪罕寨主題最相關的分類優先
from collections import Counter
cnt = Counter(x.get("category", "") for x in items)
with open(os.path.join(ROOT, "docs", "knowledge-library.md"), "w", encoding="utf-8") as f:
    f.write("# 茶知識後備資料庫（鏡像自 new.dazi.uk/knowledge.html）\n\n")
    f.write(f"共 {meta.get('total')} 篇，抓取時間 {meta.get('fetchedAt')}。")
    f.write("來源：中國普洱茶網、故宮博物院等公開欄目。\n\n")
    f.write("> 用途：每日寫作時作**知識背景**參考，輔助潤色；不得整段照抄，")
    f.write("不得引入與「不炒作、回歸本心」中心思想衝突的內容（如功效、金融茶、名貴稀缺）。\n\n")
    f.write("## 分類概覽\n\n")
    for c, n in cnt.most_common():
        f.write(f"- {c}：{n} 篇\n")
    f.write("\n## 與哪罕寨主題高度相關的分類（優先檢索）\n\n")
    for c in ["製作工藝", "種植栽培", "產地名山", "古樹茶", "生普熟普", "存放倉儲", "基礎知識", "茶文化"]:
        if c in cnt:
            f.write(f"- **{c}**（{cnt[c]} 篇）\n")

# 3) 每日寫作用：按分類抽取的精選標題池（供 LLM prompt 注入）
with open(os.path.join(ROOT, "docs", "knowledge-topics.json"), "w", encoding="utf-8") as f:
    json.dump({c: [x.get("title", "") for x in items if x.get("category") == c][:40]
               for c in meta.get("categories", [])}, f, ensure_ascii=False, indent=1)

print(f"[knowledge] {len(items)} 篇 -> knowledge-library.json/.md + knowledge-topics.json")
print("[categories]", ", ".join(f"{c}:{n}" for c, n in cnt.most_common(8)))

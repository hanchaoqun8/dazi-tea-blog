# -*- coding: utf-8 -*-
"""每日自動化流水線（GitHub Actions 每日 08:00 昆明時間執行）
流程：讀一筆未用筆記 -> 選取同名/關聯實拍圖 -> 調智譜(失效回退魔搭) ->
生成繁體雙模文章 -> 存 published -> 筆記移 used-notes -> 重建雙站 -> 日志。
兜底：無筆記 / API 皆不可用 / 圖片異常 -> 停止並寫告警，絕不亂編。
"""
import os, re, sys, json, shutil, datetime, urllib.request, urllib.error
from opencc import OpenCC

S2T = OpenCC("s2t")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = os.path.join(ROOT, "notes")
USED = os.path.join(ROOT, "used-notes")
PUB = os.path.join(ROOT, "published")
IMG = os.path.join(ROOT, "images-final")
LOG_DIR = os.path.join(ROOT, "logs")
for d in (USED, PUB, LOG_DIR):
    os.makedirs(d, exist_ok=True)

LOG = os.path.join(LOG_DIR, "daily_post.log")


def log(level, msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {level} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


# 使用者指定模型池（依優先順序；平台已下線者會自動跳過，不硬失敗）
ZHIPU_MODELS = ["glm-4-plus", "glm-4.7", "glm-4.7-flash", "glm-4-flash", "glm-4"]
MODELSCOPE_MODELS = ["Qwen/Qwen3.5-27B", "Qwen/Qwen3.8-Flash-Next", "ZhipuAI/GLM-4.7-Flash",
                     "Qwen/Qwen2.5-7B-Instruct", "internlm/internlm2_5-7b-chat"]


def call_llm(messages, max_tokens=2400):
    """智譜優先，魔搭回退；依模型池逐一嘗試，跳過下線/限流者。"""
    zp_key = os.environ.get("ZHIPU_API_KEY", "")
    ms_key = os.environ.get("MODELSCOPE_API_KEY", "")
    providers = []
    if zp_key:
        zp_models = [os.environ.get("ZHIPU_MODEL", "")] + ZHIPU_MODELS \
            if os.environ.get("ZHIPU_MODEL") else ZHIPU_MODELS
        providers.append(("zhipu", "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                          zp_key, list(dict.fromkeys(zp_models))))
    if ms_key:
        ms_models = [os.environ.get("MODELSCOPE_MODEL", "")] + MODELSCOPE_MODELS \
            if os.environ.get("MODELSCOPE_MODEL") else MODELSCOPE_MODELS
        providers.append(("modelscope", "https://api-inference.modelscope.cn/v1/chat/completions",
                          ms_key, list(dict.fromkeys(ms_models))))
    if not providers:
        return None, "NO_API_KEY"

    for name, url, key, model_list in providers:
        for attempt_model in model_list:
            payload = {"model": attempt_model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.8}
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json; charset=utf-8",
            })
            try:
                r = urllib.request.urlopen(req, timeout=90)
                res = json.loads(r.read().decode("utf-8"))
                content = res["choices"][0]["message"]["content"]
                log("INFO", f"模型呼叫成功：{name} / {attempt_model}")
                return content, attempt_model
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")[:200]
                log("WARN", f"模型 {name}/{attempt_model} HTTP {e.code}: {body}")
                if e.code in (401, 403):
                    break  # 帳號級錯誤，換供應商
                continue
            except Exception as e:
                log("WARN", f"模型 {name}/{attempt_model} 異常: {type(e).__name__} {e}")
                continue
    return None, "ALL_MODELS_FAILED"


def pick_note():
    files = sorted(f for f in os.listdir(NOTES) if f.lower().endswith((".md", ".txt")))
    if not files:
        return None, None
    f = files[0]
    return os.path.join(NOTES, f), f


def pick_images(note_name):
    """同名匹配：筆記檔名(去副檔名)對應的圖；否則取通用圖池前 3 張。"""
    base = os.path.splitext(note_name)[0]
    matched = [f for f in os.listdir(IMG) if f.lower().startswith(base.lower()) and f.lower().endswith(".jpg")]
    if not matched:
        # 從 photo-manifest 挑 3 張（按筆記關鍵詞簡單匹配，否則頭 3 張）
        manifest_path = os.path.join(ROOT, "docs", "photo-manifest.json")
        pool = []
        if os.path.exists(manifest_path):
            manifest = json.load(open(manifest_path, encoding="utf-8"))
            pool = list(manifest.keys())
        if not pool:
            pool = [os.path.splitext(f)[0] for f in os.listdir(IMG) if f.endswith(".jpg")]
        kw_map = {"花": ["tea-flower", "flower", "bee"], "茶湯": ["pour-tea", "tea-cake"],
                  "製": ["bamboo-tray", "withering", "dry-tea"], "採": ["hands-fresh", "farmer"],
                  "霧": ["mist", "cloud", "fog"], "樹": ["tree", "trunk"]}
        chosen = []
        note_txt = open(os.path.join(NOTES, note_name), encoding="utf-8").read()
        for k, pats in kw_map.items():
            if k in note_txt:
                for p in pats:
                    hits = [x for x in pool if p in x]
                    for h in hits:
                        if h not in chosen: chosen.append(h)
                        if len(chosen) >= 3: break
                if len(chosen) >= 3: break
        matched = (chosen or pool[:3])[:3]
        matched = [m + ".jpg" for m in matched]
    return matched[:4]


def slugify(name):
    base = os.path.splitext(name)[0]
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", base).strip("-").lower()
    return s or "tea-note"


def get_knowledge_context(note_text, limit=5):
    """從 474 篇後備知識庫檢索相關條目（標題+摘要），供寫作參考，不照抄。"""
    path = os.path.join(ROOT, "docs", "knowledge-library.json")
    if not os.path.exists(path):
        return ""
    try:
        lib = json.load(open(path, encoding="utf-8"))
        items = lib.get("items", [])
        # 簡單關鍵詞匹配：從筆記提取 2 字以上詞，與標題/摘要比對計分
        keys = set(re.findall(r"[\u4e00-\u9fff]{2,4}", note_text))
        stop = {"我們", "一個", "這些", "那個", "什麼", "可以", "沒有", "就是", "這樣", "時候"}
        keys -= stop
        scored = []
        for it in items:
            blob = it.get("t", "") + " " + it.get("s", "")
            score = sum(1 for k in keys if k in blob)
            if score:
                scored.append((score, it))
        scored.sort(key=lambda x: -x[0])
        picked = scored[:limit]
        if not picked:
            return ""
        lines = [f"- 《{it['t']}》（{it['c']}）：{it['s'][:80]}" for _, it in picked]
        return "\n".join(lines)
    except Exception as e:
        log("WARN", f"知識庫檢索失敗（忽略）: {e}")
        return ""


def build_prompt(note_text, images, date_str):
    img_lines = "\n".join(f"- images-final/{i}" for i in images)
    kb = get_knowledge_context(note_text)
    kb_section = (
        "\n\n【後備知識庫參考（僅供背景知識與潤色，切勿整段照抄，切勿引入功效/金融茶/名貴稀缺等衝突內容）：】\n"
        + kb + "\n"
    ) if kb else ""
    return [
        {"role": "system", "content": (
            "你是雲南景東大街鄉哪罕寨的茶農，世代做茶、批發茶葉、修禪。請全程用繁體中文寫作。"
            "中心思想：不炒山頭、不玩金融茶、不做虛高溢價；回歸茶本心——生津止渴、日常飲用；"
            "做老百姓喝得起、喝得安心的良心茶；禪茶一味、以茶養心、勤修戒定慧遠離貪嗔癡。"
            "雙模風格：科普Wiki風(客觀記錄風土/工藝/生態) + 禪茶人文風(質樸真誠的茶農自述)。"
            "禁令：禁止頂級/天花板/神茶/名貴/稀缺；禁止金融茶投資保值話題(除非明確批判)；"
            "禁止任何保健治病療效宣傳；禁止玄學吹捧；禁止簡體字；禁止虛構數據；"
            "地名只用哪罕寨/景東大街鄉/哀牢山/雲南，禁用『哪罕村』。"
            "SEO關鍵詞自然植入：哪罕寨、景東哀牢山、雲南原生茶、茶農直供、百姓良心茶、平價普洱、禪茶一味、喝茶悟道、不炒作山頭茶。"
        )},
        {"role": "user", "content": (
            f"以下是我這次的茶山筆記原文，請只據此整理潤色，不得虛構：\n---\n{note_text}\n---\n"
            + kb_section + "\n"
            f"本次可用照片（從中選2-3張，用【配圖：images-final/xxx.jpg】圖說 的格式插入正文）：\n{img_lines}\n\n"
            f"請輸出完整繁體 Markdown，800-1100字，嚴格按此結構：\n"
            f"---\ntitle: \"哪罕寨原生茶｜繁體SEO標題\"\nslug: \"英文-slug\"\ndate: \"{date_str}\"\n"
            f"description: \"150-160字繁體摘要\"\nkeywords: \"哪罕寨, 景東哀牢山, 雲南原生茶, 茶農直供, 百姓良心茶, 平價普洱, 禪茶一味, 喝茶悟道, 不炒作山頭茶\"\n"
            f"cover: \"images-final/封面圖檔名\"\nimage_caption: \"封面圖繁體說明\"\n---\n\n"
            f"# 標題\n引言80-120字(含哪罕寨/景東哀牢山)\n\n"
            f"## 一、產地真實風土（Wiki科普）\n## 二、茶農做茶本心（核心立場）\n"
            f"## 三、禪茶一味｜喝茶悟道（修行內核）\n## 四、百姓日常飲茶真義\n"
            f"（正文合適處插入2-3張配圖）\n\n## 常見問題（FAQ）\n"
            f"四問四答：為何不炒作山頭/適合日常與茶館嗎/如何拿樣拿貨/口感特色\n\n"
            f"結尾禪意總結+軟引流：守哀牢山一方茶園，守茶農一顆本心……歡迎茶友品飲、茶店同業批發洽詢。"
            f"\n\n只輸出 Markdown，不要任何額外說明。"
        )}
    ]


def normalize_output(content, images):
    """後處理規範化：簡轉繁、修 front matter、補配圖、清占位提示。"""
    # 1. 去代碼圍欄
    content = re.sub(r"^```(?:markdown)?\s*\n?", "", content.strip())
    content = re.sub(r"\n?```\s*$", "", content.strip())
    # 2. 全文簡轉繁（確保零簡體）
    content = S2T.convert(content)
    # 3. 修 front matter：補閉合的 ---
    if content.startswith("---"):
        parts = content.split("\n", 2)
        if len(parts) == 3 and not parts[2].lstrip().startswith("---"):
            # 找第一個非 front matter 標題行，在其前插入 ---
            body_start = re.search(r"^# ", parts[2], re.M)
            if body_start:
                fm_body = parts[2][:body_start.start()]
                rest = parts[2][body_start.start():]
                content = parts[0] + "\n" + parts[1] + "\n" + fm_body.rstrip() + "\n---\n\n" + rest
    # 4. 修 cover 占位符 -> 用真實首圖
    if images:
        cover = images[0]
        content = re.sub(r'^cover:\s*".*?"\s*$', f'cover: "images-final/{cover}"', content, flags=re.M)
        content = re.sub(r'^cover:\s*.*$', f'cover: "images-final/{cover}"', content, flags=re.M)
    # 5. 落地配圖：把模型的占位提示換成真實配圖（若模型沒自己插）
    placeholders = re.findall(r"（正文合適處插入\d+[-~]?\d*張配圖）|\(insert images? here\)", content, re.I)
    for ph in placeholders:
        figs = "\n".join(
            f"【配圖：images-final/{im}】哪罕寨茶園實拍：{os.path.splitext(im)[0].replace('-', ' ')}。"
            for im in images[:2])
        content = content.replace(ph, figs, 1)
    # 若全文完全沒有配圖標記，正文第一個章節後補一張
    if "【配圖：" not in content and images:
        m = re.search(r"(## 一、[^\n]+\n)", content)
        if m:
            content = content.replace(m.group(1),
                m.group(1) + f"\n【配圖：images-final/{images[0]}】哪罕寨茶園實拍。\n", 1)
    # 6. 清理模型多餘口語
    content = re.sub(r"^(好的|以下是|這是).*?[:：]\s*\n", "", content)
    return content.strip() + "\n"


def main():
    log("INFO", "===== 每日自動化開始 =====")
    # 1. 選筆記（兜底）
    note_path, note_name = pick_note()
    if not note_path:
        log("WARN", "無待處理筆記（notes/ 為空）→ 停止生成，不亂編。")
        return 0
    log("INFO", f"選中筆記：{note_name}")
    note_text = open(note_path, encoding="utf-8").read().strip()
    if len(note_text) < 30:
        log("WARN", f"筆記內容過短（{len(note_text)}字）→ 停止生成。")
        return 0

    # 2. 選圖（兜底）
    images = pick_images(note_name)
    if not images:
        log("WARN", "無可用照片 → 停止生成。")
        return 0
    missing = [i for i in images if not os.path.exists(os.path.join(IMG, i))]
    if missing:
        log("WARN", f"照片缺失 {missing} → 保留佔位但繼續（不強塞損壞圖）。")
        images = [i for i in images if i not in missing]
    log("INFO", f"配圖：{images}")

    # 3. 調 LLM（兜底：皆失敗則停止）
    date_str = datetime.date.today().isoformat()
    content, model_or_reason = call_llm(build_prompt(note_text, images, date_str))
    if not content:
        log("ERROR", f"所有模型皆不可用（{model_or_reason}）→ 停止生成，不亂編。")
        return 2

    # 4. 清洗 + 規範化 + 存檔
    content = normalize_output(content, images)
    slug = slugify(note_name)
    out = os.path.join(PUB, slug + ".md")
    with open(out, "w", encoding="utf-8") as f:
        f.write(content + "\n")
    log("INFO", f"文章已存：{out}（模型 {model_or_reason}）")

    # 5. 歸檔筆記
    shutil.move(note_path, os.path.join(USED, note_name))
    log("INFO", f"筆記已歸檔：{note_name} -> used-notes/")

    # 6. 重建雙站
    try:
        import build
        build.main()
        log("INFO", "雙站重建完成。")
    except Exception as e:
        log("ERROR", f"重建失敗：{e}")

    log("INFO", "===== 每日自動化完成 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""自動修圖：images-source/* -> images-final/<同名>.jpg
規則：16:9 居中裁切、主體居中、長邊最大1600px、壓縮優化、色調自然不加濾鏡。
HEIC 先轉 JPG。失敗寫入 logs/process_images.log 告警，不強塞損壞圖。
"""
import os, sys, logging
from PIL import Image, ImageOps, ImageEnhance
import pillow_heif

pillow_heif.register_heif_opener()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "images-source")
DST = os.path.join(ROOT, "images-final")
LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(DST, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "process_images.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)

TARGET_RATIO = 16 / 9
MAX_LONG = 1600
VALID_EXT = (".jpg", ".jpeg", ".png", ".heic", ".webp")


def process_one(path):
    name = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(DST, name + ".jpg")
    try:
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            w, h = im.size
            cur = w / h
            if cur > TARGET_RATIO:          # 太寬 → 裁左右
                new_w = int(h * TARGET_RATIO)
                left = (w - new_w) // 2
                im = im.crop((left, 0, left + new_w, h))
            elif cur < TARGET_RATIO:        # 太高 → 裁上下（偏上，保留主體/茶青）
                new_h = int(w / TARGET_RATIO)
                top = int((h - new_h) * 0.38)
                im = im.crop((0, top, w, top + new_h))
            w, h = im.size
            if max(w, h) > MAX_LONG:
                scale = MAX_LONG / max(w, h)
                im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            # 溫和微調：對比+3%，銳度+5%，色彩+2%（區別於網紅重濾鏡）
            im = ImageEnhance.Contrast(im).enhance(1.03)
            im = ImageEnhance.Sharpness(im).enhance(1.05)
            im = ImageEnhance.Color(im).enhance(1.02)
            im.save(out_path, "JPEG", quality=82, optimize=True, progressive=True)
        logging.info("OK %s -> %s", os.path.basename(path), os.path.basename(out_path))
        return True
    except Exception as e:
        logging.error("FAIL %s :: %s", os.path.basename(path), e)
        return False


def main():
    ok = fail = 0
    for f in sorted(os.listdir(SRC)):
        if f.lower().endswith(VALID_EXT):
            if process_one(os.path.join(SRC, f)):
                ok += 1
            else:
                fail += 1
    print(f"[process_images] ok={ok} fail={fail} -> {DST}")
    # 輸出清單供文章引用（JSON）
    import json
    names = sorted(os.path.splitext(f)[0] for f in os.listdir(DST) if f.lower().endswith(".jpg"))
    with open(os.path.join(ROOT, "docs", "images-final-index.json"), "w", encoding="utf-8") as fh:
        json.dump(names, fh, ensure_ascii=False, indent=2)
    print(f"[index] {len(names)} images -> docs/images-final-index.json")


if __name__ == "__main__":
    main()

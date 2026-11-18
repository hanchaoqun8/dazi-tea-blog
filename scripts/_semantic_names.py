# -*- coding: utf-8 -*-
"""为46张剪贴板实拍图建立语义化文件名副本（依用户上传顺序）。"""
import os, shutil, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "images-final")
src_clip = r"C:/Users/哪罕/.workbuddy/clipboard-images"


def clip_name(i):
    fs = sorted(f for f in os.listdir(src_clip) if "2026-11-18T10-14" in f and f.lower().endswith((".jpg", ".png")))
    return os.path.splitext(fs[i])[0] + ".jpg"


# index -> (语义名, 内容描述)
MAP = [
    (0,  "morning-mist-garden",      "晨霧中的哪罕寨茶園梯田，遠山雲海"),
    (1,  "ancient-tea-tree",         "原生古茶樹，彎曲樹幹布滿青苔，陽光穿透"),
    (2,  "loose-leaf-dry-tea",       "白瓷盤盛裝的紅褐色條索乾茶"),
    (3,  "tea-flower-bee",           "茶花與採蜜蜜蜂，黃色花蕊"),
    (4,  "tea-flower-wasp",          "茶花上的馬蜂"),
    (5,  "village-morning-fog",      "山村晨霧與瓦房，晨光"),
    (6,  "tea-mountain-bluesky",     "茶山藍天，山坡與電線，紅葉樹"),
    (7,  "cloud-sea-peaks",          "雲海山巒，層疊山峰"),
    (8,  "tea-mountain-sunset",      "茶山日落晚霞與村莊"),
    (9,  "shield-bugs-group",        "茶葉背面聚集的橙紅色椿象若蟲"),
    (10, "pour-tea-glass",           "玻璃公道杯將淺黃茶湯倒入深色茶杯"),
    (11, "green-hills-clouds",       "翠綠茶山與雲海"),
    (12, "pour-tea-rock",            "岩石上將琥珀茶湯倒入青花杯"),
    (13, "farmer-on-path",           "茶農戴斗笠背竹簍走山路，水印哪罕村"),
    (14, "hands-fresh-leaves",       "手捧剛採的鮮綠茶青"),
    (15, "bamboo-tray-withering",    "多層竹匾攤晾茶青，初製場景"),
    (16, "bamboo-tray-fresh",        "竹匾上鋪滿新鮮綠色茶青"),
    (17, "basket-fresh-leaves",      "竹簍中的茶青特寫"),
    (18, "forest-green-slope",       "茶山林間綠坡遠景"),
    (19, "farmer-under-tree",        "茶農戴草帽在綠樹下的仰拍"),
    (20, "farmer-sitting-garden",    "茶農坐在茶園，綠外套黃馬甲持拐杖"),
    (21, "bug-on-trunk",             "茶樹幹上的紅黑色椿象"),
    (22, "hands-tender-bud",         "手捧一芽葉嫩芽，銀手鐲"),
    (23, "dry-tea-closeup",          "乾茶條索與銀毫特寫"),
    (24, "pour-tea-plum-cup",        "玻璃壺倒茶入梅花紋茶杯"),
    (25, "tea-flower-bud",           "青綠色茶花花苞"),
    (26, "sunrise-rays",             "金色朝陽與光芒"),
    (27, "bamboo-sunset",            "夕陽穿透竹林"),
    (28, "dew-on-leaf",              "茶葉上的露珠逆光"),
    (29, "dew-tea-flower",           "晨露與陽光中的茶花"),
    (30, "farmer-offering-leaves",   "茶農戴草帽微笑捧出茶青"),
    (31, "farmer-bag-leaves",        "茶農將茶青投入大織袋"),
    (32, "tea-cake-poster",          "茶餅豎圖，文字慢煮歲月普洱知味"),
    (33, "rainbow-over-garden",      "雨後彩虹跨越茶園"),
    (34, "red-tender-leaves",        "紫紅色新芽嫩葉"),
    (35, "old-tree-trunk",           "林間古茶樹粗壯樹幹"),
    (36, "red-green-tea-leaves",     "紅色新芽與綠色老葉同枝"),
    (37, "flowers-bees-cluster",     "多朵白色茶花與蜜蜂"),
    (38, "basket-tea-flowers",       "竹匾盛滿白色茶花黃蕊"),
    (39, "sun-drying-flowers",       "竹匾上日曬茶花"),
    (40, "bird-nest-eggs",           "茶樹綠葉間的鳥巢與斑點蛋"),
    (41, "nest-red-eggs",            "鳥巢中三顆紅褐色鳥蛋"),
    (42, "basket-purple-leaves",     "竹籃中帶紫紅葉的茶青"),
    (43, "bugs-on-leaf",             "綠葉上兩隻橙紅色椿象"),
    (44, "mountain-sunset-glow",     "橙紅晚霞與層疊遠山"),
    (45, "nest-white-eggs",          "鳥巢中三顆淡藍白鳥蛋"),
]

manifest = {}
for i, (idx, slug, desc) in enumerate(MAP):
    src = os.path.join(SRC, clip_name(idx))
    dst = os.path.join(SRC, slug + ".jpg")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        manifest[slug] = {"file": slug + ".jpg", "desc": desc, "index": i}
    else:
        print("MISSING", i, src)

with open(os.path.join(ROOT, "docs", "photo-manifest.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=2)
print(f"[semantic] created {len(manifest)} named photos -> docs/photo-manifest.json")
for k, v in manifest.items():
    print(f"  {k}.jpg :: {v['desc']}")

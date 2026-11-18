# -*- coding: utf-8 -*-
"""雙站靜態生成器：blog.dazi.uk(博客) + wiki.dazi.uk(百科詞條)
讀取 published/*.md -> 生成 site_blog/ 與 site_wiki/。
零第三方依賴，Markdown 用簡易解析器。
"""
import os, re, shutil, html, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, "published")
IMG_SRC = os.path.join(ROOT, "images-final")
SITE_BLOG = os.path.join(ROOT, "site_blog")
SITE_WIKI = os.path.join(ROOT, "site_wiki")
BLOG_URL = "https://blog.dazi.uk"
WIKI_URL = "https://wiki.dazi.uk"


def parse_md(path):
    txt = open(path, encoding="utf-8").read()
    meta = {}
    body = txt
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", txt, re.S)
    if m:
        fm, body = m.group(1), m.group(2)
        for line in fm.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def inline(s):
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def md_to_html(body):
    lines = body.splitlines()
    out, para, in_ul = [], [], False

    def flush():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []

    for ln in lines:
        t = ln.strip()
        if not t:
            flush(); continue
        if t.startswith("【配圖："):
            flush()
            mm = re.match(r"【配圖：([^】]+)】\s*(.*)", t)
            if mm:
                f = mm.group(1).split("/")[-1]
                cap = mm.group(2).strip()
                out.append(
                    f'<figure class="photo"><img src="/assets/img/{f}" alt="{html.escape(cap)}" loading="lazy">'
                    + (f"<figcaption>{inline(cap)}</figcaption>" if cap else "") + "</figure>")
            continue
        if t.startswith("### "):
            flush(); out.append("<h3>" + inline(t[4:]) + "</h3>"); continue
        if t.startswith("## "):
            flush(); out.append("<h2>" + inline(t[3:]) + "</h2>"); continue
        if t.startswith("# "):
            flush(); out.append("<h1>" + inline(t[2:]) + "</h1>"); continue
        if re.match(r"^\d+[\.、]\s", t) or t.startswith("- "):
            if not in_ul:
                flush(); out.append("<ul>"); in_ul = True
            item = re.sub(r"^\d+[\.、]\s*", "", t)
            item = re.sub(r"^-\s*", "", item)
            out.append("<li>" + inline(item) + "</li>")
            continue
        if in_ul:
            out.append("</ul>"); in_ul = False
        para.append(t)
    flush()
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def seo_desc(meta):
    d = meta.get("description", "")
    return d[:160]


def layout(title, desc, content, site_url, is_wiki=False, cover=""):
    og = f'<meta property="og:image" content="{site_url}/assets/img/{cover.split("/")[-1]}">' if cover else ""
    wiki_badge = '<span class="badge">百科詞條</span>' if is_wiki else ""
    return f"""<!DOCTYPE html>
<html lang="zh-Hant"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{site_url}/">
{og}
<link rel="stylesheet" href="/assets/style.css">
</head><body>
<header class="top"><a class="brand" href="/">哪罕寨原生茶 <small>{'百科' if is_wiki else '本心禪茶博客'}</small></a>
<nav><a href="/">首頁</a> <a href="{BLOG_URL}" {'class="on" ' if not is_wiki else ''}>博客</a> <a href="{WIKI_URL}" {'class="on" ' if is_wiki else ''}>百科詞條</a></nav></header>
<main class="wrap">{wiki_badge}{content}</main>
<footer class="foot">雲南景東大街鄉 · 哪罕寨｜守一方茶園，守一顆本心。<br>
<a href="{BLOG_URL}">blog.dazi.uk</a> · <a href="{WIKI_URL}">wiki.dazi.uk</a></footer>
</body></html>"""


def ensure_assets(site_dir):
    adir = os.path.join(site_dir, "assets")
    os.makedirs(adir, exist_ok=True)
    src_css = os.path.join(ROOT, "scripts", "style.css")
    shutil.copy2(src_css, os.path.join(adir, "style.css"))
    idir = os.path.join(adir, "img")
    os.makedirs(idir, exist_ok=True)
    for f in os.listdir(IMG_SRC):
        if f.lower().endswith(".jpg"):
            shutil.copy2(os.path.join(IMG_SRC, f), os.path.join(idir, f))


def build_blog(posts):
    for d in [SITE_BLOG]:
        os.makedirs(d, exist_ok=True)
    ensure_assets(SITE_BLOG)
    # 首頁
    cards = []
    for p in posts:
        m = p["meta"]
        slug = m.get("slug") or p["slug"]
        cover = m.get("cover", "")
        img = f'<img src="/assets/img/{cover.split("/")[-1]}" alt="{html.escape(m.get("image_caption",""))}" loading="lazy">' if cover else ""
        cards.append(f"""<article class="card">
  {img}
  <h2><a href="/posts/{slug}/">{html.escape(m.get('title',''))}</a></h2>
  <p>{html.escape(m.get('description',''))[:110]}…</p>
  <div class="meta">{html.escape(m.get('date',''))} · 哪罕寨茶農手記</div>
</article>""")
    home = layout("哪罕寨原生茶｜本心禪茶博客",
                  "雲南景東哀牢山哪罕寨，一位茶農的真實記錄。不炒山頭、不玩金融茶，只做老百姓喝得起的原生良心茶。",
                  '<section class="hero"><h1>回歸茶的本心</h1><p>守哀牢山一方茶園，守茶農一顆本心。不逐浮名、不隨炒作、不貪暴利，只做一杯樸實、乾淨、老百姓喝得起的原生良心茶。</p></section>'
                  + '<div class="grid">' + "".join(cards) + "</div>", BLOG_URL)
    open(os.path.join(SITE_BLOG, "index.html"), "w", encoding="utf-8").write(home)
    # 文章頁
    for p in posts:
        m = p["meta"]
        slug = m.get("slug") or p["slug"]
        body = md_to_html(p["body"])
        content = f'<article class="post">{body}</article>'
        page = layout(m.get("title", ""), seo_desc(m), content, BLOG_URL, cover=m.get("cover", ""))
        pd = os.path.join(SITE_BLOG, "posts", slug)
        os.makedirs(pd, exist_ok=True)
        open(os.path.join(pd, "index.html"), "w", encoding="utf-8").write(page)
    # sitemap
    urls = [BLOG_URL + "/"] + [BLOG_URL + "/posts/" + (m.get("slug") or p["slug"]) + "/" for p in posts for m in [p["meta"]]]
    open(os.path.join(SITE_BLOG, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    open(os.path.join(SITE_BLOG, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\nSitemap: " + BLOG_URL + "/sitemap.xml\n")
    return len(posts)


def build_wiki(posts):
    os.makedirs(SITE_WIKI, exist_ok=True)
    ensure_assets(SITE_WIKI)
    cards = []
    for p in posts:
        m = p["meta"]
        slug = m.get("slug") or p["slug"]
        cards.append(f'<li><a href="/entries/{slug}/">{html.escape(m.get("title",""))}</a> — {html.escape(m.get("description",""))[:70]}…</li>')
    home = layout("哪罕寨原生茶 · 百科詞條",
                  "哪罕寨、景東哀牢山原生茶的客觀百科記錄：產地風土、茶樹品種、初製工藝、茶園生態。",
                  '<section class="hero"><h1>哪罕寨原生茶 · 百科詞條</h1><p>客觀、乾淨、專業的詞條式記錄：產地、茶樹、工藝、生態。適合茶友查閱，亦供百科站的詞條收錄。</p></section>'
                  + '<ul class="entries">' + "".join(cards) + "</ul>", WIKI_URL, is_wiki=True)
    open(os.path.join(SITE_WIKI, "index.html"), "w", encoding="utf-8").write(home)
    for p in posts:
        m = p["meta"]
        slug = m.get("slug") or p["slug"]
        body = md_to_html(p["body"])
        page = layout(m.get("title", ""), seo_desc(m), f'<article class="post wiki-entry">{body}</article>',
                      WIKI_URL, is_wiki=True, cover=m.get("cover", ""))
        ed = os.path.join(SITE_WIKI, "entries", slug)
        os.makedirs(ed, exist_ok=True)
        open(os.path.join(ed, "index.html"), "w", encoding="utf-8").write(page)
    urls = [WIKI_URL + "/"] + [WIKI_URL + "/entries/" + (m.get("slug") or p["slug"]) + "/" for p in posts for m in [p["meta"]]]
    open(os.path.join(SITE_WIKI, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    open(os.path.join(SITE_WIKI, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\nSitemap: " + WIKI_URL + "/sitemap.xml\n")
    return len(posts)


def main():
    posts = []
    for f in sorted(os.listdir(PUB)):
        if f.endswith(".md"):
            meta, body = parse_md(os.path.join(PUB, f))
            posts.append({"slug": f[:-3], "meta": meta, "body": body})
    posts.sort(key=lambda p: p["meta"].get("date", ""), reverse=True)
    nb = build_blog(posts)
    nw = build_wiki(posts)
    print(f"[build] blog posts={nb} -> {SITE_BLOG}")
    print(f"[build] wiki entries={nw} -> {SITE_WIKI}")


if __name__ == "__main__":
    main()

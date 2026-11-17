#!/usr/bin/env python3
"""
Static site generator for blog.dazi.uk — zero third-party dependencies.
Reads content/posts/*.md with YAML front matter, outputs a clean static site
into site/ (index, category pages, post pages, sitemap.xml, rss.xml, robots.txt).

Usage:
    python scripts/build.py
"""
import os, re, json, html, shutil, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(ROOT, "content", "posts")
SITE_DIR = os.path.join(ROOT, "site")
SITE_URL = "https://blog.dazi.uk"
SITE_TITLE = "The Tea Ledger"
SITE_TAGLINE = "Plain-English guides to tea safety, residues and import compliance."

CATEGORY_ORDER = ["EU Rules", "US Import Rules", "Testing & Lab Reports",
                  "Safety & Storage", "Buying Guide"]

# ---------- minimal front matter parser ----------
def parse_front_matter(text):
    meta, body = {}, text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return meta, body
    fm, body = m.group(1), m.group(2)
    # keys with simple scalar values
    cur_list_key = None
    for line in fm.splitlines():
        if re.match(r"^\s+-\s+", line) and cur_list_key:
            meta.setdefault(cur_list_key, []).append(line.strip()[2:].strip().strip('"'))
            continue
        cur_list_key = None
        mm = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if not mm:
            continue
        key, val = mm.group(1), mm.group(2).strip()
        if val == "":
            meta[key] = []
            cur_list_key = key
        elif val.startswith("["):
            inner = val.strip("[] ")
            meta[key] = [x.strip().strip('"') for x in re.split(r",(?![^\[]*\])", inner) if x.strip()]
        else:
            meta[key] = val.strip('"')
    return meta, body

# ---------- tiny markdown renderer (headings, lists, links, bold, code, paragraphs) ----------
def inline_md(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"(?<![\w/])((?:https?://)[^\s<)]+)", r'<a href="\1" rel="nofollow">\1</a>', s)
    return s

def render_markdown(md):
    lines = md.splitlines()
    out, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i].rstrip()
        if not line.strip():
            i += 1; continue
        mh = re.match(r"^(#{1,6})\s+(.*)$", line)
        if mh:
            lvl = len(mh.group(1)); txt = inline_md(mh.group(2))
            out.append(f"<h{lvl}>{txt}</h{lvl}>"); i += 1; continue
        # bullet / numbered list
        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            tag = "ol" if ordered else "ul"
            items = []
            while i < n and (re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])):
                item = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", lines[i]).rstrip()
                items.append(f"<li>{inline_md(item)}</li>"); i += 1
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>"); continue
        if line.startswith(">"):
            quote = []
            while i < n and lines[i].startswith(">"):
                quote.append(lines[i].lstrip("> ").rstrip()); i += 1
            out.append("<blockquote>" + inline_md(" ".join(quote)) + "</blockquote>"); continue
        # paragraph
        para = [line]
        i += 1
        while i < n and lines[i].strip() and not re.match(r"^(#{1,6})\s", lines[i]) \
              and not re.match(r"^\s*[-*]\s+", lines[i]) and not re.match(r"^\s*\d+\.\s+", lines[i]) \
              and not lines[i].startswith(">"):
            para.append(lines[i].rstrip()); i += 1
        out.append("<p>" + inline_md(" ".join(para)) + "</p>")
    return "\n".join(out)

# ---------- page templates ----------
def layout(title, description, content, body_class="", og_image=""):
    og_img_tag = f'<meta property="og:image" content="{html.escape(og_image)}">' if og_image else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(description)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}/">
{og_img_tag}
<link rel="stylesheet" href="/assets/style.css">
<link rel="alternate" type="application/rss+xml" title="RSS" href="/rss.xml">
</head><body class="{body_class}">
<header class="site-head"><div class="wrap">
  <a class="brand" href="/">{SITE_TITLE}</a>
  <nav><a href="/">All guides</a> <a href="/sitemap.xml">Sitemap</a> <a href="/rss.xml">RSS</a></nav>
</div></header>
<main class="wrap">{content}</main>
<footer class="site-foot"><div class="wrap">
  <p>{SITE_TITLE} — {SITE_TAGLINE}</p>
  <p class="muted">Independent buyer education. Not affiliated with any regulator or seller. No health claims.</p>
</div></footer>
</body></html>"""

def load_posts():
    posts = []
    for fn in os.listdir(POSTS_DIR):
        if not fn.endswith(".md"): continue
        with open(os.path.join(POSTS_DIR, fn), "r", encoding="utf-8") as f:
            text = f.read()
        meta, body = parse_front_matter(text)
        if not meta.get("slug") or not meta.get("title"):
            print("SKIP (missing slug/title):", fn); continue
        posts.append({"meta": meta, "body": body,
                      "date": meta.get("date", "2026-11-18")})
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts

def cat_slug(c):
    return re.sub(r"[^a-z0-9]+", "-", c.lower()).strip("-")

def build():
    # Overwrite in place instead of rmtree: safe on sandboxes and preview-locked dirs.
    os.makedirs(SITE_DIR, exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "assets"), exist_ok=True)
    # ensure style copied from source location (docs/source kept in scripts dir too)
    src_css = os.path.join(ROOT, "scripts", "style.css")
    if os.path.exists(src_css):
        shutil.copy(src_css, os.path.join(SITE_DIR, "assets", "style.css"))

    posts = load_posts()
    # group by category
    cats = {}
    for p in posts:
        c = p["meta"].get("category", "Buying Guide")
        cats.setdefault(c, []).append(p)

    # home
    cards = []
    for p in posts:
        m = p["meta"]
        cover = m.get("cover", "")
        cover_alt = m.get("cover_alt", m.get("title", ""))
        thumb = (f'<img class="card-img" src="{html.escape(cover)}" alt="{html.escape(cover_alt)}" loading="lazy">' if cover else "")
        cards.append(f"""<article class="card">
  {thumb}
  <div class="card-cat">{html.escape(m.get('category',''))}</div>
  <h2><a href="/posts/{m['slug']}/">{html.escape(m['title'])}</a></h2>
  <p>{html.escape(m.get('description',''))}</p>
  <div class="card-meta">{p['date']}</div>
</article>""")
    nav_cats = " ".join(f'<a href="/category/{cat_slug(c)}/">{html.escape(c)}</a>' for c in CATEGORY_ORDER if c in cats)
    home = layout(SITE_TITLE, SITE_TAGLINE, f"""
<section class="hero"><h1>{SITE_TITLE}</h1><p>{SITE_TAGLINE}</p>
<p class="lede">Clear, no-nonsense guides for tea drinkers and small importers on EU and US rules, pesticide MRLs, heavy metals, lab reports and how to spot a good supplier. Safety and compliance only — no health claims.</p>
<div class="catnav">{nav_cats}</div></section>
<section class="grid">{''.join(cards)}</section>""")
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(home)

    # category pages
    for c, plist in cats.items():
        items = []
        for p in plist:
            m = p["meta"]
            items.append(f"""<article class="card"><h2><a href="/posts/{m['slug']}/">{html.escape(m['title'])}</a></h2>
<p>{html.escape(m.get('description',''))}</p><div class="card-meta">{p['date']}</div></article>""")
        content = f"""<section class="hero"><h1>{html.escape(c)}</h1>
<p><a href="/">← All guides</a></p></section><section class="grid">{''.join(items)}</section>"""
        d = os.path.join(SITE_DIR, "category", cat_slug(c))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(layout(f"{c} — {SITE_TITLE}", f"{c} guides on {SITE_TITLE}.", content))

    # post pages
    for p in posts:
        m = p["meta"]; slug = m["slug"]
        body_html = render_markdown(p["body"])
        # remove the H1 from body if present (we render it ourselves)
        body_html = re.sub(r"<h1>.*?</h1>", "", body_html, count=1)
        tags = " ".join(f'<span class="tag">{html.escape(t)}</span>' for t in m.get("tags", []))
        cover = m.get("cover", "")
        cover_alt = m.get("cover_alt", m.get("title", ""))
        cover_html = (f'<figure class="post-cover"><img src="{html.escape(cover)}" alt="{html.escape(cover_alt)}"></figure>' if cover else "")
        content = f"""<article class="post">
<div class="post-cat">{html.escape(m.get('category',''))} · {p['date']}</div>
<h1>{html.escape(m['title'])}</h1>
<div class="tags">{tags}</div>
{cover_html}
<div class="post-body">{body_html}</div>
</article>"""
        d = os.path.join(SITE_DIR, "posts", slug)
        os.makedirs(d, exist_ok=True)
        og = (SITE_URL + cover) if cover.startswith("/") else cover
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(layout(m["title"], m.get("description", ""), content, "post-page", og_image=og))

    # sitemap
    urls = [SITE_URL + "/"] + [SITE_URL + "/category/" + cat_slug(c) + "/" for c in cats] \
           + [SITE_URL + "/posts/" + p["meta"]["slug"] + "/" for p in posts]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    for u in urls:
        sm += f"\n  <url><loc>{u}</loc></url>"
    sm += "\n</urlset>"
    with open(os.path.join(SITE_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sm)

    # rss
    items = []
    for p in posts[:30]:
        m = p["meta"]
        items.append(f"""<item><title>{html.escape(m['title'])}</title>
<link>{SITE_URL}/posts/{m['slug']}/</link>
<guid>{SITE_URL}/posts/{m['slug']}/</guid>
<description>{html.escape(m.get('description',''))}</description></item>""")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>
<title>{SITE_TITLE}</title><link>{SITE_URL}</link><description>{SITE_TAGLINE}</description>
{''.join(items)}</channel></rss>"""
    with open(os.path.join(SITE_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss)

    with open(os.path.join(SITE_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")

    print(f"Built {len(posts)} posts, {len(cats)} categories -> {SITE_DIR}")

if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""
Fetch overseas tea-related regulatory news from VERIFIED official sources:
  - FDA Recalls RSS (20 items, tested 2026-11-18)
  - openFDA food enforcement API (JSON, tested)
  - EFSA news RSS (tested)
  - European Commission presscorner RSS (tested)
Writes raw items to scripts/news_queue.json. Dedupes vs published posts.

Usage: python scripts/fetch_news.py
"""
import os, re, json, hashlib, datetime, urllib.request, ssl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "scripts", "news_queue.json")
POSTS_DIR = os.path.join(ROOT, "content", "posts")
# GHA runners have proper CA certs. Local Windows may need SSL_CERT_VERIFY=0 override.
VERIFY = os.environ.get("SSL_CERT_VERIFY", "1") != "0"
CTX = ssl.create_default_context()
if not VERIFY:
    CTX.check_hostname = False
    CTX.verify_mode = ssl.CERT_NONE

RSS_FEEDS = [
    ("FDA Recalls, Market Withdrawals & Safety Alerts",
     "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/recalls/rss.xml"),
    ("EFSA (European Food Safety Authority) News",
     "https://www.efsa.europa.eu/en/rss/news"),
    ("European Commission Newsroom",
     "https://ec.europa.eu/commission/presscorner/api/rss?language=en"),
]
OPENFDA = ("openFDA — FDA Food Enforcement Reports",
           "https://api.fda.gov/food/enforcement.json?search=recall_initiation_date:%5B20250101+TO+20261231%5D&limit=20")

# Strong-relevance terms only. Generic "recall"/"import"/"food safety" were removed
# because they let unrelated items (cheese, hay, supplements) through.
STRONG_KEYS = ["tea", "pesticide", "residue", "mrl", "maximum residue", "heavy metal",
               "arsenic", "cadmium", "aflatoxin", "ochratoxin", "mycotoxin",
               "camellia", "infusion", "herbal tea", "botanical",
               "fsvp", "prior notice", "import alert", "import refusal"]
WEAK_KEYS = ["lead", "contaminant", "detention", "food safety", "import"]

def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; TeaLedgerBot/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        print("FETCH FAIL", url, "->", e)
        return ""

def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s)
    for a, b in [("&amp;","&"),("&quot;",'"'),("&#39;","'"),("&lt;","<"),("&gt;",">"),("&nbsp;"," ")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()

def parse_rss(xml, source):
    items = []
    for block in re.findall(r"<item>(.*?)</item>", xml, re.S | re.I):
        def g(tag):
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.S | re.I)
            return strip_tags(m.group(1)) if m else ""
        items.append({"title": g("title"), "summary": g("description")[:600],
                      "link": g("link"), "date": g("pubDate") or g("dc:date"),
                      "source": source})
    return items

def parse_openfdA(data, source):
    items = []
    try:
        results = json.loads(data).get("results", [])
    except Exception:
        return items
    for r in results:
        title = r.get("reason_for_recall") or r.get("product_description") or "FDA food recall"
        desc = "Product: %s. Reason: %s. Status: %s. Distribution: %s." % (
            r.get("product_description", ""), r.get("reason_for_recall", ""),
            r.get("status", ""), r.get("distribution_pattern", "")[:200])
        items.append({"title": title[:200], "summary": desc[:600],
                      "link": "https://www.accessdata.fda.gov/scripts/ires/index.cfm?Product=%s" % r.get("code_info", ""),
                      "date": r.get("recall_initiation_date", ""), "source": source})
    return items

def published_links():
    seen = set()
    if not os.path.isdir(POSTS_DIR): return seen
    for fn in os.listdir(POSTS_DIR):
        if fn.endswith(".md"):
            txt = open(os.path.join(POSTS_DIR, fn), encoding="utf-8").read()
            for u in re.findall(r"https?://[^\s)\"']+", txt):
                seen.add(u.rstrip(".,"))
    return seen

def main():
    all_items = []
    for name, url in RSS_FEEDS:
        got = parse_rss(fetch(url), name)
        print(f"{name}: {len(got)} items")
        all_items += got
    name, url = OPENFDA
    got = parse_openfdA(fetch(url), name)
    print(f"{name}: {len(got)} items")
    all_items += got

    seen = published_links()
    scored = []
    for it in all_items:
        if not it["title"]: continue
        blob = (it["title"] + " " + it["summary"]).lower()
        score = sum(3 for k in STRONG_KEYS if k in blob) + sum(1 for k in WEAK_KEYS if k in blob)
        if score == 0: continue
        if it["link"] and it["link"].rstrip(".,") in seen: continue
        it["score"] = score
        it["hash"] = hashlib.md5((it["title"] + it["link"]).encode()).hexdigest()[:12]
        scored.append(it)
    scored.sort(key=lambda x: x["score"], reverse=True)
    uniq, hs = [], set()
    for it in scored:
        if it["hash"] in hs: continue
        hs.add(it["hash"]); uniq.append(it)
    today = datetime.date.today().isoformat()
    json.dump({"fetched": today, "items": uniq}, open(QUEUE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"Queued {len(uniq)} relevant items -> {QUEUE}")

if __name__ == "__main__":
    main()

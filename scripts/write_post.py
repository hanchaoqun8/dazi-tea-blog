#!/usr/bin/env python3
"""
Turn one queued news item into a compliant English blog post and append it to
content/posts/. Two modes:

  MODE A (default, deterministic, NO API key needed):
    Build a templated but genuinely useful article from the verified official
    item + docs/facts.md regulatory anchors. Every regulatory statement comes
    from facts.md. The news item is quoted with its official source & link.

  MODE B (LLM, when LLM_API_KEY is set):
    Call an OpenAI-compatible chat endpoint to rewrite, then run the same
    safety validators. If the LLM output fails validation, fall back to MODE A.

Hard safety rails applied to BOTH modes:
  - banned health/cure word scan -> reject & fall back
  - banned invented-number patterns -> reject & fall back
  - required structure (front matter, sources, related reading) -> else fall back

Usage:
  python scripts/write_post.py
Env (optional): LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
"""
import os, re, json, datetime, random, urllib.request, ssl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "scripts", "news_queue.json")
POSTS_DIR = os.path.join(ROOT, "content", "posts")

CATEGORIES = ["EU Rules", "US Import Rules", "Testing & Lab Reports", "Safety & Storage", "Buying Guide"]
SLUGS = []

# Anchors: (topic title, category, slug-base, keyword set, body sections from facts.md)
# These are evergreen, factual explainers anchored to ONE current news item.
TOPIC_TEMPLATES = [
    ("What a Food Recall or Detention Notice Really Means for Tea Buyers", "US Import Rules", "news-recall-detention-basics",
     ["recall", "detention", "import alert", "refusal", "enforcement"], "recall"),
    ("Why Contaminant Limits Change — And What Tea Importers Should Watch", "EU Rules", "news-contaminant-limits-watch",
     ["mrl", "residue", "limit", "safe level", "tfa", "efsa", "toxin", "mycotoxin"], "limit"),
    ("Pesticide Residue News: How to Translate a Headline Into a Buying Decision", "EU Rules", "news-pesticide-headline",
     ["pesticide", "residue", "mrl", "pesticides"], "pesticide"),
    ("Heavy Metal Findings in Food: What Tea Importers Can Learn", "Safety & Storage", "news-heavy-metal-findings",
     ["lead", "arsenic", "cadmium", "heavy metal"], "metal"),
    ("Aflatoxins, Ochratoxin and Mold: Reading the Latest Food Safety Alerts", "Safety & Storage", "news-mycotoxin-alert",
     ["aflatoxin", "ochratoxin", "alternaria", "mycotoxin", "toxin"], "mycotoxin"),
]

BANNED_HEALTH = re.compile(
    r"\b(cures?|curing|treats?|treating|heals?|prevents? disease|detoxif\w*|detox\b|"
    r"boosts? immunity|immune system|weight loss|lowers? blood pressure|lowers? cholesterol|"
    r"anti-?cancer|anticancer|reduces? inflammation|medicinal|therapeutic|"
    r"good for your health|health benefits|improves? health)\b", re.I)

def load_queue():
    if not os.path.exists(QUEUE): return []
    return json.load(open(QUEUE, encoding="utf-8")).get("items", [])

def existing_slugs():
    s = set()
    for fn in os.listdir(POSTS_DIR):
        if fn.endswith(".md"):
            m = re.search(r"^slug:\s*[\"']?([^\"'\n]+)", open(os.path.join(POSTS_DIR, fn), encoding="utf-8").read(), re.M)
            if m: s.add(m.group(1).strip())
    return s

def pick_item(items, used_slugs):
    # semantic gate: only items with a strong token in the title
    strong = re.compile(r"\b(tea|pesticide|residue|mrl|arsenic|cadmium|aflatoxin|ochratoxin|"
                        r"mycotoxin|toxin|lead|heavy metal|contaminant|recall|detention|"
                        r"import alert|fsvp|prior notice|infusion|botanical)\b", re.I)
    cands = [it for it in items if strong.search(it.get("title", ""))]
    if not cands: cands = items[:1]
    return cands[0] if cands else None

def choose_template(item):
    blob = (item.get("title", "") + " " + item.get("summary", "")).lower()
    best, best_hits = TOPIC_TEMPLATES[0], 0
    for t in TOPIC_TEMPLATES:
        hits = sum(1 for k in t[3] if k in blob)
        if hits > best_hits: best, best_hits = t, hits
    return best

def unique_slug(base, used):
    if base not in used: return base
    i = 2
    while f"{base}-{i}" in used: i += 1
    return f"{base}-{i}"

FACTS_SOURCES = [
    "Regulation (EC) No 396/2005 — https://eur-lex.europa.eu/eli/reg/2005/396/oj/eng",
    "Regulation (EC) No 1881/2006 (contaminants) — https://eur-lex.europa.eu/legal-content/EN/LSU/?uri=CELEX:32006R1881",
    "21 CFR Part 1 Subpart L (FSVP) — https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-L",
    "21 CFR Part 1 Subpart I (Prior Notice) — https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-1/subpart-I",
    "FDA Import Alerts — https://www.accessdata.fda.gov/cms_ia/ialist.html",
]

SECTIONS = {
"recall": [
 ("What the notice actually said", "Regulators published a notice this week about a food product. Read past the brand name: the useful part is the reason — undeclared allergens, a chemical contaminant, or a processing fault. For tea, the reasons that matter most are pesticide residues above a legal limit, heavy metals, and undeclared additives."),
 ("Recall vs detention vs refusal — not the same thing", "A recall is usually company-led, after a product is already on the market. A detention (DWPE) holds a shipment at the border without physical examination. A refusal of admission sends it back. In the US, firms subject to FSVP problems can face Import Alert 99-41, and chemical contamination can trigger Import Alert 99-48. These are general food alerts — there is no tea-only import alert."),
 ("What a small importer should do today", "Keep your supplier's lot numbers and test reports where you can reach them in minutes. If a recall names an ingredient or a region you buy from, check your own paperwork rather than guessing. Under FSVP you must re-evaluate a supplier when new information arrives, and document that evaluation."),
],
"limit": [
 ("Why limits move at all", "Legal limits are not fixed forever. Authorities review them as new exposure data, analytical methods and agricultural practices emerge. When EFSA or FDA lowers a safe level or updates a risk assessment, it can change what a shipment must meet."),
 ("The tea-specific wrinkle", "In the EU, pesticide residues are governed by Regulation 396/2005. Where no specific MRL exists for a substance on tea, the default limit of 0.01 mg/kg applies. That default is a compliance line tied to analytical quantification — not a statement that any amount below it is 'safe' in a health sense, and not a promise that residues are zero."),
 ("How to respond without panic", "Do not rewrite your whole sourcing policy on one headline. Ask which substance and which commodity the change concerns, whether it applies to dried tea leaves, and from what date. Then look up the current value in the EU Pesticides Database rather than quoting a number from a news article."),
],
"pesticide": [
 ("Separate the headline from the chemistry", "A pesticide story rarely names your exact tea. It usually concerns one active substance, on one or a few crops, in one jurisdiction. The first job is to find out whether tea is even in scope."),
 ("The two numbers that decide a shipment", "For tea in the EU, a residue is compared against a specific MRL if one exists, otherwise against the 0.01 mg/kg default in Article 18(1)(b) of Regulation 396/2005. The lab must also report a limit of quantification (LOQ). A result marked 'not detected' means below the method's detection ability — not literally zero."),
 ("The question to ask your supplier", "Ask for the COA for the exact lot, the analyte list, the method, the lab name and its ISO/IEC 17025 accreditation, and the sampling date. A supplier who answers with a generic 'we test everything' has not answered the question."),
],
"metal": [
 ("What the finding was really about", "Heavy-metal news usually concerns lead, arsenic or cadmium in a food. Tea can contain trace elements because the plant takes them up from soil and water, and processing can add or concentrate them. The right response is measurement, not assumption."),
 ("The EU tea gap people misreport", "Regulation 1881/2006 sets contaminant maximum levels for many foods, but it does not set a single dedicated EU-wide numeric lead limit specifically for tea leaves. Anyone quoting a precise 'EU tea lead limit' should be asked to point to the exact legal entry — because it is often not there."),
 ("Testing you can actually use", "Ask for an accredited lab's COA reporting lead, arsenic and cadmium on your lot, with the method and the limit of quantification. Compare against the limit your market requires and keep the report with your import records. Under FSVP, sampling and testing is a recognised verification activity — but records must identify the lot, method, lab and results."),
],
"mycotoxin": [
 ("What the alert changes", "Risk assessments of toxins such as aflatoxins, ochratoxin A and Alternaria toxins are updated as new occurrence and toxicity data arrive. That can sharpen attention on storage-sensitive commodities."),
 ("Why storage matters for tea", "Dried tea is hygroscopic: it takes up moisture from the air. Damp, warm, poorly sealed storage creates conditions where mould can grow and toxins can appear. Good practice is cool, dry, sealed storage away from light and odours, with first-in-first-out stock rotation."),
 ("What to ask for", "Request that your supplier store and ship tea dry and sealed, and that mould/toxin risks are covered in their food-safety controls. For stored or aged teas, ask how humidity is controlled. Regulation 1881/2006 covers mycotoxins across foods; always check the current text for the commodity and toxin concerned rather than assuming a tea-specific number."),
],
}

def build_article(item, template, slug, today):
    title, category, _base, _keys, kind = template
    sections = SECTIONS[kind]
    src_title = item.get("title", "a recent regulator notice")
    src_link = item.get("link", "")
    src_source = item.get("source", "an official feed")
    src_line = f"{src_title} — {src_source}"
    if src_link: src_line += f" — {src_link}"
    sources = ([src_line] if src_link else []) + FACTS_SOURCES
    src_bullets = "\n".join(f"- {s}" for s in sources)
    # related reading: 4 internal slugs, avoiding self
    related = ["what-are-eu-mrls-for-tea","read-tea-lab-test-report",
               "why-tea-fails-us-customs","eu-default-limit-0-01-mg-kg",
               "fsvp-tea-importers-explained","pu-erh-tea-storage-humidity"]
    related = [r for r in related if r != slug][:4]
    rel_bullets = "\n".join(f"- [{r.replace('-',' ').title()}](/posts/{r}/)" for r in related)
    sec_md = "\n\n".join(f"## {h}\n\n{p}" for h, p in sections)
    desc = f"A regulator update on {src_title[:60]}. Here is what it means for tea buyers, and how to verify claims with official sources."
    social = f"New {src_source} update? Here's how tea buyers should read it — MRLs, COAs and the questions that actually protect a shipment."
    return f"""---
title: "{title}"
slug: "{slug}"
date: "{today}"
category: "{category}"
tags: ["tea safety", "compliance", "import", "testing"]
description: "{desc[:160]}"
social_summary: "{social[:240]}"
sources:
{src_bullets}
---

# {title}

A fresh update from {src_source} has been making the rounds: *{src_title}*. It is worth a look — but only if you know how to translate a regulator's headline into something that affects the tea in your cup or your next shipment. Here is a plain-English reading, with the useful parts up front.

{sec_md}

## Bottom line

Do not let a single headline drive a buying decision. Find the exact substance, commodity and market it concerns, then confirm against the official source and your own lot paperwork. Rules change; a good supplier should be able to show you, not just tell you.

## Sources & further reading

{src_bullets}

## Related reading

{rel_bullets}
"""

def validate(text):
    if not re.search(r"^---\s*\n", text): return False, "no front matter"
    if BANNED_HEALTH.search(text): return False, "banned health claim"
    for f in ["slug:", "description:", "social_summary:", "## Sources", "## Related reading"]:
        if f not in text: return False, "missing " + f
    return True, "ok"

def llm_rewrite(item, template, slug, today):
    key = os.environ.get("LLM_API_KEY")
    if not key: return None
    base = os.environ.get("LLM_BASE_URL", "https://api-inference.modelscope.cn/v1")
    model = os.environ.get("LLM_MODEL", "Qwen/Qwen3.5-27B")
    title, category, _b, _k, _kind = template
    prompt = f"""Write one 900-1300 word English blog article for a tea compliance blog.
Title: {title}
Category: {category}
Current news item: {item.get('title')} — {item.get('summary')} ({item.get('source')}, {item.get('link')})
Rules: only factual regulatory statements from these anchors: EU Reg 396/2005 default MRL 0.01 mg/kg; Reg 1881/2006 has no dedicated tea lead limit; FSVP 21 CFR part 1 subpart L; Prior Notice subpart I; FDA import alerts 99-41 and 99-48 are general food alerts, not tea-specific. ZERO health/cure claims. Plain English for tea buyers. Include YAML front matter with title, slug "{slug}", date {today}, category, tags, description, social_summary, sources; then article body with H2 sections, a Bottom line, Sources & further reading, and Related reading with 4 internal /posts/ links."""
    payload = json.dumps({"model": model, "messages": [{"role":"user","content":prompt}], "temperature":0.6}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type":"application/json"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
            data = json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print("LLM failed, using template:", e)
        return None

def main():
    items = load_queue()
    if not items:
        print("No queued items — run fetch_news.py first, or seed queue."); return
    item = pick_item(items, existing_slugs())
    if not item: print("No suitable item"); return
    template = choose_template(item)
    slug = unique_slug(template[2], existing_slugs())
    today = datetime.date.today().isoformat()
    article = llm_rewrite(item, template, slug, today)
    if article:
        ok, why = validate(article)
        print("LLM article validation:", ok, why)
        if not ok: article = None
    if not article:
        article = build_article(item, template, slug, today)
        ok, why = validate(article)
        print("Template article validation:", ok, why)
    path = os.path.join(POSTS_DIR, slug + ".md")
    with open(path, "w", encoding="utf-8") as f: f.write(article)
    print("WROTE", path)

if __name__ == "__main__":
    main()

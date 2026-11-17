#!/usr/bin/env python3
"""Validate all posts against hard rules. Reports problems; exits 1 if any blocking issue."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "content", "posts")
# An actual promotional health claim = tea/product + efficacy verb + disease/body-function,
# stated positively. Legal quotations ("intended to diagnose, cure, mitigate, treat or
# prevent disease") and the ordinary verb "treat X as Y" are NOT claims.
PROMO_CLAIM = re.compile(
    r"\b(?:drinking\s+)?(?:this\s+)?tea\b[^.]{0,60}\b(?:cures?|heals?|treats?|prevents?|reverses?|alleviates?)\b[^.]{0,60}\b(?:diseases?|cancer|illness|diabetes|hypertension|infection)\b"
    r"|\b(?:boosts?|strengthens?)\s+(?:your\s+)?immune\s+system\b"
    r"|\b(?:aids?|helps?\s+with|causes?)\s+weight\s+loss\b"
    r"|\b(?:lowers?|reduces?)\s+blood\s+pressure\b"
    r"|\banti-?cancer\b"
    r"|\bdetoxif(?:ies|y|ying|ication)\b"
    r"|\breduces?\s+inflammation\b", re.I)
# Lines that are clear legal / negation context are exempt from the promo scan.
LEGAL_OR_NEG = re.compile(r"\b(do not|don't|must not|cannot|can't|never|prohibit\w*|illegal|unapproved|unlawful|claim\w*|FD&C|drug|intended use|diagnose|mitigate|structure or any function|marketing phrase|not a)\b", re.I)
INVENTED_NUM = re.compile(r"(EU|FDA|China|GB)\s*(lead|arsenic|residue|MRL)\s*(limit|level)?\s*(is|of|:)?\s*0?\.\d+\s*mg/kg", re.I)

def promo_hits(text):
    hits = []
    for line in text.splitlines():
        if PROMO_CLAIM.search(line) and not LEGAL_OR_NEG.search(line):
            hits.append(line.strip()[:120])
    return hits

problems = []
files = sorted(f for f in os.listdir(POSTS) if f.endswith(".md"))
slugs = set()
for fn in files:
    txt = open(os.path.join(POSTS, fn), encoding="utf-8").read()
    def chk(cond, msg):
        if not cond: problems.append(f"{fn}: {msg}")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", txt, re.S)
    chk(bool(m), "missing front matter")
    fm = m.group(1) if m else ""
    sm = re.search(r"^slug:\s*[\"']?([^\"'\n]+)", fm, re.M)
    chk(bool(sm), "missing slug")
    if sm:
        slug = sm.group(1).strip()
        chk(slug not in slugs, f"duplicate slug {slug}")
        slugs.add(slug)
        chk(slug + ".md" == fn, f"slug '{slug}' != filename '{fn}'")
    for field in ["title:", "date:", "category:", "tags:", "description:", "social_summary:", "sources:"]:
        chk(field in fm, f"front matter missing {field}")
    ds = re.search(r"^description:\s*[\"']?(.*?)[\"']?$", fm, re.M)
    if ds: chk(len(ds.group(1).strip('"')) <= 165, f"description too long ({len(ds.group(1))})")
    ss = re.search(r"^social_summary:\s*[\"']?(.*?)[\"']?$", fm, re.M)
    if ss: chk(len(ss.group(1).strip('"')) <= 245, f"social_summary too long ({len(ss.group(1))})")
    chk(len(re.findall(r"^# ", txt, re.M)) <= 1, "more than one H1")
    chk("## Sources" in txt or "Sources & further" in txt, "no sources section")
    chk("Related reading" in txt or "Related Read" in txt, "no related reading")
    rels = re.findall(r"/posts/([a-z0-9-]+)/", txt)
    chk(len(rels) >= 2, f"too few internal links ({len(rels)})")
    for r in rels:
        chk(r + ".md" in files or r in ("what-are-eu-mrls-for-tea",), f"dangling internal link: {r}")
    hits = promo_hits(txt)
    chk(not hits, "promotional health claim found: " + (hits[0] if hits else ""))
    chk(not INVENTED_NUM.search(txt), "possible invented numeric limit")
    wc = len(txt.split())
    chk(wc >= 800, f"too short ({wc} words)")

print(f"Checked {len(files)} posts.")
if problems:
    print(f"\n{len(problems)} PROBLEM(S):")
    for p in problems: print("  !", p)
    sys.exit(1)
else:
    print("ALL CHECKS PASSED")

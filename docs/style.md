# WRITING STYLE & FORMAT SPEC — dazi tea blog
# Every article (28 foundation posts + daily automation) MUST follow this.

## Audience
Overseas tea drinkers (consumer) AND small tea importers / small retailers (B2B-lite).
Plain, practical, "help you understand the risk and not get ripped off" tone.
Think: a knowledgeable tea trader explaining over a cup — not a journal paper, not a marketing brochure.

## Hard rules (non-negotiable)
1. FACTUAL INTEGRITY: Only state regulatory facts that are in docs/facts.md. If a number is not there, DO NOT invent it — say "check the current official text" and link the source. Never fabricate MRL values, limits, dates, alert numbers, or study results.
2. NO HEALTH / MEDICAL / CURE CLAIMS. Zero. Do not write or imply any tea cures, treats, prevents disease, "detoxes", "boosts immunity", aids weight loss, lowers blood pressure, etc. Only: safety standards, pesticide residues, heavy metals, storage, compliance, testing, and how to read labels/reports. (Even when a title mentions "health claims", discuss them only as a LEGAL labeling topic — e.g. claims you must NOT make — never as actual benefits.)
3. INTERNAL LINKS: Every article ends with a "Related reading" block linking to other articles ON THIS BLOG (blog.dazi.uk), 3–5 relevant internal links, using relative or absolute /posts/<slug>/ URLs. NO links to dazi.uk product pages (user decided: internal blog links only).
4. SOCIAL SUMMARY: Every article has a short social blurb (~1–2 sentences, <= 240 chars) for Pinterest / Instagram, stored in front matter as `social_summary`.
5. ENGLISH: Natural, idiomatic, SEO-friendly. Avoid obscure academic jargon; if a technical term is needed, define it in plain words.
6. SEO: front matter with `title`, `description` (150–160 chars), `slug`, `category`, `tags`, `date`, `social_summary`. H1 = article title (one H1 only). Use H2/H3 subheads. Keyword used naturally in title, first paragraph, and a few times — no stuffing.

## Article front matter (YAML) — exact fields
```
---
title: "..."
slug: "..."
date: "2026-11-18"
category: "EU Rules" | "US Import Rules" | "Testing & Lab Reports" | "Safety & Storage" | "Buying Guide" | "Myths & Claims"
tags: ["tag1", "tag2", "tag3"]
description: "150-160 char meta description"
social_summary: "short blurb for Pinterest / Instagram, <=240 chars"
sources:
  - "Regulation (EC) No 396/2005 — https://eur-lex.europa.eu/eli/reg/2005/396/oj/eng"
---
```

## Body structure (follow this order)
1. Hook — 2–4 sentences addressing the reader's real question/concern. No "In this article we will..." filler.
2. Main sections under descriptive H2s. Use short paragraphs (2–4 sentences), bullet lists where useful. Put the practical "what to do" up front.
3. A "Bottom line" or "What this means for you" short wrap-up (the takeaway).
4. "Sources & further reading" — bullet list of official sources (from front matter `sources`), plain URLs.
5. "Related reading" — 3–5 internal links to other posts on this blog, each as `- [Post title](/posts/<slug>/)`.

## Length
1,100–1,600 words of real content. Depth over padding. A buyer should finish genuinely more informed.

## Tone / style dos and don'ts
- DO: second person ("you"), concrete examples, plain analogies, short sentences, active voice.
- DO: explain trade "tells" and how to ask a supplier the right question.
- DON'T: hype words ("revolutionary", "game-changer"), fear-mongering, absolutes not backed by law.
- DON'T: mention health benefits of drinking tea, even positively — topic is safety & compliance only.
- DON'T: invent brand names doing bad things. Use generic "some sellers"/"a supplier".
- DON'T: make up statistics ("70% of tea fails...") unless in facts.md (there are none). Say "no reliable public figure" instead.

## Internal link map (slugs) — use these exact slugs
1. what-are-eu-mrls-for-tea
2. zero-pesticide-residue-meaning
3. fda-tea-import-rules
4. read-tea-lab-test-report
5. common-pesticides-eu-shipment-rejection
6. fsvp-tea-importers-explained
7. lead-arsenic-in-tea
8. eu-regulation-396-2005-tea
9. third-party-tea-test-labs
10. why-tea-fails-us-customs
11. organic-vs-conventional-tea-residue
12. how-tea-samples-tested-eu-labs
13. tea-labeling-rules-us-health-claims
14. when-tea-fails-eu-inspection
15. pu-erh-tea-storage-humidity
16. heavy-metal-sources-tea
17. tea-prior-notice-fda
18. can-aging-puerh-remove-pesticides
19. green-vs-black-tea-pesticide-risk
20. choose-low-residue-tea-online
21. china-gb-vs-eu-mrl
22. fda-import-alert-detention
23. mycotoxin-risk-stored-tea
24. eu-default-limit-0-01-mg-kg
25. tea-batch-testing-limits
26. importing-tea-australia-canada
27. retailers-hide-poor-test-results
28. safe-tea-compliance-checklist

## Category values
- "EU Rules": 1,5,8,14,21,24
- "US Import Rules": 3,6,10,13,17,22,26
- "Testing & Lab Reports": 4,9,12,25,27
- "Safety & Storage": 7,15,16,18,23
- "Buying Guide": 2,11,19,20,28
- (adjust if a better fit; keep consistent)

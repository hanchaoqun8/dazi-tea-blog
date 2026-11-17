# The Tea Ledger (blog.dazi.uk)

Plain-English guides to tea safety, EU/US pesticide MRLs, FDA import rules, heavy metals and lab-test literacy. 28 foundation articles plus a daily overseas tea news pipeline.

- **Live site:** https://blog.dazi.uk
- **Content:** `content/posts/*.md` (YAML front matter)
- **Build:** `python scripts/build.py` → outputs `site/`
- **Validate:** `python scripts/validate.py`
- **Daily automation:** `.github/workflows/daily-post.yml` (fetch → rewrite → validate → build → Cloudflare Pages deploy)

Regulatory facts live in `docs/facts.md`; writing rules in `docs/style.md`. No health claims, no invented numbers.

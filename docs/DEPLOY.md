# Deployment Guide — blog.dazi.uk

The site is a pure static site. Cloudflare Pages serves the `site/` directory. The daily workflow deploys automatically. Complete these one-time steps.

## STATUS (2026-11-18 02:20) — what is already DONE

- GitHub repo `hanchaoqun8/dazi-tea-blog` created; all 107 files pushed via REST API
  (28 articles, 28 cover images in `site/assets/img/`, generated HTML, scripts, docs).
- Cloudflare Pages project `dazi-tea-blog` **created and deployed** via wrangler.
  Live preview URL: **https://dazi-tea-blog.pages.dev**
  Verified: home 200, 28 cover images on home, article pages 200, images 200.
- 28 articles each have `cover` + `cover_alt`; build.py renders card thumbnails,
  post cover images and og:image. All 28 validate clean.

### Still manual (token limitations, not code issues)
1. **Custom domain `blog.dazi.uk`**: the provided CF token has Pages rights but no
   DNS-record rights (list/add DNS returns 10000 auth error), and the Pages domain API
   rejected `.uk` with 8000015. In the Cloudflare dashboard: Pages project
   `dazi-tea-blog` → Custom domains → Set up `blog.dazi.uk` (CF adds the DNS record).
   Or provide a CF token with `Zone:DNS Edit` for dazi.uk.
2. **Daily GitHub Actions workflow**: the provided GitHub PAT has only `repo` scope,
   not `workflow`, so it cannot write `.github/workflows/`. The file is staged at repo
   root as `daily-post.workflow.yml`; move it to `.github/workflows/daily-post.yml`
   (or push from a normal git client, where the local copy is already in the right path),
   then add the CF secrets below. Until then the daily job is NOT running (by design —
   foundation first, automation after).

## 0. Activate the automation workflow (one manual step)

The CI workflow file is included in this repo as **`daily-post.workflow.yml`** at the repo root. GitHub's API blocked writing directly into the protected `.github/workflows/` path, so the last step is to move it into place:

- On GitHub, open `daily-post.workflow.yml`, copy its full content.
- Create the file `.github/workflows/daily-post.yml` (via **Add file → Create new file**, typing the full path in the filename box) and paste the content.
- Delete the root `daily-post.workflow.yml` copy.

The local copy also lives at `.github/workflows/daily-post.yml` in this working folder, so if you push from a normal git client it will already be in the correct location — in that case just delete the root-level `daily-post.workflow.yml` duplicate.

## 1. Push the code to GitHub

The local machine's git protocol is blocked by a proxy, so push from a normal network, or use the Contents API. From a machine with working GitHub access:

```bash
cd dazi-tea-blog
git init
git branch -M main
git add -A
git commit -m "Initial: 28 articles + daily automation"
git remote add origin https://github.com/hanchaoqun8/dazi-tea-blog.git
git push -u origin main
```

The repo `hanchaoqun8/dazi-tea-blog` has already been created (README seeded).

## 2. Cloudflare Pages — create the project

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Select `hanchaoqun8/dazi-tea-blog`, branch `main`.
3. Build settings:
   - **Framework preset:** None
   - **Build command:** `python scripts/build.py` (or leave blank — `site/` is already committed and the workflow deploys it directly)
   - **Build output directory:** `site`
4. Project name: **`dazi-tea-blog`** (must match the workflow's `--project-name`).
5. Create the project.

## 3. Cloudflare API token (for the workflow)

Cloudflare dashboard → **My Profile** → **API Tokens** → **Create Token** → use the **Edit Cloudflare Workers** template, or a custom token with:
- Account → **Workers Scripts: Edit**  (Pages deploy uses this)
- Account → **Account Settings: Read**

Copy the token. Get the **Account ID** from the right sidebar of the Workers & Pages overview.

## 4. GitHub Secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**. Add:

| Secret | Value | Required |
|---|---|---|
| `CLOUDFLARE_API_TOKEN` | the token from step 3 | Yes |
| `CLOUDFLARE_ACCOUNT_ID` | your Cloudflare account ID (`6ab80b215b6a39fb9627f536af57daa` if reusing the existing account) | Yes |
| `LLM_API_KEY` | API key for an OpenAI-compatible endpoint | No — without it, the built-in safe template is used |
| `LLM_BASE_URL` | e.g. `https://api-inference.modelscope.cn/v1` | No |
| `LLM_MODEL` | e.g. a currently available Qwen/DeepSeek model | No |

> If you do set an LLM, confirm the model is currently available on the provider — retired models will fail and the script falls back to the template automatically.

## 5. Custom domain

Cloudflare Pages project → **Custom domains** → **Set up a custom domain** → `blog.dazi.uk`.
Add the DNS record Cloudflare instructs (usually a CNAME). Cloudflare provisions SSL automatically.

## 6. Verify the daily automation

Repo → **Actions** → **Daily Tea News Post** → **Run workflow** to trigger manually once.

Expected steps: fetch → write post → validate → build → deploy → commit. Check the deployed site shows a new article and zero broken links.

## Data-safety design

- If the daily fetch returns nothing relevant, the workflow fails before deploying — it never publishes an empty or broken article.
- Every article is validated for health claims and invented numeric limits before deploy.
- The site contains no health claims and no product links (per requirements).

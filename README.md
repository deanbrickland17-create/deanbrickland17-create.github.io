# deanbrickland.com

Personal website for Dean Brickland — town planner, Director at the
Irish Planning Institute. Single-page static site, no build step.

## Status

The site is currently **unpublished** (GitHub Pages Source is set to
`None` under Settings → Pages) while it's under revision. `main` is
the published branch — see [Branches](#branches) below before pushing
anything to it.

## Stack

Plain HTML/CSS/vanilla JS. No framework, no bundler, no `npm install`.
Everything needed to render the page ships in `index.html` plus the
static assets alongside it.

## Local preview

```
python3 -m http.server 8000
```

then open `http://localhost:8000/`. Any static file server works —
there's nothing to build.

## Deployment

Hosted on **GitHub Pages**, deployed from a branch (Settings → Pages →
Build and deployment → Source). **Every push to whichever branch is
set as the Pages source redeploys the live site immediately** — there
is no staging step and no build to wait on. See
[AGENTS.md](./AGENTS.md) for the branch discipline this requires.

## Domain

- Custom domain: `deanbrickland.com`, set via the `CNAME` file at the
  repo root (required by GitHub Pages — don't remove it).
- DNS and email are managed in **Cloudflare**:
  - Email Routing forwards `dean@deanbrickland.com` to a personal
    Gmail address. The **catch-all rule is intentionally disabled**
    (set to Drop) to avoid amplifying dictionary-attack spam — don't
    re-enable it.
  - Don't touch DNS records (especially MX) without understanding
    what they serve; breaking them breaks mail delivery, not just the
    site.

## Assets

| File | Purpose |
|---|---|
| `index.html` | The entire site |
| `404.html` | Custom not-found page, auto-served by GitHub Pages |
| `CNAME` | Custom domain config for GitHub Pages |
| `robots.txt` | Crawler rules — explicitly allows major AI crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.) |
| `sitemap.xml` | Single-page sitemap |
| `llms.txt` | Plain-text site summary for LLMs that check this convention |
| `favicon.png` | Browser tab icon |
| `logo.png` | "DB" monogram mark, used in the nav and 404 page |
| `portrait.webp` | Headshot, used in the About section |
| `og-image.jpg` | 1200×630 social share card (Open Graph / Twitter Card image) — JPEG here since the Soft Club version's grain texture compresses far better than PNG (51KB vs 590KB); `main`/`draft` use `og-image.png` instead |
| `card-photo-1.webp`, `card-photo-2.webp`, `card-photo-3.webp` | Cropped station photos used as the three focus-card images (this branch only — `main`/`draft` use `card-plan-*.webp` crops of a site-plan drawing instead) |

The page also carries `Person`/`ProfilePage` JSON-LD structured data
and Open Graph/Twitter Card meta tags for search and social previews
— see the `<head>` of `index.html`.

## Checks

```
python3 scripts/check.py
```

Runs on every push/PR via `.github/workflows/check.yml`. See
[AGENTS.md](./AGENTS.md) for what it checks and why.

## More

Development conventions, content rules, and the branch/publish
workflow live in [AGENTS.md](./AGENTS.md) — read that before making
changes.

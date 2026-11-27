# deanbrickland.com

Personal website for Dean Brickland — town planner, Director at the
Irish Planning Institute. Static HTML/CSS/JS site, no build step.

## Status

The custom domain is live, and `main` currently serves an intentional
"New site coming soon" holding page in the white/charcoal editorial
style. The full personal site and writing live on `draft` and must not
be published without explicit approval.

## Branches

| Ref | Purpose |
|---|---|
| `main` | Production-only GitHub Pages source; currently the holding page |
| `draft` | Canonical development branch for the personal website |
| `concept/pine-original` | Tag preserving the original pine/cream/lime design |
| `concept/softclub-original` | Tag preserving the original Soft Club design |

The design tags are reference snapshots, not active development
branches. New website work should start from `draft`. Any other
branch is temporary and should be deleted once its work is merged.

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

Hosted on **GitHub Pages**, deployed from `main` (Settings → Pages →
Build and deployment → Source). Every merge into `main` redeploys the
live site immediately — there is no staging step. See
[AGENTS.md](./AGENTS.md) for the branch discipline this requires.

## Domain

- Custom domain: `deanbrickland.com`, set via the `CNAME` file at the
  repo root (required by GitHub Pages — don't remove it).
- DNS and email are managed in **Cloudflare**:
  - Email Routing forwards the site's contact address (the one the
    "Show address" button assembles) to a personal Gmail address. The
    **catch-all rule is intentionally disabled** (set to Drop) to avoid
    amplifying dictionary-attack spam — don't re-enable it.
  - Don't touch DNS records (especially MX) without understanding
    what they serve; breaking them breaks mail delivery, not just the
    site.

## Assets (`main`)

| File | Purpose |
|---|---|
| `index.html` | Holding page (`noindex`, click-to-reveal contact address) |
| `404.html` | Custom not-found page (`noindex`, root-absolute assets), auto-served by GitHub Pages |
| `CNAME` | Custom domain config for GitHub Pages |
| `_config.yml` | Tells GitHub Pages' Jekyll build not to publish internal files (`README.md`, `AGENTS.md`, `scripts/`) |
| `robots.txt` | Crawler rules — explicitly allows major AI crawlers (GPTBot, ClaudeBot, PerplexityBot, etc.) |
| `sitemap.xml` | Single-page sitemap |
| `llms.txt` | Plain-text site summary for LLMs that check this convention |
| `fonts/` | Self-hosted Archivo and IBM Plex Mono (Latin-subset WOFF2) with their SIL OFL licence texts. The site makes no third-party requests |
| `favicon.png` | Browser tab icon |
| `logo.png` | "DB" monogram mark, used in the header and 404 page |
| `og-image.png` | 1200×630 social share card (Open Graph / Twitter Card image), in the white/charcoal style |

## Checks

```
python3 scripts/check.py
```

Runs on every push/PR via `.github/workflows/check.yml`. It checks
links, `srcset`, CSS `url()`, `404.html` root-absolute URLs, CSP
inline-script hashes, metadata, and ensures no internal files or
plaintext email addresses are committed or published. See
[AGENTS.md](./AGENTS.md) for full details.

## More

Development conventions, content rules, and the branch/publish
workflow live in [AGENTS.md](./AGENTS.md) — read that before making
changes.

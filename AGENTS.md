# AGENTS.md

Instructions for any AI coding agent (Codex, Claude Code, etc.)
working in this repo. Read this before making changes — several of
the rules below exist because of mistakes already made and fixed once
in this project's history. Don't repeat them.

## Branch discipline — read this first

**GitHub Pages currently deploys `main`, which intentionally serves a
holding page. Every push to the Pages source redeploys the live site
immediately.** There is no staging, preview step, or confirmation.
Check Settings → Pages → Source before changing deployment behavior.

Rules:

- **Never push to `main`** (or whichever branch Settings → Pages
  currently names as the Source) unless the human has explicitly said
  the site should go live now. "Make this change" is not the same
  instruction as "publish this change" — they are two separate asks
  and the second one requires explicit confirmation.
- Treat `draft` as the canonical website development branch. Temporary
  feature branches should start from it and be removed after integration.
- The original visual directions are preserved as
  `concept/pine-original` and `concept/softclub-original` tags. Use
  those tags for reference; do not recreate long-lived style branches.
- This repo holds the website and nothing else. Dean's other projects
  have their own repos (the finance tracker lives in `Financial-Tracker`).
  If a session has been opened in the wrong repo, stop: don't push
  unrelated work here. A `claude/*` or other stray branch whose changes
  have nothing to do with the website was pushed to the wrong repo. Tell
  Dean it can be deleted; don't document it as something to "retain".
- If you're unsure whether the site is currently meant to be live or
  not, ask. Don't infer it from the state of the branch.
- If you discover the site republished unexpectedly, the cause is
  almost certainly a push landed on the Pages source branch. Check
  `git log` on that branch before assuming it's a GitHub-side issue.

## Content rules

- **Never invent facts about Dean.** No fabricated stats, job history,
  article titles/links, credentials, or employer details. If a piece
  of content needs a real fact you don't have, leave it as a visible
  placeholder or ask, rather than writing something plausible-sounding.
- **The Writing section currently has no articles.** It shows an honest
  "first essays are still in progress" note with a LinkedIn link. Don't
  invent article titles, dates or content to fill it. When Dean supplies
  a real piece, add it as a real entry with a working link; never add
  an entry that points at `#`.
- Settled word choices — don't silently revert these:
  - "town planner", not "spatial planner"
  - "economy" / "local economic development", not "technology" (the
    site was deliberately repositioned away from a technology framing)
  - No "drawing"/"drawings" in visitor-facing copy (image alt text and
    headings were specifically reworded to avoid this)
  - "Dean Brickland" (no middle initial) in visible text; the nav
    wordmark has no separator character between the names

## Email / anti-scraping — do not regress this

`dean@deanbrickland.com` was harvested by spam bots once already. The
fix in place:

- The contact email is **assembled only after the visitor activates
  "Show address"** (`index.html`, near the closing `</body>`). It is
  not written as a plaintext `mailto:` link, inserted into the DOM on
  page load, or stored as a plaintext text node.
- The literal address does **not** appear anywhere in static HTML,
  JSON-LD, or `llms.txt`. `llms.txt` points at `/#contact` instead of
  printing the address.
- `scripts/check.py` enforces this automatically (it fails the build
  if a plaintext `name@domain` pattern appears in rendered HTML) — if
  you need to change the contact flow, keep this check passing, don't
  weaken or remove it to make a change land.
- Cloudflare Email Routing catch-all is intentionally **Drop**, not
  forwarding — this is infrastructure config, not something in this
  repo, but don't reference or imply a catch-all setup in any content.

## Design conventions

The current style (on `draft`) is a white/charcoal editorial system,
defined entirely as CSS custom properties at the top of the `<style>`
block in `index.html`. It is the same system as the live holding page
on `main` and as `404.html`:

```
--paper                white ground
--ink                  charcoal text (16:1 on paper)
--ink-soft             body copy (6.0:1)
--ink-faint            small mono labels (5.1:1, AA) -- do not lighten
--line, --line-strong  hairline dividers / row rules
--surface              ground behind images
```

Structure is hairline rules and rows rather than cards or filled
pills: uppercase mono labels, underlined text links with a `↗`
arrow, small radii (`--radius: 3px`), greyscale photography (applied
in CSS, not baked into the files). Sections are lettered A–D in scroll
order (Focus, About, Writing, Contact) -- keep the letters in the
order they appear on the page.

The former dark pine/cream/lime identity is archived at the
`concept/pine-original` tag.

Another direction ("Gen X Soft Club" — cool greys, washed denim/sage,
lowercase Helvetica, blue-cast imagery) is archived at the
`concept/softclub-original` tag. If asked to restyle:

- Change tokens, not one-off hex values scattered through rules. Every
  color in the page should trace back to a `:root` custom property.
- Check contrast for every new text/background pair (small text needs
  4.5:1). The holding page's original `--ink-faint` (`#7B7E84`) failed
  at 4.07:1 and was darkened here.
- The site has no build step and no bundler. Don't introduce one for
  a styling change — plain CSS in the single `<style>` block is the
  convention here, on purpose, for a page this size.
- Preserve the responsive breakpoints (`840px`, `480px`) and the
  `prefers-reduced-motion` handling already in place.
- **No third-party requests.** Fonts are self-hosted in `fonts/` (two
  Latin-subset WOFF2 files plus their OFL licence texts). Don't add a
  Google Fonts, CDN or analytics link: it would send every visitor's IP
  address to another company. If a new font is needed, download it into
  `fonts/` with its licence file and add a `@font-face` rule.
- Any new branch should fork from `draft` (which carries the current
  content/SEO/anti-scraping baseline), not from `main`.
- **`404.html` has its own inline `<style>` block and does not share
  `index.html`'s `:root` tokens** (it's a standalone minimal page, kept
  deliberately small). If you change the active palette/type on a
  branch, update `404.html` to match by hand — otherwise a broken link
  drops visitors onto what looks like a different site.

## Testing expectations

Before committing:

1. **Run the checker**: `python3 scripts/check.py` (add `--no-network`
   in a sandboxed environment with no outbound access). It checks for
   broken local links/images, dead `#fragment` anchors, duplicate IDs,
   image dimensions and `alt` attributes, document landmarks/headings,
   safe new-tab links, metadata, JSON-LD syntax and membership ranges,
   and the plaintext-email regression described above. This also runs
   automatically in CI via `.github/workflows/check.yml` on every push
   and PR.
2. **Visually check both a mobile (~390px) and desktop (~1280px)
   viewport** after any layout or copy change — this is a single
   `index.html` with hand-written responsive CSS, not a framework with
   guardrails. Confirm no horizontal overflow.
3. **Validate the JSON-LD** stays valid JSON (the checker does this,
   but worth knowing: it's the `<script type="application/ld+json">`
   block in `<head>`).
4. If the change touches images, keep an eye on file size — everything
   in this repo is hand-optimized (WebP, compressed) specifically to
   keep the page light; don't drop in an unoptimized multi-MB source
   image.

## Commands

```bash
# Local preview
python3 -m http.server 8000

# Run all checks (local files only, no network)
python3 scripts/check.py --no-network

# Run all checks (also probes external links, best-effort/non-fatal)
python3 scripts/check.py
```

There is no install step, no lockfile, and no `package.json` — nothing
to run before the above commands work.

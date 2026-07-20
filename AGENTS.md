# AGENTS.md

Instructions for any AI coding agent (Codex, Claude Code, etc.)
working in this repo. Read this before making changes — several of
the rules below exist because of mistakes already made and fixed once
in this project's history. Don't repeat them.

## Branch discipline — read this first

**GitHub Pages deploys from a branch, and every push to that branch
redeploys the live site immediately.** There is no staging, no
preview step, no confirmation. Check Settings → Pages → Source to see
which branch is currently live before doing anything else.

Rules:

- **Never push to `main`** (or whichever branch Settings → Pages
  currently names as the Source) unless the human has explicitly said
  the site should go live now. "Make this change" is not the same
  instruction as "publish this change" — they are two separate asks
  and the second one requires explicit confirmation.
- Do development on `draft` or a feature branch. Push there freely.
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
- **The three "Writing" entries are currently placeholders** with
  `href="#"`. Don't invent article content for them. Either wire them
  to real URLs once supplied, or restructure the section (e.g. link
  out to LinkedIn) rather than leave dead links live.
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

- The contact email is **assembled at runtime by a small inline
  script** (`index.html`, near the closing `</body>`), not written as
  a plaintext `mailto:` link or plaintext text node.
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

The current default style (on `draft`) is a dark pine/cream/lime
identity, defined entirely as CSS custom properties at the top of the
`<style>` block in `index.html`:

```
--pine, --pine-deep, --pine-card   dark grounds
--sage, --sage-img                  muted green / image-tint
--cream, --cream-line               light ground / hairlines
--lime                              accent
--ink, --ink-fade                   text on cream
```

An alternate style direction ("Gen X Soft Club" — cool greys, washed
denim/sage, lowercase Helvetica, blue-cast imagery) exists on
`style-softclub`, branched from `draft`. If asked to restyle:

- Change tokens, not one-off hex values scattered through rules. Every
  color in the page should trace back to a `:root` custom property.
- Keep both light/dark visual roles working — sections alternate
  between a dark "hero" band and light content bands; a new palette
  needs to work in both.
- The site has no build step and no bundler. Don't introduce one for
  a styling change — plain CSS in the single `<style>` block is the
  convention here, on purpose, for a page this size.
- Preserve the responsive breakpoints (`840px`, `560px`) and the
  `prefers-reduced-motion` handling already in place.
- Any new branch should fork from `draft` (which carries the current
  content/SEO/anti-scraping baseline), not from `main`.

## Testing expectations

Before committing:

1. **Run the checker**: `python3 scripts/check.py` (add `--no-network`
   in a sandboxed environment with no outbound access). It checks for
   broken local links/images, dead `#fragment` anchors, missing `alt`
   attributes, missing `<title>`/description/`lang`, invalid JSON-LD,
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

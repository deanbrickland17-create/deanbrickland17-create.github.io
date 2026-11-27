#!/usr/bin/env python3
"""
Static checks for this repo's HTML pages. No dependencies beyond the
standard library, so it runs the same locally and in CI.

Checks:
  - every local href/src/srcset, CSS url() inside <style>/style="", and
    og:image/twitter:image/og:url (relative path, or an absolute
    https://<CNAME domain>/... URL) points at a file that exists in the repo
  - every #fragment link resolves to an id= in its target page
  - 404.html uses only root-absolute local URLs (GitHub Pages serves it for
    missing paths at any depth, where relative URLs break)
  - every on-site URL in sitemap.xml and llms.txt resolves, and every
    published page except 404.html is listed in sitemap.xml
  - ids are unique
  - every <img> has an alt attribute (empty alt="" is fine for decorative images)
  - every <img> declares width and height to reserve layout space
  - every target="_blank" link includes rel="noopener"
  - each page has exactly one <main> and one <h1>, with no heading-level skips
  - <title>, <meta name="description">, <meta name="viewport">, and html[lang] are present
  - any application/ld+json block is valid JSON, and Person.memberOf uses an expected type
  - any <meta http-equiv="Content-Security-Policy"> with script-src matches
    the SHA-256 hash of every inline executable <script> on the page
  - no plaintext "name@domain" email pattern appears in any tracked text file
    in the repo (published or excluded docs -- see AGENTS.md), and no
    internal Markdown or Python file is published (see _config.yml exclude)
  - (network, best-effort, non-fatal) external https:// links resolve.
    Skipped automatically when the sandbox has no outbound access.

Usage:
    python3 scripts/check.py            # check every *.html in the repo (root and subfolders like writing/)
    python3 scripts/check.py index.html # check a specific file
    python3 scripts/check.py --no-network
"""
import base64
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PERSON_MEMBER_OF_TYPES = {"MemberProgramTier", "Organization", "ProgramMembership"}
META_URL_KEYS = {"og:image", "og:url", "twitter:image"}
CSS_URL_RE = re.compile(r"""url\(\s*["']?([^"')]+)""")
TEXT_EXTENSIONS = {
    ".html", ".htm", ".md", ".markdown", ".txt", ".xml", ".json", ".css",
    ".js", ".py", ".yml", ".yaml", ".csv", ".svg",
}
INTERNAL_EXTENSIONS = {".md", ".markdown", ".py"}


def read_jekyll_excludes():
    """The exclude list from _config.yml (simple "- item" entries only)."""
    excludes = []
    path = os.path.join(REPO_ROOT, "_config.yml")
    if not os.path.isfile(path):
        return excludes
    in_exclude = False
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.split("#", 1)[0].rstrip()
            if not line:
                continue
            if not line.startswith((" ", "-")):
                in_exclude = line.startswith("exclude:")
                continue
            m = re.match(r"\s*-\s*(.+)", line)
            if in_exclude and m:
                excludes.append(m.group(1).strip().strip("\"'").rstrip("/"))
    return excludes


def published_files():
    """Repo-relative paths GitHub Pages' Jekyll build would publish."""
    excludes = read_jekyll_excludes()

    def excluded(rel):
        return any(rel == e or rel.startswith(e + "/") for e in excludes)

    published = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        rel_dir = os.path.relpath(dirpath, REPO_ROOT)
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        # Jekyll skips names starting with "." or "_" unless told otherwise.
        dirnames[:] = sorted(
            d for d in dirnames
            if not d.startswith((".", "_")) and not excluded(rel_dir + d)
        )
        for name in sorted(filenames):
            rel = rel_dir + name
            if name.startswith((".", "_")) or excluded(rel):
                continue
            published.append(rel)
    return published


def read_cname_domains():
    """Absolute URLs against these hosts are treated as local files."""
    domains = set()
    cname_path = os.path.join(REPO_ROOT, "CNAME")
    if os.path.isfile(cname_path):
        with open(cname_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    domains.add(line)
    return domains


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []  # (tag, attr, value, line)
        self.csp_policies = []  # (content, line)
        self.ids = set()
        self.duplicate_ids = []  # (id, line)
        self.imgs_missing_alt = []  # line numbers
        self.imgs_missing_dimensions = []  # line numbers
        self.blank_targets_missing_noopener = []  # (tag, line)
        self.title = None
        self.has_description = False
        self.has_viewport = False
        self.lang = None
        self._in_title = False
        self.main_count = 0
        self.h1_count = 0
        self.heading_skips = []  # (line, from_level, to_level)
        self._max_heading_seen = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        line = self.getpos()[0]

        if tag == "html" and "lang" in attrs:
            self.lang = attrs["lang"]

        if "id" in attrs:
            element_id = attrs["id"]
            if element_id in self.ids:
                self.duplicate_ids.append((element_id, line))
            self.ids.add(element_id)

        if tag == "meta" and attrs.get("name") == "description":
            self.has_description = bool(attrs.get("content"))
        if tag == "meta" and attrs.get("name") == "viewport":
            self.has_viewport = bool(attrs.get("content"))

        for attr in ("href", "src"):
            if attr in attrs and attrs[attr]:
                self.links.append((tag, attr, attrs[attr], line))
        if tag in ("img", "source") and attrs.get("srcset"):
            for candidate in attrs["srcset"].split(","):
                parts = candidate.strip().split()
                if parts:
                    self.links.append((tag, "srcset", parts[0], line))
        if attrs.get("style"):
            for m in CSS_URL_RE.finditer(attrs["style"]):
                self.links.append((tag, "style url()", m.group(1).strip(), line))
        if tag == "meta" and attrs.get("content"):
            key = attrs.get("property") or attrs.get("name")
            if key in META_URL_KEYS:
                self.links.append((tag, "content", attrs["content"], line))
            if (attrs.get("http-equiv") or "").lower() == "content-security-policy":
                self.csp_policies.append((attrs["content"], line))

        if tag == "img":
            if "alt" not in attrs:
                self.imgs_missing_alt.append(line)
            if not attrs.get("width") or not attrs.get("height"):
                self.imgs_missing_dimensions.append(line)

        if attrs.get("target", "").lower() == "_blank":
            rel_values = set((attrs.get("rel") or "").lower().split())
            if "noopener" not in rel_values:
                self.blank_targets_missing_noopener.append((tag, line))

        if tag == "title":
            self._in_title = True

        if tag == "main":
            self.main_count += 1

        if tag == "h1":
            self.h1_count += 1

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            if level > self._max_heading_seen + 1:
                self.heading_skips.append((line, self._max_heading_seen, level))
            self._max_heading_seen = max(self._max_heading_seen, level)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title and data.strip():
            self.title = data.strip()


def jsonld_types(value):
    """Return a JSON-LD object's declared @type values as a set."""
    if not isinstance(value, dict):
        return set()
    declared = value.get("@type", [])
    if isinstance(declared, str):
        return {declared}
    if isinstance(declared, list):
        return {item for item in declared if isinstance(item, str)}
    return set()


def check_jsonld_semantics(value, rel, errors):
    """Check the small set of Schema.org ranges this site relies on."""
    if isinstance(value, list):
        for item in value:
            check_jsonld_semantics(item, rel, errors)
        return
    if not isinstance(value, dict):
        return

    if "Person" in jsonld_types(value) and "memberOf" in value:
        memberships = value["memberOf"]
        if not isinstance(memberships, list):
            memberships = [memberships]
        for membership in memberships:
            declared = jsonld_types(membership)
            if declared and declared.isdisjoint(PERSON_MEMBER_OF_TYPES):
                errors.append(
                    f"{rel}: Person.memberOf uses unexpected @type "
                    f"{', '.join(sorted(declared))}; expected one of "
                    f"{', '.join(sorted(PERSON_MEMBER_OF_TYPES))}"
                )

    for child in value.values():
        check_jsonld_semantics(child, rel, errors)


def check_file(path, domains, network, errors, warnings):
    rel = os.path.relpath(path, REPO_ROOT)
    with open(path, encoding="utf-8") as f:
        html = f.read()

    parser = PageParser()
    parser.feed(html)

    if not parser.title:
        errors.append(f"{rel}: missing <title>")
    if not parser.has_description:
        errors.append(f"{rel}: missing <meta name=\"description\">")
    if not parser.lang:
        errors.append(f"{rel}: <html> is missing a lang attribute")
    if not parser.has_viewport:
        errors.append(f"{rel}: missing <meta name=\"viewport\">")
    if parser.main_count == 0:
        errors.append(f"{rel}: no <main> landmark -- screen reader users lose a way to jump straight to content")
    elif parser.main_count > 1:
        errors.append(f"{rel}: {parser.main_count} <main> elements -- there should be exactly one")
    if parser.h1_count != 1:
        errors.append(f"{rel}: expected exactly one <h1>, found {parser.h1_count}")

    for element_id, line in parser.duplicate_ids:
        errors.append(f"{rel}:{line}: duplicate id=\"{element_id}\"")

    for line, from_level, to_level in parser.heading_skips:
        errors.append(f"{rel}:{line}: heading jumps from h{from_level} to h{to_level} with no h{to_level - 1} in between")

    for line in parser.imgs_missing_alt:
        errors.append(f"{rel}:{line}: <img> has no alt attribute (use alt=\"\" if decorative)")

    for line in parser.imgs_missing_dimensions:
        errors.append(f"{rel}:{line}: <img> must declare width and height to prevent layout shift")

    for tag, line in parser.blank_targets_missing_noopener:
        errors.append(f"{rel}:{line}: <{tag}> with target=\"_blank\" must include rel=\"noopener\"")

    links = list(parser.links)
    for style_m in re.finditer(r"<style[^>]*>(.*?)</style>", html, re.S | re.I):
        style_body = style_m.group(1)
        style_offset = style_m.start(1)
        for m in CSS_URL_RE.finditer(style_body):
            line = html.count("\n", 0, style_offset + m.start()) + 1
            links.append(("style", "url()", m.group(1).strip(), line))

    for tag, attr, value, line in links:
        if value.startswith(("mailto:", "tel:", "data:")):
            continue
        if value.startswith("#"):
            frag = value[1:]
            if frag and frag not in parser.ids:
                errors.append(f"{rel}:{line}: {tag} {attr}=\"{value}\" has no matching id on the page")
            continue
        is_absolute = value.startswith(("http://", "https://"))
        if rel == "404.html" and not is_absolute and not value.startswith("/"):
            errors.append(
                f"{rel}:{line}: {tag} {attr}=\"{value}\" is relative; 404.html is served at any "
                f"depth (e.g. /writing/missing), so use a root-absolute URL like \"/{value}\""
            )
        if is_absolute and urllib.parse.urlsplit(value).hostname not in domains:
            if network:
                check_external(value, rel, line, tag, attr, warnings)
            continue
        problem = check_site_url(value, path, domains)
        if problem:
            errors.append(f"{rel}:{line}: {tag} {attr}=\"{value}\" {problem}")

    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            errors.append(f"{rel}: invalid JSON-LD ({e})")
        else:
            check_jsonld_semantics(data, rel, errors)

    check_csp_scripts(html, parser.csp_policies, rel, errors)


def check_csp_scripts(html, csp_policies, rel, errors):
    """Ensure every inline executable <script> is allowed by any <meta> CSP."""
    if not csp_policies:
        return
    inline_scripts = []
    for m in re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, re.S | re.I):
        attrs = m.group("attrs")
        if re.search(r"\bsrc\s*=", attrs, re.I):
            continue
        type_m = re.search(r'\btype\s*=\s*["\']?([^"\'\s>]+)', attrs, re.I)
        if type_m and type_m.group(1).lower() not in ("text/javascript", "application/javascript", "module"):
            continue
        body = m.group("body").replace("\r\n", "\n").replace("\r", "\n")
        if not body.strip():
            continue
        digest = base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii")
        line = html.count("\n", 0, m.start()) + 1
        inline_scripts.append((line, f"'sha256-{digest}'"))

    for policy, csp_line in csp_policies:
        directives = {}
        for part in policy.split(";"):
            tokens = part.strip().split()
            if tokens:
                directives[tokens[0].lower()] = tokens[1:]
        effective = directives.get("script-src", directives.get("default-src", []))
        if "'unsafe-inline'" in effective:
            continue
        for script_line, expected_hash in inline_scripts:
            if expected_hash not in effective:
                errors.append(
                    f"{rel}:{script_line}: inline <script> hash {expected_hash} missing from "
                    f"CSP at line {csp_line} (update script-src after editing the script)"
                )


_ID_CACHE = {}


def page_ids(local):
    if local not in _ID_CACHE:
        parser = PageParser()
        with open(local, encoding="utf-8") as f:
            parser.feed(f.read())
        _ID_CACHE[local] = parser.ids
    return _ID_CACHE[local]


def check_site_url(value, page_path, domains):
    """Resolve an on-site URL to a repo file. Returns a problem string or None."""
    parts = urllib.parse.urlsplit(value)
    if parts.scheme:
        if parts.hostname not in domains:
            return None
        base, target = REPO_ROOT, parts.path.lstrip("/")
    elif parts.path.startswith("/"):
        base, target = REPO_ROOT, parts.path.lstrip("/")
    else:
        base, target = os.path.dirname(page_path), parts.path
    if not target or target.endswith("/"):
        target = os.path.join(target, "index.html")
    local = os.path.normpath(os.path.join(base, urllib.parse.unquote(target)))
    if not os.path.isfile(local):
        return f"-> file not found ({os.path.relpath(local, REPO_ROOT)})"
    if parts.fragment and local.endswith(".html") and parts.fragment not in page_ids(local):
        return f"-> no id=\"{parts.fragment}\" in {os.path.relpath(local, REPO_ROOT)}"
    return None


SKIP_SCAN_DIRS = {".git", "_site", ".jekyll-cache", ".sass-cache", "node_modules", "vendor"}


def repo_text_files():
    """All repo-relative text files (including excluded docs) to scan for secrets/emails."""
    files = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        rel_dir = os.path.relpath(dirpath, REPO_ROOT)
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_SCAN_DIRS)
        for name in sorted(filenames):
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXTENSIONS:
                files.append(rel_dir + name)
    return files


def check_published(domains, errors):
    """Repo-wide checks over what GitHub Pages would actually serve, plus repo-wide email scan."""
    published = published_files()
    for rel in published:
        ext = os.path.splitext(rel)[1].lower()
        if ext in INTERNAL_EXTENSIONS:
            errors.append(f"{rel}: internal file would be published on the site -- add it to _config.yml exclude")

    for rel in repo_text_files():
        with open(os.path.join(REPO_ROOT, rel), encoding="utf-8", errors="replace") as f:
            text = f.read()
        for m in EMAIL_RE.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            errors.append(
                f"{rel}:{line}: plaintext email address \"{m.group(0)}\" found in repo "
                f"(the address is assembled at runtime -- see AGENTS.md)"
            )

    sitemap = os.path.join(REPO_ROOT, "sitemap.xml")
    listed = set()
    if os.path.isfile(sitemap):
        with open(sitemap, encoding="utf-8") as f:
            for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", f.read()):
                problem = check_site_url(loc, sitemap, domains)
                if problem:
                    errors.append(f"sitemap.xml: {loc} {problem}")
                path = urllib.parse.urlsplit(loc).path.lstrip("/")
                listed.add(path if path and not path.endswith("/") else path + "index.html")
        for rel in published:
            if rel.endswith(".html") and rel != "404.html" and rel not in listed:
                errors.append(f"sitemap.xml: published page {rel} is not listed")

    llms = os.path.join(REPO_ROOT, "llms.txt")
    if os.path.isfile(llms):
        with open(llms, encoding="utf-8") as f:
            for url in re.findall(r"https?://[^\s)>\]]+", f.read()):
                problem = check_site_url(url.rstrip(".,;"), llms, domains)
                if problem:
                    errors.append(f"llms.txt: {url} {problem}")


def check_external(url, rel, line, tag, attr, warnings):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; site-link-check/1.1)"})
        urllib.request.urlopen(req, timeout=8).close()
    except Exception as e:
        detail = getattr(e, "code", None) or e.__class__.__name__
        warnings.append(f"{rel}:{line}: {tag} {attr}=\"{url}\" unreachable ({detail}) -- not fatal")


def main():
    args = sys.argv[1:]
    network = "--no-network" not in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        targets = [os.path.join(REPO_ROOT, a) for a in args]
    else:
        targets = [
            os.path.join(REPO_ROOT, rel) for rel in published_files() if rel.endswith(".html")
        ]

    domains = read_cname_domains()
    errors, warnings = [], []

    for path in targets:
        if not os.path.isfile(path):
            errors.append(f"{path}: not found")
            continue
        check_file(path, domains, network, errors, warnings)
    check_published(domains, errors)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"FAIL  {e}")

    print(f"\n{len(targets)} file(s) checked, {len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

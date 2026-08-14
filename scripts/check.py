#!/usr/bin/env python3
"""
Static checks for this repo's HTML pages. No dependencies beyond the
standard library, so it runs the same locally and in CI.

Checks:
  - every local href/src (relative path, or an absolute
    https://<CNAME domain>/... URL) points at a file that exists in the repo
  - every #fragment link resolves to an id= in the same page
  - ids are unique
  - every <img> has an alt attribute (empty alt="" is fine for decorative images)
  - every <img> declares width and height to reserve layout space
  - every target="_blank" link includes rel="noopener"
  - each page has exactly one <main> and one <h1>, with no heading-level skips
  - <title>, <meta name="description">, <meta name="viewport">, and html[lang] are present
  - any application/ld+json block is valid JSON, and Person.memberOf uses an expected type
  - no plaintext "name@domain" email pattern appears anywhere in the static HTML
    source (the contact address is assembled at runtime on purpose --
    see AGENTS.md -- so a literal match here is a regression)
  - (network, best-effort, non-fatal) external https:// links resolve.
    Skipped automatically when the sandbox has no outbound access.

Usage:
    python3 scripts/check.py            # check all *.html at repo root
    python3 scripts/check.py index.html # check a specific file
    python3 scripts/check.py --no-network
"""
import json
import os
import re
import sys
import urllib.request
from html.parser import HTMLParser

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PERSON_MEMBER_OF_TYPES = {"MemberProgramTier", "Organization", "ProgramMembership"}


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

    for tag, attr, value, line in parser.links:
        if value.startswith("mailto:") or value.startswith("tel:"):
            continue
        if value.startswith("#"):
            frag = value[1:]
            if frag and frag not in parser.ids:
                errors.append(f"{rel}:{line}: {tag} {attr}=\"{value}\" has no matching id on the page")
            continue
        if value.startswith("http://") or value.startswith("https://"):
            m = re.match(r"https?://([^/]+)(/.*)?", value)
            host, path_part = m.group(1), (m.group(2) or "/")
            if host in domains:
                local = os.path.join(REPO_ROOT, path_part.lstrip("/") or "index.html")
                if not os.path.isfile(local):
                    errors.append(f"{rel}:{line}: {tag} {attr}=\"{value}\" -> no local file at {os.path.relpath(local, REPO_ROOT)}")
            elif network:
                check_external(value, rel, line, tag, attr, warnings)
            continue
        # relative local path (strip any #fragment / ?query suffix)
        clean = value.split("#")[0].split("?")[0]
        if not clean:
            continue
        if clean.startswith("/"):
            base, clean = REPO_ROOT, clean.lstrip("/")
        else:
            base = os.path.dirname(path)
        if not clean or clean.endswith("/"):
            clean = os.path.join(clean, "index.html")
        local = os.path.normpath(os.path.join(base, clean))
        if not os.path.isfile(local):
            errors.append(f"{rel}:{line}: {tag} {attr}=\"{value}\" -> file not found ({os.path.relpath(local, REPO_ROOT)})")

    for m in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError as e:
            errors.append(f"{rel}: invalid JSON-LD ({e})")
        else:
            check_jsonld_semantics(data, rel, errors)

    static_source = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    for m in EMAIL_RE.finditer(static_source):
        errors.append(
            f"{rel}: plaintext email address \"{m.group(0)}\" found in static HTML "
            f"(the address should be assembled at runtime -- see AGENTS.md)"
        )


def check_external(url, rel, line, tag, attr, warnings):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "repo-link-check/1.0"})
        urllib.request.urlopen(req, timeout=6)
    except Exception as e:
        warnings.append(f"{rel}:{line}: {tag} {attr}=\"{url}\" unreachable ({e.__class__.__name__}) -- not fatal")


def main():
    args = sys.argv[1:]
    network = "--no-network" not in args
    args = [a for a in args if not a.startswith("--")]

    if args:
        targets = [os.path.join(REPO_ROOT, a) for a in args]
    else:
        targets = [
            os.path.join(REPO_ROOT, f)
            for f in sorted(os.listdir(REPO_ROOT))
            if f.endswith(".html")
        ]

    domains = read_cname_domains()
    errors, warnings = [], []

    for path in targets:
        if not os.path.isfile(path):
            errors.append(f"{path}: not found")
            continue
        check_file(path, domains, network, errors, warnings)

    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"FAIL  {e}")

    print(f"\n{len(targets)} file(s) checked, {len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()

"""Compare a crawl from before a site migration with a crawl from after it and flag what broke.

Input: two crawl CSVs (Screaming Frog "Internal: All", Sitebulb, or any CSV with a URL column), and
optionally the redirect map you planned (old -> new). No network: everything comes from the two crawls.

For every page that answered 200 before the migration the tool finds where it lives now (same URL,
the planned target, or the same path on the new host), follows redirects inside the new crawl, and
compares the SEO fields of the old page with the page it lands on.

Why: NP Digital found automated checks catch about 3x more SEO errors than manual reviews, and the
insight is to "Compare Results Side by Side" (slug: seo-audit-ai-vs-manual). A migration is exactly that
side-by-side check. Basics like HTTPS and sitemaps still matter for AI search (slug: technical-seo-ai-search).
Thresholds (content drop 30%, inlinks drop 50%, 10 hops) are general best practice.
"""
from urllib.parse import urlsplit

import pandas as pd

from .report import find_column, to_number

MAX_HOPS = 10
CONTENT_DROP = 30.0   # % fewer words on the landing page: content was cut (general best practice)
INLINKS_DROP = 50.0   # % fewer internal links pointing at the page (general best practice)
SEVERITY = {"critical": 0, "high": 1, "medium": 2, "low": 3}

COLUMNS = {
    "url": ["address", "url", "page", "page url", "uri", "loc"],
    "status": ["status code", "status", "http status", "http status code", "response code", "code"],
    "title": ["title 1", "title", "page title", "meta title"],
    "description": ["meta description 1", "meta description", "description"],
    "h1": ["h1-1", "h1 1", "h1", "first h1"],
    "canonical": ["canonical link element 1", "canonical", "canonical url", "canonical link"],
    "robots": ["meta robots 1", "meta robots", "robots", "x-robots-tag 1", "x-robots-tag"],
    "indexability": ["indexability status", "indexability", "indexable"],
    "word_count": ["word count", "words", "word_count"],
    "redirect_to": ["redirect url", "redirect to", "redirect_url", "location", "redirect target"],
    "inlinks": ["unique inlinks", "inlinks", "internal links in", "unique internal inlinks"],
}

PAGE_COLS = ["old_url", "new_url", "final_status", "hops", "severity", "issues", "fix"]
CHANGE_COLS = ["old_url", "new_url", "field", "before", "after"]
FIXES = {
    "not in new crawl": "Find the new home and add a 301, or check why the crawler can't reach it",
    "redirect missing": "Add a 301 to the closest matching live page",
    "server error": "Fix the server error; the page is down",
    "redirects to an error": "Publish the target page, or point the redirect at a live one",
    "redirect loop": "Break the loop: point the old URL at the live page",
    "redirect target not crawled": "Crawl the target (list mode) to confirm it is live",
    "noindex added": "Remove noindex from the new page",
    "canonical points to old domain": "Update the canonical to the new URL",
    "canonical points elsewhere": "Make the canonical self-referencing unless the move was intended",
    "not redirected as planned": "Add the planned 301 from the map",
    "redirects to wrong target": "Change the redirect to the planned target from the map",
    "temporary redirect": "Use 301 for a permanent move",
    "redirect chain": "Redirect straight to the final URL",
    "title missing": "Add a title tag",
    "h1 missing": "Add an H1",
    "content cut": "Compare old and new copy; restore the sections that ranked",
    "fewer internal links": "Restore internal links (menus, related links, breadcrumbs)",
    "title changed": "Check the new title still targets the same query",
    "h1 changed": "Check the new H1 still matches the page topic",
    "description changed": "Fine if intended; check it still matches the query",
}
LEVEL = {
    "not in new crawl": "critical", "redirect missing": "critical", "server error": "critical",
    "redirects to an error": "critical", "redirect loop": "critical", "noindex added": "critical",
    "canonical points to old domain": "high", "canonical points elsewhere": "high",
    "not redirected as planned": "high", "redirects to wrong target": "high", "title missing": "high",
    "redirect target not crawled": "medium", "temporary redirect": "medium", "redirect chain": "medium",
    "h1 missing": "medium", "content cut": "medium", "fewer internal links": "medium",
    "title changed": "low", "h1 changed": "low", "description changed": "low",
}


def key(url: str) -> str:
    """Host-independent key: path + query, so a domain move still matches pages by path."""
    p = urlsplit(str(url).strip())
    path = p.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")
    return path.lower() + (f"?{p.query}" if p.query else "")


def host(url: str) -> str:
    return urlsplit(str(url).strip()).netloc.lower().removeprefix("www.")


def same_page(planned: str, actual: str) -> bool:
    """Planned target matches the landing URL (path key, and host when the plan names one)."""
    return key(planned) == key(actual) and (not host(planned) or host(planned) == host(actual))


def clean_url(url: str) -> str:
    return str(url).strip().split("#")[0]


def load_crawl(path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8-sig", sep=None, engine="python", dtype=str).fillna("")
    found = {name: find_column(raw, cands) for name, cands in COLUMNS.items()}
    if found["url"] is None:
        raise ValueError(f"{path}: no URL column (looked for Address / URL).")
    out = pd.DataFrame({name: (raw[col].astype(str).str.strip() if col else "") for name, col in found.items()})
    out["url"] = out["url"].map(clean_url)
    out = out[out["url"].str.startswith(("http://", "https://"))]
    out["status"] = to_number(out["status"]).astype(int) if found["status"] else 200
    out["word_count"] = to_number(out["word_count"]).astype(int) if found["word_count"] else 0
    out["inlinks"] = to_number(out["inlinks"]).astype(int) if found["inlinks"] else 0
    flags = (out["robots"] + " " + out["indexability"]).str.lower()
    out["noindex"] = [("noindex" in f) for f in flags]
    out["key"] = out["url"].map(key)
    out.attrs["has"] = {name for name, col in found.items() if col}
    return out.drop_duplicates("url").reset_index(drop=True)


def load_map(path) -> dict:
    """Planned redirects: {key(old): new_url}."""
    df = pd.read_csv(path, encoding="utf-8-sig", sep=None, engine="python", dtype=str).fillna("")
    s = find_column(df, ["source", "from", "old url", "old", "old_url", "redirect from", "url"])
    t = find_column(df, ["target", "to", "new url", "new", "new_url", "redirect to", "destination"])
    if s is None or t is None:
        s, t = df.columns[:2]
    return {key(a): b.strip() for a, b in zip(df[s], df[t]) if a.strip() and b.strip()}


class Index:
    """Look up rows of the after-crawl by exact URL, then by path key (200 pages first)."""

    def __init__(self, after: pd.DataFrame):
        self.rows = after.to_dict("records")
        self.by_url = {r["url"]: r for r in self.rows}
        self.by_key = {}
        for r in sorted(self.rows, key=lambda r: r["status"] != 200):
            self.by_key.setdefault(r["key"], r)

    def get(self, url, exact_only=False):
        url = clean_url(url)
        if url in self.by_url:
            return self.by_url[url]
        if exact_only:
            return None
        return self.by_key.get(key(url))


def resolve(start: dict, index: Index):
    """Follow redirects inside the after-crawl. Returns (final_row, hops, codes, problem)."""
    row, hops, codes, seen = start, 0, [], {start["url"]}
    while 300 <= row["status"] < 400:
        codes.append(row["status"])
        target = row["redirect_to"]
        if not target:
            return row, hops, codes, "redirect target not crawled"
        if not target.startswith(("http://", "https://")):
            p = urlsplit(row["url"])
            target = f"{p.scheme}://{p.netloc}{target if target.startswith('/') else '/' + target}"
        hops += 1
        nxt = index.get(target, exact_only=True) or index.get(target)
        if nxt is None:
            return {**row, "url": target, "status": 0}, hops, codes, "redirect target not crawled"
        if nxt["url"] in seen or hops > MAX_HOPS:
            return nxt, hops, codes, "redirect loop"
        seen.add(nxt["url"])
        row = nxt
    return row, hops, codes, ""


def _norm(text) -> str:
    return " ".join(str(text).split()).casefold()


def compare(before: pd.DataFrame, after: pd.DataFrame, planned: dict | None = None):
    """Returns (pages, changes): one row per old 200 page, and one row per changed SEO field."""
    planned = planned or {}
    has = after.attrs.get("has", set()) & before.attrs.get("has", set())
    index = Index(after)
    old_hosts = {host(u) for u in before["url"]}
    pages, changes = [], []
    live = before[before["status"] == 200]
    for old in live.to_dict("records"):
        issues, target = [], planned.get(old["key"], "")
        start = index.get(old["url"], exact_only=True)
        if start is None and target:
            start = index.get(target)
        if start is None:
            start = index.get(old["url"])
        if start is None:
            pages.append(_page(old["url"], "", "", 0, ["not in new crawl"]))
            continue
        final, hops, codes, problem = resolve(start, index)
        if problem:
            issues.append(problem)
        st = final["status"]
        if problem != "redirect loop" and st and st != 200:
            if hops:
                issues.append("redirects to an error")
            elif st >= 500:
                issues.append("server error")
            else:
                issues.append("redirect missing")
        if hops > 1 and problem != "redirect loop":
            issues.append("redirect chain")
        if any(c in (302, 303, 307) for c in codes):
            issues.append("temporary redirect")
        if target and st == 200 and not same_page(target, final["url"]):
            issues.append("redirects to wrong target" if hops else "not redirected as planned")
        if st == 200:
            issues += _field_issues(old, final, has, old_hosts, changes)
        pages.append(_page(old["url"], final["url"], st or "", hops, issues))
    pages = pd.DataFrame(pages, columns=PAGE_COLS)
    if not pages.empty:
        pages["_s"] = pages["severity"].map(lambda s: SEVERITY.get(s, 9))
        pages = pages.sort_values(["_s", "old_url"]).drop(columns="_s").reset_index(drop=True)
    return pages, pd.DataFrame(changes, columns=CHANGE_COLS)


def _field_issues(old, new, has, old_hosts, changes):
    issues = []

    def change(field, a, b):
        changes.append({"old_url": old["url"], "new_url": new["url"], "field": field, "before": a, "after": b})

    if new["noindex"] and not old["noindex"]:
        issues.append("noindex added")
        change("noindex", "no", "yes")
    if "canonical" in has and new["canonical"]:
        canon_elsewhere = key(new["canonical"]) != new["key"] or host(new["canonical"]) != host(new["url"])
        old_canon_self = not old["canonical"] or key(old["canonical"]) == old["key"]
        if canon_elsewhere and old_canon_self:
            moved_host = host(new["url"]) not in old_hosts
            issues.append("canonical points to old domain" if moved_host and host(new["canonical"]) in old_hosts
                          else "canonical points elsewhere")
            change("canonical", old["canonical"], new["canonical"])
    for field, missing, changed in [("title", "title missing", "title changed"), ("h1", "h1 missing", "h1 changed"),
                                    ("description", "", "description changed")]:
        if field not in has or not old[field]:
            continue
        if not new[field] and missing:
            issues.append(missing)
            change(field, old[field], "")
        elif _norm(old[field]) != _norm(new[field]):
            issues.append(changed)
            change(field, old[field], new[field])
    if "word_count" in has and old["word_count"] >= 100:
        drop = (old["word_count"] - new["word_count"]) / old["word_count"] * 100
        if drop >= CONTENT_DROP:
            issues.append("content cut")
            change("word_count", old["word_count"], new["word_count"])
    if "inlinks" in has and old["inlinks"] >= 4:
        drop = (old["inlinks"] - new["inlinks"]) / old["inlinks"] * 100
        if drop >= INLINKS_DROP:
            issues.append("fewer internal links")
            change("inlinks", old["inlinks"], new["inlinks"])
    return issues


def _page(old_url, new_url, status, hops, issues):
    issues = list(dict.fromkeys(issues))
    issues.sort(key=lambda i: SEVERITY[LEVEL[i]])
    severity = LEVEL[issues[0]] if issues else "ok"
    return {"old_url": old_url, "new_url": new_url, "final_status": status, "hops": hops,
            "severity": severity, "issues": "; ".join(issues), "fix": FIXES[issues[0]] if issues else ""}


def summary(pages: pd.DataFrame) -> pd.DataFrame:
    cols = ["issue", "severity", "pages", "fix"]
    if pages.empty:
        return pd.DataFrame([], columns=cols)
    counts = {}
    for issues in pages["issues"]:
        for i in filter(None, str(issues).split("; ")):
            counts[i] = counts.get(i, 0) + 1
    rows = [{"issue": i, "severity": LEVEL[i], "pages": n, "fix": FIXES[i]} for i, n in counts.items()]
    rows.sort(key=lambda r: (SEVERITY[r["severity"]], -r["pages"]))
    return pd.DataFrame(rows, columns=cols)


def new_only(before: pd.DataFrame, after: pd.DataFrame, pages: pd.DataFrame) -> pd.DataFrame:
    """200 pages in the new crawl that no old page lands on (new content, or old pages that lost their match)."""
    cols = ["url", "status", "title"]
    landed = set(pages["new_url"]) if not pages.empty else set()
    old_urls = set(before["url"])
    rows = after[(after["status"] == 200) & ~after["url"].isin(landed) & ~after["url"].isin(old_urls)]
    return pd.DataFrame(rows[["url", "status", "title"]].values.tolist(), columns=cols)


def redirects_to_add(pages: pd.DataFrame, planned: dict) -> pd.DataFrame:
    """301 rules for broken old URLs that have a planned target in the map."""
    cols = ["source", "target", "status"]
    if pages.empty or not planned:
        return pd.DataFrame([], columns=cols)
    need = ("not in new crawl", "redirect missing", "not redirected as planned", "redirects to wrong target",
            "redirects to an error", "redirect chain", "redirect loop", "server error")
    rows = []
    for old, new, issues in zip(pages["old_url"], pages["new_url"], pages["issues"]):
        t = planned.get(key(old))
        if t and new and same_page(t, new) and "redirects to an error" in issues:
            continue  # the redirect is right; the planned page itself is broken
        if t and any(n in issues for n in need):
            rows.append({"source": old, "target": t, "status": 301})
    return pd.DataFrame(rows, columns=cols)

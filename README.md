<div align="center">

# 🚚 site-migration-diff

### Compare a crawl from before a site migration with one from after it, and get a list of every page that broke and why.

[![tests](https://github.com/marketing-MEER/site-migration-diff/actions/workflows/ci.yml/badge.svg)](https://github.com/marketing-MEER/site-migration-diff/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![No API keys](https://img.shields.io/badge/API%20keys-none%20needed-brightgreen)
[![Part of SEO Toolbox](https://img.shields.io/badge/part%20of-SEO%20Toolbox-orange)](https://github.com/marketing-MEER/seo-toolbox)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Meer%20Hamza-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)

[🚀 Quick start](#quick-start) · [⚙️ How it works](#how-it-works) · [📄 Report](#report) · [❓ FAQ](#faq) · [👤 Author](#author)

</div>

---

## 💡 What it does

On launch day of a migration someone usually puts two crawl exports side by side in a spreadsheet and VLOOKUPs their way through thousands of rows. `site-migration-diff` does that comparison for you: every page that answered 200 before the move is matched to where it lives now, redirects are followed inside the new crawl, and the SEO fields of the old page are compared with the page it lands on.

- ✅ Finds lost pages, missing redirects, redirects to 404s, loops, chains, 302s and server errors
- ✅ Catches the quiet ones: noindex added, canonicals left on the old domain, titles and H1s changed or gone, content cut, internal links lost
- ✅ With your redirect map: checks each old URL lands where you planned, and writes the 301 rules that are still missing
- ✅ Works across a domain change (pages are matched by path when the host changed)
- ✅ Free, MIT licensed, no API keys. Works with the crawl exports you already have.

## 📊 Why this matters

> **AI Detects 3x More SEO Errors Than Humans** · NP Digital, February 2025 (NP Digital worked with 13 SEOs to audit 5 random sites manually, comparing results to AI tools. 1000-page crawl limit)
> - AI tools detected 259 SEO errors vs. 83 by human audits.
> - 185 errors were detected by AI but not by humans.
> - AI identifies more technical and small-scale issues.
>
> **Technical SEO Still Matters for AI Search** · NP Digital, November 2024 (Based on ChatGPT responses and 409 SEO expert rankings)
> - Factors like XML sitemaps and HTTPS still ranked meaningfully.
>
> Data: [AI vs manual SEO audits](https://neilpatel.com/marketing-stats/seo-audit-ai-vs-manual/) · [technical SEO and AI search](https://neilpatel.com/marketing-stats/technical-seo-ai-search/)

**How site-migration-diff uses this:** the audit study's insight is to *"Compare Results Side by Side"*, and a migration check is exactly that. The tool compares every field automatically so a person only reviews the pages that changed. And because fundamentals like HTTPS and crawlability still count for AI search, the problems that take a page out of the index (lost, noindex, server error, canonical on the old domain) are rated critical or high.

<a id="quick-start"></a>

## 🚀 Quick start

```bash
git clone https://github.com/marketing-MEER/site-migration-diff.git
cd site-migration-diff
pip install -e .
site-migration-diff examples/crawl_before.csv examples/crawl_after.csv --map examples/redirect_map.csv
```

This writes **`migration_diff.html`** (a formatted report you can open, share or print to PDF) and **`migration_diff.xlsx`** (all the data).

> [!TIP]
> If the `site-migration-diff` command isn't found, use `python -m site_migration_diff`.

## 📥 Input

| Input | How to get it |
|---|---|
| `BEFORE` crawl | Crawl the old site **before** launch. Screaming Frog: *Internal → All → Export*. Sitebulb or any crawler CSV works too |
| `AFTER` crawl | After launch, crawl the **old URLs in list mode** (Screaming Frog: *Mode → List*, paste the old URLs) **plus** the new site, and export both in one CSV. Don't let the crawler follow redirects into one row; each hop should be its own row with its `Redirect URL` |
| `--map FILE` (optional) | Your planned redirects: a CSV with old and new URL columns (`old_url`/`source`/`from` and `new_url`/`target`/`to`). Paths or full URLs |

Columns are detected by name: `Address`/`URL`, `Status Code`, `Title 1`, `Meta Description 1`, `H1-1`, `Canonical Link Element 1`, `Meta Robots 1` (or `Indexability Status`), `Word Count`, `Unique Inlinks`/`Inlinks`, `Redirect URL`. Only the URL column is required; a field is compared only when both crawls have it.

<a id="how-it-works"></a>

## ⚙️ How it works

1. **Which pages:** every URL that answered 200 in the before crawl. Old redirects and errors are skipped.
2. **Where it lives now:** the same URL in the after crawl; if it isn't there, the planned target from your map; if that isn't there either, the same path on any host (so `www.old.shop/tents` finds `new.com/tents`).
3. **Follow redirects** inside the after crawl, up to 10 hops, and note loops, chains (more than one hop) and 302/303/307s.
4. **Compare** the old page with the landing page: noindex, canonical, title, H1, meta description, word count and internal links pointing at the page.
5. **Rate** each issue (general best practice):

| Severity | Issues |
|---|---|
| critical | not in new crawl, redirect missing (old URL now 4xx), server error, redirects to an error, redirect loop, noindex added |
| high | canonical points to old domain, canonical points elsewhere, redirects to wrong target / not redirected as planned (needs `--map`), title missing |
| medium | redirect chain, temporary redirect, redirect target not crawled, H1 missing, content cut (30%+ fewer words), fewer internal links (50%+ fewer) |
| low | title, H1 or meta description changed |

A page's severity is its worst issue. Content and inlink drops are only checked on pages that had at least 100 words or 4 inlinks before.

### Options

| Option | Default | What it does |
|---|---|---|
| `BEFORE`, `AFTER` | required | The two crawl CSVs |
| `--map` | none | Planned redirect map; adds the "as planned" checks and the *Redirects to add* sheet |
| `-o`, `--output` | `migration_diff` | File name for the report (`.html` + `.xlsx`) |

<a id="report"></a>

## 📄 The report

| Section / Excel sheet | Shows |
|---|---|
| Summary cards | Old pages checked, OK, and pages per severity |
| Benchmark panels | The two NP Digital stats and how the tool uses them |
| **Summary** | Each issue with its severity, number of pages and the fix |
| **Pages to fix** | Every old page with a problem: where it lands, final status, hops, severity, all issues, the fix for the worst one |
| **Redirects to add** | With `--map`: 301 rules from your map for old URLs that don't land where planned (left out when the redirect is right but the planned page itself is broken) |
| **Changed fields** | Old and new value for every changed title, H1, description, canonical, noindex, word count and inlink count |
| **New only** | 200 pages in the new crawl that no old page lands on: new content, or the real new home of an old page that lost its match |
| **All pages** | Every old page, including the ones that are fine |

<details>
<summary>📄 Example: real output from <code>examples/</code> (fictional shop moving from www.trailforge.shop to trailforge.com)</summary>

16 old pages checked, 13 with issues:

| issue | severity | pages |
|---|---|---|
| redirect missing | critical | 1 |
| redirects to an error | critical | 1 |
| not in new crawl | critical | 1 |
| server error | critical | 1 |
| redirect loop | critical | 1 |
| noindex added | critical | 1 |
| redirects to wrong target | high | 1 |
| canonical points to old domain | high | 1 |
| content cut | medium | 2 |
| h1 missing | medium | 1 |
| fewer internal links | medium | 1 |
| redirect chain | medium | 1 |
| temporary redirect | medium | 1 |
| title changed | low | 2 |
| description changed | low | 2 |
| h1 changed | low | 1 |

Pages to fix (old paths on `www.trailforge.shop`, `new:` = `trailforge.com`):

| old url | new url | final status | severity | issues |
|---|---|---|---|---|
| /backpacks/daypack-25l | /backpacks/daypack-25l | 404 | critical | redirect missing |
| /blog/layering-guide | new:/journal/layering-guide | 404 | critical | redirects to an error |
| /gift-cards |  |  | critical | not in new crawl |
| /returns | /returns | 503 | critical | server error |
| /shipping | /shipping | 301 | critical | redirect loop |
| /sleeping-bags/down-0c | new:/shop/sleeping-bags/down-0c | 200 | critical | noindex added |
| /tents/family-6p | new:/shop/tents | 200 | high | redirects to wrong target; content cut; title changed; h1 changed; description changed |
| /tents/ultralight-2p | new:/shop/tents/ultralight-2p | 200 | high | canonical points to old domain |
| /about | new:/about-us | 200 | medium | h1 missing; fewer internal links |
| /backpacks | new:/shop/backpacks | 200 | medium | redirect chain |
| /blog/how-to-pick-a-tent | new:/journal/how-to-pick-a-tent | 200 | medium | content cut; title changed |
| /sleeping-bags | new:/shop/sleeping-bags | 200 | medium | temporary redirect |
| /contact | new:/contact | 200 | low | description changed |

Redirects to add:

| source | target | status |
|---|---|---|
| old:/backpacks/daypack-25l | new:/shop/backpacks/daypack-25l | 301 |
| old:/gift-cards | new:/gift-cards | 301 |
| old:/returns | new:/help/returns | 301 |
| old:/shipping | new:/help/shipping | 301 |
| old:/tents/family-6p | new:/shop/tents/family-6p | 301 |
| old:/backpacks | new:/shop/backpacks | 301 |

</details>

## 🧰 More free SEO tools

This repo is one tool in the **[SEO Toolbox](https://github.com/marketing-MEER/seo-toolbox)**, a family of free, single-purpose SEO tools. Related:
- [redirect-chain-fixer](https://github.com/marketing-MEER/redirect-chain-fixer): find redirect chains and loops and write the direct rules for Apache and nginx
- [robots-sitemap-validator](https://github.com/marketing-MEER/robots-sitemap-validator): find redirects, 404s and noindex pages listed in your sitemaps
- [internal-link-analyzer](https://github.com/marketing-MEER/internal-link-analyzer): orphan pages, click depth and internal link equity
- [seo-workhorse](https://github.com/marketing-MEER/seo-workhorse): audit, clustering, redirects and GSC quick wins in one CLI

<a id="faq"></a>

## ❓ FAQ

<details><summary><b>Why does the after crawl need the old URLs too?</b></summary>

A normal crawl of the new site never visits the old URLs, so it can't tell you whether they redirect. Crawl the old URL list in list mode and add the new site crawl to the same export. If an old URL is missing from the after crawl, the tool still tries the planned target and the same path on the new host, but it can't check the redirect itself.
</details>

<details><summary><b>I only changed URLs, not the domain. Does it work?</b></summary>

Yes. Same-domain restructures, domain moves, http to https and www to non-www all work. With a domain move, pages are matched by path when there is no redirect map.
</details>

<details><summary><b>Every title changed because we changed the brand suffix. Now what?</b></summary>

Title, H1 and description changes are rated low and sit at the bottom. Filter the *Changed fields* sheet in Excel to see whether the change is only the suffix.
</details>

<details><summary><b>Is my data sent anywhere?</b></summary>

No. The tool only reads the CSV files you give it and makes no network requests.
</details>

## 🧪 Tests

```bash
python -m unittest discover -s tests -t . -v
```

## 📄 License

[MIT](LICENSE). Free for personal and commercial use. Benchmark figures © their original publishers and quoted with a link to the source.

<a id="author"></a>

## 👤 Author

**Meer Hamza** · SEO Team Lead · Berlin 🇩🇪
10+ years in SEO, AEO and GEO. I build small tools that take the spreadsheet work out of SEO.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)
[![Email](https://img.shields.io/badge/Email-meerhamza5%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:meerhamza5@gmail.com)

<div align="center">

**If this saved you time, a ⭐ helps other SEOs find it.**

</div>

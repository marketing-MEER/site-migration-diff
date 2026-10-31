# 📂 Examples

Made-up data for a fictional outdoor shop moving from `www.trailforge.shop` to `trailforge.com`. Not a real company; every URL, title and number is invented.

| File | What |
|---|---|
| `crawl_before.csv` | Screaming Frog style "Internal: All" export of the old site, before the move |
| `crawl_after.csv` | Crawl after the move: the old URLs in list mode plus a crawl of the new site |
| `redirect_map.csv` | The planned redirects (old URL, new URL) |

The after crawl has the usual launch-day problems built in: a missing redirect, a redirect to a 404, a loop, a 302, a chain, a page with noindex, a canonical left on the old domain, cut content and a page that lost its menu links.

```bash
site-migration-diff examples/crawl_before.csv examples/crawl_after.csv --map examples/redirect_map.csv
```

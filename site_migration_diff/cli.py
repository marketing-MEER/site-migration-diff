"""Command line entry point: `site-migration-diff BEFORE.csv AFTER.csv [--map REDIRECTS.csv]`."""
from pathlib import Path

import click

from . import __version__, core
from .benchmark import STATS
from .report import Report, write_excel


@click.command()
@click.argument("before", type=click.Path(exists=True))
@click.argument("after", type=click.Path(exists=True))
@click.option("--map", "map_file", type=click.Path(exists=True), default=None,
              help="Planned redirect map CSV (old, new). Checks each old URL lands where you planned.")
@click.option("-o", "--output", default="migration_diff", show_default=True,
              help="Report name; writes <name>.html and <name>.xlsx")
@click.version_option(__version__)
def main(before, after, map_file, output):
    """Compare a crawl from BEFORE a site migration with one from AFTER it and flag what broke.

    Built by Meer Hamza - linkedin.com/in/meerhamza-seo
    """
    old, new = core.load_crawl(before), core.load_crawl(after)
    planned = core.load_map(map_file) if map_file else {}
    pages, changes = core.compare(old, new, planned)
    summ = core.summary(pages)
    broken = pages[pages["severity"] != "ok"]
    out = Path(output)

    sources = [f"{Path(before).name}: {len(old):,} URLs", f"{Path(after).name}: {len(new):,} URLs"]
    if map_file:
        sources.append(f"{Path(map_file).name}: {len(planned):,} planned redirects")
    report = Report(title="Site migration diff", subtitle=" · ".join(sources), tool="site-migration-diff")
    count = lambda s: int((pages["severity"] == s).sum())
    report.add_cards([("Old pages checked", len(pages)), ("OK", count("ok"), "good"),
                      ("Critical", count("critical"), "bad"), ("High", count("high"), "warn"),
                      ("Medium", count("medium")), ("Low", count("low"))])
    report.add_benchmark(STATS[0], how_used="The insight 'Compare Results Side by Side' is what a migration "
                         "check is: every page that answered 200 before is matched to where it lives now, and "
                         "status, redirects, title, H1, canonical, noindex, word count and inlinks are compared "
                         "automatically, so a person only reviews the pages that changed.")
    report.add_benchmark(STATS[1], how_used="Fundamentals still count for AI search, so the checks that matter "
                         "most after a move (pages lost, noindex added, canonicals left on the old domain) are "
                         "rated critical or high.")
    report.add_table("Issues", summ, sheet="Summary", note="Severity: critical = page lost or blocked from the "
                     "index, high = signals point the wrong way, medium = works but leaks, low = check it.")
    report.add_table("Pages to fix", broken, sheet="Pages to fix")
    if map_file:
        report.add_table("Redirects to add", core.redirects_to_add(pages, planned), sheet="Redirects to add",
                         note="301 rules from your map for old URLs that don't land where planned.")
    report.add_table("Changed SEO fields", changes, sheet="Changed fields")
    report.add_table("New pages no old URL lands on", core.new_only(old, new, pages), sheet="New only",
                     note="New content, or the new home of an old page that lost its match.")
    report.add_table("All old pages", pages, sheet="All pages")
    skipped = len(old) - len(pages)
    if skipped:
        report.add_text("Not checked", [f"{skipped:,} URLs in the before crawl were not 200 (redirects, errors) "
                                        "and are not checked."])

    html_path = report.save_html(out.with_suffix(".html"))
    xlsx_path = write_excel(report.sheets, out.with_suffix(".xlsx"))
    click.secho(f"Report: {html_path}\nData:   {xlsx_path}", fg="green", bold=True)
    click.echo(f"{len(pages)} old pages checked, {len(broken)} with issues.")
    if not summ.empty:
        click.echo(summ[["issue", "severity", "pages"]].to_string(index=False))


if __name__ == "__main__":
    main()

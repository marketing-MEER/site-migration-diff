import tempfile
import unittest
from pathlib import Path

import pandas as pd
from click.testing import CliRunner

from site_migration_diff import cli, core

EXAMPLES = Path(__file__).parent.parent / "examples"
O, N = "https://www.trailforge.shop", "https://trailforge.com"


def crawl(rows, has=("url", "status", "title", "h1", "canonical", "robots", "word_count", "inlinks", "redirect_to")):
    base = {"title": "", "description": "", "h1": "", "canonical": "", "robots": "", "indexability": "",
            "word_count": 0, "inlinks": 0, "redirect_to": ""}
    df = pd.DataFrame([{**base, **r} for r in rows])
    df["noindex"] = [("noindex" in r) for r in df["robots"]]
    df["key"] = df["url"].map(core.key)
    df.attrs["has"] = set(has)
    return df


class ExampleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = core.load_crawl(EXAMPLES / "crawl_before.csv")
        cls.after = core.load_crawl(EXAMPLES / "crawl_after.csv")
        cls.plan = core.load_map(EXAMPLES / "redirect_map.csv")
        cls.pages, cls.changes = core.compare(cls.before, cls.after, cls.plan)
        cls.by = cls.pages.set_index("old_url")

    def issues(self, path):
        return self.by.at[O + path, "issues"]

    def test_load(self):
        self.assertEqual(len(self.before), 17)
        self.assertEqual(len(self.pages), 16)               # the 301 in the old crawl is not checked
        self.assertTrue(self.after.set_index("url").at[N + "/shop/sleeping-bags/down-0c", "noindex"])

    def test_broken_pages(self):
        self.assertIn("redirect missing", self.issues("/backpacks/daypack-25l"))
        self.assertEqual(self.issues("/blog/layering-guide"), "redirects to an error")
        self.assertEqual(self.issues("/gift-cards"), "not in new crawl")
        self.assertEqual(self.issues("/returns"), "server error")
        self.assertEqual(self.issues("/shipping"), "redirect loop")
        self.assertEqual(self.issues("/sleeping-bags/down-0c"), "noindex added")

    def test_signals_and_redirects(self):
        self.assertEqual(self.issues("/tents/ultralight-2p"), "canonical points to old domain")
        self.assertTrue(self.issues("/tents/family-6p").startswith("redirects to wrong target"))
        self.assertEqual(self.issues("/backpacks"), "redirect chain")
        self.assertEqual(self.by.at[O + "/backpacks", "hops"], 2)
        self.assertEqual(self.issues("/sleeping-bags"), "temporary redirect")
        self.assertEqual(self.issues("/about"), "h1 missing; fewer internal links")
        self.assertIn("content cut", self.issues("/blog/how-to-pick-a-tent"))
        self.assertEqual(self.by.at[O + "/tents", "severity"], "ok")

    def test_rules_and_new_pages(self):
        rules = core.redirects_to_add(self.pages, self.plan)
        self.assertIn(O + "/backpacks/daypack-25l", set(rules["source"]))
        self.assertNotIn(O + "/tents", set(rules["source"]))
        self.assertNotIn(O + "/blog/layering-guide", set(rules["source"]))   # redirect is right, target is broken
        self.assertEqual(len(rules), 6)
        new = core.new_only(self.before, self.after, self.pages)
        self.assertIn(N + "/journal/trail-food-ideas", set(new["url"]))
        self.assertIn(N + "/shop/tents/family-6p", set(new["url"]))


class RuleTest(unittest.TestCase):
    def test_same_path_on_new_host_without_map(self):
        before = crawl([{"url": "https://old.com/a", "status": 200, "title": "A"}])
        after = crawl([{"url": "https://new.com/a/", "status": 200, "title": "A"}])
        pages, _ = core.compare(before, after)
        self.assertEqual(pages.iloc[0]["severity"], "ok")
        self.assertEqual(pages.iloc[0]["new_url"], "https://new.com/a/")

    def test_old_host_still_live_is_not_as_planned(self):
        before = crawl([{"url": "https://old.com/a", "status": 200}])
        after = crawl([{"url": "https://old.com/a", "status": 200}, {"url": "https://new.com/a", "status": 200}])
        pages, _ = core.compare(before, after, {"/a": "https://new.com/a"})
        self.assertEqual(pages.iloc[0]["issues"], "not redirected as planned")

    def test_relative_redirect_and_missing_columns(self):
        before = crawl([{"url": "https://s.com/a", "status": 200, "title": "A"}], has=("url", "status", "title"))
        after = crawl([{"url": "https://s.com/a", "status": 301, "redirect_to": "/b"},
                       {"url": "https://s.com/b", "status": 200, "title": "A", "canonical": "https://x.com/"}],
                      has=("url", "status", "title", "redirect_to"))
        pages, changes = core.compare(before, after)
        self.assertEqual(pages.iloc[0]["severity"], "ok")     # canonical not compared: not in both crawls
        self.assertTrue(changes.empty)

    def test_empty(self):
        before = crawl([{"url": "https://s.com/a", "status": 404}])
        pages, changes = core.compare(before, crawl([{"url": "https://s.com/a", "status": 404}]))
        self.assertTrue(pages.empty and changes.empty)
        self.assertTrue(core.summary(pages).empty)
        self.assertTrue(core.redirects_to_add(pages, {"/a": "/b"}).empty)
        self.assertEqual(list(core.new_only(before, before, pages).columns), ["url", "status", "title"])


class CliTest(unittest.TestCase):
    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "m"
            result = CliRunner().invoke(cli.main, [str(EXAMPLES / "crawl_before.csv"), str(EXAMPLES / "crawl_after.csv"),
                                                   "--map", str(EXAMPLES / "redirect_map.csv"), "-o", str(out)])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Site migration diff", out.with_suffix(".html").read_text(encoding="utf-8"))
            sheets = pd.read_excel(out.with_suffix(".xlsx"), sheet_name=None)
            self.assertEqual(len(sheets["Pages to fix"]), 13)
            self.assertIn("Redirects to add", sheets)


if __name__ == "__main__":
    unittest.main()

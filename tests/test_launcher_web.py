import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "web-results.py"
sys.path.insert(0, str(SOURCE.parent))
spec = importlib.util.spec_from_file_location("launcher_web", SOURCE)
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


class WebResultsTests(unittest.TestCase):
    def test_rss_titles_urls_and_deduplication(self):
        rss = b"""<rss><channel>
          <item><title> Docs &amp; examples </title><link>https://www.example.com/docs?q=a&amp;b=2</link></item>
          <item><title>Duplicate</title><link>https://www.example.com/docs?q=a&amp;b=2</link></item>
          <item><title>Executable URL</title><link>javascript:alert(1)</link></item>
          <item><title>Missing host</title><link>https:///bad</link></item>
          <item><title>Second result</title><link>https://docs.example.org/</link></item>
        </channel></rss>"""
        rows = web.parse_results(rss)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], {"title": "Docs & examples", "url": "https://www.example.com/docs?q=a&b=2", "detail": "example.com"})

    def test_result_limit(self):
        items = "".join(f"<item><title>Result {i}</title><link>https://example.com/{i}</link></item>" for i in range(10))
        self.assertEqual(len(web.parse_results(f"<rss><channel>{items}</channel></rss>")), 4)

    def test_html_results_and_redirect_links(self):
        html = b'''<a href="/settings">Settings</a>
        <a href="/url?q=https%3A%2F%2Fexample.com%2Fdocs"><h3>Docs &amp; examples</h3><span>Not the title</span></a>
        <a href="https://example.com/docs"><h3>Duplicate</h3></a>
        <a class="result__a" href="https://another.example/">Another result</a>
        <a href="javascript:alert(1)"><h3>Unsafe</h3></a>'''
        rows = web.parse_html(html, "https://www.google.com/search?q=docs")
        self.assertEqual([row["url"] for row in rows], ["https://example.com/docs", "https://another.example/"])
        self.assertEqual(rows[0]["title"], "Docs & examples")

    def test_duckduckgo_redirect(self):
        self.assertEqual(web.result_url("/l/?uddg=https%3A%2F%2Fexample.com%2F", "https://duckduckgo.com/html/"), "https://example.com/")

    def test_configured_provider_is_the_only_preview_destination(self):
        engine = {"template": "https://custom.example/search?q={searchTerms}"}
        with patch.object(web.urllib.request, "urlopen", side_effect=OSError("offline")) as request:
            with self.assertRaises(OSError):
                web.search("cats & dogs", engine)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args[0].full_url, "https://custom.example/search?q=cats+%26+dogs")

    def test_native_browser_does_not_request_preview_from_another_provider(self):
        engine = {"browser": "Firefox", "name": "Browser default", "mode": "native", "desktop": "firefox.desktop"}
        with patch.object(web.browser_search, "resolve", return_value=engine), patch.object(web.urllib.request, "urlopen") as request:
            result = web.query_results("cats")
        self.assertEqual(result["status"], "native")
        self.assertEqual(result["rows"], [])
        request.assert_not_called()

    def test_helper_never_writes_cache_files_into_watched_plugin_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory)
            for name in ("web-results.py", "browser_search.py"):
                shutil.copyfile(SOURCE.parent / name, plugin / name)
            # Even an invocation without -B must not create a __pycache__ folder.
            env = {**os.environ, "PATH": ""}
            env.pop("PYTHONDONTWRITEBYTECODE", None)
            result = subprocess.run([sys.executable, str(plugin / "web-results.py"), "ab"],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({path.name for path in plugin.iterdir()}, {"web-results.py", "browser_search.py"})


if __name__ == "__main__":
    unittest.main()

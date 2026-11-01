import json
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import browser_search as browser


class BrowserSearchTests(unittest.TestCase):
    def test_custom_engine_and_safe_query_encoding(self):
        self.assertEqual(browser.search_url("https://unduck.link?q={searchTerms}", "!w cats & dogs"),
                         "https://unduck.link?q=%21w+cats+%26+dogs")
        self.assertEqual(browser.search_url("https://custom.example/?q=%s", "a+b"), "https://custom.example/?q=a%2Bb")
        with self.assertRaises(browser.SearchSettingError):
            browser.search_url("javascript:alert({searchTerms})", "cats")
        with self.assertRaises(browser.SearchSettingError):
            browser.search_url("https://custom.example/?unsupported={requiredToken}", "cats")

    def test_google_browser_specific_template_parameters(self):
        url = browser.search_url("{google:baseURL}search?q={searchTerms}&{google:RLZ}&ie={inputEncoding}", "a b")
        self.assertEqual(url, "https://www.google.com/search?q=a+b&&ie=UTF-8")

    def test_default_browser_ignores_browser_shell_override_and_uses_xdg_fallback(self):
        responses = [subprocess.CompletedProcess([], 0, ""), subprocess.CompletedProcess([], 0, "google-chrome.desktop\n")]
        with patch.dict(os.environ, {"BROWSER": "some-other-browser"}), patch.object(browser.subprocess, "run", side_effect=responses) as run:
            self.assertEqual(browser.default_desktop(), "google-chrome.desktop")
        self.assertNotIn("BROWSER", run.call_args_list[0].kwargs["env"])
        self.assertEqual(run.call_args_list[1].args[0], ("xdg-mime", "query", "default", "x-scheme-handler/https"))

    def test_selected_chrome_profile_and_changed_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            chrome = home / ".config/google-chrome"
            profile = chrome / "Profile 2"
            profile.mkdir(parents=True)
            (chrome / "Local State").write_text(json.dumps({"profile": {"last_used": "Profile 2"}}))
            preferences = profile / "Secure Preferences"
            def save(name, url):
                preferences.write_text(json.dumps({"default_search_provider_data": {"template_url_data": {"short_name": name, "url": url}}}))
            with patch.object(browser.Path, "home", return_value=home), patch.dict(os.environ, {"XDG_CONFIG_HOME": str(home / ".config")}), \
                    patch.object(browser, "default_desktop", return_value="google-chrome.desktop"), \
                    patch.object(browser, "desktop_entry", return_value=("Google Chrome", ["google-chrome-stable", "%U"])):
                save("Unduck", "https://unduck.link?q={searchTerms}")
                first = browser.resolve()
                self.assertEqual(first["name"], "Unduck")
                self.assertEqual(first["profile"], str(profile))
                save("Custom", "https://custom.example/search?q={searchTerms}")
                second = browser.resolve()
                self.assertNotEqual(browser.describe(first)["key"], browser.describe(second)["key"])
                with patch.object(browser.subprocess, "Popen") as launch:
                    browser.open_search("!w cats & dogs")
                self.assertEqual(launch.call_args.args[0], ["omarchy", "launch", "browser", "https://custom.example/search?q=%21w+cats+%26+dogs"])

    def test_readonly_database_selects_default_not_first_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Web Data"
            with closing(sqlite3.connect(path)) as database:
                database.execute("CREATE TABLE meta (key TEXT, value TEXT)")
                database.execute("CREATE TABLE keywords (id INTEGER, short_name TEXT, url TEXT)")
                database.execute("INSERT INTO meta VALUES (?, ?)", ("Default Search Provider ID", "2"))
                database.executemany("INSERT INTO keywords VALUES (?, ?, ?)", [
                    (1, "Other", "https://other.example/?q={searchTerms}"), (2, "Selected", "https://selected.example/?q={searchTerms}")])
                database.commit()
            before = path.read_bytes()
            self.assertEqual(browser.database_engine(path)["short_name"], "Selected")
            self.assertEqual(path.read_bytes(), before)

    def test_firefox_native_search_uses_its_own_engine(self):
        with patch.object(browser, "default_desktop", return_value="firefox.desktop"), \
                patch.object(browser, "desktop_entry", return_value=("Firefox", ["firefox", "%u"])), \
                patch.object(browser.subprocess, "Popen") as launch:
            browser.open_search("cats & dogs")
        self.assertEqual(launch.call_args.args[0], ["omarchy", "launch", "browser", "--search", "cats & dogs"])

    def test_unknown_browser_never_substitutes_a_provider(self):
        with patch.object(browser, "default_desktop", return_value="custom-browser.desktop"), \
                patch.object(browser, "desktop_entry", return_value=("Custom", ["custom-browser"])), \
                patch.object(browser.subprocess, "Popen") as launch:
            self.assertFalse(browser.describe()["ready"])
            with self.assertRaises(browser.SearchSettingError):
                browser.open_search("cats")
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()

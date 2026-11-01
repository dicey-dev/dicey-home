#!/usr/bin/env python3
"""Best-effort previews from the default browser's configured search engine."""
from html.parser import HTMLParser
import json
import sys
sys.dont_write_bytecode = True  # Cache files in a plugin trigger shell hot-reload.
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import browser_search


def parse_results(data):
    rows = []
    seen = set()
    for item in ET.fromstring(data).findall("./channel/item"):
        title = " ".join((item.findtext("title") or "").split())[:180]
        url = (item.findtext("link") or "").strip()
        parsed = urllib.parse.urlsplit(url)
        if not title or parsed.scheme not in {"http", "https"} or not parsed.netloc or url in seen:
            continue
        seen.add(url)
        rows.append({"title": title, "url": url, "detail": parsed.netloc.removeprefix("www.")})
        if len(rows) == 4:
            break
    return rows


def result_url(href, base):
    url = urllib.parse.urljoin(base, href)
    parsed = urllib.parse.urlsplit(url)
    parameters = urllib.parse.parse_qs(parsed.query)
    # Google and DuckDuckGo wrap outbound result links. Only unwrap URLs from
    # the actual search host, not similarly named parameters on result sites.
    if parsed.hostname == urllib.parse.urlsplit(base).hostname:
        for key in ("uddg", "q", "url"):
            candidate = parameters.get(key, [""])[0]
            if parsed.path in {"/url", "/l/"} and candidate.startswith(("https://", "http://")):
                url = candidate
                parsed = urllib.parse.urlsplit(url)
                break
    return url if parsed.scheme in {"http", "https"} and parsed.netloc else ""


class SearchHTML(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.anchor = None
        self.heading = 0
        self.rows = []
        self.seen = set()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "h3":
            self.heading += 1
            if self.anchor:
                self.anchor.update(candidate=True, heading=True, parts=[])
        elif tag == "a":
            classes = attrs.get("class", "")
            candidate = self.heading > 0 or any(name in classes for name in ("result__a", "result-link", "heading-serpresult"))
            self.anchor = {"href": attrs.get("href", ""), "candidate": candidate, "heading": self.heading > 0, "parts": []}

    def handle_data(self, data):
        if self.anchor and (not self.anchor["heading"] or self.heading > 0):
            self.anchor["parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "h3":
            self.heading = max(0, self.heading - 1)
        elif tag == "a" and self.anchor:
            anchor, self.anchor = self.anchor, None
            url = result_url(anchor["href"], self.base)
            title = " ".join("".join(anchor["parts"]).split())[:180]
            if anchor["candidate"] and url and title and url not in self.seen and len(self.rows) < 4:
                self.seen.add(url)
                self.rows.append({"title": title, "url": url, "detail": urllib.parse.urlsplit(url).netloc.removeprefix("www.")})


def parse_html(data, base):
    parser = SearchHTML(base)
    parser.feed(data.decode("utf-8", errors="replace"))
    return parser.rows


def search(query, engine):
    url = browser_search.search_url(engine["template"], query)
    parsed = urllib.parse.urlsplit(url)
    rss = parsed.hostname in {"bing.com", "www.bing.com"} and parsed.path == "/search"
    if rss:
        parameters = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        parameters = [(key, value) for key, value in parameters if key != "format"] + [("format", "rss")]
        url = urllib.parse.urlunsplit(parsed._replace(query=urllib.parse.urlencode(parameters)))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DiceyHome/1.3)"})
    with urllib.request.urlopen(request, timeout=5) as response:
        data = response.read(512 * 1024)
        return parse_results(data) if rss else parse_html(data, response.geturl())


def query_results(query):
    result = {"query": query, "rows": [], "status": "empty", "engine": {
        "browser": "Default browser", "name": "Browser default", "mode": "unavailable", "key": "", "ready": False}}
    if len(query) < 3:
        result["engine"] = browser_search.describe()
        return result
    try:
        engine = browser_search.resolve()
        result["engine"] = browser_search.describe(engine)
        if engine["mode"] == "native":
            result["status"] = "native"
        else:
            result["rows"] = search(query, engine)
            result["status"] = "ok" if result["rows"] else "unavailable"
    except (OSError, ValueError, ET.ParseError) as error:
        if not result["engine"]["ready"]:
            result["engine"]["error"] = str(error)
        result["status"] = "unavailable"
    return result


def main():
    query = sys.argv[1].strip()[:256] if len(sys.argv) > 1 else ""
    print(json.dumps(query_results(query), ensure_ascii=False))


if __name__ == "__main__":
    main()

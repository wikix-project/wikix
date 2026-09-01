from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parents[1]
QUICK_SETUP = ROOT / "quick-setup.html"
GUIDE_URL = "/guide.html"
GITHUB_QUICK_SETUP = "https://github.com/wikix-project/wikix/blob/HEAD/docs/quick-setup.md"
SOURCE_INSTALL = "uv tool install --python 3.12 git+https://github.com/wikix-project/wikix.git"
INIT_COMMAND = "wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID"
LOGIN_COMMAND = "wikix auth login"
SYNC_COMMAND = "wikix sync"
CD_COMMAND = "cd ~/Documents/MyVault/X-Bookmarks"


class QuickSetupPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.text: list[str] = []
        self.links: list[str] = []
        self.stylesheets: list[str] = []
        self.scripts = 0
        self.ids: set[str] = set()
        self.meta: dict[str, str] = {}
        self.headings: list[tuple[int, str]] = []
        self._heading_level: int | None = None
        self._heading_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.tags.append(tag)
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(str(values["href"]))
        if tag == "meta" and values.get("content"):
            key = values.get("name") or values.get("property")
            if key:
                self.meta[str(key)] = str(values["content"])
        if tag == "script":
            self.scripts += 1
        if tag in {"h1", "h2", "h3"}:
            self._heading_level = int(tag[1])
            self._heading_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h1", "h2", "h3"} and self._heading_level is not None:
            self.headings.append((self._heading_level, " ".join(self._heading_text).strip()))
            self._heading_level = None
            self._heading_text = []

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._heading_level is not None:
            self._heading_text.append(data)


def parse_quick_setup_page() -> QuickSetupPageParser:
    parser = QuickSetupPageParser()
    parser.feed(QUICK_SETUP.read_text(encoding="utf-8"))
    return parser


def test_quick_setup_page_contains_only_the_short_path() -> None:
    parser = parse_quick_setup_page()
    content = " ".join(parser.text)

    assert QUICK_SETUP.is_file()
    assert parser.headings[0] == (1, "Quick setup")
    assert "quick-setup" in parser.ids
    for command in (SOURCE_INSTALL, INIT_COMMAND, CD_COMMAND, LOGIN_COMMAND, SYNC_COMMAND):
        assert command in content


def test_quick_setup_page_is_static_and_links_to_the_detailed_paths() -> None:
    parser = parse_quick_setup_page()
    content = " ".join(parser.text)

    assert {"header", "nav", "main", "section", "footer"}.issubset(parser.tags)
    assert parser.stylesheets == ["styles.css"]
    assert parser.scripts == 0
    assert parser.meta["description"].startswith("Run the shortest Wikix setup path")
    assert GUIDE_URL in parser.links
    assert GITHUB_QUICK_SETUP in parser.links
    assert "Before you begin" in content
    assert "Run these commands" in content
    assert "What happens next" in content


def test_quick_setup_documentation_matches_the_page_commands() -> None:
    page = " ".join(parse_quick_setup_page().text)
    quick_setup = (ROOT / "docs/quick-setup.md").read_text(encoding="utf-8")

    for command in (SOURCE_INSTALL, INIT_COMMAND, CD_COMMAND, LOGIN_COMMAND, SYNC_COMMAND):
        assert command in page
        assert command in quick_setup

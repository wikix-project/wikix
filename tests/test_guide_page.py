from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parents[1]
GUIDE = ROOT / "guide.html"
QUICK_SETUP = ROOT / "quick-setup.html"
QUICK_SETUP_URL = "/quick-setup.html"
SOURCE_INSTALL = "uv tool install --python 3.12 git+https://github.com/wikix-project/wikix.git"
INIT_COMMAND = "wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID"
LOGIN_COMMAND = "wikix auth login"
SYNC_COMMAND = "wikix sync"
QUICK_COMMAND_BLOCK = f"""{SOURCE_INSTALL}
wikix init ~/Documents/MyVault/X-Bookmarks --client-id YOUR_CLIENT_ID
cd ~/Documents/MyVault/X-Bookmarks
wikix auth login
wikix sync"""


class GuidePageParser(HTMLParser):
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
        self.footer_links: list[str] = []
        self.nav_labels: list[str] = []
        self._heading_level: int | None = None
        self._heading_text: list[str] = []
        self._in_footer = False

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
            href = str(values["href"])
            self.links.append(href)
            if self._in_footer:
                self.footer_links.append(href)
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(str(values["href"]))
        if tag == "meta" and values.get("content"):
            key = values.get("name") or values.get("property")
            if key:
                self.meta[str(key)] = str(values["content"])
        if tag == "nav" and values.get("aria-label"):
            self.nav_labels.append(str(values["aria-label"]))
        if tag == "footer":
            self._in_footer = True
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
        if tag == "footer":
            self._in_footer = False

    def handle_data(self, data: str) -> None:
        self.text.append(data)
        if self._heading_level is not None:
            self._heading_text.append(data)


def parse_guide_page() -> GuidePageParser:
    parser = GuidePageParser()
    parser.feed(GUIDE.read_text(encoding="utf-8"))
    return parser


def test_step_by_step_guide_is_static_and_semantic() -> None:
    parser = parse_guide_page()

    assert GUIDE.is_file()
    assert parser.tags.count("h1") == 1
    assert {"header", "nav", "main", "section", "footer"}.issubset(parser.tags)
    assert parser.stylesheets == ["styles.css"]
    assert parser.scripts == 0
    assert parser.meta["description"].startswith("Set up Wikix")


def test_step_by_step_guide_uses_numbered_heading_levels() -> None:
    headings = parse_guide_page().headings

    assert headings[0] == (1, "Step-by-Step Guide")
    assert (2, "1. Create your X app") in headings
    assert (2, "7. Inspect and maintain your export") in headings
    assert any(level == 3 for level, _ in headings)
    assert len({text for level, text in headings if level == 2}) >= 8


def test_step_by_step_guide_links_to_quick_setup_without_embedding_the_short_path() -> None:
    parser = parse_guide_page()
    content = " ".join(parser.text)
    html = GUIDE.read_text(encoding="utf-8")

    assert QUICK_SETUP_URL in parser.links
    assert "Quick setup" in content
    assert "quick-setup" not in parser.ids
    assert QUICK_COMMAND_BLOCK not in html


def test_getting_started_preserves_platform_chooser_and_links_quick_setup() -> None:
    content = (ROOT / "docs/getting-started.md").read_text(encoding="utf-8")

    assert QUICK_SETUP.is_file()
    assert "[Quick setup](quick-setup.md)" in content
    assert "[macOS](getting-started-macos.md)" in content
    assert "[Windows](getting-started-windows.md)" in content
    assert "[Linux](getting-started-linux.md)" in content


def test_guide_commands_use_the_current_source_contract() -> None:
    website = " ".join(parse_guide_page().text)

    for command in (SOURCE_INSTALL, INIT_COMMAND, LOGIN_COMMAND, SYNC_COMMAND):
        assert command in website

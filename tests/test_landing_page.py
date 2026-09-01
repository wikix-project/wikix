import json
import tomllib
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).parents[1]
GUIDE_URL = "/guide.html"
QUICK_SETUP_URL = "/quick-setup.html"
GETTING_STARTED = "https://github.com/wikix-project/wikix/blob/HEAD/docs/getting-started.md"
PRIVACY = "https://github.com/wikix-project/wikix/blob/HEAD/PRIVACY.md"
SECURITY = "https://github.com/wikix-project/wikix/blob/HEAD/SECURITY.md"
CONTRIBUTING = "https://github.com/wikix-project/wikix/blob/HEAD/CONTRIBUTING.md"
LICENSE = "https://github.com/wikix-project/wikix/blob/HEAD/LICENSE"
GITHUB = "https://github.com/wikix-project/wikix"
SOURCE_INSTALL_UV = "uv tool install --python 3.12 git+https://github.com/wikix-project/wikix.git"
GUIDE_ROOT = "https://github.com/wikix-project/wikix/blob/HEAD/docs"
GUIDE_LINKS = {
    "macOS": f"{GUIDE_ROOT}/getting-started-macos.md",
    "Windows": f"{GUIDE_ROOT}/getting-started-windows.md",
    "Linux": f"{GUIDE_ROOT}/getting-started-linux.md",
}


class LandingPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.links: list[str] = []
        self.stylesheets: list[str] = []
        self.scripts = 0
        self.text: list[str] = []
        self.ids: set[str] = set()
        self.meta: dict[str, str] = {}
        self.links_by_section: dict[str, list[str]] = {}
        self.footer_links: list[str] = []
        self.nav_labels: list[str] = []
        self.primary_nav_links: list[str] = []
        self._current_section: str | None = None
        self._in_footer = False
        self._in_primary_nav = False

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.tags.append(tag)
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "section":
            self._current_section = values.get("id")
        if tag == "footer":
            self._in_footer = True
        if tag == "nav" and values.get("aria-label"):
            label = str(values["aria-label"])
            self.nav_labels.append(label)
            self._in_primary_nav = label == "Primary navigation"
        if tag == "a" and values.get("href"):
            href = str(values["href"])
            self.links.append(href)
            if self._in_primary_nav:
                self.primary_nav_links.append(href)
            if self._current_section:
                self.links_by_section.setdefault(self._current_section, []).append(href)
            if self._in_footer:
                self.footer_links.append(href)
        if tag == "link" and values.get("rel") == "stylesheet" and values.get("href"):
            self.stylesheets.append(str(values["href"]))
        if tag == "meta" and values.get("content"):
            key = values.get("name") or values.get("property")
            if key:
                self.meta[str(key)] = str(values["content"])
        if tag == "script":
            self.scripts += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            self._current_section = None
        if tag == "footer":
            self._in_footer = False
        if tag == "nav":
            self._in_primary_nav = False

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def parse_landing_page() -> LandingPageParser:
    parser = LandingPageParser()
    parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    return parser


def test_landing_page_links_to_each_operating_system_guide() -> None:
    parser = parse_landing_page()

    assert "#get-started" in parser.links
    for link in GUIDE_LINKS.values():
        assert parser.links.count(link) == 1
    assert parser.scripts == 0


def test_landing_page_is_user_first_and_literal() -> None:
    parser = parse_landing_page()
    content = " ".join(parser.text)

    assert parser.tags.count("h1") == 1
    assert {"header", "nav", "main", "section", "footer"}.issubset(parser.tags)
    assert "Export X bookmarks to Markdown and JSONL." in content
    assert "files you own" not in content
    assert "Stable release" in content
    assert "Wikix 1.0" in content
    assert "install from source" in content
    assert SOURCE_INSTALL_UV in content
    assert GUIDE_URL in parser.links
    assert QUICK_SETUP_URL in parser.links
    assert "/guide.html#quick-setup" not in parser.links


def test_landing_page_leads_with_exported_note_and_first_action() -> None:
    parser = parse_landing_page()
    content = " ".join(parser.text)
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert parser.tags.count("h1") == 1
    assert "Export X bookmarks to Markdown and JSONL." in content
    assert "one Obsidian-ready Markdown file per current bookmark" in content
    assert "Wikix 1.0 · Python 3.12+" in content
    assert "requires your own X developer app and API credits" in content
    assert "bookmarks/1900000000000000000.md" in content
    assert "## Post" in content
    assert "```text" in content
    assert "## Source" in content
    assert "## Personal notes" in content
    assert "Useful idea to revisit when planning local search." in content
    assert "Synthetic shortened example" in content
    assert html.index('class="hero-copy"') < html.index('class="note-specimen"')
    assert GUIDE_URL in parser.links
    assert QUICK_SETUP_URL in parser.links
    assert "/guide.html#quick-setup" not in parser.links


def test_landing_page_uses_three_evidence_backed_value_pillars() -> None:
    content = " ".join(parse_landing_page().text)

    assert "Markdown for ordinary tools." in content
    assert "JSONL for private workflows." in content
    assert "Careful updates." in content
    assert "Personal annotations survive normal syncs" in content


def test_landing_page_explains_workflow_and_material_requirements() -> None:
    parser = parse_landing_page()
    content = " ".join(parser.text)

    for expected in (
        "Official X API",
        "Wikix on your computer",
        "Markdown + JSONL",
        "1. Connect",
        "2. Authorize",
        "3. Sync",
        "Python 3.12 or newer",
        "approved X developer app and API credits",
        "Every sync scans the complete current bookmark collection",
        "may incur X API charges",
    ):
        assert expected in content
    assert GUIDE_URL in parser.links_by_section["requirements"]


def test_landing_page_combines_privacy_and_reliability_as_three_trust_statements() -> None:
    parser = parse_landing_page()
    content = " ".join(parser.text)

    assert parser.tags.count("dl") == 1
    assert parser.tags.count("dt") == 3
    assert parser.tags.count("dd") == 3
    for expected in (
        "No Wikix server or telemetry.",
        "Credentials stay local.",
        "The last good export is protected.",
        "operating-system credential store",
        "Managed-content conflicts are reported instead of overwritten.",
    ):
        assert expected in content


def test_landing_page_ends_with_source_install_action() -> None:
    parser = parse_landing_page()
    content = " ".join(parser.text)

    assert "If Wikix fits your setup, create your first local collection." in content
    assert SOURCE_INSTALL_UV in content
    assert GUIDE_URL in parser.links_by_section["start"]
    assert GITHUB in parser.links_by_section["start"]


def test_primary_navigation_stays_compact() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    header = html.split('<header class="site-header">', 1)[1].split("</header>", 1)[0]

    assert header.count("<a ") == 4
    assert 'href="#how-it-works"' in header
    assert 'href="#requirements"' in header
    assert f'href="{GITHUB}"' in header
    assert 'href="#privacy"' not in header


def test_footer_links_to_project_resources_and_license() -> None:
    parser = parse_landing_page()

    assert "Footer navigation" in parser.nav_labels
    assert parser.footer_links == [
        GUIDE_URL,
        QUICK_SETUP_URL,
        GETTING_STARTED,
        PRIVACY,
        SECURITY,
        CONTRIBUTING,
        GITHUB,
        LICENSE,
    ]


def test_mobile_requirements_have_no_orphan_punctuation() -> None:
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    assert "</strong>.</li>" not in html


def test_landing_page_is_static_accessible_and_links_to_user_resources() -> None:
    parser = parse_landing_page()

    assert parser.stylesheets == ["styles.css"]
    assert parser.scripts == 0
    assert {"value", "how-it-works", "requirements", "privacy", "start"}.issubset(parser.ids)
    assert "#main-content" in parser.links
    assert "https://github.com/wikix-project/wikix" in parser.links
    assert GUIDE_URL in parser.links
    assert all(link.startswith(("https://", "#", "/")) for link in parser.links)
    assert parser.meta["description"].startswith("Export X bookmarks")


def test_landing_page_has_site_specific_social_metadata() -> None:
    parser = parse_landing_page()

    assert parser.meta["og:title"] == "Wikix — Export X bookmarks to Markdown and JSONL"
    assert parser.meta["og:description"].startswith("A local-first Python CLI")
    assert parser.meta["og:type"] == "website"
    assert "og:image" not in parser.meta
    assert parser.meta["twitter:card"] == "summary"


def test_install_docs_and_project_urls_use_current_source_repository() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    combined_docs = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "docs/getting-started.md",
            "docs/getting-started-macos.md",
            "docs/getting-started-windows.md",
            "docs/getting-started-linux.md",
            "CONTRIBUTING.md",
        )
    )

    assert project["project"]["urls"] == {
        "Homepage": "https://github.com/wikix-project/wikix",
        "Issues": "https://github.com/wikix-project/wikix/issues",
    }
    assert "pipx install wikix" not in combined_docs
    assert "uv tool install wikix" not in combined_docs
    assert "github.com/atharvafulay/wikix" not in combined_docs
    assert SOURCE_INSTALL_UV in combined_docs


def test_local_stylesheet_exists() -> None:
    parser = parse_landing_page()

    for stylesheet in parser.stylesheets:
        assert (ROOT / stylesheet).is_file()


def test_site_identifies_the_stable_1_0_release() -> None:
    for page in ("index.html", "guide.html", "quick-setup.html"):
        html = (ROOT / page).read_text(encoding="utf-8")

        assert 'class="wordmark"' in html
        assert "wikix <span>1.0</span>" in html
        assert "alpha" not in html.casefold()


def test_mobile_header_keeps_a_contextual_internal_link_on_each_page() -> None:
    expected_first_links = {
        "index.html": "#how-it-works",
        "guide.html": "/quick-setup.html",
        "quick-setup.html": "/",
    }

    for page, expected_first_link in expected_first_links.items():
        parser = LandingPageParser()
        parser.feed((ROOT / page).read_text(encoding="utf-8"))

        assert parser.primary_nav_links[0] == expected_first_link


def test_styles_encode_compact_note_led_responsive_layout() -> None:
    stylesheet = (ROOT / "styles.css").read_text(encoding="utf-8")
    mobile_styles = stylesheet.split("@media (max-width: 760px) {", maxsplit=1)[1]

    for selector in (
        ".hero-copy",
        ".note-specimen",
        ".value-list",
        ".trust-list",
        ".start-section",
        ".install-panel",
        ".guide-command code",
    ):
        assert selector in stylesheet
    assert "grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);" in stylesheet
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in stylesheet
    assert ".site-header nav a:not(:first-child)" in mobile_styles
    assert ".site-header nav a:not(:last-child)" not in mobile_styles
    assert "display: none;" in mobile_styles
    assert "white-space: pre-wrap;" in mobile_styles
    assert "white-space: inherit;" in stylesheet
    assert "overflow-wrap: anywhere;" in mobile_styles


def test_vercel_configuration_sets_static_security_headers() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    headers = {item["key"]: item["value"] for rule in config["headers"] for item in rule["headers"]}

    assert config["cleanUrls"] is True
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in headers["Content-Security-Policy"]


def test_vercel_upload_is_limited_to_landing_page_files() -> None:
    patterns = [
        line.strip()
        for line in (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert patterns == [
        "/*",
        "!index.html",
        "!guide.html",
        "!quick-setup.html",
        "!styles.css",
        "!vercel.json",
        "!assets",
    ]


def test_landing_page_assets_are_local_and_deployable() -> None:
    stylesheet = (ROOT / "styles.css").read_text(encoding="utf-8")

    for asset in (
        "assets/fonts/ibm-plex-sans-latin-wght-normal.woff2",
        "assets/fonts/ibm-plex-mono-latin-400-normal.woff2",
        "assets/fonts/IBM-Plex-Sans-LICENSE.txt",
        "assets/fonts/IBM-Plex-Mono-LICENSE.txt",
    ):
        assert (ROOT / asset).is_file()

    assert "ibm-plex-sans-latin-wght-normal.woff2" in stylesheet
    assert "ibm-plex-mono-latin-400-normal.woff2" in stylesheet
    assert "scroll-behavior: smooth" not in stylesheet

    patterns = [
        line.strip()
        for line in (ROOT / ".vercelignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert patterns == [
        "/*",
        "!index.html",
        "!guide.html",
        "!quick-setup.html",
        "!styles.css",
        "!vercel.json",
        "!assets",
    ]

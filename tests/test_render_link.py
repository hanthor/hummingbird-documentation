"""Build a minimal Hugo site (no Docsy) to verify render-link hook behaviour."""

import html.parser
import pathlib
import shutil
import subprocess
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]


class LinkParser(html.parser.HTMLParser):
    """Collect every <a> element as (href, target) pairs."""

    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            d = dict(attrs)
            self.links.append((d.get("href", ""), d.get("target")))


def parse_links(html_text: str) -> list[tuple[str, str | None]]:
    parser = LinkParser()
    parser.feed(html_text)
    return parser.links


class RenderLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="render-link-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.site = pathlib.Path(cls.directory.name)

        # Minimal hugo.toml — no Docsy, no network
        (cls.site / "hugo.toml").write_text(
            'baseURL = "https://docs.example.com/"\n'
            'title = "Render link tests"\n'
            'disableKinds = ["taxonomy", "term", "RSS", "sitemap"]\n'
        )

        # Minimal layouts so Hugo can render pages without a theme
        layouts = cls.site / "layouts"
        markup = layouts / "_default" / "_markup"
        markup.mkdir(parents=True)
        shutil.copy(
            REPO / "layouts/_default/_markup/render-link.html",
            markup / "render-link.html",
        )
        (layouts / "_default" / "single.html").write_text(
            "{{ .Content }}\n"
        )
        (layouts / "_default" / "list.html").write_text(
            "{{ .Content }}\n"
        )

        # Content
        pages = {
            "docs/_index.md": (
                "---\ntitle: Docs\n---\n"
            ),
            "docs/talk/_index.md": (
                "---\ntitle: Talk\n---\n"
                # static .html link — must NOT be rewritten to /docs/talk/slides/
                "[Slides](https://docs.example.com/docs/talk/slides.html)\n"
                # relative .md link — must resolve to /docs/talk/other/
                "[Notes](other.md)\n"
                # absolute own-host .md link — must resolve to /docs/talk/other/
                "[Public notes](https://hummingbird-project.io/docs/talk/other.md)\n"
                # external link — must keep target=_blank
                "[External](https://example.org/page.html)\n"
            ),
            "docs/talk/slides.md": (
                "---\ntitle: Slides\n---\nSlide content.\n"
            ),
            "docs/talk/other.md": (
                "---\ntitle: Other\n---\nOther content.\n"
            ),
        }
        for name, content in pages.items():
            path = cls.site / "content" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

        # Static file that must not be rewritten
        static_html = cls.site / "static" / "docs" / "talk"
        static_html.mkdir(parents=True)
        (static_html / "slides.html").write_text("<html><body>Marp export</body></html>\n")

        result = subprocess.run(
            ["hugo", "--source", str(cls.site), "--destination", str(cls.site / "public")],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        cls.public = cls.site / "public"

    def _links_on(self, path: str) -> list[tuple[str, str | None]]:
        return parse_links((self.public / path / "index.html").read_text())

    def test_static_html_link_not_rewritten(self):
        """A link to a .html static file must be left exactly as authored."""
        links = self._links_on("docs/talk")
        hrefs = [href for href, _ in links]
        with self.subTest("contains original .html href"):
            self.assertIn("https://docs.example.com/docs/talk/slides.html", hrefs)
        with self.subTest("does not rewrite to hugo page"):
            self.assertNotIn("/docs/talk/slides/", hrefs)

    def test_relative_md_link_resolved(self):
        """A relative .md link must be resolved to the Hugo page URL."""
        links = self._links_on("docs/talk")
        hrefs = [href for href, _ in links]
        with self.subTest("other.md resolves to /docs/talk/other/"):
            self.assertIn("/docs/talk/other/", hrefs)

    def test_absolute_own_host_md_link_resolved(self):
        """An absolute hummingbird-project.io .md link must resolve to the local page URL."""
        links = self._links_on("docs/talk")
        hrefs = [href for href, _ in links]
        with self.subTest("absolute .md link resolves to /docs/talk/other/"):
            self.assertIn("/docs/talk/other/", hrefs)

    def test_external_link_has_target_blank(self):
        """An external link to a different host must carry target=_blank."""
        links = self._links_on("docs/talk")
        for href, target in links:
            if href == "https://example.org/page.html":
                with self.subTest("target is _blank"):
                    self.assertEqual(target, "_blank")
                return
        self.fail("External link not found in rendered output")

    def test_internal_links_no_target_blank(self):
        """Resolved internal links must not carry target=_blank."""
        links = self._links_on("docs/talk")
        for href, target in links:
            if href in ("/docs/talk/other/", "https://docs.example.com/docs/talk/slides.html"):
                with self.subTest(href=href):
                    self.assertNotEqual(target, "_blank")

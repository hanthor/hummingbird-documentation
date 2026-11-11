"""Build a small Docsy site to check Mermaid renderer inclusion."""

import html.parser
import pathlib
import shutil
import subprocess
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
DIAGRAM = "\n```mermaid\nflowchart LR\n    A --> B\n```\n"


class MermaidParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.diagrams = 0

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and "mermaid" in dict(attrs).get("class", "").split():
            self.diagrams += 1


class MermaidPrintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="mermaid-print-")
        cls.addClassCleanup(cls.directory.cleanup)
        cls.site = pathlib.Path(cls.directory.name)
        shutil.copyfile(REPO / "go.mod", cls.site / "go.mod")
        (cls.site / "hugo.toml").write_text(
            f'''baseURL = "https://docs.example.com/"
title = "Mermaid print tests"
theme = ["github.com/google/docsy/theme"]
disableKinds = ["taxonomy", "term", "RSS", "sitemap"]

[security.http]
# match config.yaml: route resources.GetRemote through HTTP(S)_PROXY so the
# mermaid CDN fetch works on the proxied runner clusters
proxyFromEnvironment = true

[outputs]
home = ["HTML"]
section = ["HTML", "print"]
page = ["HTML"]

[module]
[[module.mounts]]
source = "content"
target = "content"
[[module.mounts]]
source = "{REPO / "layouts/docs/list.print.html"}"
target = "layouts/docs/list.print.html"
[[module.mounts]]
source = "{REPO / "node_modules/bootstrap"}"
target = "assets/vendor/bootstrap"
[[module.mounts]]
source = "{REPO / "node_modules/@fortawesome/fontawesome-free"}"
target = "assets/vendor/Font-Awesome"
''',
        )
        pages = {
            "docs/_index.md": "",
            "docs/child-only/_index.md": "",
            "docs/child-only/first.md": DIAGRAM,
            "docs/child-only/second.md": DIAGRAM,
            "docs/nested/_index.md": "",
            "docs/nested/subsection/_index.md": "",
            "docs/nested/subsection/child.md": DIAGRAM,
            "docs/parent-only/_index.md": DIAGRAM,
            "docs/parent-only/child.md": "Plain child content.\n",
            "docs/parent-and-child/_index.md": DIAGRAM,
            "docs/parent-and-child/child.md": DIAGRAM,
            "docs/plain/_index.md": "Plain section content.\n",
            "docs/plain/child.md": "Plain child content.\n",
            "docs/excluded/_index.md": "",
            "docs/excluded/child.md": DIAGRAM,
            "docs/excluded/subsection/_index.md": DIAGRAM,
            "docs/excluded/subsection/child.md": DIAGRAM,
            "docs/literal/_index.md": '\n```html\n<pre class="mermaid">\n```\n',
        }
        for name, content in pages.items():
            path = cls.site / "content" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            excluded = name in (
                "docs/excluded/child.md",
                "docs/excluded/subsection/_index.md",
            )
            frontmatter = f'+++\ntitle = "{name}"\n'
            if excluded:
                frontmatter += "no_print = true\n"
            path.write_text(frontmatter + "+++\n" + content)

        for environment in ("development", "production"):
            result = subprocess.run(
                [
                    "hugo",
                    "--source",
                    str(cls.site),
                    "--destination",
                    str(cls.site / environment),
                    "--environment",
                    environment,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)

    def assert_mermaid(self, environment, path, diagrams):
        content = (self.site / environment / path / "index.html").read_text()
        parser = MermaidParser()
        parser.feed(content)
        self.assertEqual(parser.diagrams, diagrams)
        self.assertEqual(content.count("import mermaid from"), int(diagrams > 0))

    def test_print_renderer_inclusion(self):
        cases = {
            "child-only": 2,
            "nested": 1,
            "nested/subsection": 1,
            "parent-only": 1,
            "parent-and-child": 2,
            "plain": 0,
            "excluded": 0,
            "literal": 0,
        }
        for environment in ("development", "production"):
            for section, diagrams in cases.items():
                with self.subTest(environment=environment, section=section):
                    self.assert_mermaid(environment, f"_print/docs/{section}", diagrams)

    def test_normal_renderer_inclusion(self):
        cases = {
            "child-only": 0,
            "child-only/first": 1,
            "child-only/second": 1,
            "nested": 0,
            "nested/subsection/child": 1,
            "parent-only": 1,
            "parent-only/child": 0,
            "parent-and-child": 1,
            "parent-and-child/child": 1,
            "plain": 0,
            "excluded": 0,
            "excluded/child": 1,
            "literal": 0,
        }
        for environment in ("development", "production"):
            for page, diagrams in cases.items():
                with self.subTest(environment=environment, page=page):
                    self.assert_mermaid(environment, f"docs/{page}", diagrams)

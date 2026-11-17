"""Check the redirect-aware static server used by the afdocs checks."""

import pathlib
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from functools import partial

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))

import serve_redirects  # noqa: E402

REDIRECTS = """\
# comment line
/l/guide/*  /docs/section/guide/:splat  301
/l/home/*  /docs/ 301
/old-page  /docs/new-page/ 301
"""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Turn redirects into HTTPError so tests can inspect them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ParseRedirectsTests(unittest.TestCase):
    def test_parses_splat_exact_and_comment_rules(self):
        rules = serve_redirects.parse_redirects(REDIRECTS)
        self.assertEqual(
            rules,
            [
                ("/l/guide", "/docs/section/guide/:splat", 301, True),
                ("/l/home", "/docs/", 301, True),
                ("/old-page", "/docs/new-page/", 301, False),
            ],
        )

    def test_defaults_to_301_without_status_code(self):
        rules = serve_redirects.parse_redirects("/a  /b")
        self.assertEqual(rules, [("/a", "/b", 301, False)])


class MatchRedirectTests(unittest.TestCase):
    def setUp(self):
        self.rules = serve_redirects.parse_redirects(REDIRECTS)

    def test_splat_rule_matches_bare_prefix_and_children(self):
        for path in ("/l/guide", "/l/guide/", "/l/guide/"):
            with self.subTest(path=path):
                self.assertEqual(
                    serve_redirects.match_redirect(path, self.rules),
                    ("/docs/section/guide/", 301),
                )
        self.assertEqual(
            serve_redirects.match_redirect("/l/guide/index.md", self.rules),
            ("/docs/section/guide/index.md", 301),
        )

    def test_exact_rule_matches_only_the_exact_path(self):
        self.assertEqual(
            serve_redirects.match_redirect("/old-page", self.rules),
            ("/docs/new-page/", 301),
        )
        self.assertIsNone(serve_redirects.match_redirect("/old-page/extra", self.rules))

    def test_unmatched_paths_return_none(self):
        for path in ("/docs/", "/l/guide.md", "/l/other", "/"):
            with self.subTest(path=path):
                self.assertIsNone(serve_redirects.match_redirect(path, self.rules))


class ServeRedirectsTests(unittest.TestCase):
    """Serve a scratch build directory over HTTP and exercise the handler."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="serve-redirects-")
        cls.addClassCleanup(cls.directory.cleanup)
        root = pathlib.Path(cls.directory.name)
        (root / "_redirects").write_text(REDIRECTS)
        (root / "docs" / "section" / "guide").mkdir(parents=True)
        (root / "docs" / "section" / "guide" / "index.html").write_text(
            "<html><body>Guide page</body></html>\n"
        )
        (root / "docs" / "section" / "guide" / "index.md").write_text("# Guide\n")
        server = serve_redirects.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(serve_redirects.RedirectAwareHandler, directory=str(root)),
        )
        server.redirect_rules = serve_redirects.parse_redirects(REDIRECTS)
        cls.server = server
        threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.origin = f"http://127.0.0.1:{server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _fetch(self, path):
        request = urllib.request.Request(self.origin + path, method="GET")
        try:
            return urllib.request.urlopen(request), None
        except urllib.error.HTTPError as error:
            return None, error

    def test_alias_answers_301_with_mapped_location(self):
        opener = urllib.request.build_opener(_NoRedirect)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            opener.open(f"{self.origin}/l/guide")
        self.assertEqual(caught.exception.code, 301)
        self.assertEqual(caught.exception.headers["Location"], "/docs/section/guide/")

    def test_alias_redirects_to_the_target_page(self):
        with self._fetch("/l/guide")[0] as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.url, f"{self.origin}/docs/section/guide/")
            self.assertIn("Guide page", response.read().decode())

    def test_markdown_files_serve_as_text_markdown(self):
        with self._fetch("/docs/section/guide/index.md")[0] as response:
            self.assertEqual(response.status, 200)
            self.assertIn("text/markdown", response.headers["content-type"])

    def test_unknown_path_returns_404(self):
        _, error = self._fetch("/docs/missing/")
        self.assertEqual(error.code, 404)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Serve a Hugo build output directory with its _redirects rules applied.

The production CDN serves the _redirects file Hugo generates, so /l/
stable-link aliases answer with redirects to real pages. Hugo's dev
server neither serves those rules nor emits alias pages (disableAliases
keeps builds free of them), so this server stands in for the CDN when
the agent-friendly docs checks run against a static build.
"""

import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RULE = re.compile(r"^(\S+)\s+(\S+)(?:\s+(\d+))?$")


def parse_redirects(text):
    """Parse _redirects content into (source, target, code, splat) rules."""
    rules = []
    for line in text.splitlines():
        line = line.strip()
        match = RULE.match(line) if line and not line.startswith("#") else None
        if match:
            source, target, code = match.groups()
            splat = source.endswith("/*")
            rules.append((source[:-2] if splat else source, target, int(code or 301), splat))
    return rules


def match_redirect(path, rules):
    """Return (location, status code) for a request path, or None."""
    for source, target, code, splat in rules:
        if splat:
            if path == source or path.startswith(source + "/"):
                remainder = path[len(source):].lstrip("/")
                return target.replace(":splat", remainder), code
        elif path == source:
            return target, code
    return None


class RedirectAwareHandler(SimpleHTTPRequestHandler):
    # Markdown pages must serve as text/markdown for the docs checks.
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".md": "text/markdown"}

    def _maybe_redirect(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        match = match_redirect(path, self.server.redirect_rules)
        if match is None:
            return False
        location, code = match
        self.send_response(code)
        self.send_header("Location", location)
        self.end_headers()
        return True

    def do_GET(self):
        if not self._maybe_redirect():
            super().do_GET()

    def do_HEAD(self):
        if not self._maybe_redirect():
            super().do_HEAD()


def main():
    if len(sys.argv) < 2:
        sys.exit(f"usage: {sys.argv[0]} DIRECTORY [PORT]")
    directory = Path(sys.argv[1])
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 1313
    rules = parse_redirects((directory / "_redirects").read_text(encoding="utf-8"))
    handler = partial(RedirectAwareHandler, directory=str(directory))
    server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    server.redirect_rules = rules
    print(f"serving {directory} at http://0.0.0.0:{port} with {len(rules)} redirect rules", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

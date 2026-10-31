"""Remote and document-derived URLs must not reach innerHTML templates unescaped."""
import re
from pathlib import Path

from django.test import SimpleTestCase

JS = Path(__file__).resolve().parents[1] / "static" / "js"
RAW_LINK = re.compile(r'(?:href|src)="\$\{(?:item\.(?:source_url|link|photo_url)|proof\.source_url|link)\}"')


class UntrustedLinkRenderingTests(SimpleTestCase):
    def test_link_sinks_go_through_safe_helpers(self):
        for name, safe_calls in {"risk.js": 2, "relationship.js": 1, "investments.js": 2, "career.js": 3, "mobility.js": 1}.items():
            with self.subTest(name):
                source = (JS / name).read_text(encoding="utf-8")
                self.assertIsNone(RAW_LINK.search(source))
                self.assertEqual(source.count("Alfred.safeHref("), safe_calls)
        self.assertIn('src="${Alfred.escapeHtml(item.photo_url)}"', (JS / "mobility.js").read_text(encoding="utf-8"))

    def test_helper_is_exported_and_allows_only_web_schemes(self):
        source = (JS / "app.js").read_text(encoding="utf-8")
        self.assertRegex(source, r"\n    safeHref,\n")
        self.assertIn('url.protocol === "https:" || url.protocol === "http:"', source)
        self.assertIn("return escapeHtml(url.href);", source)

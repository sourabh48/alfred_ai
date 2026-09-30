import ipaddress
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from alfred_ai.services.public_http import PublicHTTPError, normalized_link, request


class TravelHTTPTests(SimpleTestCase):
    def setUp(self):
        self.dns = patch("alfred_ai.services.public_http._resolve_host_ips", return_value=[ipaddress.ip_address("93.184.215.14")]).start()
        self.pool_class = patch("alfred_ai.services.public_http.urllib3.HTTPSConnectionPool").start()
        self.addCleanup(patch.stopall)
        self.pool = self.pool_class.return_value
        self.response = Mock(status=200, headers={"Content-Type":"application/json"})
        self.response.read.side_effect = [b'{"ok":true}', b""]
        self.pool.urlopen.return_value = self.response

    def test_public_connection_pins_ip_but_verifies_original_tls_host(self):
        result = request("GET", "https://example.org/data", params={"q":"Coorg & hills"})
        self.assertEqual(result.json(), {"ok":True})
        self.assertEqual(self.pool_class.call_args.args[0], "93.184.215.14")
        self.assertEqual(self.pool_class.call_args.kwargs["assert_hostname"], "example.org")
        self.assertEqual(self.pool_class.call_args.kwargs["server_hostname"], "example.org")
        self.assertEqual(self.dns.call_count, 1)
        self.assertFalse(self.pool.urlopen.call_args.kwargs["redirect"])
        self.assertFalse(self.pool.urlopen.call_args.kwargs["preload_content"])
        self.assertIn("q=Coorg+%26+hills", self.pool.urlopen.call_args.args[1])
        self.response.close.assert_called_once()

    def test_unsafe_urls_are_rejected_before_connecting(self):
        for url in ["http://example.org", "https://localhost/", "https://localhost./", "https://a.local/",
                    "https://127.0.0.1/", "https://169.254.169.254/", "https://[::1]/", "https://example.org:8000/",
                    "https://user:secret@example.org/", "https://example.org\\@localhost/", "javascript:alert(1)",
                    "data:text/html,unsafe", "https://example.org/\r\nCookie:x"]:
            with self.subTest(url=url), self.assertRaises(PublicHTTPError):
                request("GET", url)
        self.pool_class.assert_not_called()

    def test_any_private_dns_record_blocks_host(self):
        for address in ["127.0.0.1", "10.0.0.2", "169.254.169.254", "::1", "::ffff:127.0.0.1"]:
            self.dns.return_value = [ipaddress.ip_address("93.184.215.14"), ipaddress.ip_address(address)]
            with self.assertRaisesRegex(PublicHTTPError, "unsafe_url"):
                request("GET", "https://attacker.example/")
        self.pool_class.assert_not_called()

    def test_redirect_never_follows_private_target_or_forwards_key(self):
        self.response.status = 302
        self.response.headers["Location"] = "http://169.254.169.254/latest/meta-data"
        with self.assertRaisesRegex(PublicHTTPError, "redirect_blocked"):
            request("POST", "https://example.org/", headers={"Authorization":"secret"}, json_body={"q":"travel"})
        self.assertEqual(self.pool.urlopen.call_count, 1)
        self.response.read.assert_not_called()

    def test_size_type_and_compression_limits(self):
        for headers, code in [({"Content-Type":"text/html"}, "unexpected_content_type"),
                              ({"Content-Type":"application/json", "Content-Encoding":"gzip"}, "unexpected_content_encoding"),
                              ({"Content-Type":"application/json", "Content-Length":"9000000"}, "response_too_large")]:
            self.response.headers = headers
            with self.assertRaisesRegex(PublicHTTPError, code):
                request("GET", "https://example.org/")
        self.response.headers = {"Content-Type":"application/json"}
        self.response.read.side_effect = [b"123456"]
        with self.assertRaisesRegex(PublicHTTPError, "response_too_large"):
            request("GET", "https://example.org/", max_bytes=5)

    def test_errors_do_not_expose_keys(self):
        import urllib3
        self.pool.urlopen.side_effect = urllib3.exceptions.ReadTimeoutError(None, "/?api_key=secret", "secret")
        with self.assertRaisesRegex(PublicHTTPError, "^timeout$"):
            request("GET", "https://example.org/", params={"api_key":"secret"})

    def test_display_links_reject_unsafe_schemes_without_network(self):
        self.assertEqual(normalized_link("data:hello"), "")
        self.assertEqual(normalized_link("https://example.org/page#entry"), "https://example.org/page#entry")
        self.dns.assert_not_called()

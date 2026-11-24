"""The standard-library transport against a small local HTTP server (no internet)."""

import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from helpers import Checks

from mygeocode import ApiError, Client, NetworkError, RequestTimeoutError
from mygeocode._core import HttpRequest, urllib_transport


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # keep the test output quiet
        pass

    def _reply(self, status, body, headers=None):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def _echo(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8") if length else None
        if self.path.startswith("/v1/slow"):
            time.sleep(1.5)
        if self.path.startswith("/v1/limited"):
            self._reply(429, {"status": "error", "error": {"code": "rate_limited", "message": "Slow down."}}, {"Retry-After": "1"})
            return
        self._reply(
            200,
            {
                "status": "ok",
                "method": self.command,
                "path": self.path,
                "ua": self.headers.get("User-Agent"),
                "key": self.headers.get("X-API-Key"),
                "content_type": self.headers.get("Content-Type"),
                "body": body,
                "query": None,
                "results": [],
            },
            {"X-Request-Id": "local-1", "X-Quota-Limit": "2500"},
        )

    def do_GET(self):
        self._echo()

    def do_POST(self):
        self._echo()


class TransportTest(Checks, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.server.daemon_threads = True  # type: ignore[attr-defined]
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.daemon = True
        cls.thread.start()
        cls.base = "http://127.0.0.1:{}/v1".format(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(5)

    def test_get_with_headers(self):
        response = urllib_transport(HttpRequest("GET", self.base + "/x?a=1", {"X-API-Key": "k1", "User-Agent": "ua-test"}, None, 5.0))
        body = json.loads(response.body.decode("utf-8"))
        self.assertEqual(response.status, 200)
        self.assertEqual((body["method"], body["path"], body["key"], body["ua"]), ("GET", "/v1/x?a=1", "k1", "ua-test"))
        self.assertEqual(response.headers["x-request-id"], "local-1")

    def test_post_body(self):
        response = urllib_transport(HttpRequest("POST", self.base + "/x", {"Content-Type": "application/json"}, b'{"a":1}', 5.0))
        body = json.loads(response.body.decode("utf-8"))
        self.assertEqual((body["method"], body["body"], body["content_type"]), ("POST", '{"a":1}', "application/json"))

    def test_an_error_status_is_an_answer_not_an_exception(self):
        response = urllib_transport(HttpRequest("GET", self.base + "/limited", {}, None, 5.0))
        self.assertEqual(response.status, 429)
        self.assertEqual(response.headers["Retry-After"], "1")

    def test_timeout(self):
        with self.assertRaises(RequestTimeoutError):
            urllib_transport(HttpRequest("GET", self.base + "/slow", {}, None, 0.3))

    def test_connection_refused(self):
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        with self.assertRaises(NetworkError):
            urllib_transport(HttpRequest("GET", "http://127.0.0.1:{}/v1/x".format(port), {}, None, 2.0))

    def test_client_end_to_end(self):
        client = Client(key="k2", base_url=self.base)
        result = client.forward("Brandenburg Gate, Berlin")
        self.assertEqual(result.raw["method"], "GET")
        self.assertEqual(result.raw["key"], "k2")
        self.assertTrue(result.raw["ua"].startswith("mygeocode-python/"))
        self.assertIn("q=Brandenburg+Gate%2C+Berlin", result.raw["path"])
        self.assertEqual(result.meta.request_id, "local-1")

    def test_client_post_end_to_end(self):
        result = Client(base_url=self.base).forward_batch(["Brandenburg Gate, Berlin"])
        self.assertEqual(result.raw["method"], "POST")
        self.assertEqual(json.loads(result.raw["body"]), {"queries": ["Brandenburg Gate, Berlin"]})
        self.assertEqual(result.raw["path"], "/v1/forward?lang=en")

    def test_client_api_error_and_timeout(self):
        with self.assertRaises(ApiError) as caught:
            Client(base_url=self.base.replace("/v1", "/v1/limited"), max_retries=0).forward("x")
        self.assertEqual(caught.exception.code, "rate_limited")
        with self.assertRaises(RequestTimeoutError):
            Client(base_url=self.base.replace("/v1", "/v1/slow"), timeout=0.3, max_retries=0).forward("x")


if __name__ == "__main__":
    unittest.main()

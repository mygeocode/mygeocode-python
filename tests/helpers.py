"""Shared test helpers: the recorded answers in tests/fixtures, a recording transport, and request checks."""

import asyncio
import json
import os
import urllib.parse

from mygeocode import AsyncClient, Client
from mygeocode._core import Headers, HttpResponse

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")

EIFFEL = (48.8584, 2.2945)
LIBERTY = (40.6892, -74.0445)
OPERA = (-33.8568, 151.2153)


def recording(name):
    """A recorded answer: {"request": {...}, "status": ..., "headers": {...}, "body": {...}}."""
    with open(os.path.join(FIXTURES, name + ".json"), encoding="utf-8") as handle:
        return json.load(handle)


def answer(status=200, body=None, headers=None, text=None):
    data = text if text is not None else json.dumps(body)
    return HttpResponse(status, Headers(headers or {}), data.encode("utf-8"))


def replay(name, status=None, headers=None):
    """The recorded status, headers and body of a recording, optionally overridden."""
    rec = recording(name)
    merged = dict(rec["headers"])
    merged.update({k.lower(): v for k, v in (headers or {}).items()})
    return answer(rec["status"] if status is None else status, rec["body"], merged)


class Sent(object):
    """A request as the transport received it, with the URL taken apart."""

    def __init__(self, request):
        self.method = request.method
        self.url = request.url
        self.headers = Headers(request.headers)
        self.body = request.body
        self.timeout = request.timeout
        parts = urllib.parse.urlsplit(request.url)
        self.path = parts.path
        self.query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))

    def json(self):
        return None if self.body is None else json.loads(self.body.decode("utf-8"))


class Recorder(object):
    """Collects requests and answers with the queued responses in turn (the last one repeats).

    A queued exception is raised instead of answering.
    """

    def __init__(self, *responses):
        self.sent = []
        self.queue = list(responses)

    def __call__(self, request):
        self.sent.append(Sent(request))
        item = self.queue.pop(0) if len(self.queue) > 1 else self.queue[0]
        if isinstance(item, BaseException):
            raise item
        return item

    @property
    def last(self):
        return self.sent[-1]


def _same(a, b):
    if a == b:
        return True
    try:
        return float(a) == float(b)
    except ValueError:
        return False


class Checks(object):
    """Mixin for unittest.TestCase classes."""

    def setUp(self):
        self._saved_key = os.environ.pop("MYGEOCODE_KEY", None)
        self.sleeps = []

    def tearDown(self):
        os.environ.pop("MYGEOCODE_KEY", None)
        if self._saved_key is not None:
            os.environ["MYGEOCODE_KEY"] = self._saved_key

    def client(self, transport, **options):
        options.setdefault("sleep", self.sleeps.append)
        options.setdefault("clock", lambda: 1000.0)
        return Client(transport=transport, **options)

    def async_client(self, transport, **options):
        sleeps = self.sleeps

        async def fake_sleep(seconds):
            sleeps.append(seconds)

        options.setdefault("sleep", fake_sleep)
        options.setdefault("clock", lambda: 1000.0)
        return AsyncClient(transport=transport, **options)

    def assertSentLike(self, name, sent):
        """The request equals the recorded one: method, path, every query parameter and the JSON body."""
        want = recording(name)["request"]
        self.assertEqual(sent.method, want["method"])
        self.assertEqual(sent.path, want["path"])
        self.assertEqual(set(sent.query), set(want["query"]), "query of " + name)
        for key, value in want["query"].items():
            self.assertTrue(_same(sent.query[key], str(value)), "{}: {} != {}".format(key, sent.query[key], value))
        self.assertEqual(sent.json(), want["body"])


def run(coroutine):
    """Run a coroutine on a fresh event loop (works the same on every Python from 3.6)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

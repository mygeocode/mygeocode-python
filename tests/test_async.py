"""AsyncClient: the same 16 methods and options as Client, each awaited, with the same requests and retries."""

import inspect
import unittest

from helpers import EIFFEL, LIBERTY, OPERA, Checks, Recorder, answer, recording, replay, run

from mygeocode import ApiError, AsyncClient, Client, NetworkError

METHODS = (
    "forward", "reverse", "autocomplete", "ip", "ipv4", "ipv6", "timezone", "elevation", "postcode",
    "forward_batch", "reverse_batch", "ip_batch", "ipv4_batch", "ipv6_batch", "timezone_batch", "elevation_batch",
)  # fmt: skip


class AsyncTest(Checks, unittest.TestCase):
    def test_same_methods_and_options_as_the_client(self):
        for name in METHODS:
            sync = inspect.signature(getattr(Client, name))
            asyn = inspect.signature(getattr(AsyncClient, name))
            self.assertEqual(list(sync.parameters), list(asyn.parameters), name)
            self.assertTrue(inspect.iscoroutinefunction(getattr(AsyncClient, name)), name)
        self.assertEqual(
            sorted(n for n in dir(Client) if not n.startswith("_")),
            sorted([n for n in dir(AsyncClient) if not n.startswith("_") and n != "aclose"] + ["close"]),
        )

    def test_every_method_against_its_recording(self):
        calls = (
            ("forward", lambda c: c.forward("Brandenburg Gate, Berlin")),
            ("forward_structured", lambda c: c.forward(street="10 Downing Street", city="London", country="GB")),
            ("reverse", lambda c: c.reverse(*EIFFEL)),
            ("autocomplete", lambda c: c.autocomplete("1600 Pennsylvania")),
            ("ip", lambda c: c.ip("8.8.8.8")),
            ("ipv4", lambda c: c.ipv4("8.8.8.8")),
            ("ipv6", lambda c: c.ipv6("2001:4860:4860::8888")),
            ("timezone", lambda c: c.timezone(35.6762, 139.6503)),
            ("timezone_tz", lambda c: c.timezone(tz="Europe/Paris")),
            ("elevation", lambda c: c.elevation(27.9881, 86.9250)),
            ("postcode", lambda c: c.postcode("10001", country="US")),
            ("forward_batch", lambda c: c.forward_batch(["Brandenburg Gate, Berlin", "Sydney Opera House", "Statue of Liberty, New York"])),
            ("reverse_batch", lambda c: c.reverse_batch([EIFFEL, LIBERTY, OPERA])),
            ("ip_batch", lambda c: c.ip_batch(["8.8.8.8", "2606:4700:4700::1111"])),
            ("ipv4_batch", lambda c: c.ipv4_batch(["8.8.8.8", "1.1.1.1", "9.9.9.9"])),
            ("ipv6_batch", lambda c: c.ipv6_batch(["2001:4860:4860::8888", "2606:4700:4700::1111"])),
            ("timezone_batch", lambda c: c.timezone_batch([EIFFEL, LIBERTY, OPERA])),
            ("elevation_batch", lambda c: c.elevation_batch([EIFFEL, LIBERTY, OPERA])),
        )
        for name, call in calls:
            rec = Recorder(replay(name))
            result = run(call(self.async_client(rec)))
            self.assertSentLike(name, rec.last)
            self.assertEqual(result.raw, recording(name)["body"], name)
        rec = Recorder(replay("reverse"))
        self.assertEqual(run(self.async_client(rec).reverse(*EIFFEL)).result.formatted, "5 Avenue Anatole France, 75007 Paris, France")

    def test_retries_wait_with_the_async_sleep(self):
        rec = Recorder(answer(429, {"status": "error", "error": {"code": "rate_limited", "message": "x"}}, {"Retry-After": "3"}), replay("forward"))
        run(self.async_client(rec).forward("Brandenburg Gate, Berlin"))
        self.assertEqual(self.sleeps, [3.0])
        rec = Recorder(answer(500, {"status": "error", "error": {"code": "server_error", "message": "x"}}))
        self.sleeps[:] = []
        with self.assertRaises(ApiError):
            run(self.async_client(rec).forward("Brandenburg Gate, Berlin"))
        self.assertEqual(self.sleeps, [1.0])

    def test_network_errors(self):
        rec = Recorder(NetworkError("refused"), replay("forward"))
        run(self.async_client(rec).forward("Brandenburg Gate, Berlin"))
        self.assertEqual(self.sleeps, [1.0])
        rec = Recorder(NetworkError("reset"))
        with self.assertRaises(NetworkError):
            run(self.async_client(rec).forward_batch(["Brandenburg Gate, Berlin"]))
        self.assertEqual(len(rec.sent), 1)

    def test_async_with_block(self):
        rec = Recorder(replay("forward"))

        async def use():
            async with AsyncClient(transport=rec) as client:
                return await client.forward("Brandenburg Gate, Berlin")

        self.assertEqual(run(use()).status, "ok")


if __name__ == "__main__":
    unittest.main()

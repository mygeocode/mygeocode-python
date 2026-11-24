"""Client behaviour: key handling, defaults, errors, retries, timeouts and the language rules."""

import os
import unittest

from helpers import Checks, Recorder, answer, recording, replay

from mygeocode import ApiError, Client, DecodeError, NetworkError, RequestTimeoutError, __version__
from mygeocode._core import USER_AGENT


class ClientTest(Checks, unittest.TestCase):
    def test_keyless_sends_no_key_and_our_user_agent(self):
        rec = Recorder(replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertNotIn("X-API-Key", rec.last.headers)
        self.assertEqual(rec.last.headers["User-Agent"], "mygeocode-python/{} (+https://www.mygeocode.com/sdks/)".format(__version__))
        self.assertEqual(USER_AGENT, rec.last.headers["User-Agent"])
        self.assertTrue(rec.last.url.startswith("https://api.mygeocode.com/v1/forward?"))

    def test_key_goes_in_the_header_never_the_url(self):
        rec = Recorder(replay("forward"))
        self.client(rec, key="mg_test_key").forward("Brandenburg Gate, Berlin")
        self.assertEqual(rec.last.headers["X-API-Key"], "mg_test_key")
        self.assertNotIn("mg_test_key", rec.last.url)
        self.assertNotIn("key", rec.last.query)

    def test_key_from_the_environment_and_empty_key_means_none(self):
        os.environ["MYGEOCODE_KEY"] = "mg_env_key"
        rec = Recorder(replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(rec.last.headers["X-API-Key"], "mg_env_key")
        rec = Recorder(replay("forward"))
        self.client(rec, key="").forward("Brandenburg Gate, Berlin")
        self.assertNotIn("X-API-Key", rec.last.headers)

    def test_defaults_are_ten_seconds_and_english(self):
        rec = Recorder(replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(rec.last.timeout, 10.0)
        self.assertEqual(rec.last.query["lang"], "en")

    def test_base_url_and_timeout_reach_the_transport(self):
        rec = Recorder(replay("forward"))
        self.client(rec, base_url="https://example.test/v1/", timeout=3).forward("Brandenburg Gate, Berlin")
        self.assertTrue(rec.last.url.startswith("https://example.test/v1/forward?"))
        self.assertEqual(rec.last.timeout, 3.0)

    def test_lang_on_the_client_and_per_call(self):
        rec = Recorder(replay("forward"))
        client = self.client(rec, lang="de")
        client.forward("Brandenburg Gate, Berlin")
        self.assertEqual(rec.last.query["lang"], "de")
        client.forward("Brandenburg Gate, Berlin", lang="fr")
        self.assertEqual(rec.last.query["lang"], "fr")

    def test_timezone_language_only_when_chosen(self):
        rec = Recorder(replay("timezone"))
        self.client(rec).timezone(35.6762, 139.6503)
        self.assertNotIn("language", rec.last.query)
        self.client(rec).timezone(35.6762, 139.6503, lang="ja")
        self.assertEqual(rec.last.query["language"], "ja")
        self.client(rec).timezone(35.6762, 139.6503, language="de")
        self.assertEqual(rec.last.query["language"], "de")
        self.client(rec, lang="en").timezone(35.6762, 139.6503)
        self.assertEqual(rec.last.query["language"], "en")
        self.assertNotIn("lang", rec.last.query)

    def test_error_envelope_becomes_api_error(self):
        rec = Recorder(replay("error_invalid_request"))
        with self.assertRaises(ApiError) as caught:
            self.client(rec).forward("")
        error = caught.exception
        body = recording("error_invalid_request")
        self.assertEqual(error.status, body["status"])
        self.assertEqual(error.code, body["body"]["error"]["code"])
        self.assertEqual(error.message, body["body"]["error"]["message"])
        self.assertEqual(error.param, body["body"]["error"].get("param"))
        self.assertEqual(error.request_id, body["headers"]["x-request-id"])
        self.assertEqual(error.body, body["body"])
        self.assertIsNone(error.retry_after)

    def test_error_without_a_json_body(self):
        rec = Recorder(answer(502, text="<html>Bad gateway</html>"))
        with self.assertRaises(ApiError) as caught:
            self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(caught.exception.status, 502)
        self.assertEqual(caught.exception.code, "http_error")

    def test_success_that_is_not_json_is_a_decode_error(self):
        rec = Recorder(answer(200, text="not json"))
        with self.assertRaises(DecodeError):
            self.client(rec).forward("Brandenburg Gate, Berlin")

    def test_429_waits_for_retry_after(self):
        rec = Recorder(answer(429, {"status": "error", "error": {"code": "rate_limited", "message": "slow down"}}, {"Retry-After": "7"}), replay("forward"))
        result = self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(self.sleeps, [7.0])
        self.assertEqual(result.status, "ok")
        self.assertEqual(len(rec.sent), 2)

    def test_429_waits_until_the_quota_reset(self):
        rec = Recorder(answer(429, {"status": "error", "error": {"code": "quota_exceeded", "message": "x"}}, {"X-Quota-Reset": "1030"}), replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(self.sleeps, [30.0])

    def test_quota_gone_for_the_day_raises_at_once(self):
        rec = Recorder(answer(429, {"status": "error", "error": {"code": "quota_exceeded", "message": "x"}}, {"X-Quota-Reset": "90000"}))
        with self.assertRaises(ApiError) as caught:
            self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(caught.exception.code, "quota_exceeded")
        self.assertEqual(caught.exception.retry_after, 89000.0)
        self.assertEqual(self.sleeps, [])
        self.assertEqual(len(rec.sent), 1)

    def test_max_retry_wait_is_configurable(self):
        rec = Recorder(answer(429, {"status": "error", "error": {"code": "rate_limited", "message": "x"}}, {"Retry-After": "90"}), replay("forward"))
        self.client(rec, max_retry_wait=120).forward("Brandenburg Gate, Berlin")
        self.assertEqual(self.sleeps, [90.0])

    def test_retries_stop_at_max_retries(self):
        busy = answer(503, {"status": "error", "error": {"code": "unavailable", "message": "x"}})
        rec = Recorder(busy)
        with self.assertRaises(ApiError):
            self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(self.sleeps, [1.0, 2.0])
        self.assertEqual(len(rec.sent), 3)

    def test_max_retries_zero_never_retries(self):
        rec = Recorder(answer(503, {"status": "error", "error": {"code": "unavailable", "message": "x"}}))
        with self.assertRaises(ApiError):
            self.client(rec, max_retries=0).forward("Brandenburg Gate, Berlin")
        self.assertEqual(len(rec.sent), 1)

    def test_503_uses_retry_after(self):
        rec = Recorder(answer(503, {"status": "error", "error": {"code": "maintenance", "message": "x"}}, {"Retry-After": "5"}), replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(self.sleeps, [5.0])

    def test_503_with_a_long_retry_after_raises(self):
        rec = Recorder(answer(503, {"status": "error", "error": {"code": "maintenance", "message": "x"}}, {"Retry-After": "900"}))
        with self.assertRaises(ApiError) as caught:
            self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(caught.exception.retry_after, 900.0)

    def test_500_is_retried_once_after_one_second(self):
        broken = answer(500, {"status": "error", "error": {"code": "server_error", "message": "x"}})
        rec = Recorder(broken, replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(self.sleeps, [1.0])
        rec = Recorder(broken)
        self.sleeps[:] = []
        with self.assertRaises(ApiError):
            self.client(rec, max_retries=5).forward("Brandenburg Gate, Berlin")
        self.assertEqual(len(rec.sent), 2)
        self.assertEqual(self.sleeps, [1.0])

    def test_500_on_post_and_max_retries(self):
        broken = answer(500, {"status": "error", "error": {"code": "server_error", "message": "x"}})
        rec = Recorder(broken, replay("forward_batch"))
        self.client(rec).forward_batch(["Brandenburg Gate, Berlin"])
        self.assertEqual(len(rec.sent), 2)
        rec = Recorder(broken)
        with self.assertRaises(ApiError):
            self.client(rec, max_retries=0).forward_batch(["Brandenburg Gate, Berlin"])
        self.assertEqual(len(rec.sent), 1)

    def test_connection_errors_are_retried_on_get(self):
        rec = Recorder(NetworkError("refused"), NetworkError("refused"), replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(self.sleeps, [1.0, 2.0])

    def test_network_error_after_the_retries(self):
        rec = Recorder(NetworkError("refused"))
        with self.assertRaises(NetworkError):
            self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(len(rec.sent), 3)

    def test_timeouts_are_retried_then_raised(self):
        rec = Recorder(RequestTimeoutError("slow"))
        with self.assertRaises(RequestTimeoutError):
            self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertEqual(len(rec.sent), 3)

    def test_post_is_not_retried_after_a_connection_error(self):
        rec = Recorder(NetworkError("reset"), replay("forward_batch"))
        with self.assertRaises(NetworkError):
            self.client(rec).forward_batch(["Brandenburg Gate, Berlin"])
        self.assertEqual(len(rec.sent), 1)

    def test_post_is_retried_on_429(self):
        rec = Recorder(answer(429, {"status": "error", "error": {"code": "rate_limited", "message": "x"}}, {"Retry-After": "2"}), replay("forward_batch"))
        self.client(rec).forward_batch(["Brandenburg Gate, Berlin"])
        self.assertEqual(self.sleeps, [2.0])

    def test_with_block(self):
        rec = Recorder(replay("forward"))
        with Client(transport=rec) as client:
            client.forward("Brandenburg Gate, Berlin")
        self.assertEqual(len(rec.sent), 1)


if __name__ == "__main__":
    unittest.main()

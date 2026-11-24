"""Every method sends the shared example values, the request must equal the recorded one, and the answer must be
read into the right objects (the recordings in tests/fixtures are real answers of the API)."""

import unittest

from helpers import EIFFEL, LIBERTY, OPERA, Checks, Recorder, recording, replay

from mygeocode import (
    ElevationPoint,
    ForwardBatchEntry,
    IpInfo,
    Place,
    PostcodePlace,
    ReverseResponse,
    TimezoneInfo,
)


class EndpointsTest(Checks, unittest.TestCase):
    def test_forward(self):
        rec = Recorder(replay("forward"))
        r = self.client(rec).forward("Brandenburg Gate, Berlin")
        self.assertSentLike("forward", rec.last)
        want = recording("forward")["body"]["results"][0]
        self.assertEqual(r.status, "ok")
        self.assertIsInstance(r.results[0], Place)
        self.assertEqual(r.results[0].formatted, "Brandenburg Gate, State of Berlin, Germany")
        self.assertEqual(r.results[0].lat, want["lat"])
        self.assertEqual(r.results[0].lon, want["lon"])
        self.assertEqual(r.results[0].components.country_code, want["components"]["country_code"])
        self.assertEqual(r.raw, recording("forward")["body"])

    def test_forward_meta_comes_from_the_headers(self):
        rec = Recorder(replay("forward"))
        r = self.client(rec).forward("Brandenburg Gate, Berlin")
        headers = recording("forward")["headers"]
        self.assertEqual(r.meta.request_id, headers["x-request-id"])
        self.assertEqual(r.meta.quota_limit, int(headers["x-quota-limit"]))
        self.assertEqual(r.meta.quota_used, int(headers["x-quota-used"]))
        self.assertEqual(r.meta.quota_free_remaining, int(headers["x-quota-free-remaining"]))
        self.assertEqual(r.meta.quota_reset, int(headers["x-quota-reset"]))
        self.assertIsNone(r.meta.credits_remaining)

    def test_forward_structured(self):
        rec = Recorder(replay("forward_structured"))
        r = self.client(rec).forward(street="10 Downing Street", city="London", country="GB")
        self.assertSentLike("forward_structured", rec.last)
        self.assertEqual(r.results[0].formatted, "Downing Street, London SW1A, United Kingdom")

    def test_reverse(self):
        rec = Recorder(replay("reverse"))
        r = self.client(rec).reverse(*EIFFEL)
        self.assertSentLike("reverse", rec.last)
        self.assertEqual(r.result.formatted, "5 Avenue Anatole France, 75007 Paris, France")
        self.assertEqual(r.result.distance_m, 47)

    def test_autocomplete(self):
        rec = Recorder(replay("autocomplete"))
        r = self.client(rec).autocomplete("1600 Pennsylvania")
        self.assertSentLike("autocomplete", rec.last)
        self.assertEqual(r.suggestions[0].text, "1600 Pennsylvania Avenue NW, Washington, DC 20500, United States")

    def test_ip_ipv4_ipv6(self):
        for method, name, address in (("ip", "ip", "8.8.8.8"), ("ipv4", "ipv4", "8.8.8.8"), ("ipv6", "ipv6", "2001:4860:4860::8888")):
            rec = Recorder(replay(name))
            r = getattr(self.client(rec), method)(address)
            self.assertSentLike(name, rec.last)
            self.assertIsInstance(r, IpInfo)
            self.assertEqual(r.ip, address)
            self.assertEqual(r.as_name, "Google LLC")
        rec = Recorder(replay("ip"))
        r = self.client(rec).ip("8.8.8.8")
        self.assertEqual((r.country, r.city, r.asn, r.is_datacenter), ("United States", "Mountain View", 15169, True))

    def test_ip_of_the_caller_sends_no_address(self):
        rec = Recorder(replay("ip"))
        self.client(rec).ip()
        self.assertNotIn("ip", rec.last.query)
        self.assertEqual(rec.last.path, "/v1/ip")

    def test_timezone(self):
        rec = Recorder(replay("timezone"))
        r = self.client(rec).timezone(35.6762, 139.6503)
        self.assertSentLike("timezone", rec.last)
        self.assertEqual((r.timezone, r.utc_offset, r.name, r.abbreviation), ("Asia/Tokyo", "+09:00", "Japan Standard Time", "JST"))

    def test_timezone_by_zone_id(self):
        rec = Recorder(replay("timezone_tz"))
        r = self.client(rec).timezone(tz="Europe/Paris")
        self.assertSentLike("timezone_tz", rec.last)
        self.assertEqual(r.timezone, "Europe/Paris")

    def test_elevation(self):
        rec = Recorder(replay("elevation"))
        r = self.client(rec).elevation(27.9881, 86.9250)
        self.assertSentLike("elevation", rec.last)
        self.assertIsInstance(r.results[0], ElevationPoint)
        self.assertEqual(r.results[0].elevation_m, 8627.0)

    def test_postcode(self):
        rec = Recorder(replay("postcode"))
        r = self.client(rec).postcode("10001", country="US")
        self.assertSentLike("postcode", rec.last)
        self.assertIsInstance(r.results[0], PostcodePlace)
        self.assertEqual((r.results[0].place, r.results[0].region_code), ("New York", "NY"))

    def test_forward_batch(self):
        rec = Recorder(replay("forward_batch"))
        r = self.client(rec).forward_batch(["Brandenburg Gate, Berlin", "Sydney Opera House", "Statue of Liberty, New York"])
        self.assertSentLike("forward_batch", rec.last)
        self.assertIsInstance(r.results[0], ForwardBatchEntry)
        self.assertEqual(
            [(e.query, e.results[0].formatted) for e in r.results],
            [
                ("Brandenburg Gate, Berlin", "Brandenburg Gate, State of Berlin, Germany"),
                ("Sydney Opera House", "Sydney Opera House, Sydney, New South Wales, Australia"),
                ("Statue of Liberty, New York", "Statue of Liberty, New York, New York, United States"),
            ],
        )

    def test_forward_batch_reads_a_numeric_postcode_as_text(self):
        rec = Recorder(replay("forward_batch"))
        r = self.client(rec).forward_batch(["Brandenburg Gate, Berlin", "Sydney Opera House", "Statue of Liberty, New York"])
        york = r.results[2].results[3]
        self.assertEqual(york.raw["components"]["postcode"], 68467)
        self.assertEqual(york.components.postcode, "68467")

    def test_reverse_batch(self):
        rec = Recorder(replay("reverse_batch"))
        r = self.client(rec).reverse_batch([EIFFEL, LIBERTY, OPERA])
        self.assertSentLike("reverse_batch", rec.last)
        self.assertIsInstance(r.results[0], ReverseResponse)
        self.assertEqual(
            [p.result.formatted for p in r.results],
            [
                "5 Avenue Anatole France, 75007 Paris, France",
                "1 Liberty Island, New York, NY 10004, United States",
                "2B Macquarie Street, Sydney NSW 2000, Australia",
            ],
        )

    def test_ip_batches(self):
        cases = (
            ("ip_batch", "ip_batch", ["8.8.8.8", "2606:4700:4700::1111"]),
            ("ipv4_batch", "ipv4_batch", ["8.8.8.8", "1.1.1.1", "9.9.9.9"]),
            ("ipv6_batch", "ipv6_batch", ["2001:4860:4860::8888", "2606:4700:4700::1111"]),
        )
        for method, name, addresses in cases:
            rec = Recorder(replay(name))
            r = getattr(self.client(rec), method)(addresses)
            self.assertSentLike(name, rec.last)
            self.assertEqual([i.ip for i in r.results], addresses)
        rec = Recorder(replay("ipv4_batch"))
        r = self.client(rec).ipv4_batch(["8.8.8.8", "1.1.1.1", "9.9.9.9"])
        self.assertEqual([i.as_name for i in r.results], ["Google LLC", "Cloudflare, Inc.", "Quad9"])

    def test_ip_batch_entry_the_api_rejects(self):
        from helpers import answer

        body = {"status": "ok", "results": [recording("ipv4")["body"], {"status": "error", "ip": "not-an-ip", "error": {"code": "invalid_ip", "message": "Not an IP address."}}]}
        rec = Recorder(answer(200, body))
        r = self.client(rec).ip_batch(["8.8.8.8", "not-an-ip"])
        self.assertEqual(r.results[0].status, "ok")
        self.assertEqual(r.results[1].status, "error")
        self.assertEqual(r.results[1].error["code"], "invalid_ip")

    def test_timezone_batch(self):
        rec = Recorder(replay("timezone_batch"))
        r = self.client(rec).timezone_batch([EIFFEL, LIBERTY, OPERA])
        self.assertSentLike("timezone_batch", rec.last)
        self.assertIsInstance(r.results[0], TimezoneInfo)
        self.assertEqual([z.timezone for z in r.results], ["Europe/Paris", "America/New_York", "Australia/Sydney"])
        self.assertEqual(r.timestamp, recording("timezone_batch")["body"]["timestamp"])

    def test_elevation_batch(self):
        rec = Recorder(replay("elevation_batch"))
        r = self.client(rec).elevation_batch([EIFFEL, LIBERTY, OPERA])
        self.assertSentLike("elevation_batch", rec.last)
        self.assertEqual([p.elevation_m for p in r.results], [37.0, 0.0, 10.0])

    def test_unknown_fields_do_not_break_parsing(self):
        from helpers import answer

        body = dict(recording("reverse")["body"], brand_new_field={"x": 1})
        body["result"] = dict(body["result"], another_new_field=[1, 2])
        rec = Recorder(answer(200, body))
        r = self.client(rec).reverse(*EIFFEL)
        self.assertEqual(r.raw["brand_new_field"], {"x": 1})
        self.assertEqual(r.result.raw["another_new_field"], [1, 2])
        self.assertEqual(r.result.formatted, "5 Avenue Anatole France, 75007 Paris, France")


if __name__ == "__main__":
    unittest.main()

"""Every documented parameter is a keyword argument, sent under the API's own name."""

import unittest

from helpers import EIFFEL, LIBERTY, Checks, Recorder, replay

FLAGS = (
    "timezone", "elevation", "wikidata", "country_info", "codes", "sun", "regions", "districts", "census",
    "demographics", "road", "site",
)  # fmt: skip


class ParametersTest(Checks, unittest.TestCase):
    def test_forward_every_parameter(self):
        rec = Recorder(replay("forward"))
        self.client(rec).forward(
            "Brandenburg Gate, Berlin", street="Pariser Platz", city="Berlin", state="Berlin", postcode="10117",
            country="DE", place_id="abc", limit=3, countries=["de", "at"], bounds=[52.3, 13.0, 52.7, 13.8],
            strict=True, proximity=[52.5, 13.4], types=["poi", "address"], lang="de", annotations=True, pretty=True,
        )  # fmt: skip
        self.assertEqual(rec.last.query, {
            "q": "Brandenburg Gate, Berlin", "street": "Pariser Platz", "city": "Berlin", "state": "Berlin",
            "postcode": "10117", "country": "DE", "place_id": "abc", "limit": "3", "countries": "de,at",
            "bounds": "52.3,13.0,52.7,13.8", "strict": "1", "proximity": "52.5,13.4", "types": "poi,address",
            "lang": "de", "annotations": "1", "pretty": "1",
        })  # fmt: skip

    def test_flags_on_forward_reverse_and_their_batches(self):
        for flag in FLAGS:
            rec = Recorder(replay("forward"))
            client = self.client(rec)
            client.forward("Brandenburg Gate, Berlin", **{flag: True})
            self.assertEqual(rec.last.query[flag], "1", flag)
            client.reverse(*EIFFEL, **{flag: True})
            self.assertEqual(rec.last.query[flag], "1", flag)
            client.forward_batch(["Brandenburg Gate, Berlin"], **{flag: True})
            self.assertEqual(rec.last.query[flag], "1", flag)
            client.reverse_batch([EIFFEL], **{flag: True})
            self.assertEqual(rec.last.query[flag], "1", flag)

    def test_reverse_every_parameter(self):
        rec = Recorder(replay("reverse"))
        self.client(rec).reverse(*EIFFEL, level="city", radius=500, lang="fr", boundaries=True, annotations=True, pretty=True)
        self.assertEqual(rec.last.query, {
            "lat": "48.8584", "lon": "2.2945", "level": "city", "radius": "500", "lang": "fr", "boundaries": "1",
            "annotations": "1", "pretty": "1",
        })  # fmt: skip

    def test_autocomplete_every_parameter(self):
        rec = Recorder(replay("autocomplete"))
        self.client(rec).autocomplete(
            "1600 Pennsylvania", limit=5, countries="us", proximity=[38.9, -77.0], bounds="38,-78,39,-76",
            strict=True, types="address", lang="en", pretty=True,
        )  # fmt: skip
        self.assertEqual(rec.last.query, {
            "q": "1600 Pennsylvania", "limit": "5", "countries": "us", "proximity": "38.9,-77.0",
            "bounds": "38,-78,39,-76", "strict": "1", "types": "address", "lang": "en", "pretty": "1",
        })  # fmt: skip

    def test_ip_parameters(self):
        rec = Recorder(replay("ip"))
        client = self.client(rec)
        client.ipv4("8.8.8.8", elevation=True, pretty=True)
        self.assertEqual(rec.last.query, {"ip": "8.8.8.8", "elevation": "1", "pretty": "1"})
        client.ipv6_batch(["2001:4860:4860::8888", "2606:4700:4700::1111"], elevation=True)
        self.assertEqual(rec.last.query, {"ips": "2001:4860:4860::8888,2606:4700:4700::1111", "elevation": "1"})
        self.assertNotIn("lang", rec.last.query)

    def test_timezone_parameters(self):
        rec = Recorder(replay("timezone"))
        client = self.client(rec)
        client.timezone(35.6762, 139.6503, timestamp=1767225600, lang="ja", pretty=True)
        self.assertEqual(rec.last.query, {"lat": "35.6762", "lon": "139.6503", "timestamp": "1767225600", "language": "ja", "pretty": "1"})
        client.timezone(locations=[EIFFEL, LIBERTY])
        self.assertEqual(rec.last.query, {"locations": "48.8584,2.2945|40.6892,-74.0445"})
        client.timezone(path="enc:abc", samples=10)
        self.assertEqual(rec.last.query, {"path": "enc:abc", "samples": "10"})
        client.timezone(bounds=[40, -75, 41, -73], rows=3, cols=4)
        self.assertEqual(rec.last.query, {"bounds": "40,-75,41,-73", "rows": "3", "cols": "4"})
        client.timezone_batch([EIFFEL], timestamp=1767225600, lang="de")
        self.assertEqual(rec.last.query, {"locations": "48.8584,2.2945", "timestamp": "1767225600", "language": "de"})

    def test_elevation_parameters(self):
        rec = Recorder(replay("elevation"))
        client = self.client(rec)
        client.elevation(locations=[EIFFEL, LIBERTY], pretty=True)
        self.assertEqual(rec.last.query, {"locations": "48.8584,2.2945|40.6892,-74.0445", "pretty": "1"})
        client.elevation(path=[EIFFEL, LIBERTY], samples=5)
        self.assertEqual(rec.last.query, {"path": "48.8584,2.2945|40.6892,-74.0445", "samples": "5"})
        client.elevation(bounds=[27, 86, 28, 87], rows=2, cols=2)
        self.assertEqual(rec.last.query, {"bounds": "27,86,28,87", "rows": "2", "cols": "2"})

    def test_postcode_parameters(self):
        rec = Recorder(replay("postcode"))
        self.client(rec).postcode("75008", country="FR", pretty=True)
        self.assertEqual(rec.last.query, {"code": "75008", "country": "FR", "pretty": "1"})

    def test_batch_options_go_in_the_query_string(self):
        rec = Recorder(replay("forward_batch"))
        client = self.client(rec)
        client.forward_batch(["Brandenburg Gate, Berlin"], limit=1, countries=["de"], bounds="52,13,53,14", strict=True, proximity=[52.5, 13.4], types="poi", lang="fr", annotations=True)
        self.assertEqual(rec.last.json(), {"queries": ["Brandenburg Gate, Berlin"]})
        self.assertEqual(rec.last.query, {
            "limit": "1", "countries": "de", "bounds": "52,13,53,14", "strict": "1", "proximity": "52.5,13.4",
            "types": "poi", "lang": "fr", "annotations": "1",
        })  # fmt: skip
        client.reverse_batch([EIFFEL], level="street", radius=100, boundaries=True)
        self.assertEqual(rec.last.json(), {"coords": [[48.8584, 2.2945]]})
        self.assertEqual(rec.last.query, {"level": "street", "radius": "100", "lang": "en", "boundaries": "1"})
        client.elevation_batch([EIFFEL], pretty=True)
        self.assertEqual(rec.last.json(), {"locations": [[48.8584, 2.2945]]})
        self.assertEqual(rec.last.query, {"pretty": "1"})

    def test_params_pass_through_and_win(self):
        rec = Recorder(replay("forward"))
        self.client(rec).forward("Brandenburg Gate, Berlin", limit=2, params={"limit": 5, "brand_new": "x", "skip": None})
        self.assertEqual(rec.last.query["limit"], "5")
        self.assertEqual(rec.last.query["brand_new"], "x")
        self.assertNotIn("skip", rec.last.query)

    def test_unknown_keyword_is_rejected(self):
        with self.assertRaises(TypeError):
            self.client(Recorder(replay("forward"))).forward("Brandenburg Gate, Berlin", limt=1)  # type: ignore[call-arg]


if __name__ == "__main__":
    unittest.main()

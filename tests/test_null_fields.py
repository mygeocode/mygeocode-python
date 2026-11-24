"""The API may one day answer a field with null instead of dropping it (fields this library reads are never removed;
they become null). Every method must keep working: a null field stays None (never a made-up 0 or ''), a null list
reads as an empty list and a null object as None, with no error or warning.

Each recorded answer is replayed twice: once with every scalar set to null ("leaves"), once with every value set to
null, lists and objects included ("all"). Only the top-level "status" stays "ok", so the answer is not an error.
"""

import unittest

from helpers import EIFFEL, LIBERTY, Checks, Recorder, answer, recording

from mygeocode.models import Model

CALLS = (
    ("forward", "forward", lambda c: c.forward("Brandenburg Gate, Berlin")),
    ("reverse", "reverse", lambda c: c.reverse(*EIFFEL)),
    ("autocomplete", "autocomplete", lambda c: c.autocomplete("1600 Pennsylvania")),
    ("ip", "ip", lambda c: c.ip("8.8.8.8")),
    ("ipv4", "ipv4", lambda c: c.ipv4("8.8.8.8")),
    ("ipv6", "ipv6", lambda c: c.ipv6("2001:4860:4860::8888")),
    ("timezone", "timezone", lambda c: c.timezone(35.6762, 139.6503)),
    ("elevation", "elevation", lambda c: c.elevation(27.9881, 86.9250)),
    ("postcode", "postcode", lambda c: c.postcode("10001", country="US")),
    ("forward_batch", "forward_batch", lambda c: c.forward_batch(["Brandenburg Gate, Berlin", "Sydney Opera House"])),
    ("reverse_batch", "reverse_batch", lambda c: c.reverse_batch([EIFFEL, LIBERTY])),
    ("ip_batch", "ip_batch", lambda c: c.ip_batch(["8.8.8.8", "2606:4700:4700::1111"])),
    ("ipv4_batch", "ipv4_batch", lambda c: c.ipv4_batch(["8.8.8.8", "1.1.1.1", "9.9.9.9"])),
    ("ipv6_batch", "ipv6_batch", lambda c: c.ipv6_batch(["2001:4860:4860::8888"])),
    ("timezone_batch", "timezone_batch", lambda c: c.timezone_batch([EIFFEL, LIBERTY])),
    ("elevation_batch", "elevation_batch", lambda c: c.elevation_batch([EIFFEL, LIBERTY])),
)


def nullify(value, everything, top=True):
    if not isinstance(value, dict):
        return None
    out = {}
    for key, item in value.items():
        if top and key == "status":
            out[key] = "ok"
        elif everything or not isinstance(item, (dict, list)):
            out[key] = None
        elif isinstance(item, list):
            out[key] = [nullify(i, False, False) if isinstance(i, dict) else None for i in item]
        else:
            out[key] = nullify(item, False, False)
    return out


def non_null(value, path, found):
    """Every field of the result tree (meta and raw aside) must be None, an empty list, or hold only Nones."""
    if isinstance(value, Model):
        for name in value._fields:
            item = getattr(value, name)
            if not (name == "status" and item == "ok"):
                non_null(item, path + "." + name, found)
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            non_null(item, "{}[{}]".format(path, i), found)
    elif isinstance(value, dict):  # the extra blocks (codes, timezone ...) stay plain dicts
        for key, item in value.items():
            non_null(item, "{}[{!r}]".format(path, key), found)
    elif value is not None:
        found.append("{} = {!r}".format(path, value))


class NullFieldsTest(Checks, unittest.TestCase):
    def check(self, everything):
        for method, name, call in CALLS:
            body = nullify(recording(name)["body"], everything)
            result = call(self.client(Recorder(answer(200, body))))
            found = []
            non_null(result, method, found)
            self.assertEqual(found, [], ("all" if everything else "leaves") + " null: fields must stay null")
            self.assertEqual(result.status, "ok", method)

    def test_every_scalar_null_stays_none(self):
        self.check(False)

    def test_every_value_null_including_lists_and_objects(self):
        self.check(True)

    def test_null_lists_read_as_empty_lists(self):
        r = self.client(Recorder(answer(200, {"status": "ok", "query": None, "results": None}))).forward("Brandenburg Gate, Berlin")
        self.assertEqual(r.results, [])
        r = self.client(Recorder(answer(200, {"status": "ok", "lat": None, "lon": None, "result": None}))).reverse(*EIFFEL)
        self.assertIsNone(r.result)
        self.assertIsNone(r.lat)
        r = self.client(Recorder(answer(200, {"status": "ok", "ip": "8.8.8.8", "tags": None}))).ip("8.8.8.8")
        self.assertEqual(r.tags, [])


if __name__ == "__main__":
    unittest.main()

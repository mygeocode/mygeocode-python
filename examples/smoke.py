"""Live smoke test: 7 requests in total (limit is 8). Uses MYGEOCODE_KEY if set, else the free requests.

Run: python examples/smoke.py
"""

from mygeocode import Client

c = Client()

fwd = c.forward("Brandenburg Gate, Berlin", limit=1)
assert fwd.results and fwd.results[0].components.country_code == "de"

rev = c.reverse(48.8584, 2.2945)
assert rev.result is not None and rev.result.components.country_code == "fr"

ac = c.autocomplete("1600 Pennsylvania", limit=3)
assert ac.suggestions

ip = c.ipv4("8.8.8.8")
assert ip.country_code == "US" and ip.asn == 15169

tz = c.timezone(35.6762, 139.6503)
assert tz.timezone == "Asia/Tokyo"

el = c.elevation(27.9881, 86.9250)
assert el.results and el.results[0].elevation_m > 8000

pc = c.postcode("10001", country="US")
assert pc.results

print("ok; request id", pc.meta.request_id, "free left", pc.meta.quota_free_remaining)

"""Keyless example: the network's free requests apply. Run: python examples/quickstart.py"""

from mygeocode import Client

client = Client()

found = client.forward("Brandenburg Gate, Berlin", limit=1)
best = found.results[0]
print(best.formatted, best.lat, best.lon, best.precision)

back = client.reverse(48.8584, 2.2945)
print(back.result.formatted if back.result else "nothing nearby")

print("free requests left today:", found.meta.quota_free_remaining)

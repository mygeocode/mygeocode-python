# My Geocode Python SDK

The official Python client for the [My Geocode API](https://www.mygeocode.com/): forward and reverse geocoding,
address autocomplete, IPv4 and IPv6 lookup, timezones, elevation and postal codes.

![Python 3.6 to 3.15](https://img.shields.io/badge/python-3.6%20to%203.15-3776ab)
![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

- Works on every Python from 3.6 to 3.15, so it also runs on the Python 3.6 that ships with RHEL 8, Rocky and Alma
  Linux 8, and on Ubuntu 18.04 and 20.04. No warnings on any of them.
- No dependencies: only the standard library.
- A normal client and an asyncio client with the same methods.
- Safe to drop into any project: it changes no global state (logging, warnings, socket defaults, SSL settings).
- 2,500 free requests a day without a key or an account.

## Install

```bash
pip install mygeocode
```

## Quick start (no key)

```python
from mygeocode import Client

client = Client()

found = client.forward("Brandenburg Gate, Berlin")
place = found.results[0]
print(place.formatted)          # Brandenburg Gate, State of Berlin, Germany
print(place.lat, place.lon)     # 52.516268 13.377692

address = client.reverse(48.8584, 2.2945)
print(address.result.formatted)  # 5 Avenue Anatole France, 75007 Paris, France
```

Without a key, each network gets 2,500 free requests a day. `found.meta.quota_free_remaining` tells you how many are
left.

## Using a key

A key adds your account's prepaid credit or Unlimited package on top of the free requests. Create one in the
[dashboard](https://www.mygeocode.com/dashboard).

```python
client = Client("YOUR_KEY")
```

If you leave out the key, the client reads the `MYGEOCODE_KEY` environment variable. Pass `Client("")` to make sure no
key is sent. The key always travels in the `X-API-Key` header, never in the URL, and the SDK never writes it anywhere.

## Language

Results are in English unless you set `lang`. Set it once on the client, or per call:

```python
client = Client(lang="de")

client.reverse(48.8584, 2.2945, lang="fr")  # this call only
```

`lang` takes an ISO 639-1 code such as `de`, `ja` or `pt-BR`. The whole address comes back in that language and
script. On its own, the API answers each result in the language of its area; the SDK sends `lang=en` by default so
that every result reads the same.

## Methods

Every method takes its main arguments first, then keyword options named after the API's own parameters. Every method
also accepts `params`, a dict of extra query parameters that are sent as they are (and win over the named options),
and `pretty=True` for indented JSON. A keyword the method does not know raises a `TypeError`, so typos show up
straight away.

| Method | Endpoint |
|---|---|
| [`forward`](#forward) | `GET /v1/forward` |
| [`reverse`](#reverse) | `GET /v1/reverse` |
| [`autocomplete`](#autocomplete) | `GET /v1/autocomplete` |
| [`ip`, `ipv4`, `ipv6`](#ip-ipv4-ipv6) | `GET /v1/ip`, `/v1/ipv4`, `/v1/ipv6` |
| [`timezone`](#timezone) | `GET /v1/timezone` |
| [`elevation`](#elevation) | `GET /v1/elevation` |
| [`postcode`](#postcode) | `GET /v1/postcode` |
| [`forward_batch`](#forward_batch) | `POST /v1/forward` |
| [`reverse_batch`](#reverse_batch) | `POST /v1/reverse` |
| [`ip_batch`, `ipv4_batch`, `ipv6_batch`](#ip_batch-ipv4_batch-ipv6_batch) | `GET /v1/ip`, `/v1/ipv4`, `/v1/ipv6` with `ips` |
| [`timezone_batch`](#timezone_batch) | `GET /v1/timezone` with `locations` |
| [`elevation_batch`](#elevation_batch) | `POST /v1/elevation` |

### forward

Text, structured address fields or a place id to coordinates. Returns a `ForwardResponse` whose `results` holds up to
`limit` `Place` objects, best first. An empty list means nothing matched.

```python
found = client.forward("Brandenburg Gate, Berlin")
print(found.results[0].formatted)               # Brandenburg Gate, State of Berlin, Germany

client.forward("Brandenburg Gate, Berlin", limit=3, countries=["de"])
client.forward(street="10 Downing Street", city="London", country="GB")
```

| Option | Type | What it does |
|---|---|---|
| `street`, `city`, `state`, `postcode`, `country` | str | Structured search instead of (or as well as) free text. |
| `place_id` | str | Look up a `place_id` from an earlier result. |
| `limit` | int | 1 to 10 results. |
| `countries` | str or list | ISO 3166-1 alpha-2 codes to search in, such as `["de", "at"]`. |
| `bounds` | str or list | `south,west,north,east` box that results should fall in. |
| `strict` | bool | Only return results inside `bounds`. |
| `proximity` | str or list | `lat,lon` to prefer results near. |
| `types` | str or list | Kinds of result to keep, such as `address` or `poi`. |
| `lang` | str | Language of the result. |
| `timezone`, `elevation`, `wikidata`, `country_info`, `codes`, `sun`, `regions`, `districts`, `census`, `demographics`, `road`, `site` | bool | Each adds its extra block to every result. |
| `annotations` | bool | Adds every extra block at once. |

### reverse

A point to the nearest address. Returns a `ReverseResponse` whose `result` is a `Place`, or `None` when nothing is in
range.

```python
address = client.reverse(48.8584, 2.2945)
print(address.result.formatted)    # 5 Avenue Anatole France, 75007 Paris, France
print(address.result.distance_m)   # 47 (metres from the point you gave)

client.reverse(48.8584, 2.2945, level="city", timezone=True)
```

| Option | Type | What it does |
|---|---|---|
| `level` | str | `address`, `street`, `postcode`, `city`, `region` or `country`. |
| `radius` | int | Search radius in metres, 1 to 5000. |
| `lang` | str | Language of the result. |
| `boundaries` | bool | Add the administrative boundaries the point falls in (Australia). |
| `timezone`, `elevation`, `wikidata`, `country_info`, `codes`, `sun`, `regions`, `districts`, `census`, `demographics`, `road`, `site` | bool | Each adds its extra block, as for `forward`. |
| `annotations` | bool | Adds every extra block at once. |

### autocomplete

Suggestions while someone types an address. Returns an `AutocompleteResponse` with a `suggestions` list; each
`Suggestion` has `text`, `lat`, `lon`, `type`, `precision` and `place_id`.

```python
typed = client.autocomplete("1600 Pennsylvania")
print(typed.suggestions[0].text)   # 1600 Pennsylvania Avenue NW, Washington, DC 20500, United States

client.autocomplete("1600 Pennsylvania", limit=5, countries="us")
```

Options: `limit`, `countries`, `proximity`, `bounds`, `strict`, `types` and `lang`, as for `forward`.

### ip, ipv4, ipv6

Country, region, city, coordinates, timezone, network owner (ASN) and proxy, VPN and data centre flags for an IP
address. `ip` takes either version; `ipv4` and `ipv6` accept only their own. Without an address you get the address the
request came from. Returns an `IpInfo`.

```python
google = client.ip("8.8.8.8")
print(google.country, google.city)   # United States Mountain View
print(google.asn, google.as_name)    # 15169 Google LLC
print(google.is_datacenter)          # True

client.ipv6("2001:4860:4860::8888")
client.ip()                                # the address the request came from
client.ipv4("8.8.8.8", elevation=True)     # adds elevation_m
```

Option: `elevation` (bool). The full list of `IpInfo` fields is under [Results and meta](#results-and-meta).

### timezone

The IANA zone, UTC offset, daylight saving state and local time for a point, now or at a given moment. Returns a
`TimezoneInfo`.

```python
tokyo = client.timezone(35.6762, 139.6503)
print(tokyo.timezone, tokyo.utc_offset)     # Asia/Tokyo +09:00
print(tokyo.name, tokyo.abbreviation)       # Japan Standard Time JST
print(tokyo.local_time)                     # 2026-11-24T18:07:15+09:00

client.timezone(35.6762, 139.6503, timestamp=1767225600)
client.timezone(tz="Europe/Paris")
```

| Option | Type | What it does |
|---|---|---|
| `tz` | str | Look up a zone by its IANA or Windows id instead of a point (leave out lat and lon). |
| `timestamp` | int | Unix time to answer for. Default: now. |
| `lang` | str | Language of the zone name. Sent as the API's `language` parameter, only when you set it here or on the client. `language` works as another name for this option. |
| `locations` | list or str | Several points: `[(lat, lon), ...]`, `"lat,lon\|lat,lon"` or an `enc:` polyline. |
| `path`, `samples` | list or str, int | Points along a path, sampled `samples` times (2 to 100). |
| `bounds`, `rows`, `cols` | str or list, int, int | A grid of points over a box. |

For a plain list of points, `timezone_batch` is simpler.

### elevation

Height in metres above sea level (negative for the sea floor), from a global 15 arc-second grid. Returns an
`ElevationResponse` whose `results` holds `ElevationPoint` objects with `lat`, `lon`, `elevation_m` and `resolution_m`.

```python
everest = client.elevation(27.9881, 86.9250)
print(everest.results[0].elevation_m)   # 8627.0
```

| Option | Type | What it does |
|---|---|---|
| `locations` | list or str | Several points (leave out lat and lon). |
| `path`, `samples` | list or str, int | Heights along a path. |
| `bounds`, `rows`, `cols` | str or list, int, int | Heights over a grid. |

### postcode

A postal code to its place, region and coordinates. Returns a `PostcodeResponse` whose `results` lists every place that
uses the code.

```python
nyc = client.postcode("10001", country="US")
first = nyc.results[0]
print(first.place, first.region_code)   # New York NY
print(first.lat, first.lon)             # 40.748401 -73.996702

client.postcode("75008", country="FR")
```

Option: `country` (ISO alpha-2). Without it, the code is matched in every country.

### forward_batch

Up to 100 searches in one request (each counts as one request against your quota). Returns a `ForwardBatchResponse`
whose `results` holds one `ForwardBatchEntry` per search, in the order you sent them; each entry has the `query` and
its own `results` list of `Place` objects.

```python
batch = client.forward_batch(["Brandenburg Gate, Berlin", "Sydney Opera House", "Statue of Liberty, New York"])
for entry in batch.results:
    print(entry.query + ":", entry.results[0].formatted)
# Brandenburg Gate, Berlin: Brandenburg Gate, State of Berlin, Germany
# Sydney Opera House: Sydney Opera House, Sydney, New South Wales, Australia
# Statue of Liberty, New York: Statue of Liberty, New York, New York, United States

client.forward_batch(["Brandenburg Gate, Berlin", "Sydney Opera House"], limit=1, timezone=True)
```

The options apply to every search in the batch:

| Option | Type | What it does |
|---|---|---|
| `limit` | int | 1 to 10 results per search. |
| `countries`, `bounds`, `strict`, `proximity`, `types` | as for `forward` | Filters for every search. |
| `lang` | str | Language of the results. |
| `timezone`, `elevation`, `wikidata`, `country_info`, `codes`, `sun`, `regions`, `districts`, `census`, `demographics`, `road`, `site` | bool | Each adds its extra block to every result. |
| `annotations` | bool | Adds every extra block at once. |

Structured fields and `place_id` are not available in a batch; use `forward` for those.

### reverse_batch

Up to 100 points in one request (each counts as one request). Returns a `ReverseBatchResponse` whose `results` holds
one `ReverseResponse` per point, in the order you sent them; its `result` is a `Place`, or `None` when nothing is in
range.

```python
batch = client.reverse_batch([(48.8584, 2.2945), (40.6892, -74.0445), (-33.8568, 151.2153)])
for point in batch.results:
    print(point.result.formatted if point.result else "nothing in range")
# 5 Avenue Anatole France, 75007 Paris, France
# 1 Liberty Island, New York, NY 10004, United States
# 2B Macquarie Street, Sydney NSW 2000, Australia
```

The options apply to every point in the batch:

| Option | Type | What it does |
|---|---|---|
| `level` | str | `address`, `street`, `postcode`, `city`, `region` or `country`. |
| `radius` | int | Search radius in metres, 1 to 5000. |
| `lang` | str | Language of the results. |
| `boundaries` | bool | Add the administrative boundaries each point falls in (Australia). |
| `timezone`, `elevation`, `wikidata`, `country_info`, `codes`, `sun`, `regions`, `districts`, `census`, `demographics`, `road`, `site` | bool | Each adds its extra block, as for `forward`. |
| `annotations` | bool | Adds every extra block at once. |

### ip_batch, ipv4_batch, ipv6_batch

Up to 100 addresses in one request. `ip_batch` takes both versions mixed; `ipv4_batch` and `ipv6_batch` accept only
their own. Returns an `IpBatchResponse` whose `results` holds one `IpInfo` per address, in the order you sent them. An
address the API cannot read gets an entry whose `status` is `error` and whose `error` explains why, while the rest
still answer.

```python
batch = client.ipv4_batch(["8.8.8.8", "1.1.1.1", "9.9.9.9"])
for info in batch.results:
    print(info.ip + ":", info.as_name if info.status == "ok" else info.error["message"])
# 8.8.8.8: Google LLC
# 1.1.1.1: Cloudflare, Inc.
# 9.9.9.9: Quad9

client.ipv6_batch(["2001:4860:4860::8888", "2606:4700:4700::1111"])
client.ip_batch(["8.8.8.8", "2606:4700:4700::1111"], elevation=True)
```

Option: `elevation` (bool), adds `elevation_m` to every address.

### timezone_batch

Timezones for up to 100 points. Returns a `TimezoneBatchResponse` whose `results` holds one `TimezoneInfo` per point,
in the order you sent them.

```python
batch = client.timezone_batch([(48.8584, 2.2945), (40.6892, -74.0445), (-33.8568, 151.2153)])
for zone in batch.results:
    print(zone.timezone)
# Europe/Paris
# America/New_York
# Australia/Sydney
```

Options: `timestamp` (Unix time, default now) and `lang` (also accepted as `language`), as for `timezone`.

### elevation_batch

Heights for up to 100 points, sent as a POST body. Returns an `ElevationResponse`.

```python
batch = client.elevation_batch([(48.8584, 2.2945), (40.6892, -74.0445), (-33.8568, 151.2153)])
for point in batch.results:
    print(point.elevation_m)
# 37.0
# 0.0
# 10.0
```

## Async client

`AsyncClient` has the same methods and options; each one is a coroutine. The request runs in the event loop's thread
pool, so it never blocks the loop.

```python
import asyncio

from mygeocode import AsyncClient


async def main():
    async with AsyncClient() as client:
        tokyo, everest = await asyncio.gather(
            client.timezone(35.6762, 139.6503),
            client.elevation(27.9881, 86.9250),
        )
        print(tokyo.timezone, everest.results[0].elevation_m)   # Asia/Tokyo 8627.0


asyncio.run(main())  # on Python 3.6: asyncio.get_event_loop().run_until_complete(main())
```

## Results and meta

Results are plain objects whose attributes carry the API's own field names, so the
[API documentation](https://www.mygeocode.com/docs/) describes them field by field:

```python
place = client.forward("Brandenburg Gate, Berlin").results[0]

place.formatted                  # "Brandenburg Gate, State of Berlin, Germany"
place.precision                  # "house"
place.components.city            # address parts: road, house_number, postcode, city, state, country ...
place.components.country_code    # "de"
```

A field the API did not send is `None`, so check for `None` before you use one. The fields this SDK reads are never
renamed or removed from the API: if one ever has to go, it keeps coming back with the value `None`, and your code
keeps working. A list that comes back as `null` reads as an empty list. Every result object also has `raw`, the decoded
JSON as a dict, so fields added to the API later are readable before the SDK knows them.

What each method returns, and the attributes you can read:

| Class | Returned by | Attributes |
|---|---|---|
| `ForwardResponse` | `forward` | `status`, `query`, `results` (list of `Place`), `meta`, `raw` |
| `ReverseResponse` | `reverse`, each entry of `reverse_batch` | `status`, `lat`, `lon`, `result` (`Place` or `None`), `boundaries`, `meta`, `raw` |
| `Place` | inside forward and reverse results | `formatted`, `lat`, `lon`, `type`, `precision`, `confidence`, `place_id`, `components`, `bounds`, `distance_m`, `formatted_place`, `place`, `parcel`, `codes`, `population`, `un_locode`, `timezone`, `elevation_m`, `wikidata`, `country_info`, `sun`, `regions`, `districts`, `census`, `demographics`, `road`, `intersection`, `site`, `raw` |
| `Components` | `Place.components` | `poi`, `building`, `unit`, `level`, `house_number`, `road`, `lot`, `suburb`, `municipality`, `city`, `county`, `state`, `state_code`, `postcode`, `country`, `country_code`, `official_name`, `raw` |
| `Bounds` | `Place.bounds` | `north`, `south`, `east`, `west`, `raw` |
| `AutocompleteResponse` | `autocomplete` | `status`, `query`, `suggestions` (list of `Suggestion`), `meta`, `raw` |
| `Suggestion` | inside autocomplete results | `text`, `lat`, `lon`, `type`, `precision`, `place_id`, `raw` |
| `IpInfo` | `ip`, `ipv4`, `ipv6`, each entry of the IP batches | `status`, `ip`, `version`, `found`, `prefix`, `country`, `country_code`, `continent`, `continent_code`, `region`, `region_code`, `city`, `postcode`, `lat`, `lon`, `elevation_m`, `timezone`, `utc_offset`, `utc_offset_seconds`, `is_eu`, `asn`, `as_name`, `org`, `usage_type`, `registry`, `allocated`, `tags`, `is_anycast`, `is_satellite`, `is_datacenter`, `is_proxy`, `is_vpn_provider`, `is_tor`, `crawler`, `is_private`, `reason`, `abuse_email`, `threat`, `updated_at`, `error`, `meta`, `raw` |
| `TimezoneInfo` | `timezone`, each entry of `timezone_batch` | `status`, `lat`, `lon`, `timezone`, `name`, `abbreviation`, `utc_offset`, `utc_offset_seconds`, `raw_offset_seconds`, `dst`, `dst_offset_seconds`, `timestamp`, `local_time`, `country_code`, `is_ocean`, `windows_timezone`, `next_transition` (`TimezoneTransition`), `meta`, `raw` |
| `TimezoneTransition` | `TimezoneInfo.next_transition` | `timestamp`, `utc_offset`, `utc_offset_seconds`, `dst`, `abbreviation`, `raw` |
| `ElevationResponse` | `elevation`, `elevation_batch` | `status`, `results` (list of `ElevationPoint`), `meta`, `raw` |
| `ElevationPoint` | inside elevation results | `lat`, `lon`, `elevation_m`, `resolution_m`, `raw` |
| `PostcodeResponse` | `postcode` | `status`, `postcode`, `country_code`, `results` (list of `PostcodePlace`), `meta`, `raw` |
| `PostcodePlace` | inside postcode results | `postcode`, `place`, `region`, `region_code`, `country`, `country_code`, `lat`, `lon`, `raw` |
| `ForwardBatchResponse` | `forward_batch` | `status`, `results` (list of `ForwardBatchEntry`), `meta`, `raw` |
| `ForwardBatchEntry` | inside forward batch results | `query`, `results` (list of `Place`), `raw` |
| `ReverseBatchResponse` | `reverse_batch` | `status`, `results` (list of `ReverseResponse`), `meta`, `raw` |
| `IpBatchResponse` | `ip_batch`, `ipv4_batch`, `ipv6_batch` | `status`, `results` (list of `IpInfo`), `meta`, `raw` |
| `TimezoneBatchResponse` | `timezone_batch` | `status`, `timestamp`, `results` (list of `TimezoneInfo`), `meta`, `raw` |

The extra blocks you ask for with the flags (`timezone`, `elevation`, `wikidata` and the rest) are attributes of
`Place` and stay plain dicts.

Every response object has `meta`, filled from the response headers:

| Attribute | Header | Meaning |
|---|---|---|
| `request_id` | `X-Request-Id` | Quote it when you contact support. |
| `quota_limit` | `X-Quota-Limit` | Free requests a day for this key's account or network. |
| `quota_used` | `X-Quota-Used` | Free requests used today. |
| `quota_free_remaining` | `X-Quota-Free-Remaining` | Free requests left today. |
| `quota_reset` | `X-Quota-Reset` | Unix time when the free requests reset. |
| `credits_remaining` | `X-Credits-Remaining` | Prepaid credit left, when a key with credit is used. |

## Errors

Everything the SDK raises derives from `mygeocode.MyGeocodeError`:

| Class | When |
|---|---|
| `ApiError` | The API answered with an error. `status` is the HTTP status, `code` the API's error code (such as `invalid_request`, `invalid_key` or `quota_exceeded`), `message` its explanation, `param` the parameter at fault, `request_id`, `retry_after` (seconds, or `None`) and `body` (the decoded answer). |
| `RequestTimeoutError` | No answer within `timeout`. |
| `NetworkError` | The connection failed: DNS, refused, reset or TLS. |
| `DecodeError` | The answer could not be read as JSON. |

```python
from mygeocode import ApiError, MyGeocodeError

try:
    client.forward("Brandenburg Gate, Berlin")
except ApiError as error:
    print(error.status, error.code, error.message)
except MyGeocodeError as error:
    print("Could not reach the API:", error)
```

The [errors page](https://www.mygeocode.com/docs/errors/) lists every error code.

## Retries

The client retries on its own, up to `max_retries` times (default 2):

- **429** (too many requests): waits for `Retry-After`, or until `X-Quota-Reset`. If that is longer than
  `max_retry_wait` (default 60 seconds), for example when the day's free requests are gone, it raises the `ApiError`
  straight away instead of waiting.
- **500**: tries once more after one second.
- **503**: waits for `Retry-After`, or 1, 2 and then 4 seconds.
- **Timeouts and connection errors**: retried with the same 1, 2, 4 second pattern for GET requests. The POST batch
  calls are not retried after a connection error, so a batch is never charged twice.

Other errors are raised at once.

## Configuration

All options are optional:

```python
client = Client(
    "YOUR_KEY",                               # default: MYGEOCODE_KEY, else no key
    base_url="https://api.mygeocode.com/v1",
    timeout=10,                               # seconds per request
    max_retries=2,
    max_retry_wait=60,                        # seconds
    lang="en",
)
```

`transport`, `sleep` and `clock` replace the HTTP layer, the wait and the clock the retry logic uses. They are meant
for tests, see below. `Client` also works as a context manager (`with Client() as client:`), and `AsyncClient` with
`async with`.

## Testing your code (transport hook)

The client sends every request through its `transport`: any callable that takes an `HttpRequest` (`method`, `url`,
`headers`, `body`, `timeout`) and returns an `HttpResponse`. Give it your own to test code that uses the SDK without
touching the network:

```python
import json

from mygeocode import Client, HttpResponse


def canned(request):
    body = {
        "status": "ok",
        "lat": 48.8584,
        "lon": 2.2945,
        "result": {"formatted": "5 Avenue Anatole France, 75007 Paris, France", "lat": 48.858821, "lon": 2.294596},
    }
    return HttpResponse(200, {"Content-Type": "application/json"}, json.dumps(body).encode("utf-8"))


client = Client(transport=canned, sleep=lambda seconds: None)  # no real waiting in retry tests
print(client.reverse(48.8584, 2.2945).result.formatted)
```

The same hook plugs in any HTTP library, such as `requests` with your own session and proxy settings. Raise
`mygeocode.RequestTimeoutError` for a timeout and `mygeocode.NetworkError` for any other failure to get an answer;
return every HTTP status as an `HttpResponse`.

### Running the SDK's own tests

The tests need nothing but Python, so the same suite runs on every version from 3.6 up. It answers from real recorded
API responses and never calls the API:

```bash
python tests/run.py
```

Any warning counts as a failed test.

## Requirements

- Python 3.6 or newer. Tested on 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15 and 3.16 (alpha), with every
  warning treated as a failure.
- Nothing else: only the standard library.

## Links

- [API documentation](https://www.mygeocode.com/docs/)
- [Pricing and free tier](https://www.mygeocode.com/pricing/)
- [Dashboard and API keys](https://www.mygeocode.com/dashboard)
- [Issues](https://github.com/mygeocode/mygeocode-python/issues)
- Support: [support@mygeocode.com](mailto:support@mygeocode.com)

## Licence

MIT. See [LICENSE](LICENSE).

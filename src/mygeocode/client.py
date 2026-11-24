"""The client. ``async_client.py`` holds the same class for asyncio; keep the two in step."""

import time
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Optional, Union

from . import _endpoints as ep
from . import models as m
from ._core import DEFAULT_BASE_URL, Options, backoff, build_request, parse_response, retry_wait, urllib_transport
from .errors import NetworkError, RequestTimeoutError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from types import TracebackType

    from ._core import Transport

    Params = Optional[Mapping[str, Any]]
    Points = Iterable[Sequence[float]]
    Strings = Union[str, Sequence[str]]
    Box = Union[str, Sequence[float]]


class Client(object):
    """Client for the My Geocode API.

    Every option is optional. ``key`` defaults to the ``MYGEOCODE_KEY`` environment variable; with neither, no key is
    sent and the network's free requests apply. ``lang`` defaults to English and is sent on every endpoint that takes
    it. ``transport`` replaces the default ``urllib`` transport: any callable that takes an ``HttpRequest`` and returns
    an ``HttpResponse``. ``sleep`` and ``clock`` replace the retry wait and the clock, for tests.
    """

    def __init__(
        self,
        key: Optional[str] = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 10.0,
        max_retries: int = 2,
        max_retry_wait: float = 60.0,
        lang: Optional[str] = None,
        transport: "Optional[Transport]" = None,
        sleep: "Optional[Callable[[float], None]]" = None,
        clock: "Optional[Callable[[], float]]" = None
    ) -> None:
        self._opts = Options(key, base_url, timeout, max_retries, max_retry_wait, lang, clock)
        self._transport = transport or urllib_transport  # type: Transport
        self._sleep = sleep or time.sleep  # type: Callable[[float], None]

    def __enter__(self) -> "Client":
        return self

    def __exit__(
        self,
        exc_type: "Optional[type[BaseException]]",
        exc: Optional[BaseException],
        tb: "Optional[TracebackType]",
    ) -> None:
        self.close()

    def close(self) -> None:
        """Nothing to release (each request opens and closes its own connection); there for ``with`` blocks."""

    # ---- helpers ----------------------------------------------------------------------------------------------

    def _lang(self, lang: Optional[str]) -> str:
        return lang if lang is not None else self._opts.lang

    def _language(self, lang: Optional[str], language: Optional[str]) -> Optional[str]:
        """Timezone's ``language``: only when the caller chose one, here or on the client (the API answers English)."""
        chosen = lang if lang is not None else language
        if chosen is not None:
            return chosen
        return self._opts.lang if self._opts.lang_set else None

    def _call(self, spec: ep.Spec) -> Any:
        opts = self._opts
        request = build_request(opts, spec.method, spec.path, spec.params, spec.body)
        attempt = 0
        retried_500 = False
        while True:
            try:
                response = self._transport(request)
            except (NetworkError, RequestTimeoutError):
                if spec.method == "GET" and attempt < opts.max_retries:
                    self._sleep(backoff(attempt))
                    attempt += 1
                    continue
                raise
            if response.status in (429, 500, 503):
                wait = retry_wait(opts, response, attempt, retried_500)
                if wait is not None:
                    retried_500 = retried_500 or response.status == 500
                    self._sleep(wait)
                    attempt += 1
                    continue
            data, meta = parse_response(response, opts.clock)
            return spec.parse(data, meta)

    # ---- the 16 endpoint methods --------------------------------------------------------------------------------

    def forward(
        self,
        query: Optional[str] = None,
        *,
        street: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postcode: Optional[str] = None,
        country: Optional[str] = None,
        place_id: Optional[str] = None,
        limit: Optional[int] = None,
        countries: "Optional[Strings]" = None,
        bounds: "Optional[Box]" = None,
        strict: bool = False,
        proximity: "Optional[Box]" = None,
        types: "Optional[Strings]" = None,
        lang: Optional[str] = None,
        annotations: bool = False,
        timezone: bool = False,
        elevation: bool = False,
        wikidata: bool = False,
        country_info: bool = False,
        codes: bool = False,
        sun: bool = False,
        regions: bool = False,
        districts: bool = False,
        census: bool = False,
        demographics: bool = False,
        road: bool = False,
        site: bool = False,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.ForwardResponse:
        """Text, structured address fields or a ``place_id`` to coordinates."""
        values = dict(
            q=query, street=street, city=city, state=state, postcode=postcode, country=country, place_id=place_id,
            limit=limit, countries=countries, bounds=bounds, strict=strict, proximity=proximity, types=types,
            lang=self._lang(lang), annotations=annotations, timezone=timezone, elevation=elevation,
            wikidata=wikidata, country_info=country_info, codes=codes, sun=sun, regions=regions,
            districts=districts, census=census, demographics=demographics, road=road, site=site, pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.get("forward", values, params, m.ForwardResponse))  # type: m.ForwardResponse
        return result

    def reverse(
        self,
        lat: float,
        lon: float,
        *,
        level: Optional[str] = None,
        radius: Optional[int] = None,
        lang: Optional[str] = None,
        boundaries: bool = False,
        annotations: bool = False,
        timezone: bool = False,
        elevation: bool = False,
        wikidata: bool = False,
        country_info: bool = False,
        codes: bool = False,
        sun: bool = False,
        regions: bool = False,
        districts: bool = False,
        census: bool = False,
        demographics: bool = False,
        road: bool = False,
        site: bool = False,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.ReverseResponse:
        """A point to the nearest address. ``result`` is ``None`` when nothing is within ``radius``."""
        values = dict(
            lat=lat, lon=lon, level=level, radius=radius, lang=self._lang(lang), boundaries=boundaries,
            annotations=annotations, timezone=timezone, elevation=elevation, wikidata=wikidata,
            country_info=country_info, codes=codes, sun=sun, regions=regions, districts=districts, census=census,
            demographics=demographics, road=road, site=site, pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.get("reverse", values, params, m.ReverseResponse))  # type: m.ReverseResponse
        return result

    def autocomplete(
        self,
        query: str,
        *,
        limit: Optional[int] = None,
        countries: "Optional[Strings]" = None,
        proximity: "Optional[Box]" = None,
        bounds: "Optional[Box]" = None,
        strict: bool = False,
        types: "Optional[Strings]" = None,
        lang: Optional[str] = None,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.AutocompleteResponse:
        """Address suggestions for what someone has typed so far."""
        values = dict(
            q=query, limit=limit, countries=countries, proximity=proximity, bounds=bounds, strict=strict,
            types=types, lang=self._lang(lang), pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.get("autocomplete", values, params, m.AutocompleteResponse))  # type: m.AutocompleteResponse
        return result

    def ip(
        self, address: Optional[str] = None, *, elevation: bool = False, pretty: bool = False, params: "Params" = None
    ) -> m.IpInfo:
        """An IPv4 or IPv6 address; without one, the address the request came from."""
        values = dict(ip=address, elevation=elevation, pretty=pretty)
        result = self._call(ep.get("ip", values, params, m.IpInfo))  # type: m.IpInfo
        return result

    def ipv4(
        self, address: Optional[str] = None, *, elevation: bool = False, pretty: bool = False, params: "Params" = None
    ) -> m.IpInfo:
        """An IPv4 address; without one, the address the request came from."""
        values = dict(ip=address, elevation=elevation, pretty=pretty)
        result = self._call(ep.get("ipv4", values, params, m.IpInfo))  # type: m.IpInfo
        return result

    def ipv6(
        self, address: Optional[str] = None, *, elevation: bool = False, pretty: bool = False, params: "Params" = None
    ) -> m.IpInfo:
        """An IPv6 address; without one, the address the request came from."""
        values = dict(ip=address, elevation=elevation, pretty=pretty)
        result = self._call(ep.get("ipv6", values, params, m.IpInfo))  # type: m.IpInfo
        return result

    def timezone(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        *,
        tz: Optional[str] = None,
        timestamp: Optional[int] = None,
        lang: Optional[str] = None,
        language: Optional[str] = None,
        locations: "Optional[Union[str, Points]]" = None,
        path: "Optional[Union[str, Points]]" = None,
        samples: Optional[int] = None,
        bounds: "Optional[Box]" = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.TimezoneInfo:
        """Zone, offset and local time for a point, or for a zone id with ``tz`` (``lat`` and ``lon`` left out).

        ``locations``, ``path`` with ``samples`` or ``bounds`` with ``rows`` and ``cols`` ask for several points at
        once; the answer then also has them under ``raw["results"]`` (``timezone_batch`` reads them for you).
        """
        values = dict(
            lat=lat, lon=lon, tz=tz, timestamp=timestamp, language=self._language(lang, language),
            locations=ep.points_param(locations), path=ep.points_param(path), samples=samples, bounds=bounds,
            rows=rows, cols=cols, pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.get("timezone", values, params, m.TimezoneInfo))  # type: m.TimezoneInfo
        return result

    def elevation(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        *,
        locations: "Optional[Union[str, Points]]" = None,
        path: "Optional[Union[str, Points]]" = None,
        samples: Optional[int] = None,
        bounds: "Optional[Box]" = None,
        rows: Optional[int] = None,
        cols: Optional[int] = None,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.ElevationResponse:
        """Height of a point, or of several points with ``locations``, a ``path`` with ``samples``, or a grid."""
        values = dict(
            lat=lat, lon=lon, locations=ep.points_param(locations), path=ep.points_param(path), samples=samples,
            bounds=bounds, rows=rows, cols=cols, pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.elevation(values, params))  # type: m.ElevationResponse
        return result

    def postcode(
        self, code: str, *, country: Optional[str] = None, pretty: bool = False, params: "Params" = None
    ) -> m.PostcodeResponse:
        """A postal code to every place that uses it. ``country`` (ISO alpha-2) narrows it to one country."""
        values = dict(code=code, country=country, pretty=pretty)
        result = self._call(ep.get("postcode", values, params, m.PostcodeResponse))  # type: m.PostcodeResponse
        return result

    def forward_batch(
        self,
        queries: "Iterable[str]",
        *,
        limit: Optional[int] = None,
        countries: "Optional[Strings]" = None,
        bounds: "Optional[Box]" = None,
        strict: bool = False,
        proximity: "Optional[Box]" = None,
        types: "Optional[Strings]" = None,
        lang: Optional[str] = None,
        annotations: bool = False,
        timezone: bool = False,
        elevation: bool = False,
        wikidata: bool = False,
        country_info: bool = False,
        codes: bool = False,
        sun: bool = False,
        regions: bool = False,
        districts: bool = False,
        census: bool = False,
        demographics: bool = False,
        road: bool = False,
        site: bool = False,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.ForwardBatchResponse:
        """Up to 100 searches in one request (each counts as one). The options apply to every search."""
        values = dict(
            limit=limit, countries=countries, bounds=bounds, strict=strict, proximity=proximity, types=types,
            lang=self._lang(lang), annotations=annotations, timezone=timezone, elevation=elevation,
            wikidata=wikidata, country_info=country_info, codes=codes, sun=sun, regions=regions,
            districts=districts, census=census, demographics=demographics, road=road, site=site, pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.forward_batch(queries, values, params))  # type: m.ForwardBatchResponse
        return result

    def reverse_batch(
        self,
        points: "Points",
        *,
        level: Optional[str] = None,
        radius: Optional[int] = None,
        lang: Optional[str] = None,
        boundaries: bool = False,
        annotations: bool = False,
        timezone: bool = False,
        elevation: bool = False,
        wikidata: bool = False,
        country_info: bool = False,
        codes: bool = False,
        sun: bool = False,
        regions: bool = False,
        districts: bool = False,
        census: bool = False,
        demographics: bool = False,
        road: bool = False,
        site: bool = False,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.ReverseBatchResponse:
        """Up to 100 ``(lat, lon)`` points in one request (each counts as one). The options apply to every point."""
        values = dict(
            level=level, radius=radius, lang=self._lang(lang), boundaries=boundaries, annotations=annotations,
            timezone=timezone, elevation=elevation, wikidata=wikidata, country_info=country_info, codes=codes,
            sun=sun, regions=regions, districts=districts, census=census, demographics=demographics, road=road,
            site=site, pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.reverse_batch(points, values, params))  # type: m.ReverseBatchResponse
        return result

    def ip_batch(
        self, addresses: "Iterable[str]", *, elevation: bool = False, pretty: bool = False, params: "Params" = None
    ) -> m.IpBatchResponse:
        """Up to 100 addresses of either version in one request."""
        values = dict(ips=",".join(addresses), elevation=elevation, pretty=pretty)
        result = self._call(ep.get("ip", values, params, m.IpBatchResponse))  # type: m.IpBatchResponse
        return result

    def ipv4_batch(
        self, addresses: "Iterable[str]", *, elevation: bool = False, pretty: bool = False, params: "Params" = None
    ) -> m.IpBatchResponse:
        """Up to 100 IPv4 addresses in one request."""
        values = dict(ips=",".join(addresses), elevation=elevation, pretty=pretty)
        result = self._call(ep.get("ipv4", values, params, m.IpBatchResponse))  # type: m.IpBatchResponse
        return result

    def ipv6_batch(
        self, addresses: "Iterable[str]", *, elevation: bool = False, pretty: bool = False, params: "Params" = None
    ) -> m.IpBatchResponse:
        """Up to 100 IPv6 addresses in one request."""
        values = dict(ips=",".join(addresses), elevation=elevation, pretty=pretty)
        result = self._call(ep.get("ipv6", values, params, m.IpBatchResponse))  # type: m.IpBatchResponse
        return result

    def timezone_batch(
        self,
        points: "Union[str, Points]",
        *,
        timestamp: Optional[int] = None,
        lang: Optional[str] = None,
        language: Optional[str] = None,
        pretty: bool = False,
        params: "Params" = None
    ) -> m.TimezoneBatchResponse:
        """Timezones of up to 100 ``(lat, lon)`` points (or an ``enc:`` polyline string)."""
        values = dict(
            locations=ep.points_param(points), timestamp=timestamp, language=self._language(lang, language),
            pretty=pretty,
        )  # fmt: skip
        result = self._call(ep.get("timezone", values, params, m.TimezoneBatchResponse))  # type: m.TimezoneBatchResponse
        return result

    def elevation_batch(self, points: "Points", *, pretty: bool = False, params: "Params" = None) -> m.ElevationResponse:
        """Heights of up to 100 ``(lat, lon)`` points, sent as a POST body."""
        result = self._call(ep.elevation_batch(points, dict(pretty=pretty), params))  # type: m.ElevationResponse
        return result

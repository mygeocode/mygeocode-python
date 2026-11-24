"""Result objects. Attribute names are the API's own field names.

Every field can be ``None``: the API never drops a field this library reads, it sends ``null`` instead, and a field it
did not send at all reads as ``None`` too. A list that arrives as ``null`` reads as an empty list. ``raw`` always holds
the decoded JSON object, so fields the library does not know yet are still there.
"""

from collections.abc import Mapping
from typing import Any, Optional, TypeVar

M = TypeVar("M", bound="Model")


class Meta(object):
    """Figures from the response headers; ``None`` when a header was not sent."""

    request_id = None  # type: Optional[str]
    quota_limit = None  # type: Optional[int]
    quota_used = None  # type: Optional[int]
    quota_free_remaining = None  # type: Optional[int]
    quota_reset = None  # type: Optional[int]
    credits_remaining = None  # type: Optional[int]

    def __init__(
        self,
        request_id: Optional[str] = None,
        quota_limit: Optional[int] = None,
        quota_used: Optional[int] = None,
        quota_free_remaining: Optional[int] = None,
        quota_reset: Optional[int] = None,
        credits_remaining: Optional[int] = None,
    ) -> None:
        self.request_id = request_id
        self.quota_limit = quota_limit
        self.quota_used = quota_used
        self.quota_free_remaining = quota_free_remaining
        self.quota_reset = quota_reset
        self.credits_remaining = credits_remaining

    @classmethod
    def from_headers(cls, headers: "Mapping[str, str]") -> "Meta":
        def number(name: str) -> Optional[int]:
            value = headers.get(name)
            if value is None:
                return None
            try:
                return int(float(value))
            except ValueError:
                return None

        return cls(
            request_id=headers.get("X-Request-Id"),
            quota_limit=number("X-Quota-Limit"),
            quota_used=number("X-Quota-Used"),
            quota_free_remaining=number("X-Quota-Free-Remaining"),
            quota_reset=number("X-Quota-Reset"),
            credits_remaining=number("X-Credits-Remaining"),
        )

    def __repr__(self) -> str:
        return "Meta(request_id={!r}, quota_free_remaining={!r})".format(self.request_id, self.quota_free_remaining)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Meta) and vars(self) == vars(other)

    def __ne__(self, other: object) -> bool:
        return not self == other

    __hash__ = None  # type: ignore[assignment]


class Model(object):
    """Base of every result: builds itself from a decoded JSON object.

    ``_fields`` lists the API fields in order, ``_objects`` maps a field to the class of the object it holds, ``_lists``
    maps a field to the class of its entries (``None`` for plain values), ``_text`` names fields whose values are
    always text (a number that arrives there is turned into a string).
    """

    _fields = ()  # type: tuple[str, ...]
    _objects = {}  # type: dict[str, type[Model]]
    _lists = {}  # type: dict[str, Optional[type[Model]]]
    _text = ()  # type: tuple[str, ...]
    _has_meta = False

    raw = {}  # type: dict[str, Any]

    def __init__(self, **values: Any) -> None:
        for name in self._fields:
            setattr(self, name, values.get(name, [] if name in self._lists else None))
        self.raw = values.get("raw") or {}
        if self._has_meta:
            setattr(self, "meta", values.get("meta"))

    @classmethod
    def from_dict(cls: "type[M]", data: "Mapping[str, Any]", meta: Optional[Meta] = None) -> M:
        obj = cls.__new__(cls)
        for name in cls._fields:
            value = data.get(name)
            if name in cls._lists:
                entry_class = cls._lists[name]
                if not isinstance(value, list):
                    value = []
                elif entry_class is not None:
                    value = [entry_class.from_dict(v) if isinstance(v, Mapping) else None for v in value]
            elif name in cls._objects:
                value = cls._objects[name].from_dict(value) if isinstance(value, Mapping) else None
            elif name in cls._text and value is not None and not isinstance(value, str):
                value = str(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
            setattr(obj, name, value)
        obj.raw = dict(data)
        if cls._has_meta:
            setattr(obj, "meta", meta)
        return obj

    def __repr__(self) -> str:
        shown = ", ".join("{}={!r}".format(n, getattr(self, n)) for n in self._fields[:4])
        return "{}({})".format(type(self).__name__, shown)

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        return all(getattr(self, n) == getattr(other, n) for n in self._fields)

    def __ne__(self, other: object) -> bool:
        return not self == other

    __hash__ = None  # type: ignore[assignment]


class Bounds(Model):
    """Bounding box of a place."""

    _fields = ("north", "south", "east", "west")
    north = None  # type: Optional[float]
    south = None  # type: Optional[float]
    east = None  # type: Optional[float]
    west = None  # type: Optional[float]


class Components(Model):
    """Address parts of a place."""

    _fields = (
        "poi", "building", "unit", "level", "house_number", "road", "lot", "suburb", "municipality", "city",
        "county", "state", "state_code", "postcode", "country", "country_code", "official_name",
    )  # fmt: skip
    _text = _fields
    poi = None  # type: Optional[str]
    building = None  # type: Optional[str]
    unit = None  # type: Optional[str]
    level = None  # type: Optional[str]
    house_number = None  # type: Optional[str]
    road = None  # type: Optional[str]
    lot = None  # type: Optional[str]
    suburb = None  # type: Optional[str]
    municipality = None  # type: Optional[str]
    city = None  # type: Optional[str]
    county = None  # type: Optional[str]
    state = None  # type: Optional[str]
    state_code = None  # type: Optional[str]
    postcode = None  # type: Optional[str]
    country = None  # type: Optional[str]
    country_code = None  # type: Optional[str]
    official_name = None  # type: Optional[str]


class Place(Model):
    """One forward or reverse result. The extra blocks (``timezone``, ``codes`` ...) stay plain dicts."""

    _fields = (
        "formatted", "lat", "lon", "type", "precision", "confidence", "place_id", "components", "bounds",
        "distance_m", "formatted_place", "place", "parcel", "codes", "population", "un_locode", "timezone",
        "elevation_m", "wikidata", "country_info", "sun", "regions", "districts", "census", "demographics", "road",
        "intersection", "site",
    )  # fmt: skip
    _objects = {"components": Components, "bounds": Bounds}
    formatted = None  # type: Optional[str]
    lat = None  # type: Optional[float]
    lon = None  # type: Optional[float]
    type = None  # type: Optional[str]
    precision = None  # type: Optional[str]
    confidence = None  # type: Optional[float]
    place_id = None  # type: Optional[str]
    components = None  # type: Optional[Components]
    bounds = None  # type: Optional[Bounds]
    distance_m = None  # type: Optional[int]
    formatted_place = None  # type: Optional[str]
    place = None  # type: Optional[dict[str, Any]]
    parcel = None  # type: Optional[dict[str, Any]]
    codes = None  # type: Optional[dict[str, Any]]
    population = None  # type: Optional[int]
    un_locode = None  # type: Optional[dict[str, Any]]
    timezone = None  # type: Optional[dict[str, Any]]
    elevation_m = None  # type: Optional[float]
    wikidata = None  # type: Optional[str]
    country_info = None  # type: Optional[dict[str, Any]]
    sun = None  # type: Optional[dict[str, Any]]
    regions = None  # type: Optional[dict[str, Any]]
    districts = None  # type: Optional[dict[str, Any]]
    census = None  # type: Optional[dict[str, Any]]
    demographics = None  # type: Optional[dict[str, Any]]
    road = None  # type: Optional[dict[str, Any]]
    intersection = None  # type: Optional[dict[str, Any]]
    site = None  # type: Optional[dict[str, Any]]


class ForwardResponse(Model):
    """Answer of ``forward``: ``results`` holds the matches, best first; empty when nothing matched."""

    _fields = ("status", "query", "results")
    _lists = {"results": Place}
    _has_meta = True
    status = None  # type: Optional[str]
    query = None  # type: Optional[str]
    results = []  # type: list[Place]
    meta = None  # type: Optional[Meta]


class ForwardBatchEntry(Model):
    """One search of a ``forward_batch``: the ``query`` and its ``results``."""

    _fields = ("query", "results")
    _lists = {"results": Place}
    query = None  # type: Optional[str]
    results = []  # type: list[Place]


class ForwardBatchResponse(Model):
    """Answer of ``forward_batch``: one entry per search, in the order they were sent."""

    _fields = ("status", "results")
    _lists = {"results": ForwardBatchEntry}
    _has_meta = True
    status = None  # type: Optional[str]
    results = []  # type: list[ForwardBatchEntry]
    meta = None  # type: Optional[Meta]


class ReverseResponse(Model):
    """Answer of ``reverse`` (and one entry of ``reverse_batch``): ``result`` is ``None`` when nothing is in range."""

    _fields = ("status", "lat", "lon", "result", "boundaries")
    _objects = {"result": Place}
    _has_meta = True
    status = None  # type: Optional[str]
    lat = None  # type: Optional[float]
    lon = None  # type: Optional[float]
    result = None  # type: Optional[Place]
    boundaries = None  # type: Optional[dict[str, Any]]
    meta = None  # type: Optional[Meta]


class ReverseBatchResponse(Model):
    """Answer of ``reverse_batch``: one ``ReverseResponse`` per point, in the order they were sent."""

    _fields = ("status", "results")
    _lists = {"results": ReverseResponse}
    _has_meta = True
    status = None  # type: Optional[str]
    results = []  # type: list[ReverseResponse]
    meta = None  # type: Optional[Meta]


class Suggestion(Model):
    """One autocomplete suggestion."""

    _fields = ("text", "lat", "lon", "type", "precision", "place_id")
    text = None  # type: Optional[str]
    lat = None  # type: Optional[float]
    lon = None  # type: Optional[float]
    type = None  # type: Optional[str]
    precision = None  # type: Optional[str]
    place_id = None  # type: Optional[str]


class AutocompleteResponse(Model):
    """Answer of ``autocomplete``."""

    _fields = ("status", "query", "suggestions")
    _lists = {"suggestions": Suggestion}
    _has_meta = True
    status = None  # type: Optional[str]
    query = None  # type: Optional[str]
    suggestions = []  # type: list[Suggestion]
    meta = None  # type: Optional[Meta]


class IpInfo(Model):
    """An IPv4 or IPv6 lookup. In a batch, an address the API cannot read has ``status == "error"`` and ``error``."""

    _fields = (
        "status", "ip", "version", "found", "prefix", "country", "country_code", "continent", "continent_code",
        "region", "region_code", "city", "postcode", "lat", "lon", "elevation_m", "timezone", "utc_offset",
        "utc_offset_seconds", "is_eu", "asn", "as_name", "org", "usage_type", "registry", "allocated", "tags",
        "is_anycast", "is_satellite", "is_datacenter", "is_proxy", "is_vpn_provider", "is_tor", "crawler",
        "is_private", "reason", "abuse_email", "threat", "updated_at", "error",
    )  # fmt: skip
    _lists = {"tags": None}
    _has_meta = True
    status = None  # type: Optional[str]
    ip = None  # type: Optional[str]
    version = None  # type: Optional[int]
    found = None  # type: Optional[bool]
    prefix = None  # type: Optional[str]
    country = None  # type: Optional[str]
    country_code = None  # type: Optional[str]
    continent = None  # type: Optional[str]
    continent_code = None  # type: Optional[str]
    region = None  # type: Optional[str]
    region_code = None  # type: Optional[str]
    city = None  # type: Optional[str]
    postcode = None  # type: Optional[str]
    lat = None  # type: Optional[float]
    lon = None  # type: Optional[float]
    elevation_m = None  # type: Optional[float]
    timezone = None  # type: Optional[str]
    utc_offset = None  # type: Optional[str]
    utc_offset_seconds = None  # type: Optional[int]
    is_eu = None  # type: Optional[bool]
    asn = None  # type: Optional[int]
    as_name = None  # type: Optional[str]
    org = None  # type: Optional[str]
    usage_type = None  # type: Optional[str]
    registry = None  # type: Optional[str]
    allocated = None  # type: Optional[str]
    tags = []  # type: list[str]
    is_anycast = None  # type: Optional[bool]
    is_satellite = None  # type: Optional[bool]
    is_datacenter = None  # type: Optional[bool]
    is_proxy = None  # type: Optional[bool]
    is_vpn_provider = None  # type: Optional[bool]
    is_tor = None  # type: Optional[bool]
    crawler = None  # type: Optional[dict[str, Any]]
    is_private = None  # type: Optional[bool]
    reason = None  # type: Optional[str]
    abuse_email = None  # type: Optional[str]
    threat = None  # type: Optional[dict[str, Any]]
    updated_at = None  # type: Optional[str]
    error = None  # type: Optional[dict[str, Any]]
    meta = None  # type: Optional[Meta]


class IpBatchResponse(Model):
    """Answer of ``ip_batch``, ``ipv4_batch`` and ``ipv6_batch``: one ``IpInfo`` per address, in order."""

    _fields = ("status", "results")
    _lists = {"results": IpInfo}
    _has_meta = True
    status = None  # type: Optional[str]
    results = []  # type: list[IpInfo]
    meta = None  # type: Optional[Meta]


class TimezoneTransition(Model):
    """The next change of a zone's offset."""

    _fields = ("timestamp", "utc_offset", "utc_offset_seconds", "dst", "abbreviation")
    timestamp = None  # type: Optional[int]
    utc_offset = None  # type: Optional[str]
    utc_offset_seconds = None  # type: Optional[int]
    dst = None  # type: Optional[bool]
    abbreviation = None  # type: Optional[str]


class TimezoneInfo(Model):
    """Answer of ``timezone`` (and one entry of ``timezone_batch``)."""

    _fields = (
        "status", "lat", "lon", "timezone", "name", "abbreviation", "utc_offset", "utc_offset_seconds",
        "raw_offset_seconds", "dst", "dst_offset_seconds", "timestamp", "local_time", "country_code", "is_ocean",
        "windows_timezone", "next_transition",
    )  # fmt: skip
    _objects = {"next_transition": TimezoneTransition}
    _has_meta = True
    status = None  # type: Optional[str]
    lat = None  # type: Optional[float]
    lon = None  # type: Optional[float]
    timezone = None  # type: Optional[str]
    name = None  # type: Optional[str]
    abbreviation = None  # type: Optional[str]
    utc_offset = None  # type: Optional[str]
    utc_offset_seconds = None  # type: Optional[int]
    raw_offset_seconds = None  # type: Optional[int]
    dst = None  # type: Optional[bool]
    dst_offset_seconds = None  # type: Optional[int]
    timestamp = None  # type: Optional[int]
    local_time = None  # type: Optional[str]
    country_code = None  # type: Optional[str]
    is_ocean = None  # type: Optional[bool]
    windows_timezone = None  # type: Optional[str]
    next_transition = None  # type: Optional[TimezoneTransition]
    meta = None  # type: Optional[Meta]


class TimezoneBatchResponse(Model):
    """Answer of ``timezone_batch``: one ``TimezoneInfo`` per point, in order."""

    _fields = ("status", "timestamp", "results")
    _lists = {"results": TimezoneInfo}
    _has_meta = True
    status = None  # type: Optional[str]
    timestamp = None  # type: Optional[int]
    results = []  # type: list[TimezoneInfo]
    meta = None  # type: Optional[Meta]


class ElevationPoint(Model):
    """Height of one point in metres above sea level (negative for the sea floor)."""

    _fields = ("lat", "lon", "elevation_m", "resolution_m")
    lat = None  # type: Optional[float]
    lon = None  # type: Optional[float]
    elevation_m = None  # type: Optional[float]
    resolution_m = None  # type: Optional[float]


class ElevationResponse(Model):
    """Answer of ``elevation`` and ``elevation_batch``: one ``ElevationPoint`` per point, in order."""

    _fields = ("status", "results")
    _lists = {"results": ElevationPoint}
    _has_meta = True
    status = None  # type: Optional[str]
    results = []  # type: list[ElevationPoint]
    meta = None  # type: Optional[Meta]


class PostcodePlace(Model):
    """One place that uses a postal code."""

    _fields = ("postcode", "place", "region", "region_code", "country", "country_code", "lat", "lon")
    _text = ("postcode",)
    postcode = None  # type: Optional[str]
    place = None  # type: Optional[str]
    region = None  # type: Optional[str]
    region_code = None  # type: Optional[str]
    country = None  # type: Optional[str]
    country_code = None  # type: Optional[str]
    lat = None  # type: Optional[float]
    lon = None  # type: Optional[float]


class PostcodeResponse(Model):
    """Answer of ``postcode``: every place that uses the code."""

    _fields = ("status", "postcode", "country_code", "results")
    _lists = {"results": PostcodePlace}
    _text = ("postcode",)
    _has_meta = True
    status = None  # type: Optional[str]
    postcode = None  # type: Optional[str]
    country_code = None  # type: Optional[str]
    results = []  # type: list[PostcodePlace]
    meta = None  # type: Optional[Meta]

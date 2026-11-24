"""Shared by the sync and async clients: options, transport, request building, parameter encoding, parsing, retries.

Written for every Python from 3.6: no dataclasses, no ``from __future__`` imports, and annotations that need a newer
Python are quoted so they are never evaluated.
"""

import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping
from http.client import HTTPException
from typing import TYPE_CHECKING, Any, Optional, Union

from ._version import __version__
from .errors import ApiError, DecodeError, NetworkError, RequestTimeoutError
from .models import Meta

DEFAULT_BASE_URL = "https://api.mygeocode.com/v1"
USER_AGENT = "mygeocode-python/{} (+https://www.mygeocode.com/sdks/)".format(__version__)

# Before 3.10 a socket timeout is socket.timeout, which is not a TimeoutError; from 3.10 it is TimeoutError itself
# (socket.timeout only remains as an alias there), so the alias is only touched on the versions that need it.
if sys.version_info >= (3, 10):
    _TIMEOUTS = (TimeoutError,)  # type: tuple[type[BaseException], ...]
else:  # pragma: no cover - depends on the running version
    _TIMEOUTS = (TimeoutError, socket.timeout)


class Options(object):
    """The client settings, shared by both clients."""

    def __init__(
        self,
        key: Optional[str],
        base_url: str,
        timeout: float,
        max_retries: int,
        max_retry_wait: float,
        lang: Optional[str],
        clock: "Optional[Callable[[], float]]",
    ) -> None:
        if key is None:
            key = os.environ.get("MYGEOCODE_KEY")
        self.key = key.strip() if key and key.strip() else None  # type: Optional[str]
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.max_retries = max(0, int(max_retries))
        self.max_retry_wait = float(max_retry_wait)
        self.lang = lang if lang is not None else "en"
        self.lang_set = lang is not None
        self.clock = clock or time.time  # type: Callable[[], float]

    def headers(self) -> "dict[str, str]":
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if self.key:
            headers["X-API-Key"] = self.key
        return headers


# ---- transport (standard library only) --------------------------------------------------------------------------

if TYPE_CHECKING:
    _HeadersBase = Mapping[str, str]
else:
    _HeadersBase = Mapping


class Headers(_HeadersBase):
    """Response headers, read-only, names matched without regard to case."""

    def __init__(self, items: "Union[Mapping[str, str], Iterable[tuple[str, str]]]" = ()) -> None:
        pairs = items.items() if isinstance(items, Mapping) else items
        self._data = {str(k).lower(): str(v) for k, v in pairs}  # type: dict[str, str]

    def __getitem__(self, name: str) -> str:
        return self._data[name.lower()]

    def __iter__(self) -> "Iterator[str]":
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


class HttpRequest(object):
    """What the client asks a transport to send."""

    def __init__(self, method: str, url: str, headers: "dict[str, str]", body: Optional[bytes], timeout: float) -> None:
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        self.timeout = timeout

    def __repr__(self) -> str:
        return "HttpRequest({!r}, {!r})".format(self.method, self.url)


class HttpResponse(object):
    """What a transport returns. Any HTTP status is a response; only a failure to get one raises."""

    def __init__(self, status: int, headers: "Union[Headers, Mapping[str, str]]", body: bytes) -> None:
        self.status = int(status)
        self.headers = headers if isinstance(headers, Headers) else Headers(headers)
        self.body = body

    @classmethod
    def make(cls, status: int, body: bytes = b"", headers: "Optional[Mapping[str, str]]" = None) -> "HttpResponse":
        return cls(status, Headers(headers or {}), body)

    def __repr__(self) -> str:
        return "HttpResponse({!r})".format(self.status)



def urllib_transport(request: HttpRequest) -> HttpResponse:
    """The default transport: ``urllib.request`` with the system's certificate store.

    Raises ``RequestTimeoutError`` or ``NetworkError`` when no answer arrives; any HTTP status is returned.
    """
    req = urllib.request.Request(request.url, data=request.body, headers=request.headers, method=request.method)
    try:
        with urllib.request.urlopen(req, timeout=request.timeout) as resp:
            return HttpResponse(resp.status, Headers(resp.getheaders()), resp.read())
    except urllib.error.HTTPError as exc:
        try:
            return HttpResponse(exc.code, Headers(exc.headers.items()), exc.read())
        finally:
            exc.close()
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, _TIMEOUTS):
            raise RequestTimeoutError("Request timed out after {} s".format(request.timeout)) from exc
        raise NetworkError("Network error: {}".format(exc.reason)) from exc
    except _TIMEOUTS as exc:
        raise RequestTimeoutError("Request timed out after {} s".format(request.timeout)) from exc
    except (OSError, HTTPException) as exc:
        raise NetworkError("Network error: {}".format(exc)) from exc


def build_request(opts: Options, method: str, path: str, params: "Mapping[str, str]", body: Any) -> HttpRequest:
    url = "{}/{}".format(opts.base_url, path.lstrip("/"))
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = opts.headers()
    data = None  # type: Optional[bytes]
    if body is not None:
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return HttpRequest(method, url, headers, data, opts.timeout)


# ---- parameter encoding -----------------------------------------------------------------------------------------


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return repr(value)
    return str(value)


def _join(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ",".join(_scalar(v) for v in value)
    return _scalar(value)


def encode_params(values: "Mapping[str, Any]", extra: "Optional[Mapping[str, Any]]" = None) -> "dict[str, str]":
    """Drop ``None`` and ``False``, write ``True`` as ``1``, join lists with commas; ``extra`` is added last and wins."""
    out = {}  # type: dict[str, str]
    for name, value in values.items():
        if value is None or value is False:
            continue
        out[name] = _join(value)
    if extra:
        for name, value in extra.items():
            if value is not None:
                out[name] = _join(value)
    return out


def encode_points(points: Any) -> str:
    """``[(lat, lon), ...]`` to ``lat,lon|lat,lon``; a string (including ``enc:...``) passes through unchanged."""
    if isinstance(points, str):
        return points
    return "|".join("{},{}".format(_scalar(p[0]), _scalar(p[1])) for p in points)


def pairs(points: Any) -> "list[list[float]]":
    return [[p[0], p[1]] for p in points]


# ---- responses --------------------------------------------------------------------------------------------------


def parse_response(response: HttpResponse, clock: "Callable[[], float]") -> "tuple[dict[str, Any], Meta]":
    """The decoded JSON object and its meta, or raise ``ApiError`` / ``DecodeError``."""
    meta = Meta.from_headers(response.headers)
    try:
        data = json.loads(response.body.decode("utf-8"))
    except ValueError:  # also UnicodeDecodeError
        data = None
    if response.status >= 400 or (isinstance(data, dict) and data.get("status") == "error"):
        raise _api_error(response, data, meta, clock)
    if not isinstance(data, dict):
        raise DecodeError(
            "Expected a JSON object from the API, got HTTP {} with a body that is not one.".format(response.status)
        )
    return data, meta


def _api_error(response: HttpResponse, data: Any, meta: Meta, clock: "Callable[[], float]") -> ApiError:
    err = {}  # type: Mapping[str, Any]
    if isinstance(data, dict) and isinstance(data.get("error"), dict):
        err = data["error"]
    code = str(err.get("code") or "http_error")
    message = str(err.get("message") or "HTTP {}".format(response.status))
    param = err.get("param")
    return ApiError(
        response.status,
        code,
        message,
        param if isinstance(param, str) else None,
        meta.request_id,
        server_wait(response, clock),
        data if isinstance(data, dict) else None,
    )


# ---- retries ----------------------------------------------------------------------------------------------------


def backoff(attempt: int) -> float:
    """1, 2, 4 ... seconds before the retry that follows failed try number ``attempt`` (counting from 0)."""
    return float(2 ** attempt)


def server_wait(response: HttpResponse, clock: "Callable[[], float]") -> Optional[float]:
    """Seconds the server asks to wait: ``Retry-After``, or on a 429 the time until ``X-Quota-Reset``."""
    value = _number(response.headers.get("Retry-After"))
    if value is not None:
        return max(0.0, value)
    if response.status == 429:
        reset = _number(response.headers.get("X-Quota-Reset"))
        if reset is not None:
            return max(0.0, reset - clock())
    return None


def retry_wait(opts: Options, response: HttpResponse, attempt: int, retried_500: bool) -> Optional[float]:
    """Seconds to wait before trying this request again, or ``None`` to raise the error now."""
    if attempt >= opts.max_retries:
        return None
    status = response.status
    if status == 429:
        wait = server_wait(response, opts.clock)
        return wait if wait is not None and wait <= opts.max_retry_wait else None
    if status == 500:
        return None if retried_500 else 1.0
    if status == 503:
        wait = server_wait(response, opts.clock)
        if wait is None:
            wait = backoff(attempt)
        return wait if wait <= opts.max_retry_wait else None
    return None


def _number(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


if TYPE_CHECKING:  # names used only in quoted annotations and type comments
    from collections.abc import Callable, Iterator  # noqa: F401

    Transport = Callable[[HttpRequest], HttpResponse]

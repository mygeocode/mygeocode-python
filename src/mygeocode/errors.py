"""Exceptions raised by the My Geocode client."""

from typing import Any, Optional


class MyGeocodeError(Exception):
    """Base class of every error this library raises."""


class ApiError(MyGeocodeError):
    """The API answered with an error.

    ``status`` is the HTTP status, ``code`` the API's error code (such as ``invalid_request``), ``message`` its
    explanation, ``param`` the parameter at fault, ``request_id`` the ``X-Request-Id`` header and ``retry_after`` the
    seconds the API asked to wait (``Retry-After``, or the time to ``X-Quota-Reset`` on a 429), or ``None``.
    ``body`` is the decoded error answer.
    """

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        param: Optional[str] = None,
        request_id: Optional[str] = None,
        retry_after: Optional[float] = None,
        body: "Optional[dict[str, Any]]" = None,
    ) -> None:
        super().__init__("{}: {} (HTTP {})".format(code, message, status))
        self.status = status
        self.code = code
        self.message = message
        self.param = param
        self.request_id = request_id
        self.retry_after = retry_after
        self.body = body


class RequestTimeoutError(MyGeocodeError):
    """No answer within ``timeout``."""


class NetworkError(MyGeocodeError):
    """The connection failed: DNS, refused, reset or TLS."""


class DecodeError(MyGeocodeError):
    """The answer could not be read as a JSON object."""

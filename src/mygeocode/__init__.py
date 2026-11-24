"""Official Python client for the My Geocode API: https://www.mygeocode.com/docs/"""

from ._core import HttpRequest, HttpResponse
from ._version import __version__
from .async_client import AsyncClient
from .client import Client
from .errors import ApiError, DecodeError, MyGeocodeError, NetworkError, RequestTimeoutError
from .models import (
    AutocompleteResponse,
    Bounds,
    Components,
    ElevationPoint,
    ElevationResponse,
    ForwardBatchEntry,
    ForwardBatchResponse,
    ForwardResponse,
    IpBatchResponse,
    IpInfo,
    Meta,
    Place,
    PostcodePlace,
    PostcodeResponse,
    ReverseBatchResponse,
    ReverseResponse,
    Suggestion,
    TimezoneBatchResponse,
    TimezoneInfo,
    TimezoneTransition,
)

__all__ = [
    "__version__",
    "Client",
    "AsyncClient",
    "MyGeocodeError",
    "ApiError",
    "RequestTimeoutError",
    "NetworkError",
    "DecodeError",
    "HttpRequest",
    "HttpResponse",
    "Meta",
    "Bounds",
    "Components",
    "Place",
    "ForwardResponse",
    "ForwardBatchEntry",
    "ForwardBatchResponse",
    "ReverseResponse",
    "ReverseBatchResponse",
    "Suggestion",
    "AutocompleteResponse",
    "IpInfo",
    "IpBatchResponse",
    "TimezoneInfo",
    "TimezoneTransition",
    "TimezoneBatchResponse",
    "ElevationPoint",
    "ElevationResponse",
    "PostcodePlace",
    "PostcodeResponse",
]

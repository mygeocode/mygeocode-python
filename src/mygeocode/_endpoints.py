"""Request specs for every endpoint. Both clients run them; nothing here touches the network."""

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Optional

from . import models as m
from ._core import encode_params, encode_points, pairs
from .models import Meta

if TYPE_CHECKING:
    from collections.abc import Callable

    Parse = Callable[[dict[str, Any], Meta], Any]

ANNOTATION_FLAGS = (
    "timezone", "elevation", "wikidata", "country_info", "codes", "sun", "regions", "districts", "census",
    "demographics", "road", "site",
)  # fmt: skip


class Spec(object):
    """One request: method, path, query parameters, JSON body, and how to read the answer."""

    def __init__(
        self, method: str, path: str, params: "dict[str, str]", body: "Optional[dict[str, Any]]", parse: "Parse"
    ) -> None:
        self.method = method
        self.path = path
        self.params = params
        self.body = body
        self.parse = parse


def _model(cls: Any) -> "Parse":
    def parse(data: "dict[str, Any]", meta: Meta) -> Any:
        return cls.from_dict(data, meta)

    return parse


def _elevation(data: "dict[str, Any]", meta: Meta) -> m.ElevationResponse:
    if "results" not in data and "elevation_m" in data:  # a single point answered flat
        data = dict(data, results=[data])
    return m.ElevationResponse.from_dict(data, meta)


def get(path: str, values: "Mapping[str, Any]", extra: "Optional[Mapping[str, Any]]", model: Any) -> Spec:
    return Spec("GET", path, encode_params(values, extra), None, _model(model))


def elevation(values: "Mapping[str, Any]", extra: "Optional[Mapping[str, Any]]") -> Spec:
    return Spec("GET", "elevation", encode_params(values, extra), None, _elevation)


def forward_batch(queries: Any, values: "Mapping[str, Any]", extra: "Optional[Mapping[str, Any]]") -> Spec:
    """POST with only the list in the body; every option goes in the query string."""
    return Spec("POST", "forward", encode_params(values, extra), {"queries": list(queries)}, _model(m.ForwardBatchResponse))


def reverse_batch(points: Any, values: "Mapping[str, Any]", extra: "Optional[Mapping[str, Any]]") -> Spec:
    return Spec("POST", "reverse", encode_params(values, extra), {"coords": pairs(points)}, _model(m.ReverseBatchResponse))


def elevation_batch(points: Any, values: "Mapping[str, Any]", extra: "Optional[Mapping[str, Any]]") -> Spec:
    return Spec("POST", "elevation", encode_params(values, extra), {"locations": pairs(points)}, _elevation)


def points_param(points: Any) -> Optional[str]:
    return None if points is None else encode_points(points)

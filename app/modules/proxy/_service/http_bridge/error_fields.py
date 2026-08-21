from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from app.core.types import JsonValue


@dataclass(frozen=True, slots=True)
class _HTTPBridgeErrorFields:
    """The error fields shared by HTTP-bridge continuity classifiers.

    ``param`` deliberately retains the value as it arrived on the wire.  The
    ``param_present`` bit is required because a missing parameter and a
    present blank, ``null`` (or other non-string JSON value) have different
    safety consequences for stale-anchor recovery.  Callers that classify the
    error may use :attr:`normalized_param` for the string-only comparison
    while still checking :attr:`param_malformed` and :attr:`param_present`.
    """

    code: str | None
    type: str | None
    message: str | None
    param_present: bool
    param: JsonValue | None
    normalized_code: str

    @property
    def normalized_param(self) -> str | None:
        if not isinstance(self.param, str):
            return None
        return self.param.strip()

    @property
    def param_malformed(self) -> bool:
        return self.param_present and (
            not isinstance(self.param, str) or not self.param.strip()
        )


def _error_detail_from_payload(payload: Mapping[str, JsonValue]) -> Mapping[str, JsonValue] | None:
    nested_error = payload.get("error")
    if isinstance(nested_error, Mapping):
        return nested_error

    response = payload.get("response")
    if isinstance(response, Mapping):
        response_error = response.get("error")
        if isinstance(response_error, Mapping):
            return response_error

    # ChatGPT-backed Codex websocket frames may put OpenAI error fields
    # directly on a ``type: error`` event rather than under ``error``.
    if payload.get("type") == "error":
        return payload
    return None


def _normalized_text(value: JsonValue) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalized_code(code: str | None, error_type: str | None) -> str:
    value = code or error_type
    return value.lower() if value else "upstream_error"


def _parse_http_bridge_error_fields(
    payload: Mapping[str, JsonValue] | None,
) -> _HTTPBridgeErrorFields | None:
    """Parse one OpenAI error envelope without coercing malformed fields.

    Recovery and explicit-rejection policy must make the same decision from
    the same normalized fields.  This parser is intentionally limited to
    field extraction; policy remains with each caller.  In particular, a
    malformed ``param`` is retained verbatim and never converted into an
    empty-string sentinel.
    """

    if not isinstance(payload, Mapping):
        return None
    detail = _error_detail_from_payload(payload)
    if detail is None:
        return None

    code = _normalized_text(detail.get("code"))
    error_type = _normalized_text(detail.get("type"))
    message = _normalized_text(detail.get("message"))
    param_present = "param" in detail
    param = detail.get("param") if param_present else None
    return _HTTPBridgeErrorFields(
        code=code,
        type=error_type,
        message=message,
        param_present=param_present,
        param=param,
        normalized_code=_normalized_code(code, error_type),
    )


__all__ = ["_HTTPBridgeErrorFields", "_parse_http_bridge_error_fields"]

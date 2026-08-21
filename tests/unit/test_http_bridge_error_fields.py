from __future__ import annotations

from app.core.types import JsonValue
from app.modules.proxy._service.http_bridge.error_fields import (
    _parse_http_bridge_error_fields,
)


def test_parser_preserves_parameter_presence_and_raw_value() -> None:
    cases: tuple[tuple[bool, JsonValue], ...] = (
        (False, None),
        (True, "previous_response_id"),
        (True, "  previous_response_id  "),
        (True, ""),
        (True, "   "),
        (True, None),
        (True, 0),
        (True, False),
        (True, {}),
        (True, []),
    )
    for param_present, param in cases:
        error: dict[str, JsonValue] = {
            "code": " invalid_request_error ",
            "type": " invalid_request_error ",
            "message": " Invalid previous_response_id. ",
        }
        if param_present:
            error["param"] = param

        fields = _parse_http_bridge_error_fields({"error": error})

        assert fields is not None
        assert fields.normalized_code == "invalid_request_error"
        assert fields.message == "Invalid previous_response_id."
        assert fields.param_present is param_present
        assert fields.param == param
        assert fields.normalized_param == (param.strip() if isinstance(param, str) else None)
        assert fields.param_malformed is (
            param_present and (not isinstance(param, str) or not param.strip())
        )


def test_parser_uses_direct_error_fields_from_top_level_error_event() -> None:
    fields = _parse_http_bridge_error_fields(
        {
            "type": "error",
            "code": "previous_response_not_found",
            "message": "Previous response was not found.",
            "param": "previous_response_id",
        }
    )

    assert fields is not None
    assert fields.normalized_code == "previous_response_not_found"
    assert fields.param_present is True
    assert fields.normalized_param == "previous_response_id"


def test_parser_reads_response_failed_error_detail() -> None:
    fields = _parse_http_bridge_error_fields(
        {
            "type": "response.failed",
            "response": {
                "error": {
                    "code": "previous_response_not_found",
                    "message": "Previous response was not found.",
                }
            },
        }
    )

    assert fields is not None
    assert fields.normalized_code == "previous_response_not_found"
    assert fields.param_present is False
    assert fields.param is None


def test_parser_rejects_payload_without_error_detail() -> None:
    assert _parse_http_bridge_error_fields({"type": "response.completed"}) is None

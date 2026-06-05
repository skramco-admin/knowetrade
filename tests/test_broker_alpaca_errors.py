import json
from unittest.mock import Mock

import pytest

from packages.broker_alpaca.client import (
    BrokerAuthError,
    OrderRejectedError,
    _parse_alpaca_error_body,
    _raise_for_order_response,
)


def _mock_response(*, status_code: int, body: dict | str | None = None) -> Mock:
    response = Mock()
    response.status_code = status_code
    if body is None:
        response.text = ""
        response.json.side_effect = ValueError("no json")
        return response
    if isinstance(body, dict):
        response.text = json.dumps(body)
        response.json.return_value = body
    else:
        response.text = body
        response.json.side_effect = ValueError("no json")
    return response


def test_parse_alpaca_error_body_reads_code_and_message() -> None:
    response = _mock_response(
        status_code=403,
        body={"code": 40310000, "message": "insufficient buying power"},
    )
    message, code = _parse_alpaca_error_body(response)
    assert code == 40310000
    assert message == "insufficient buying power"


def test_raise_for_order_response_maps_trading_403_to_order_rejected() -> None:
    response = _mock_response(
        status_code=403,
        body={"code": 40310000, "message": "insufficient buying power"},
    )
    with pytest.raises(OrderRejectedError, match="insufficient buying power"):
        _raise_for_order_response(response)


def test_raise_for_order_response_maps_401_to_auth_error() -> None:
    response = _mock_response(status_code=401, body={"message": "unauthorized"})
    with pytest.raises(BrokerAuthError, match="auth failure"):
        _raise_for_order_response(response)


def test_raise_for_order_response_maps_ambiguous_403_to_order_rejected() -> None:
    response = _mock_response(status_code=403, body="Forbidden")
    with pytest.raises(OrderRejectedError, match="Forbidden"):
        _raise_for_order_response(response)

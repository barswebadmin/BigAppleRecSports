import json
from http import HTTPStatus

import pytest
from models.api_base_model import ApiBaseModel, ApiResponse
from pydantic import ValidationError


class _NestedPayload(ApiBaseModel):
    order_number: str


def test_api_response_construction_with_data():
    r = ApiResponse(type=HTTPStatus.OK, data={"orderId": "123"})
    assert r.type == HTTPStatus.OK.value
    assert r.data == {"orderId": "123"}
    assert r.errors is None


def test_api_response_construction_with_errors_strings():
    r = ApiResponse(
        type=HTTPStatus.INTERNAL_SERVER_ERROR,
        errors=["rate limited", "timeout"],
    )
    assert r.type == HTTPStatus.INTERNAL_SERVER_ERROR.value
    assert r.errors == ["rate limited", "timeout"]
    assert r.data is None


def test_api_response_construction_with_errors_dicts():
    err = {"loc": ("body", "x"), "msg": "field required", "type": "missing"}
    r = ApiResponse(type=HTTPStatus.UNPROCESSABLE_ENTITY, errors=[err])
    assert r.errors == [err]


def test_api_response_defaults_none_without_data_or_errors():
    r = ApiResponse(type=HTTPStatus.NO_CONTENT)
    assert r.data is None
    assert r.errors is None


def test_api_response_missing_type_raises():
    with pytest.raises(ValidationError):
        ApiResponse()


def test_model_dump_type_as_int_excludes_none_camel_case_nested():
    r = ApiResponse(
        type=HTTPStatus.OK,
        data=_NestedPayload(order_number="1001"),
    )
    body = r.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert body == {"type": 200, "data": {"orderNumber": "1001"}}
    assert isinstance(body["type"], int)


def test_model_dump_omits_none_fields():
    r = ApiResponse(type=HTTPStatus.BAD_REQUEST, errors=["bad"])
    body = r.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert body == {"type": 400, "errors": ["bad"]}
    assert "data" not in body


@pytest.mark.parametrize(
    "status",
    [
        HTTPStatus.OK,
        HTTPStatus.CREATED,
        HTTPStatus.NO_CONTENT,
        HTTPStatus.BAD_REQUEST,
        HTTPStatus.UNPROCESSABLE_ENTITY,
        HTTPStatus.INTERNAL_SERVER_ERROR,
    ],
)
def test_to_http_response_status_code_matches_status(status: HTTPStatus):
    r = ApiResponse(type=status)
    resp = r.to_http_response()
    assert resp.status_code == status.value


def test_to_http_response_body_matches_model_dump():
    r = ApiResponse(
        type=HTTPStatus.UNPROCESSABLE_ENTITY,
        errors=["product_id is required"],
    )
    expected = r.model_dump(mode="json", by_alias=True, exclude_none=True)
    resp = r.to_http_response()
    assert json.loads(resp.body.decode()) == expected

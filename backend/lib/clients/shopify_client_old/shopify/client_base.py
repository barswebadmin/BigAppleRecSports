"""Base class for the generated Shopify GraphQL client.

This file is copied verbatim into ``generated/`` by ariadne-codegen on
every codegen run (configured via ``base_client_file_path`` in
ariadne-codegen.toml). The codegen-produced ``ShopifyClient`` inherits
from ``ShopifyBase`` and adds typed query/mutation methods on top.

Provides:
  - Construction from ``store_id`` + ``api_version`` + ``token``.
  - HTTP transport via httpx (single ``execute()`` + ``get_data()``).
  - File-upload multipart support (``Upload`` in variables).
  - Cursor pagination over any generated method that accepts
    ``first`` + ``after`` and returns a connection with
    ``nodes`` + ``pageInfo``.

NOT included: GraphQL-over-websockets subscription code. Shopify
Admin API does not expose subscriptions; the ~150 lines of
``execute_ws`` machinery that ariadne-codegen ships by default would
sit unused.

NOT included: alias-batched mutations. Aliased N-in-one mutations
cost the same as N independent calls against the Shopify cost budget,
so concurrent fan-out via ``asyncio.gather(...)`` is used at call sites
instead.
"""

import json
from typing import IO, Any, AsyncIterator, Awaitable, Callable, Optional, TypeVar, cast

import httpx
from pydantic import BaseModel
from pydantic_core import to_jsonable_python

from .base_model import UNSET, Upload
from .exceptions import (
    GraphQLClientGraphQLMultiError,
    GraphQLClientHttpError,
    GraphQLClientInvalidResponseError,
)

T = TypeVar("T")
Self = TypeVar("Self", bound="ShopifyBase")


class ShopifyBase:
    """Transport + pagination base for the generated Shopify GraphQL client."""

    def __init__(
        self,
        *,
        store_id: str,
        api_version: str,
        token: str,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.url = f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json"
        self.headers = {"X-Shopify-Access-Token": token}
        self.http_client = (
            http_client if http_client else httpx.AsyncClient(headers=self.headers)
        )

    async def __aenter__(self: Self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        await self.http_client.aclose()

    async def execute(
        self,
        query: str,
        operation_name: Optional[str] = None,
        variables: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> httpx.Response:
        processed_variables, files, files_map = self._process_variables(variables)

        if files and files_map:
            return await self._execute_multipart(
                query=query,
                operation_name=operation_name,
                variables=processed_variables,
                files=files,
                files_map=files_map,
                **kwargs,
            )

        return await self._execute_json(
            query=query,
            operation_name=operation_name,
            variables=processed_variables,
            **kwargs,
        )

    def get_data(self, response: httpx.Response) -> dict[str, Any]:
        if not response.is_success:
            raise GraphQLClientHttpError(
                status_code=response.status_code, response=response
            )

        try:
            response_json = response.json()
        except ValueError as exc:
            raise GraphQLClientInvalidResponseError(response=response) from exc

        if (not isinstance(response_json, dict)) or (
            "data" not in response_json and "errors" not in response_json
        ):
            raise GraphQLClientInvalidResponseError(response=response)

        data = response_json.get("data")
        errors = response_json.get("errors")

        if errors:
            raise GraphQLClientGraphQLMultiError.from_errors_dicts(
                errors_dicts=errors, data=data
            )

        return cast(dict[str, Any], data)

    async def paginate(
        self,
        query_fn: Callable[..., Awaitable[Any]],
        connection_attr: str,
        page_size: int = 100,
        **kwargs: Any,
    ) -> AsyncIterator[T]:
        """Drive any cursor-paginated Shopify query to completion, yielding nodes.

        Args:
            query_fn:        A generated client method that accepts ``first`` + ``after``.
            connection_attr: Name of the top-level connection field on the response
                             (e.g. ``"orders"``, ``"customers"``, ``"products"``).
            page_size:       Items per page (Shopify caps at 250).
            **kwargs:        Other arguments forwarded to ``query_fn``.

        Yields:
            Each node from each page in order.

        Example:
            async for order in client.paginate(
                client.orders_get, "orders", query="product_id:7678..."
            ):
                process(order)
        """
        cursor: str | None = None
        while True:
            result = await query_fn(first=page_size, after=cursor, **kwargs)
            connection = getattr(result, connection_attr)
            for node in connection.nodes:
                yield node
            if not connection.page_info.has_next_page:
                return
            cursor = connection.page_info.end_cursor

    def _process_variables(
        self, variables: Optional[dict[str, Any]]
    ) -> tuple[
        dict[str, Any], dict[str, tuple[str, IO[bytes], str]], dict[str, list[str]]
    ]:
        if not variables:
            return {}, {}, {}

        serializable_variables = self._convert_dict_to_json_serializable(variables)
        return self._get_files_from_variables(serializable_variables)

    def _convert_dict_to_json_serializable(
        self, dict_: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            key: self._convert_value(value)
            for key, value in dict_.items()
            if value is not UNSET
        }

    def _convert_value(self, value: Any) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(by_alias=True, exclude_unset=True)
        if isinstance(value, list):
            return [self._convert_value(item) for item in value]
        return value

    def _get_files_from_variables(
        self, variables: dict[str, Any]
    ) -> tuple[
        dict[str, Any], dict[str, tuple[str, IO[bytes], str]], dict[str, list[str]]
    ]:
        files_map: dict[str, list[str]] = {}
        files_list: list[Upload] = []

        def separate_files(path: str, obj: Any) -> Any:
            if isinstance(obj, list):
                nulled_list = []
                for index, value in enumerate(obj):
                    value = separate_files(f"{path}.{index}", value)
                    nulled_list.append(value)
                return nulled_list

            if isinstance(obj, dict):
                nulled_dict = {}
                for key, value in obj.items():
                    value = separate_files(f"{path}.{key}", value)
                    nulled_dict[key] = value
                return nulled_dict

            if isinstance(obj, Upload):
                if obj in files_list:
                    file_index = files_list.index(obj)
                    files_map[str(file_index)].append(path)
                else:
                    file_index = len(files_list)
                    files_list.append(obj)
                    files_map[str(file_index)] = [path]
                return None

            return obj

        nulled_variables = separate_files("variables", variables)
        files: dict[str, tuple[str, IO[bytes], str]] = {
            str(i): (file_.filename, cast(IO[bytes], file_.content), file_.content_type)
            for i, file_ in enumerate(files_list)
        }
        return nulled_variables, files, files_map

    async def _execute_multipart(
        self,
        query: str,
        operation_name: Optional[str],
        variables: dict[str, Any],
        files: dict[str, tuple[str, IO[bytes], str]],
        files_map: dict[str, list[str]],
        **kwargs: Any,
    ) -> httpx.Response:
        data = {
            "operations": json.dumps(
                {
                    "query": query,
                    "operationName": operation_name,
                    "variables": variables,
                },
                default=to_jsonable_python,
            ),
            "map": json.dumps(files_map, default=to_jsonable_python),
        }

        return await self.http_client.post(
            url=self.url, data=data, files=files, **kwargs
        )

    async def _execute_json(
        self,
        query: str,
        operation_name: Optional[str],
        variables: dict[str, Any],
        **kwargs: Any,
    ) -> httpx.Response:
        headers: dict[str, str] = {"Content-type": "application/json"}
        headers.update(kwargs.get("headers", {}))

        merged_kwargs: dict[str, Any] = kwargs.copy()
        merged_kwargs["headers"] = headers

        return await self.http_client.post(
            url=self.url,
            content=json.dumps(
                {
                    "query": query,
                    "operationName": operation_name,
                    "variables": variables,
                },
                default=to_jsonable_python,
            ),
            **merged_kwargs,
        )

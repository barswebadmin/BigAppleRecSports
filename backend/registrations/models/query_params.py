"""FastAPI query-string binding for ``ApiBaseModel`` subclasses.

``QueryParam`` builds a cached ``*AsQuery`` subclass (each field wrapped in ``fastapi.Query``)
and a ``Depends``-compatible callable. It is **not** per-parameter ``fastapi.Query``.

"""

from collections.abc import Callable
from functools import lru_cache
from typing import Annotated, Any, TypeVar

from fastapi import Depends, HTTPException, Query
from pydantic import create_model

from models.api_base_model import ApiBaseModel

M = TypeVar("M", bound=ApiBaseModel)


class QueryParam:
    """Bind one ``ApiBaseModel`` subclass to FastAPI query parsing."""

    __slots__ = ("_model_cls",)

    def __init__(self, model_cls: type[M]) -> None:
        self._model_cls = model_cls

    @staticmethod
    @lru_cache(maxsize=None)
    def _as_query_subclass(model_cls: type[M]) -> type[M]:
        defs: dict[str, tuple[Any, Any]] = {}
        for name, finfo in model_cls.model_fields.items():
            q = Query(default=None)
            meta = tuple(finfo.metadata) if finfo.metadata else ()
            defs[name] = (Annotated[finfo.annotation, *meta, q], finfo.default)

        return create_model(
            f"{model_cls.__name__}AsQuery",
            __base__=model_cls,
            __module__=model_cls.__module__,
            **defs,
        )

    @property
    def params_model(self) -> type[M]:
        return QueryParam._as_query_subclass(self._model_cls)

    def depends(self, *, policy: Callable[[M], None] | None = None) -> Callable[..., M]:
        params_model = QueryParam._as_query_subclass(self._model_cls)

        async def _dep(raw: Annotated[params_model, Depends()]) -> M:
            if policy is not None:
                try:
                    policy(raw)
                except ValueError as e:
                    raise HTTPException(status_code=422, detail=str(e)) from e
            return raw  # type: ignore[return-value]

        return _dep

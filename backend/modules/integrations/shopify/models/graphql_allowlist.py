from __future__ import annotations
from functools import lru_cache
from typing import Any, Dict, List, Set, Tuple, Type, get_args, get_origin, Union

from pydantic import BaseModel
from backend.shared.model_config import snake_to_camel


def _field_alias(model: Type[BaseModel], name: str) -> str:
    fld = model.model_fields.get(name)
    if not fld:
        return snake_to_camel(name)
    # Use explicit alias if present; otherwise apply alias_generator
    alias = fld.alias
    return alias or snake_to_camel(name)


def _is_pydantic_model(tp: Any) -> bool:
    try:
        return isinstance(tp, type) and issubclass(tp, BaseModel)
    except Exception:
        return False


def _inner_model_from_type(tp: Any) -> Type[BaseModel] | None:
    # Direct model
    if _is_pydantic_model(tp):
        return tp  # type: ignore[return-value]
    origin = get_origin(tp)
    # Optional/Union[...] → inspect args recursively
    if origin is Union:
        for arg in get_args(tp):
            inner = _inner_model_from_type(arg)
            if inner is not None:
                return inner
        return None
    # List[...] → inner element may be a model
    if origin in (list, List):
        args = get_args(tp)
        if args:
            return _inner_model_from_type(args[0])
    return None


@lru_cache(maxsize=128)
def derive_allowed_paths(model: Type[BaseModel]) -> Set[str]:
    """Return a set of GraphQL dot-paths derived from a Pydantic model.
    Uses field aliases if specified, otherwise snake_to_camel.
    """
    allowed: Set[str] = set()

    def walk(cur_model: Type[BaseModel], base: str = "") -> None:
        for name, fld in cur_model.model_fields.items():
            graphql_name = _field_alias(cur_model, name)
            full = f"{base}.{graphql_name}" if base else graphql_name
            inner = _inner_model_from_type(fld.annotation)
            if inner is None:
                # leaf or non-model container
                allowed.add(full)
            else:
                # nested model
                allowed.add(full)  # include the object name itself
                walk(inner, full)

    walk(model)
    return allowed


def convert_paths_python_to_graphql(model: Type[BaseModel], paths: List[str]) -> List[str]:
    """Convert python snake_case path segments to GraphQL names using aliases.
    Example: total_price_set.shop_money.amount -> totalPriceSet.shopMoney.amount
    """
    out: List[str] = []
    for path in paths:
        parts = path.split(".")
        cur_model: Type[BaseModel] | None = model
        gql_parts: List[str] = []
        for part in parts:
            if cur_model is None:
                gql_parts.append(snake_to_camel(part))
                continue
            gql_name = _field_alias(cur_model, part)
            gql_parts.append(gql_name)
            # Descend if nested model
            fld = cur_model.model_fields.get(part)
            if not fld:
                cur_model = None
            else:
                cur_model = _inner_model_from_type(fld.annotation)
        out.append(".".join(gql_parts))
    return out


def derive_leaf_paths(model: Type[BaseModel]) -> List[str]:
    """Return only leaf GraphQL dot-paths for a model.
    A leaf path is one that is not a prefix of any other allowed path.
    """
    allowed = derive_allowed_paths(model)
    leaves: List[str] = []
    for path in allowed:
        prefix = f"{path}."
        if not any(other.startswith(prefix) for other in allowed if other != path):
            leaves.append(path)
    return sorted(leaves)


def _is_scalar_annotation(tp: Any) -> bool:
    origin = get_origin(tp)
    if origin is None:
        return tp in (str, int, float, bool)
    if origin in (list, List, dict, Dict):
        return False
    # Optional[T] or Union types
    if origin is Union:
        args = get_args(tp)
        # scalar if all non-None args are scalar
        scalars = [a for a in args if a is not type(None)]
        return all(_is_scalar_annotation(a) for a in scalars) if scalars else False
    return False


def derive_scalar_leaf_paths(model: Type[BaseModel]) -> List[str]:
    """Return leaf paths that correspond to scalar fields only.
    Excludes dicts/lists and opaque Any-typed fields that require selections.
    """
    results: List[str] = []

    def walk(cur_model: Type[BaseModel], base: str = "") -> None:
        for name, fld in cur_model.model_fields.items():
            gql_name = _field_alias(cur_model, name)
            full = f"{base}.{gql_name}" if base else gql_name
            inner = _inner_model_from_type(fld.annotation)
            if inner is not None:
                walk(inner, full)
            else:
                if _is_scalar_annotation(fld.annotation):
                    results.append(full)

    walk(model)
    return sorted(results)



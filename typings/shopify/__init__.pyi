# It’s at the root on purpose: your pyproject.toml sets stubPath = "typings" for Pyright, so root-level typings/ is the global search location for third‑party stubs (like shopify). This lets the IDE/type checker apply the stubs across the whole repo, not just backend/.
# backend/models is for runtime models/code, not type stubs. .pyi stubs should live in a dedicated stubs dir (matching the import name, here shopify/) that the type checker knows about.

# If you really want it under backend/:
# - Move to backend/typings/shopify/__init__.pyi
# - Update pyproject.toml to stubPath = "backend/typings"
# - Restart the language server so Pyright picks it up.

class Session:
    def __init__(self, shop_url: str, api_version: str, access_token: str) -> None: ...


class ShopifyResource:
    @classmethod
    def activate_session(cls, session: Session) -> None: ...


class Customer:
    id: int | str | None
    email: str | None
    first_name: str | None
    last_name: str | None
    tags: list[str] | str | None

    @classmethod
    def find(cls, id: int | str) -> "Customer" | None: ...

    @classmethod
    def search(cls, *, query: str) -> list["Customer"]: ...

class Order:
    # Minimal attributes commonly accessed; actual SDK exposes more
    id: int | str | None
    name: str | None
    email: str | None

    # ActiveResource returns objects with attributes dict in many cases
    attributes: dict
    def to_dict(self) -> dict: ...

    @classmethod
    def find(cls, *args, **kwargs) -> list["Order"] | "Order" | None: ...

    @classmethod
    def search(cls, *, query: str) -> list["Order"]: ...



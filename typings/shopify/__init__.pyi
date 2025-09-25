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



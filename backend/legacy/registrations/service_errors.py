from clients.shopify.models.base import ClientError


class ServiceErrors(Exception):  # noqa: N818 — wraps a list of errors; plural name is intentional
    """Raised when a controller/service returns recoverable client errors as 500."""

    def __init__(self, errors: list[ClientError]) -> None:
        self.errors = errors
        super().__init__()

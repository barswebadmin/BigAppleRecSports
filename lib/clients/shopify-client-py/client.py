"""Auth + retry wrapper for the codegen'd Shopify Admin GraphQL client."""

import logging
import os
import uuid
from functools import cached_property
from typing import Any, Callable, Iterator, NamedTuple, TypedDict, TypeVar

import httpx
from httpx_retries import Retry, RetryTransport

from .exceptions import ShopifyUserError, raise_if_user_errors
from .generated.client import ShopifyAdminSyncClient
from .generated.file_update import FileUpdateFileUpdate
from .generated.find_orders import FindOrdersOrders, FindOrdersOrdersNodes
from .generated.find_products import FindProductsProducts
from .generated.get_customers import GetCustomersCustomers
from .generated.input_types import (
    CreateMediaInput,
    FileUpdateInput,
    InventoryAdjustQuantitiesInput,
    InventoryChangeInput,
    ProductUpdateInput,
    ProductVariantsBulkInput,
)
from .generated.permanently_delete_file import PermanentlyDeleteFileFileDelete
from .generated.product_update import ProductUpdateProductUpdate
from .generated.product_variants_bulk_update import (
    ProductVariantsBulkUpdateProductVariantsBulkUpdate,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# --- public API types -------------------------------------------------------

class InventoryAdjustResult(NamedTuple):
    """Return value of ``add_inventory`` / ``remove_inventory``.

    Surfaces the actual delta applied so callers can detect when a negative
    delta was capped to ``-current_before`` (i.e. fewer units shipped than
    requested).
    """

    requested_delta: int
    applied_delta: int
    current_before: int
    adjustment_group_id: str


class ProductSearchQuery(TypedDict, total=False):
    """Searchable fields for ``find_products``. All keys optional, ANDed together."""

    title: str
    status: str            # "ACTIVE" | "DRAFT" | "ARCHIVED"
    vendor: str
    product_type: str
    tag: str
    handle: str
    sku: str
    barcode: str
    inventory_total: int


class OrderSearchQuery(TypedDict, total=False):
    """Searchable fields for ``find_orders``. All keys optional, ANDed together.

    The full Shopify query syntax is much richer (date ranges, status filters, tag,
    etc.); add fields here when they're actually used. Bare values like
    ``name:"#1234"`` can also be passed via ``query=`` as a raw string.
    """

    name: str              # order display name, e.g. "#1234" — leading '#' optional
    email: str
    customer_id: str
    financial_status: str  # "PAID" | "REFUNDED" | "PARTIALLY_REFUNDED" | ...
    fulfillment_status: str
    tag: str


class CustomerSearchQuery(TypedDict, total=False):
    """Searchable fields for ``get_customers``. All keys optional, ANDed together."""

    email: str
    first_name: str
    last_name: str
    state: str             # "ENABLED" | "DISABLED" | "INVITED" | "DECLINED"
    tag: str
    phone: str


class VariantUpdate(TypedDict, total=False):
    """Updatable fields for ``update_variants``. ``id`` is required for updates."""

    id: str                # variant GID — required
    price: str             # decimal string, e.g. "10.00"
    compare_at_price: str  # decimal string
    inventory_policy: str  # "DENY" | "CONTINUE"
    barcode: str
    taxable: bool


# --- internal helpers (module-level) ----------------------------------------

def _build_search_query(q: dict[str, Any]) -> str:
    """Render a search dict as Shopify's query-string syntax (key:value pairs)."""
    parts: list[str] = []
    for k, v in q.items():
        values = v if isinstance(v, list) else [v]
        for item in values:
            s = str(item)
            if " " in s:
                s = f'"{s}"'
            parts.append(f"{k}:{s}")
    return " ".join(parts) if parts else "*"


class ShopifyClient(ShopifyAdminSyncClient):
    """Shopify Admin GraphQL client with auth, retry, and HTTP/2 baked in."""

    # --- lifecycle ---

    def __init__(
        self,
        *,
        api_token: str,
        api_version: str,
        store_id: str | None = None,
        location_id: str | None = None,
    ) -> None:
        store_id = store_id or os.environ["SHOPIFY_STORE_ID"]
        self._location_id_override = location_id
        self.admin_url = f"https://admin.shopify.com/store/{store_id}"
        url = f"https://{store_id}.myshopify.com/admin/api/{api_version}/graphql.json"
        http = httpx.Client(
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": api_token,
            },
            timeout=30,
            transport=RetryTransport(
                transport=httpx.HTTPTransport(),
                retry=Retry(total=3, backoff_factor=0.5),
            ),
        )
        super().__init__(url=url, http_client=http)

    def close(self) -> None:
        self.http_client.close()

    def __enter__(self) -> "ShopifyClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # --- state ---

    @cached_property
    def location_id(self) -> str:
        """Constructor override, or the first location's GID fetched lazily once."""
        return self._location_id_override or self.get_default_location().nodes[0].id

    # --- products ---

    def update_product(
        self,
        *,
        id: str,
        media: list[dict[str, Any]] | None = None,
        **fields: Any,
    ) -> ProductUpdateProductUpdate:
        """Update product top-level fields. Pass any ``ProductUpdateInput`` field as kwarg.

        Example::

            client.update_product(id=product_gid, title="New", tags=["x", "y"])

        Common kwargs: ``title``, ``tags``, ``status``, ``vendor``, ``handle``,
        ``description_html``, ``product_type``. snake_case or camelCase accepted.
        ``media`` (optional) is a list of dicts in CreateMediaInput shape — APPENDS
        files to the product. Use ``update_file`` to swap/detach existing media.

        Raises ``ShopifyUserError`` on rejection.
        """
        return raise_if_user_errors(
            "productUpdate",
            self.product_update(
                product=ProductUpdateInput(id=id, **fields),
                media=[CreateMediaInput(**m) for m in media] if media else None,
            ),
        )

    def find_products(  # type: ignore[override]
        self,
        *,
        query: ProductSearchQuery | str | None = None,
        num: int = 10,
        with_pagination: bool = False,
    ) -> FindProductsProducts | Iterator[Any]:
        """Search products. Pass ``query`` as a dict (autocompleted fields) or raw string.

        Examples::

            client.find_products(query={"title": "kickball", "status": "ACTIVE"})
            client.find_products(query="title:foo OR vendor:bar", num=50)

            for product in client.find_products(query={"tag": "summer"}, with_pagination=True):
                process(product)

        ``num`` is the page size. ``with_pagination=True`` returns an iterator over all
        matching products (yields ProductNode each); False returns a single page.
        """
        qstr = _build_search_query(query) if isinstance(query, dict) else (query or "*")
        if with_pagination:
            return self._iter_pages(super().find_products, page_size=num, query=qstr)
        return super().find_products(query=qstr, first=num)

    # --- orders ---

    def find_orders(  # type: ignore[override]
        self,
        *,
        query: OrderSearchQuery | str | None = None,
        num: int = 10,
        line_items_per_order: int = 50,
        with_pagination: bool = False,
    ) -> FindOrdersOrders | Iterator[FindOrdersOrdersNodes]:
        """Search orders. Pass ``query`` as a dict (autocompleted fields) or raw string.

        Examples::

            client.find_orders(query={"name": "#1234"}, num=1)
            client.find_orders(query="name:#1234 OR name:#1235", num=10)

            for order in client.find_orders(query={"financial_status": "PAID"}, with_pagination=True):
                process(order)
        """
        qstr = _build_search_query(query) if isinstance(query, dict) else (query or "*")
        if with_pagination:
            return self._iter_pages(
                super().find_orders,
                page_size=num,
                query=qstr,
                line_items_first=line_items_per_order,
            )
        return super().find_orders(query=qstr, first=num, line_items_first=line_items_per_order)

    def get_order_by_name(
        self,
        *,
        name: str,
        line_items_per_order: int = 50,
    ) -> FindOrdersOrdersNodes | None:
        """Fetch a single order by its display name (e.g. ``"#1234"`` or ``"1234"``).

        Shopify's ``orders(query:)`` filter on ``name`` matches the full display name
        including the leading ``#``. This wrapper normalizes a bare numeric string by
        prefixing ``#`` automatically so callers can pass either form.

        Returns ``None`` when no order matches.
        """
        # Normalize: "#1234" stays as-is; "1234" → "#1234"; "name:..." passthrough is the
        # caller's job (use find_orders with query= for arbitrary filter strings).
        normalized = name if name.startswith("#") else f"#{name}"
        page = super().find_orders(
            query=f'name:"{normalized}"',
            first=1,
            line_items_first=line_items_per_order,
        )
        return page.nodes[0] if page.nodes else None

    # --- inventory ---

    def get_current_inventory(
        self,
        *,
        product_id: str,
        variant_id: str | None = None,
    ) -> int:
        """Return current inventory qty for the variant at the configured location.

        Omit ``variant_id`` for single-variant products. Raises ``ValueError`` when
        the product has multiple variants and no variant is specified, or the named
        variant isn't on the product.
        """
        _, current = self._read_variant_inventory(product_id=product_id, variant_id=variant_id)
        return current

    def add_inventory(
        self,
        *,
        product_id: str,
        n: int,
        reason: str = "correction",
        variant_id: str | None = None,
        with_safe_retry: bool = False,
    ) -> InventoryAdjustResult:
        """Add ``n`` units to a variant's inventory. ``n`` must be > 0.

        Set ``with_safe_retry=True`` during active sales to retry forever on
        ``CHANGE_FROM_QUANTITY_STALE`` (concurrent purchases) until the write lands.
        Other ``ShopifyUserError`` codes propagate either way.
        """
        if n <= 0:
            raise ValueError(f"add_inventory expects n > 0; got {n}")
        op = lambda: self._adjust_inventory(
            product_id=product_id, delta=n, reason=reason, variant_id=variant_id,
        )
        return self._retry_on_stale(op) if with_safe_retry else op()

    def remove_inventory(
        self,
        *,
        product_id: str,
        n: int,
        reason: str = "correction",
        variant_id: str | None = None,
        with_safe_retry: bool = False,
    ) -> InventoryAdjustResult:
        """Remove ``n`` units from a variant's inventory. ``n`` must be > 0.

        If fewer than ``n`` units are available, removes only what's there
        (``applied_delta`` on the result reflects the actual movement).

        Set ``with_safe_retry=True`` during active sales to retry forever on
        ``CHANGE_FROM_QUANTITY_STALE`` until the write lands.
        """
        if n <= 0:
            raise ValueError(f"remove_inventory expects n > 0; got {n}")
        op = lambda: self._adjust_inventory(
            product_id=product_id, delta=-n, reason=reason, variant_id=variant_id,
        )
        return self._retry_on_stale(op) if with_safe_retry else op()

    def _read_variant_inventory(
        self,
        *,
        product_id: str,
        variant_id: str | None,
    ) -> tuple[Any, int]:
        """Shared: locate the target variant + read current qty at the configured location."""
        product = self.get_inventory_at_location(product_id=product_id, location_id=self.location_id)
        variants = product.variants.nodes
        if variant_id is None and len(variants) != 1:
            raise ValueError(f"Product {product_id} has {len(variants)} variants; specify variant_id.")
        target = variants[0] if variant_id is None else next((v for v in variants if v.id == variant_id), None)
        if target is None:
            raise ValueError(f"Variant {variant_id} not found on product {product_id}.")
        inv_level = target.inventory_item.inventory_level
        current = inv_level.quantities[0].quantity if inv_level and inv_level.quantities else 0
        return target, current

    def _adjust_inventory(
        self,
        *,
        product_id: str,
        delta: int,
        reason: str,
        variant_id: str | None,
    ) -> InventoryAdjustResult:
        """Single attempt: read current qty, cap negative delta to -current, write with CAS."""
        target, current = self._read_variant_inventory(product_id=product_id, variant_id=variant_id)
        applied = max(delta, -current)
        if applied != delta:
            logger.warning(
                "capping delta %d→%d for product=%s variant=%s (only %d available)",
                delta, applied, product_id, target.id, current,
            )
        result = raise_if_user_errors(
            "adjustInventory",
            self.adjust_inventory(
                input=InventoryAdjustQuantitiesInput(
                    reason=reason,
                    name="available",
                    changes=[InventoryChangeInput(
                        delta=applied,
                        change_from_quantity=current,
                        inventory_item_id=target.inventory_item.id,
                        location_id=self.location_id,
                    )],
                ),
                idempotency_key=str(uuid.uuid4()),
            ),
        )
        return InventoryAdjustResult(
            requested_delta=delta,
            applied_delta=applied,
            current_before=current,
            adjustment_group_id=result.inventory_adjustment_group.id,
        )

    def _retry_on_stale(self, op: Callable[[], T]) -> T:
        """Retry ``op()`` forever until it returns without CHANGE_FROM_QUANTITY_STALE."""
        attempt = 0
        while True:
            attempt += 1
            try:
                return op()
            except ShopifyUserError as exc:
                if not exc.has_code("CHANGE_FROM_QUANTITY_STALE"):
                    raise
                logger.warning(
                    "CHANGE_FROM_QUANTITY_STALE on attempt %d — concurrent write detected, retrying.",
                    attempt,
                )

    # --- variants ---

    def update_variants(
        self,
        *,
        product_id: str,
        variants: list[VariantUpdate],
    ) -> ProductVariantsBulkUpdateProductVariantsBulkUpdate:
        """Atomic bulk variant update (``allowPartialUpdates: false`` in the operation).

        Each entry in ``variants`` is a dict of updatable fields — see ``VariantUpdate``
        for the autocompleted keys. Length-1 list is the normal "update one variant"
        case. Raises ``ShopifyUserError`` on any per-variant rejection (whole call
        rolls back).
        """
        return raise_if_user_errors(
            "productVariantsBulkUpdate",
            self.product_variants_bulk_update(
                product_id=product_id,
                variants=[ProductVariantsBulkInput(**v) for v in variants],
            ),
        )

    # --- files ---

    def update_file(
        self,
        *,
        id: str,
        **fields: Any,
    ) -> FileUpdateFileUpdate:
        """Update a single file. Pass any ``FileUpdateInput`` field as kwarg.

        Typical kwargs: ``alt``, ``filename``, ``references_to_add``,
        ``references_to_remove``, ``original_source``, ``preview_image_source``.

        Example — attach to a product::

            client.update_file(id=file_gid, references_to_add=[product_gid])

        Singular by design — atomic semantics enforced client-side (one file per call).
        """
        return raise_if_user_errors(
            "fileUpdate",
            super().file_update(files=[FileUpdateInput(id=id, **fields)]),
        )

    def delete_file(self, *, file_id: str) -> PermanentlyDeleteFileFileDelete:
        """Delete a file from the Shopify Files library — permanent, no undo.

        Removes the file from the library AND from every product/variant that
        references it. For "remove image from product without deleting the file,"
        use ``update_file`` with ``references_to_remove=[product_id]`` instead.
        """
        return raise_if_user_errors(
            "fileDelete",
            super().permanently_delete_file(file_ids=[file_id]),
        )

    # --- customers ---

    def get_customers(  # type: ignore[override]
        self,
        *,
        query: CustomerSearchQuery | str | None = None,
        num: int = 10,
        with_pagination: bool = False,
    ) -> GetCustomersCustomers | Iterator[Any]:
        """Search customers. Pass ``query`` as a dict (autocompleted fields) or raw string.

        Examples::

            client.get_customers(query={"state": "ENABLED", "tag": "vip"})
            client.get_customers(query="email:*@example.com", num=100)

            for customer in client.get_customers(query={"state": "ENABLED"}, with_pagination=True):
                process(customer)

        ``num`` is the page size. ``with_pagination=True`` returns an iterator over all
        matching customers; False returns a single page.
        """
        qstr = _build_search_query(query) if isinstance(query, dict) else query
        if with_pagination:
            return self._iter_pages(super().get_customers, page_size=num, query=qstr)
        return super().get_customers(first=num, query=qstr)

    # --- internal ---

    def _iter_pages(
        self,
        query_fn: Callable[..., Any],
        *,
        page_size: int,
        **vars: Any,
    ) -> Iterator[Any]:
        """Walk a cursor-paginated connection. Yields nodes; terminates on hasNextPage=false."""
        cursor: str | None = None
        while True:
            connection = query_fn(first=page_size, after=cursor, **vars)
            yield from connection.nodes
            if not connection.page_info.has_next_page:
                return
            cursor = connection.page_info.end_cursor

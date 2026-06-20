"""Shopify products/update webhook payload model and processor."""

from dataclasses import dataclass

from pydantic import Field

from ..base import WebhookBase


class ProductVariant(WebhookBase):
    inventory_quantity: int = 0
    admin_graphql_api_id: str = ""
    title: str = ""
    inventory_item_id: int | None = None

    id: int | None = None
    product_id: int | None = None
    price: str = "0.00"
    compare_at_price: str | None = None
    sku: str | None = None
    barcode: str | None = None
    position: int | None = None
    inventory_policy: str | None = None
    old_inventory_quantity: int | None = None
    image_id: int | None = None
    option1: str | None = None
    option2: str | None = None
    option3: str | None = None
    taxable: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ProductOption(WebhookBase):
    id: int | None = None
    product_id: int | None = None
    name: str | None = None
    position: int | None = None
    values: list[str] = Field(default_factory=list)


class WebhookProductImage(WebhookBase):
    id: int | None = None
    product_id: int | None = None
    position: int | None = None
    alt: str | None = None
    width: int | None = None
    height: int | None = None
    src: str | None = None
    variant_ids: list[int] = Field(default_factory=list)
    admin_graphql_api_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class MediaPreviewImage(WebhookBase):
    width: int | None = None
    height: int | None = None
    src: str | None = None
    status: str | None = None


class ProductMedia(WebhookBase):
    admin_graphql_api_id: str = ""

    id: int | None = None
    product_id: int | None = None
    position: int | None = None
    alt: str | None = None
    status: str | None = None
    media_content_type: str | None = None
    preview_image: MediaPreviewImage | None = None
    variant_ids: list[int] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class VariantGid(WebhookBase):
    admin_graphql_api_id: str | None = None
    updated_at: str | None = None


class ProductCategory(WebhookBase):
    admin_graphql_api_id: str | None = None
    name: str | None = None
    full_name: str | None = None


class ProductUpdateWebhook(WebhookBase):
    """Shopify products/update webhook payload."""

    id: int
    title: str = ""
    handle: str = ""
    tags: str = ""
    admin_graphql_api_id: str = ""
    variants: list[ProductVariant] = Field(default_factory=list)
    media: list[ProductMedia] = Field(default_factory=list)

    body_html: str | None = None
    vendor: str | None = None
    product_type: str | None = None
    status: str | None = None
    published_scope: str | None = None
    template_suffix: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    published_at: str | None = None
    has_variants_that_requires_components: bool | None = None

    options: list[ProductOption] = Field(default_factory=list)
    images: list[WebhookProductImage] = Field(default_factory=list)
    image: WebhookProductImage | None = None
    variant_gids: list[VariantGid] = Field(default_factory=list)
    category: ProductCategory | None = None

    @property
    def tags_list(self) -> list[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def total_inventory(self) -> int:
        return sum(v.inventory_quantity for v in self.variants)

    @property
    def media_ids(self) -> list[str]:
        return [m.admin_graphql_api_id for m in self.media]


@dataclass
class ProductUpdateResult:
    product_id: str
    product_title: str
    total_inventory: int
    current_tags: list[str]
    action: str = "no_action"
    close_product_id: str | None = None


def process_product_update(product: ProductUpdateWebhook) -> ProductUpdateResult:
    """Analyze a products/update webhook and trigger close_registration when appropriate.

    Close registration triggers when ALL conditions are met:
    - total inventory across all variants is 0
    - product tags include 'live-reg'
    - product tags do NOT include 'coming-soon'
    - product tags do NOT include 'waitlist-only'
    """
    product_id = str(product.id)
    current_tags = product.tags_list
    remaining = product.total_inventory

    result = ProductUpdateResult(
        product_id=product_id,
        product_title=product.title,
        total_inventory=remaining,
        current_tags=current_tags,
    )

    if (
        remaining == 0
        and "live-reg" in current_tags
        and "coming-soon" not in current_tags
        and "waitlist-only" not in current_tags
    ):
        result.action = "close_registration"
        result.close_product_id = product_id

    return result

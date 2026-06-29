"""Shopify orders/create webhook payload model and processor."""

from dataclasses import dataclass, field

from pydantic import Field

from ..base import PriceSet, WebhookBase


class Address(WebhookBase):
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    province: str | None = None
    province_code: str | None = None
    country: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    zip: str | None = None
    phone: str | None = None
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    default: bool | None = None


class CustomerAddress(Address):
    id: int | None = None
    customer_id: int | None = None


class Customer(WebhookBase):
    id: int
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    state: str | None = None
    note: str | None = None
    verified_email: bool = False
    multipass_identifier: str | None = None
    tax_exempt: bool = False
    phone: str | None = None
    currency: str = "USD"
    tax_exemptions: list[str] = Field(default_factory=list)
    admin_graphql_api_id: str = ""
    default_address: CustomerAddress | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ClientDetails(WebhookBase):
    accept_language: str | None = None
    browser_height: int | None = None
    browser_ip: str | None = None
    browser_width: int | None = None
    session_hash: str | None = None
    user_agent: str | None = None


class NoteAttribute(WebhookBase):
    name: str = ""
    value: str = ""


class LineItemProperty(WebhookBase):
    name: str = ""
    value: str = ""


class AttributedStaff(WebhookBase):
    id: str = ""
    quantity: int = 0


class LineItem(WebhookBase):
    id: int
    admin_graphql_api_id: str = ""
    title: str = ""
    name: str = ""
    price: str = "0.00"
    price_set: PriceSet | None = None
    quantity: int = 0
    current_quantity: int = 0
    fulfillable_quantity: int = 0
    sku: str | None = None
    variant_id: int | None = None
    variant_title: str | None = None
    variant_inventory_management: str | None = None
    product_id: int | None = None
    product_exists: bool = True
    vendor: str | None = None
    fulfillment_service: str = "manual"
    fulfillment_status: str | None = None
    gift_card: bool = False
    grams: int = 0
    taxable: bool = True
    requires_shipping: bool = True
    sales_line_item_group_id: int | None = None
    total_discount: str = "0.00"
    total_discount_set: PriceSet | None = None
    properties: list[LineItemProperty] = Field(default_factory=list)
    attributed_staffs: list[AttributedStaff] = Field(default_factory=list)
    tax_lines: list[dict] = Field(default_factory=list)
    duties: list[dict] = Field(default_factory=list)
    discount_allocations: list[dict] = Field(default_factory=list)

    @property
    def properties_dict(self) -> dict[str, str]:
        return {p.name: p.value for p in self.properties if p.name}


class ShippingLine(WebhookBase):
    id: int
    title: str = ""
    price: str = "0.00"
    price_set: PriceSet | None = None
    code: str | None = None
    source: str | None = None
    phone: str | None = None
    carrier_identifier: str | None = None
    requested_fulfillment_service_id: str | None = None
    is_removed: bool = False
    discounted_price: str = "0.00"
    discounted_price_set: PriceSet | None = None
    current_discounted_price_set: PriceSet | None = None
    tax_lines: list[dict] = Field(default_factory=list)
    discount_allocations: list[dict] = Field(default_factory=list)


class OrderCreateWebhook(WebhookBase):
    """Shopify orders/create webhook payload."""

    id: int
    admin_graphql_api_id: str = ""
    name: str = ""
    order_number: int = 0
    number: int = 0
    email: str | None = None
    contact_email: str | None = None
    phone: str | None = None

    created_at: str | None = None
    updated_at: str | None = None
    processed_at: str | None = None
    cancelled_at: str | None = None
    closed_at: str | None = None

    currency: str = "USD"
    presentment_currency: str = "USD"
    financial_status: str | None = None
    fulfillment_status: str | None = None

    total_price: str = "0.00"
    total_price_set: PriceSet | None = None
    subtotal_price: str = "0.00"
    subtotal_price_set: PriceSet | None = None
    total_tax: str = "0.00"
    total_tax_set: PriceSet | None = None
    total_discounts: str = "0.00"
    total_discounts_set: PriceSet | None = None
    total_line_items_price: str = "0.00"
    total_line_items_price_set: PriceSet | None = None
    total_outstanding: str = "0.00"
    total_tip_received: str = "0.00"
    total_weight: int = 0
    total_shipping_price_set: PriceSet | None = None

    current_subtotal_price: str = "0.00"
    current_subtotal_price_set: PriceSet | None = None
    current_total_price: str = "0.00"
    current_total_price_set: PriceSet | None = None
    current_total_tax: str = "0.00"
    current_total_tax_set: PriceSet | None = None
    current_total_discounts: str = "0.00"
    current_total_discounts_set: PriceSet | None = None
    current_shipping_price_set: PriceSet | None = None
    current_total_additional_fees_set: PriceSet | None = None
    current_total_duties_set: PriceSet | None = None

    total_cash_rounding_payment_adjustment_set: PriceSet | None = None
    total_cash_rounding_refund_adjustment_set: PriceSet | None = None
    original_total_additional_fees_set: PriceSet | None = None
    original_total_duties_set: PriceSet | None = None

    tags: str = ""
    token: str = ""
    test: bool = False
    confirmed: bool = False
    buyer_accepts_marketing: bool = False
    tax_exempt: bool = False
    taxes_included: bool = False
    duties_included: bool = False
    estimated_taxes: bool = False

    cancel_reason: str | None = None
    cart_token: str | None = None
    checkout_token: str | None = None
    confirmation_number: str | None = None
    customer_locale: str | None = None
    device_id: int | None = None
    landing_site: str | None = None
    landing_site_ref: str | None = None
    location_id: int | None = None
    merchant_business_entity_id: str | None = None
    merchant_of_record_app_id: int | None = None
    note: str | None = None
    order_status_url: str = ""
    po_number: str | None = None
    reference: str | None = None
    referring_site: str | None = None
    source_identifier: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    user_id: int | None = None
    app_id: int | None = None
    browser_ip: str | None = None

    client_details: ClientDetails | None = None
    customer: Customer | None = None
    billing_address: Address | None = None
    shipping_address: Address | None = None

    line_items: list[LineItem] = Field(default_factory=list)
    shipping_lines: list[ShippingLine] = Field(default_factory=list)
    note_attributes: list[NoteAttribute] = Field(default_factory=list)
    discount_codes: list[dict] = Field(default_factory=list)
    discount_applications: list[dict] = Field(default_factory=list)
    payment_gateway_names: list[str] = Field(default_factory=list)
    tax_lines: list[dict] = Field(default_factory=list)
    fulfillments: list[dict] = Field(default_factory=list)
    refunds: list[dict] = Field(default_factory=list)
    returns: list[dict] = Field(default_factory=list)
    line_item_groups: list[dict] = Field(default_factory=list)
    payment_terms: dict | None = None

    @property
    def tags_list(self) -> list[str]:
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


@dataclass
class OrderLineItemResult:
    product_id: str
    variant_id: str
    title: str
    variant_title: str
    quantity: int
    price: str
    is_waitlist: bool = False


@dataclass
class OrderCreateResult:
    order_id: str
    order_number: int | str
    email: str
    total_price: str
    financial_status: str
    line_items: list[OrderLineItemResult] = field(default_factory=list)
    has_waitlist_item: bool = False


def process_order_create(order: OrderCreateWebhook) -> OrderCreateResult:
    """Parse an orders/create webhook, flagging waitlist variant purchases."""
    items: list[OrderLineItemResult] = []
    has_waitlist = False

    for li in order.line_items:
        is_waitlist = "waitlist" in (li.variant_title or "").lower()
        if is_waitlist:
            has_waitlist = True
        items.append(OrderLineItemResult(
            product_id=str(li.product_id or ""),
            variant_id=str(li.variant_id or ""),
            title=li.title,
            variant_title=li.variant_title or "",
            quantity=li.quantity,
            price=li.price,
            is_waitlist=is_waitlist,
        ))

    return OrderCreateResult(
        order_id=str(order.id),
        order_number=order.order_number,
        email=order.email or "",
        total_price=order.total_price,
        financial_status=order.financial_status or "",
        line_items=items,
        has_waitlist_item=has_waitlist,
    )

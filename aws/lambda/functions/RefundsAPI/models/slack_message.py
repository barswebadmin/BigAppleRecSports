"""Evaluation payload sent to Slack and echoed to the HTTP caller."""

from dataclasses import asdict, dataclass, field

from models.shopify_order import RefundTransaction


@dataclass
class RefundEstimate:
    success: bool
    amount: float
    percentage: float | None
    penalty: float | None
    timing: str | None
    has_processing_fee: bool
    no_payment: bool
    message: str | None


@dataclass
class RefundResponse:
    email: str
    first_name: str
    last_name: str
    refund_to: str

    order_number: str
    order_id: str | None
    order_found: bool

    validation_passed: bool
    warnings: list[str]

    is_test: bool = True
    notes: str | None = None

    sport: str | None = None
    season: str | None = None
    day: str | None = None
    division: str | None = None

    product_id: str | None = None
    product_title: str | None = None

    season_start_date: str | None = None
    season_week_resolved: str | None = None

    order_total: float | None = None
    total_refunded: float | None = None
    refundable_balance: float | None = None
    is_cancelled: bool | None = None

    email_matched_against: str | None = None
    first_name_matched_against: str | None = None
    last_name_matched_against: str | None = None

    estimated_refund_to_original: RefundEstimate | None = None
    estimated_store_credit: RefundEstimate | None = None

    transactions: list[RefundTransaction] = field(default_factory=list)
    currency_code: str | None = None

    phone: str | None = None

    error: str | None = None

    def to_json(self) -> dict:
        return asdict(self)

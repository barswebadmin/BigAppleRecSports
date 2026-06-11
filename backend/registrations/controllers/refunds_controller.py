from __future__ import annotations

from http import HTTPStatus

from clients.shopify.models.connections import OrderForRefund
from models.api_base_model import ApiResponse
from models.refunds import (
    RefundCreateInput,
    RefundRequestInput,
    RequestRefundAnalysisData,
)
from services.orders_service import OrdersService
from services.refunds_service import RefundsService


class RefundsController:
    def __init__(self) -> None:
        self.service = RefundsService()
        self.orders_service = OrdersService()

    def validate_order_refund_eligibility(
        self,
        req: RefundRequestInput,
        order: OrderForRefund,
    ) -> tuple[HTTPStatus, str] | None:
        """Hard blocks only (non-200). Soft eligibility lives in :class:`RequestRefundAnalysisData`."""
        del req, order
        return None

    def _request_refund_analysis(
        self,
        req: RefundRequestInput,
        order: OrderForRefund,
    ) -> RequestRefundAnalysisData:
        order_total = float(order.total_price_set.amount) if order.total_price_set else 0.0
        total_refunded = sum(
            float(r.total_refunded_set.amount) for r in order.refunds if r.total_refunded_set is not None
        )
        refundable = max(0.0, order_total - total_refunded)

        product_html: str | None = None
        product_id: str | None = None
        if order.line_items:
            first = order.line_items[0]
            if first.product is not None:
                product_id = first.product.id
                product_html = first.product.description_html

        order_email = (order.customer.email or "").strip().lower() if order.customer else ""
        req_email = str(req.email_address).strip().lower()
        email_display = order.customer.email if order.customer and order.customer.email else ""

        warnings: list[str] = []
        eligible = True

        if order.is_cancelled:
            warnings.append("Order is cancelled")
            eligible = False

        if order_email and req_email != order_email:
            warnings.append("Email does not match order")
            eligible = False
        elif not order_email:
            warnings.append("Order has no customer email on file")
            eligible = False

        if refundable <= 0 and order_total > 0:
            warnings.append("Order has already been fully refunded")
            eligible = False
        elif total_refunded > 0 and refundable > 0:
            warnings.append(
                f"Order has been partially refunded (${total_refunded:.2f} of ${order_total:.2f})",
            )
            eligible = False

        est_original = self.service.refund_estimate_breakdown(
            order_total=order_total,
            ladder="original_payment",
            product_description_html=product_html,
            submitted_at=req.created_at,
        )
        est_credit = self.service.refund_estimate_breakdown(
            order_total=order_total,
            ladder="store_credit",
            product_description_html=product_html,
            submitted_at=req.created_at,
        )

        return RequestRefundAnalysisData(
            order_id=order.id,
            order_name=order.name,
            email_address=email_display,
            product_id=product_id,
            order_total=order_total,
            total_refunded=total_refunded,
            refundable_balance=refundable,
            is_cancelled=order.is_cancelled,
            has_existing_refunds=order.has_refunds,
            estimated_refund_to_original=est_original,
            estimated_store_credit=est_credit,
            eligible=eligible,
            warnings=warnings,
        )

    async def request_refund(self, req: RefundRequestInput) -> ApiResponse:
        order, errors = await self.orders_service.get_order_for_refund(
            order_id=req.order_id,
            order_number=req.order_number,
        )
        if errors:
            return ApiResponse(
                type=HTTPStatus.INTERNAL_SERVER_ERROR,
                errors=[e.message for e in errors if e.message],
            )
        if order is None:
            return ApiResponse(
                type=HTTPStatus.NOT_FOUND,
                errors=["Order not found"],
            )

        if blocked := self.validate_order_refund_eligibility(req, order):
            status, reason = blocked
            return ApiResponse(type=status, errors=[reason])

        data = self._request_refund_analysis(req, order)
        return ApiResponse(
            type=HTTPStatus.OK,
            data=data.model_dump(mode="json", by_alias=True, exclude_none=True),
        )

    def ineligible_for_refund(
        self,
        req: RefundCreateInput,
        order: OrderForRefund,
    ) -> HTTPStatus | None:
        """Check refund eligibility for execute path. Returns an HTTPStatus if blocked, None if eligible.

        Stub until 5.3: cancelled, email, amount vs available, capture transaction for ``original_payment``.
        """
        del req, order
        return None

    async def create_refund(self, req: RefundCreateInput) -> ApiResponse:
        order, order_errors = await self.orders_service.get_order_for_refund(
            order_id=req.order_id,
            order_number=None,
        )
        if order_errors:
            return ApiResponse(
                type=HTTPStatus.INTERNAL_SERVER_ERROR,
                errors=[e.message for e in order_errors if e.message],
            )
        if order is None:
            return ApiResponse(
                type=HTTPStatus.NOT_FOUND,
                errors=["Order not found"],
            )

        if self.ineligible_for_refund(req, order):
            return ApiResponse(
                type=HTTPStatus.UNPROCESSABLE_ENTITY,
                errors=["Refund not allowed for this order"],
            )

        effective = req.model_copy(update={"order_id": order.id})
        result, errors = await self.service.refund_shopify_order(effective)
        if errors:
            return ApiResponse(
                type=HTTPStatus.INTERNAL_SERVER_ERROR,
                errors=[e.message for e in errors if e.message],
            )
        return ApiResponse(type=HTTPStatus.CREATED, data=result)

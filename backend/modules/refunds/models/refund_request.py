"""Incoming request body for ``POST /refunds/validate``.

Pydantic v2 only — used for validation of the EXTERNAL request body (D28:
Pydantic is reserved for incoming external objects). Outgoing responses are
plain dicts / TypedDicts (see ``estimate.py``).

Field requirements (post-D28 wire-shape change):
  - REQUIRED: orderNumber, requestedRefundTo, requesterEmail,
    requesterFirstName, requesterLastName.
  - OPTIONAL: notes, transferRequest, sheetRowRef, isTest (defaults to
    False; Slack handler omits it when not in test mode).

REMOVED from prior drafts:
  - ``source``               — the request always originates from a sheet;
                               there is no other source.
  - ``slackChannel``         — channel routing is fully resolved on the
                               Slack side; the backend never receives a
                               channel hint.
  - ``policyConfirmation``   — the form gates submission on it; the backend
                               does not consume it. The sheet loader still
                               captures the cell value for diagnostic
                               logging only — it is NOT sent on this body.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from .estimate import EstimateRequest


class SheetRowRef(BaseModel):
    """Sheet-row pointer round-tripped through `/refunds/validate` for
    diagnostic logging. Not consumed by `EstimateService`."""

    model_config = ConfigDict(populate_by_name=True)

    spreadsheet_id: str = Field(..., alias="spreadsheetId")
    tab_id: str = Field(..., alias="tabId")
    row_number: int = Field(..., alias="rowNumber")


class RefundRequest(BaseModel):
    """The full validate-side request body sent by the Slack handler."""

    model_config = ConfigDict(populate_by_name=True)

    order_number: str = Field(..., alias="orderNumber")
    requested_refund_to: Literal["original_method", "store_credit"] = Field(
        ..., alias="requestedRefundTo"
    )
    requester_email: str = Field(..., alias="requesterEmail")
    requester_first_name: str = Field(..., alias="requesterFirstName")
    requester_last_name: str = Field(..., alias="requesterLastName")
    notes: str | None = None
    transfer_request: str | None = Field(None, alias="transferRequest")
    sheet_row_ref: SheetRowRef | None = Field(None, alias="sheetRowRef")
    is_test: bool = Field(False, alias="isTest")

    def to_estimate_request(
        self,
        *,
        submitted_at: datetime,
        season_start_date=None,
    ) -> "EstimateRequest":
        """Translate the wire body into the internal `EstimateRequest` value
        object consumed by `EstimateService.compute_estimate(...)`."""

        # Local import keeps things cyclic-friendly: `estimate.py` does not
        # import this Pydantic module at all (TypedDicts only).
        from .estimate import EstimateRequest

        return EstimateRequest(
            order_number=self.order_number,
            requested_refund_to=self.requested_refund_to,
            submitted_at=submitted_at,
            season_start_date=season_start_date,
            notes=self.notes,
        )

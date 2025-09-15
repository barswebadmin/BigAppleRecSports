# Shared utilities package
"""
Shared Utilities Package

This package contains Python utilities converted from Google Apps Script shared utilities,
providing common functionality for BARS applications.

Available modules:
- date_utils: Date parsing, formatting, and calculation utilities
- api_utils: HTTP API request helpers and utilities
- secrets_utils: Secret management and configuration utilities
- slack_utils: Slack API integration and message formatting
- sheet_utils: Google Sheets data processing utilities (structure only)
- discount_calculator: Discount calculation based on season timing
"""

from .date_utils import (
    format_date_for_shopify,
    parse_flexible_date,
    get_season_start,
    format_date_for_slack,
    get_business_days_between,
    add_business_days,
    format_date_only,
    format_date_and_time,
    extract_season_dates,
    format_time_only,
    get_current_season,
    is_business_day,
    get_next_business_day,
    get_previous_business_day,
)

from .api_utils import (
    make_api_request,
    build_shopify_graphql_request,
    retry_api_request,
    capitalize,
    format_two_decimal_points,
    normalize_order_number,
    make_shopify_api_request,
    handle_api_response,
    build_webhook_payload,
    safe_json_loads,
    safe_json_dumps,
)

from .secrets_utils import (
    SecretsManager,
    get_secret,
    set_secret,
    list_secret_keys,
    test_secrets,
    identify_potential_secrets,
    setup_development_secrets,
    validate_secret_format,
)

from .slack_utils import (
    SlackClient,
    get_slack_refunds_channel,
    get_joe_test_channel,
    get_order_url,
    get_product_url,
    get_slack_group_id,
    create_confirm_button,
    create_deny_button,
    create_refund_different_amount_button,
    create_cancel_button,
    create_restock_inventory_buttons,
    send_waitlist_validation_error,
    send_slack_message,
    update_slack_message,
)

from .sheet_utils import (
    SheetDataProcessor,
    parse_refund_row_data,
    get_request_details_from_order_number,
    generate_sheet_row_link,
    get_row_link_for_order,
    mark_order_as_processed_in_data,
    create_update_cell_info,
    create_append_row_info,
    validate_sheet_structure,
    extract_column_data,
)

from .discount_calculator import (
    create_discount_amount,
    calculate_discounted_price,
    get_discount_percentage_for_week,
    is_discount_eligible,
    get_next_discount_tier_info,
)

__all__ = [
    # Date utilities
    "format_date_for_shopify",
    "parse_flexible_date",
    "get_season_start",
    "format_date_for_slack",
    "get_business_days_between",
    "add_business_days",
    "format_date_only",
    "format_date_and_time",
    "extract_season_dates",
    "format_time_only",
    "get_current_season",
    "is_business_day",
    "get_next_business_day",
    "get_previous_business_day",
    # API utilities
    "make_api_request",
    "build_shopify_graphql_request",
    "retry_api_request",
    "capitalize",
    "format_two_decimal_points",
    "normalize_order_number",
    "make_shopify_api_request",
    "handle_api_response",
    "build_webhook_payload",
    "safe_json_loads",
    "safe_json_dumps",
    # Secrets utilities
    "SecretsManager",
    "get_secret",
    "set_secret",
    "list_secret_keys",
    "test_secrets",
    "identify_potential_secrets",
    "setup_development_secrets",
    "validate_secret_format",
    # Slack utilities
    "SlackClient",
    "get_slack_refunds_channel",
    "get_joe_test_channel",
    "get_order_url",
    "get_product_url",
    "get_slack_group_id",
    "create_confirm_button",
    "create_deny_button",
    "create_refund_different_amount_button",
    "create_cancel_button",
    "create_restock_inventory_buttons",
    "send_waitlist_validation_error",
    "send_slack_message",
    "update_slack_message",
    # Sheet utilities
    "SheetDataProcessor",
    "parse_refund_row_data",
    "get_request_details_from_order_number",
    "generate_sheet_row_link",
    "get_row_link_for_order",
    "mark_order_as_processed_in_data",
    "create_update_cell_info",
    "create_append_row_info",
    "validate_sheet_structure",
    "extract_column_data",
    # Discount calculator
    "create_discount_amount",
    "calculate_discounted_price",
    "get_discount_percentage_for_week",
    "is_discount_eligible",
    "get_next_discount_tier_info",
]

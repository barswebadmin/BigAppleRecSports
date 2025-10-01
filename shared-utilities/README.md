# BARS Shared Utilities

This package contains Python utilities converted from Google Apps Script shared utilities, providing common functionality for BARS applications.

## Installation

Add the shared-utilities directory to your Python path or install as a package:

```python
# Add to your Python path
import sys
sys.path.append('/path/to/shared-utilities/src')

# Then import utilities
from utils import get_secret, format_date_for_slack, create_discount_amount
```

## Available Modules

### 📅 Date Utilities (`date_utils`)

Date parsing, formatting, and calculation utilities converted from GAS dateUtils.gs.

```python
from utils.date_utils import format_date_for_slack, parse_flexible_date, get_business_days_between

# Format dates for Slack messages
formatted = format_date_for_slack(datetime.now())  # "Mon, Jan 15, 2024"

# Parse flexible date formats
date_obj = parse_flexible_date("01/15/2024")

# Calculate business days
days = get_business_days_between(start_date, end_date)
```

### 🌐 API Utilities (`api_utils`)

HTTP API request helpers and utilities.

```python
from utils.api_utils import make_api_request, retry_api_request, normalize_order_number

# Make API requests with error handling
response = make_api_request("https://api.example.com/data", method="POST", payload={"key": "value"})

# Retry with exponential backoff
result = retry_api_request(lambda: make_api_request(url), max_retries=3)

# Normalize order numbers
normalized = normalize_order_number("12345")  # "#12345"
```

### 🔐 Secrets Management (`secrets_utils`)

Secret management and configuration utilities.

```python
from utils.secrets_utils import get_secret, SecretsManager, test_secrets

# Get secrets from environment variables
shopify_token = get_secret('SHOPIFY_TOKEN')

# Use custom secrets manager
manager = SecretsManager(config_file='config.json')
api_key = manager.get_secret('API_KEY')

# Test secret accessibility
results = test_secrets(['SHOPIFY_TOKEN', 'SLACK_BOT_TOKEN'])
```

### 💬 Slack Utilities (`slack_utils`)

Slack API integration and message formatting.

```python
from utils.slack_utils import SlackClient, send_slack_message, create_confirm_button

# Send messages
client = SlackClient()
client.send_message("#general", "Hello World!")

# Create interactive buttons
button = create_confirm_button(
    email_matches=True,
    requestor_name={"first": "John", "last": "Doe"},
    refund_or_credit="refund",
    refund_amount=50.00,
    raw_order_number="#12345",
    order_id="gid://shopify/Order/123"
)
```

### 📊 Sheet Utilities (`sheet_utils`)

Google Sheets data processing utilities (provides structure for sheet operations).

```python
from utils.sheet_utils import SheetDataProcessor, parse_refund_row_data

# Process sheet data (2D arrays)
data = [
    ["Name", "Email", "Order"],
    ["John Doe", "john@example.com", "#12345"]
]

processor = SheetDataProcessor(data)
row = processor.find_row_by_column_value("Order", "#12345")
```

### 💰 Discount Calculator (`discount_calculator`)

Discount calculation based on season timing (without penalties).

```python
from utils.discount_calculator import create_discount_amount, calculate_discounted_price

# Calculate discount based on timing
discount_amount, description = create_discount_amount(
    season_start_date_str="03/15/2024",
    off_dates_str="03/22/2024,04/05/2024",
    total_amount_paid=100.00,
    request_submitted_at=datetime.now()
)

# Get final discounted price
final_price, discount, desc = calculate_discounted_price(
    original_price=100.00,
    season_start_date_str="03/15/2024"
)
```

## Discount Tiers

The discount calculator applies the following tiers:

- **Before season starts**: 0% discount
- **After week 1 starts**: 15% discount  
- **After week 2 starts**: 25% discount
- **After week 3 starts**: 35% discount
- **After week 4 starts**: 45% discount
- **After week 5 starts**: 55% discount

## Integration with Existing Services

### Using with ShopifyService

The utilities are designed to work alongside the existing `ShopifyService`:

```python
from new_structure_target.clients.shopify.shopify_service import ShopifyService
from utils.api_utils import retry_api_request
from utils.secrets_utils import get_secret

shopify_service = ShopifyService()

# Retry Shopify operations
def make_shopify_call():
    return shopify_service.get_customer_by_email("customer@example.com")

result = retry_api_request(make_shopify_call, max_retries=3)
```

### Environment Variables

Set up these environment variables for full functionality:

```bash
# Shopify
SHOPIFY_TOKEN=shpat_your_token_here
SHOPIFY_GRAPHQL_URL=https://your-store.myshopify.com/admin/api/2024-01/graphql.json

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL_REFUNDS_PROD=C1234567890
SLACK_CHANNEL_JOE_TEST=C0987654321

# API Endpoints
BACKEND_API_URL=https://your-backend.example.com
API_ENDPOINT=https://your-api.example.com

# Debug
DEBUG_EMAIL=debug@example.com
```

## Testing

Each utility module includes comprehensive error handling and logging. Test your setup:

```python
from utils.secrets_utils import test_secrets

# Test if secrets are properly configured
results = test_secrets()
for key, result in results.items():
    if result['status'] == 'success':
        print(f"✅ {key}: OK")
    else:
        print(f"❌ {key}: {result['message']}")
```

## Error Handling

All utilities include proper error handling and logging:

```python
import logging

# Configure logging to see utility debug information
logging.basicConfig(level=logging.INFO)

# All utilities will log their operations
from utils.date_utils import parse_flexible_date

try:
    date = parse_flexible_date("invalid-date")
except ValueError as e:
    print(f"Date parsing failed: {e}")
```

## Migration from GAS

These utilities maintain the same function signatures and behavior as their Google Apps Script counterparts, making migration straightforward:

| GAS Function | Python Equivalent |
|-------------|------------------|
| `getSecret('KEY')` | `get_secret('KEY')` |
| `formatDateForSlack(date)` | `format_date_for_slack(date)` |
| `normalizeOrderNumber(num)` | `normalize_order_number(num)` |
| `makeApiRequest(url, options)` | `make_api_request(url, **options)` |
| `sendSlackMessage(dest, msg)` | `send_slack_message(channel, text, blocks)` |

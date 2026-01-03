# BARS Scripts - Shopify Order Management

Standalone Python command-line tools for managing Shopify orders with beautiful rich terminal output. These scripts mirror the behavior of the bash-only scripts in `bars-scripts-standalone/` but with enhanced formatting and Python's rich library.

## Available Scripts

### 💬 Slack User Lookup (`./bars-scripts/slack-get-user`)
Look up Slack user details by email address or user ID.

**Usage:**
```bash
# By email
./bars-scripts/slack-get-user stephen@bigapplerecsports.com

# By user ID
./bars-scripts/slack-get-user U03LZKQSHEU

# Interactive prompt
./bars-scripts/slack-get-user

# JSON output
./bars-scripts/slack-get-user stephen@bigapplerecsports.com --json

# Use different bot token
./bars-scripts/slack-get-user --bot refunds stephen@example.com

# Different environment
./bars-scripts/slack-get-user stephen@example.com --env development
```

**Features:**
- **Smart detection**: Automatically detects email (contains `@`) vs user ID (starts with `U`)
- **Interactive prompt**: If no identifier provided, prompts for email or user ID
- **Multiple bot tokens**: Supports leadership, refunds, registrations, payment_assistance, exec, dev, web
- Displays name, email, display name, user ID, title, phone, timezone
- JSON or formatted text output
- Environment support (production/staging/dev)

**Example Output:**
```
Name: Stephen Torres
Email: stephen@bigapplerecsports.com
Display: Stephen (He/Him/His)
User ID: U03LZKQSHEU
Title: Vice Commissioner
Phone: 9292920391
Timezone: Eastern Standard Time
```

### 🛍️ Shopify Page & Template Fetcher (`./bars-scripts/shopify-get-page`)
Fetch Shopify page content or theme template assets via the Shopify Admin API.

**Usage:**
```bash
# Fetch a page by handle
./bars-scripts/shopify-get-page contact

# Fetch page as JSON
./bars-scripts/shopify-get-page --page contact --output json

# Fetch page as raw HTML
./bars-scripts/shopify-get-page --page contact --output html

# Fetch a theme template/asset
./bars-scripts/shopify-get-page --theme 134424232030 --asset templates/page.about-us-2.json

# List all assets in a theme
./bars-scripts/shopify-get-page --theme 134424232030 --list

# List assets matching a pattern
./bars-scripts/shopify-get-page --theme 134424232030 --list --filter about
```

**Features:**
- **Fetch pages**: Get page content by handle (e.g., `contact`, `about`)
- **Fetch theme assets**: Get templates, sections, or snippets from a theme
- **List assets**: Browse all assets in a theme with optional filtering
- **Multiple formats**: Output as text, JSON, or raw HTML
- Useful for extracting content to standardize leadership titles

**Common Use Cases:**
```bash
# Get the About Us page template for leadership titles
./bars-scripts/shopify-get-page --theme 134424232030 --asset templates/page.about-us-2.json

# List all page templates
./bars-scripts/shopify-get-page --theme 134424232030 --list --filter templates/page

# Extract contact page HTML for parsing
./bars-scripts/shopify-get-page contact --output html
```

**Example Output (List Assets):**
```
📦 Theme 134424232030 Assets (8 total):

📝 Templates:
  - templates/page.about-us-2.json
  - templates/page.contact.json
  - templates/page.json

📐 Sections:
  - sections/leadership-grid.liquid
  - sections/contact-form.liquid
```

### 🔍 Order Lookup (`./bars-scripts/order`)
Look up complete order details including cancellation status, refunds, line items, and transactions.

**Usage:**
```bash
./bars-scripts/order 43261
./bars-scripts/order  # Prompts for order number if not provided
./bars-scripts/order 43261 --json
./bars-scripts/order 43261 -P  # Show line item properties (form fields)
./bars-scripts/order 43261 --env development
```

**Features:**
- **Interactive prompt**: If no order number provided, prompts for input
- Displays order info, customer, line items, and transactions
- Shows refund details if any
- **`-P` flag**: Shows line item properties/custom attributes (e.g., registration form fields like "Date of Birth", "Emergency Contact", etc.) as formatted JSON after line items

### 👤 Customer Lookup (`./bars-scripts/customer`)
Look up customer details by email, customer ID, or name, including tags, addresses, and order count.

**Usage:**
```bash
# Search by email (auto-detected with @)
./bars-scripts/customer customer@example.com

# Search by first and last name
./bars-scripts/customer "John Doe"

# Search by first name only
./bars-scripts/customer "f:John"

# Search by last name only
./bars-scripts/customer "l:Doe"

# Prompt for email/ID/name if not provided
./bars-scripts/customer

# Search by customer ID (numeric format - auto-converted)
./bars-scripts/customer 123456789

# Search by customer ID (full gid format)
./bars-scripts/customer gid://shopify/Customer/123456789

# With JSON output
./bars-scripts/customer customer@example.com --json

# Different environment
./bars-scripts/customer customer@example.com --env development

# Using explicit flags (optional)
./bars-scripts/customer --email customer@example.com
./bars-scripts/customer --id gid://shopify/Customer/123456789
```

**Features:**
- **Name search**: Search by first name, last name, or both
  - `"First Last"` - searches for both names
  - `"f:First"` - searches by first name only
  - `"l:Last"` - searches by last name only
- **Multiple results handling**: If name search returns multiple customers, displays numbered list and prompts for selection
- **Interactive prompt**: If no identifier provided, prompts for email, ID, or name
- **Smart auto-detection**: Automatically detects email (contains `@`) vs customer ID vs name
- Numeric IDs automatically converted to full `gid://shopify/Customer/{id}` format
- Displays customer info, tags, order count
- Shows default address
- **Shows 5 most recent orders** with order numbers, IDs, and creation dates
- JSON or formatted text output
- Environment support (production/staging/dev)

**Example Output (Multiple Results):**
```bash
./bars-scripts/customer "f:Chase"

✅ Found 10 customers:
============================================================
1. Chase Weber (chaseweber44@gmail.com)
2. Chase Tucker (chasewtucker@gmail.com)
3. Chase Palmer (chasepalms@gmail.com)
...
============================================================

Enter number to view details (or press Enter to cancel): 2
```

### 🎂 Birthday Lookup (`./bars-scripts/bday`)
Get customer's date of birth by searching through their 5 most recent orders for "Date of Birth" line item properties.

**Usage:**
```bash
# By email
./bars-scripts/bday customer@example.com

# By name (supports same formats as customer lookup)
./bars-scripts/bday "John Doe"           # First and last name
./bars-scripts/bday "f:John"             # First name only
./bars-scripts/bday "l:Doe"              # Last name only

# By customer ID
./bars-scripts/bday 123456789

# Interactive prompt (supports email, name, or ID)
./bars-scripts/bday

# Different environment
./bars-scripts/bday customer@example.com --env development
```

**Features:**
- **Multiple search methods**: Email, customer ID, or name (first, last, or both)
- **Name search with selection**: If multiple customers match, displays list and prompts for selection
- **Concurrent fetching**: Searches 5 most recent orders in parallel for speed
- **Name tracking per birthday**: Each birthday is shown with the name entered in that specific order
- **Case insensitive**: Finds "Date of Birth", "date of birth", "First Name", "Last Name", etc.
- **Multiple registrations**: If customer registered multiple people or used different names, each is shown separately
- **DRY design**: Reuses customer lookup logic from `get_customer_details.py`
- Line-separated output for easy parsing
- Exits with error if customer not found or no orders exist

**Example Output:**
```
08/14/1987 - Joe Randazzo
```

Or if customer registered multiple people or used different formats:
```
09/18/1993 - Chase Tucker
09/18/93 - Chase Tucker
```

Or if multiple people registered under same email:
```
02/13/1987 - Rob Johnsen
02/13/1987 - Robert Johnsen
02131987 - Rob Johnsen
12/02/1994 - Alex Li
8/22/1989 - Rainier Abrenilla
```

**Note**: Each birthday displays the name from that order's registration form fields ("First Name" / "Last Name" properties), not from the customer profile. This shows exactly what was entered during each registration, which is useful when one email is used for multiple people.

### ❌ Order Cancellation (`./bars-scripts/cancel`)
Cancel orders with built-in safety checks, confirmation prompts, and already-cancelled detection. Shows product name before cancellation.

**Usage:**
```bash
./bars-scripts/cancel 43261              # With confirmation
./bars-scripts/cancel 43261 --reason FRAUD
./bars-scripts/cancel 43261 --env development
```

**Features:**
- Always prompts for confirmation (unless already cancelled)
- Shows product name before canceling
- Prompts for restock after cancellation (even if already cancelled)
- No customer notification
- No automatic restock
- No automatic refund

### 💰 Refund Processing (`./bars-scripts/refund`)
Process refunds with automatic calculation based on season dates and off dates. Supports both original payment method and store credit.

**Usage:**
```bash
./bars-scripts/refund 43261
./bars-scripts/refund 43261 --refund-type credit
./bars-scripts/refund 43261 --env development
```

**Features:**
- Calculates refund amounts based on submission timestamp
- Shows both original payment and store credit options
- Displays refund calculation details
- Handles pending and completed refunds
- Customer notification included

### 📦 Inventory Restock (`./bars-scripts/restock`)
Restock inventory for a Shopify order or product. Displays all variants and allows selection.

**Usage:**
```bash
./bars-scripts/restock 43261
./bars-scripts/restock 7452597878878  # Product ID
./bars-scripts/restock 43261 --env development
```

**Features:**
- Works with order numbers or product IDs
- Displays all product variants
- Interactive variant selection
- Defaults to restocking 1 unit

### 🔄 Cancel & Refund (`./bars-scripts/cancel-and-refund`)
Combined workflow to cancel and refund an order. Prompts for restock regardless of cancellation success/failure.

**Usage:**
```bash
./bars-scripts/cancel-and-refund 43261
./bars-scripts/cancel-and-refund 43261 --cancel-reason CUSTOMER
./bars-scripts/cancel-and-refund 43261 --env development
```

**Features:**
- Step 1: Cancel order (with confirmation)
- Step 2: Prompt for restock (always, regardless of cancellation)
- Step 3: Process refund
- Continues even if cancellation is aborted

## Quick Start

### Installation
No installation needed! Scripts use the existing backend virtual environment.

### Basic Usage

```bash
# Look up order
./bars-scripts/order 12345

# Look up customer by email
./bars-scripts/customer customer@example.com

# Look up customer by ID
./bars-scripts/customer 123456789

# Cancel order (with prompt)
./bars-scripts/cancel 12345

# Process refund
./bars-scripts/refund 12345

# Restock inventory
./bars-scripts/restock 12345

# Combined workflow
./bars-scripts/cancel-and-refund 12345
```

## Common Workflows

### Check Order Status
```bash
./bars-scripts/order 43261
```

### Cancel Order with Verification
```bash
# Step 1: Verify order details
./bars-scripts/order 43261

# Step 2: Cancel if needed
./bars-scripts/cancel 43261

# Step 3: Confirm cancellation
./bars-scripts/order 43261  # Should show [CANCELLED]
```

### Process Refund
```bash
# Step 1: Look up order
./bars-scripts/order 43261

# Step 2: Process refund (will prompt for timestamp and type)
./bars-scripts/refund 43261
```

### Complete Cancel & Refund Workflow
```bash
# Single command handles everything
./bars-scripts/cancel-and-refund 43261

# Flow:
# 1. Cancels order (with confirmation)
# 2. Prompts for restock (always)
# 3. Processes refund (with calculation)
```

## Environment Support

All scripts support:
- **Production** (default)
- **Staging**
- **Development**

Configured via `.env` file with environment-specific credentials.

## Safety Features

### Order Cancellation
- ✅ Detects already-cancelled orders
- ✅ Always prompts for confirmation (unless already cancelled)
- ✅ Shows product name before canceling
- ✅ Shows order details before confirmation
- ✅ No customer notifications
- ✅ No inventory restocking
- ✅ No automatic refunds
- ✅ Prompts for restock after cancellation

### Refund Processing
- ✅ Checks existing refunds (pending and completed)
- ✅ Calculates refund amounts based on season dates
- ✅ Shows both original payment and store credit options
- ✅ Displays refund calculation details
- ✅ Confirms amount before processing
- ✅ Customer notification included

### Inventory Restock
- ✅ Works with order numbers or product IDs
- ✅ Displays all variants for selection
- ✅ Interactive selection process
- ✅ Defaults to 1 unit per variant

## Requirements

- Backend virtual environment (`.venv`) - already installed
- `.env` file with Shopify credentials - already configured
- Dependencies: `requests`, `rich`, `python-dotenv` - already installed

## Script Behavior Details

### Cancel Script Behavior
1. Fetches order details
2. Checks if already cancelled
   - If yes: Shows cancellation info, prompts for restock, exits
   - If no: Shows order details including product name
3. Prompts for confirmation (always, unless already cancelled)
4. Cancels order if confirmed
5. Prompts for restock (always, even if already cancelled)

### Cancel & Refund Script Behavior
1. Step 1: Cancel order
   - Shows order details with product name
   - Prompts for confirmation
   - Continues even if cancellation fails or is aborted
2. Step 2: Restock prompt
   - Always prompts, regardless of cancellation success/failure
3. Step 3: Process refund
   - Fetches order details
   - Calculates refund amounts
   - Prompts for type and amount
   - Processes refund

### Refund Script Behavior
1. Fetches order details
2. Calculates payment summary
3. Extracts season dates from product description
4. Prompts for submission timestamp (or uses current time)
5. Calculates refund amounts for both types
6. Shows refund options with emojis (💵 Original, 🎫 Store Credit)
7. Prompts for refund type selection
8. Shows refund summary with calculation details
9. Confirms amount (yes or custom amount)
10. Processes refund

## Creating Shell Aliases

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Shopify order management
alias bars-order='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/order'
alias bars-customer='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/customer'
alias bars-bday='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/bday'
alias bars-cancel='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/cancel'
alias bars-refund='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/refund'
alias bars-restock='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/restock'
alias bars-cancel-refund='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/cancel-and-refund'

# Slack user management
alias bars-slack-user='/Users/jrandazzo/Documents/git-projects/bars/BigAppleRecSports-alt/bars-scripts/slack-get-user'
```

Then use from anywhere:
```bash
bars-order 43261
bars-customer --email customer@example.com
bars-cancel 43261
bars-refund 43261
```

## Examples

### Example 1: Customer Cancellation Request

Customer requests cancellation for order #43261:

```bash
# Verify order exists and isn't already cancelled
./bars-scripts/order 43261

# Cancel the order
./bars-scripts/cancel 43261 --reason CUSTOMER

# Verify cancellation
./bars-scripts/order 43261  # Shows [CANCELLED]
```

### Example 2: Fraud Detection

Suspected fraudulent order #43999:

```bash
# Check order details
./bars-scripts/order 43999

# Cancel immediately
./bars-scripts/cancel 43999 --reason FRAUD

# Type "yes" when prompted
```

### Example 3: Complete Refund Workflow

Process refund for order #40896:

```bash
# Process refund (will prompt for timestamp and type)
./bars-scripts/refund 40896

# Enter submission timestamp: 10/04/2025 11:03:19
# Select refund type: (o) Original or (c) Store Credit
# Confirm amount or enter custom amount
```

### Example 4: Combined Cancel & Refund

Cancel and refund order #42595:

```bash
# Single command handles everything
./bars-scripts/cancel-and-refund 42595

# Flow:
# 1. Shows order details with product name
# 2. Prompts: "Are you sure you want to cancel this order? (yes/no):"
# 3. If yes, cancels order
# 4. Always prompts: "Restock inventory? (yes/no):"
# 5. Processes refund with calculation
```

## Troubleshooting

### "No order found"
- Check order number is correct
- Verify environment (`--env development` for dev orders)
- Ensure order exists in Shopify

### "Command not found"
- Run from project root directory
- Or use absolute path to scripts
- Or set up shell aliases (see above)

### "ModuleNotFoundError"
- Use the wrapper scripts (`./bars-scripts/order`, etc.)
- Don't call Python scripts directly
- Ensure backend virtual environment is set up

### Permission Errors
- Verify Shopify API token is valid
- Check token has required scopes (`read_orders`, `write_orders`, `write_inventory`)
- Ensure `.env` file exists and has correct credentials

### SSL Certificate Errors
- Scripts auto-handle macOS Homebrew SSL certs
- If issues persist, set: `export SSL_CERT_FILE=/opt/homebrew/etc/openssl@3/cert.pem`

## Technical Details

All scripts:
- Use Shopify Admin API 2025-07 GraphQL endpoint
- Authenticate with tokens from `.env`
- Handle SSL certificates automatically (macOS Homebrew)
- Parse and format responses with rich library
- Provide detailed error messages
- Follow DRY principles with shared utilities

### Shared Utilities

All scripts use `shared_utils.py` for:
- Environment loading
- Shopify configuration
- Order fetching
- Order cancellation
- Refund creation (with retry logic)

### Code Organization

- `shared_utils.py` - Common utilities and API functions
- `cancel_order.py` - Order cancellation logic
- `refund_order.py` - Refund processing logic
- `restock_order.py` - Inventory restocking logic
- `cancel_and_refund.py` - Combined workflow
- `inventory_utils.py` - Inventory management utilities

## Comparison with Bash Scripts

These Python scripts mirror the behavior of `bars-scripts-standalone/` bash scripts:
- Same confirmation logic
- Same restock prompting behavior
- Same refund calculation logic
- Enhanced with rich terminal output
- Better error handling
- More detailed formatting

## Related Files

**Scripts:**
- `bars-scripts/get_order_details.py` - Order lookup Python implementation
- `bars-scripts/get_customer_details.py` - Customer lookup Python implementation
- `bars-scripts/get_bday.py` - Birthday lookup Python implementation
- `bars-scripts/cancel_order.py` - Order cancellation Python implementation
- `bars-scripts/refund_order.py` - Refund processing Python implementation
- `bars-scripts/restock_order.py` - Inventory restocking Python implementation
- `bars-scripts/cancel_and_refund.py` - Combined workflow Python implementation
- `bars-scripts/slack_get_user.py` - Slack user lookup Python implementation
- `bars-scripts/shared_utils.py` - Shared utilities

**Bash Wrappers:**
- `bars-scripts/order` - Order lookup bash wrapper
- `bars-scripts/customer` - Customer lookup bash wrapper
- `bars-scripts/bday` - Birthday lookup bash wrapper
- `bars-scripts/cancel` - Order cancellation bash wrapper
- `bars-scripts/refund` - Refund processing bash wrapper
- `bars-scripts/restock` - Inventory restocking bash wrapper
- `bars-scripts/cancel-and-refund` - Combined workflow bash wrapper
- `bars-scripts/slack-get-user` - Slack user lookup bash wrapper

**Standalone Bash Scripts:**
- `bars-scripts-standalone/` - Bash-only scripts that don't require Python

**Backend Integration:**
- `backend/modules/integrations/shopify/` - Shopify API integration
- `backend/modules/orders/` - Orders service
- `backend/config/shopify.py` - Shopify configuration

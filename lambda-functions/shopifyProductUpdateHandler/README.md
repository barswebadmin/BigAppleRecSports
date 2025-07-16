# Shopify Product Update Handler

Automatically updates product images to "sold out" versions when all relevant variants are out of stock.

## Overview

This Lambda function responds to Shopify product update webhooks and automatically changes product images to sport-specific "sold out" images when all relevant variants (Veteran, BIPOC, Trans, Early Bird, Open registration) have zero inventory.

## Architecture

The function has been refactored from a monolithic 215-line file into a modular structure following BARS Lambda patterns:

### File Structure

```
shopifyProductUpdateHandler/
├── lambda_function.py          # Main handler (clean, focused)
├── sport_detection.py          # Sport detection & configuration
├── shopify_image_updater.py    # Shopify API operations  
├── version.py                  # Version management
├── requirements.txt            # Dependencies
└── README.md                   # Documentation
```

### Modules

#### `sport_detection.py`
- **Sport detection logic**: Identifies sports from product titles/tags
- **Variant filtering**: Determines which variants are relevant for sold-out detection
- **Configuration**: Manages sport-to-image URL mappings

#### `shopify_image_updater.py`
- **REST API updates**: Primary image update method
- **GraphQL fallback**: Media replacement when REST fails
- **Error handling**: Rollback to original image on failure

#### `lambda_function.py`
- **Event processing**: Standardized event parsing and validation
- **Orchestration**: Coordinates sport detection and image updates
- **Response formatting**: Consistent API responses

## Usage

### Environment Variables

```bash
SHOPIFY_ACCESS_TOKEN=your_shopify_access_token
```

### Webhook Configuration

Configure Shopify webhook to send `product/update` events to this Lambda function.

### Supported Sports

- **Bowling**: Bowling_ClosedWaitList.png
- **Dodgeball**: Dodgeball_Closed.png  
- **Kickball**: Kickball_WaitlistOnly.png
- **Pickleball**: Pickleball_WaitList.png

## Improvements Made

### ✅ Consistency with Other Lambda Functions

- **Modular structure**: Follows pattern of `changePricesOfOpenAndWaitlistVariants`
- **Version management**: Includes `version.py` like other functions
- **Error handling**: Standardized error responses
- **Event parsing**: Uses shared patterns (with fallbacks)

### ✅ Code Organization

- **Single responsibility**: Each module has a clear purpose
- **Testability**: Modules can be unit tested independently  
- **Maintainability**: Changes isolated to specific modules
- **Readability**: Main handler is now ~100 lines vs 215

### ✅ Shared Layer Integration

The function is designed to use `bars-common-utils` lambda layer:

```python
from bars_common_utils.event_utils import parse_event_body
from bars_common_utils.response_utils import format_response
```

With fallback implementations for local development.

### ✅ Enhanced Error Handling

- **Detailed error responses**: Specific error messages and codes
- **Graceful degradation**: Fallback strategies for failed operations
- **Rollback capability**: Restores original image if updates fail

### ✅ Type Safety

- **Type hints**: Proper typing throughout
- **Input validation**: Required field checking
- **Return types**: Consistent response structures

## Deployment

### With Lambda Layer (Recommended)

1. Deploy with `bars-common-utils` layer attached
2. Uses shared utilities for consistency
3. Smaller deployment package

### Standalone Deployment

1. Function includes fallback implementations
2. Works without lambda layer
3. Slightly larger but fully self-contained

## Future Enhancements

1. **Unit tests**: Add comprehensive test coverage
2. **More sports**: Easy to add new sports by updating `SPORT_IMAGE_URLS`
3. **Configuration**: Move image URLs to environment variables
4. **Monitoring**: Add CloudWatch metrics and alarms

## Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|--------|
| **File structure** | 1 monolithic file (215 lines) | 4 focused modules |
| **Error handling** | Basic print statements | Structured HTTP responses |
| **Reusability** | Duplicate Shopify utilities | Shared layer integration |
| **Testability** | Hard to test individual parts | Modular, testable components |
| **Consistency** | Custom patterns | Follows BARS Lambda standards |
| **Type safety** | No type hints | Full type annotations |
| **Documentation** | Minimal comments | Comprehensive docstrings | 
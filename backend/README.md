# Big Apple Rec Sports Backend API

> 📚 **Documentation**: See [README.md](../README.md#api-endpoints) for API documentation and [README_EXT/1_CONTRIBUTING.md#backend-development](../README_EXT/1_CONTRIBUTING.md#backend-development) for development setup

A Python FastAPI backend service for managing Big Apple Rec Sports operations, including leadership discount processing.

## 🚀 **Production URL**
**https://barsbackend.onrender.com**

## Features

- **CSV Processing**: Convert Google Sheets data to leadership tags and discount codes
- **Smart Email Detection**: Automatically detects email columns in CSV data
- **Batch Processing**: Efficient processing of large customer lists (optimized for performance)
- **Display Text Generation**: Backend generates formatted results for frontend display
- **Shopify Integration**: GraphQL API integration with customer management
- **Leadership Segmentation**: Automatic customer tagging and segment creation
- **Seasonal Discounts**: Winter, Spring, Summer, Fall discount code generation

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── run.py                  # Standalone run script
├── config.py               # Configuration and environment settings
├── requirements.txt        # Python dependencies
├── services/               # Business logic services
│   ├── shopify_service.py  # Shopify API integration
│   └── leadership_service.py # Leadership processing logic
├── routers/                # API route handlers
│   └── leadership.py       # Leadership endpoints
├── models/                 # Pydantic request/response models
│   └── requests.py         # Request models
└── utils/                  # Utility functions
    └── date_utils.py       # Date/season calculations
```

## Setup

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   Create a `.env` file in the backend directory:
   ```
   SHOPIFY_STORE=your-store.myshopify.com
   SHOPIFY_TOKEN=your_shopify_access_token
   ENVIRONMENT=development
   ```

3. **Run the Server**
   ```bash
   # Option 1: Using make commands (recommended)
   make start        # Start the server
   make tunnel       # Start ngrok tunnel (for development with Google Apps Script)
   make dev          # Start both server and tunnel

   # Option 2: Using uvicorn directly
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### Leadership Management

#### POST `/leadership/addTags`
Process CSV data and add leadership tags to customers.

**Request Body:**
```json
{
  "csv_data": [
    ["Personal Email", "First Name", "Last Name"],
    ["user1@example.com", "John", "Doe"],
    ["user2@example.com", "Jane", "Smith"]
  ],
  "spreadsheet_title": "2024 Leadership List",
  "year": 2024
}
```

**Response:**
```json
{
  "success": true,
  "year": 2024,
  "objects_created": 2,
  "emails_extracted": 2,
  "valid_customers": [
    {"id": "gid://shopify/Customer/789", "email": "user1@example.com", "existing_tags": ["customer"]}
  ],
  "invalid_emails": [],
  "discount_results": [...],
  "display_text": "✅ Leadership Processing Complete!\n\n📊 CSV Analysis:\n• Total rows processed: 3\n..."
}
```

#### GET `/leadership/health`
Health check for the leadership service.

### General Endpoints

#### GET `/`
API root with version information.

#### GET `/health`
General health check.

## Reusable Services

### ShopifyService
Provides reusable methods for Shopify integration:
- `get_customer_id(email)` - Get customer ID by email
- `add_tag_to_customer(customer_id, tag)` - Add tag to customer
- `create_segment(name, query)` - Create customer segment
- `create_discount_code(...)` - Create discount codes

### LeadershipService
Business logic for leadership processing:
- `process_leadership_emails(emails, year)` - Main processing function

## Deployment (Render)

This app is configured for deployment on [Render](https://render.com) using the `render.yaml` configuration.

### Deploy Steps:
1. **Connect Repository**: Link your GitHub repository to Render
2. **Environment Variables**: Set `SHOPIFY_TOKEN` in Render dashboard
3. **Deploy**: Deploy from `main` branch
4. **Access**: App will be available at `https://barsbackend.onrender.com`

### Environment Variables (Production):
- `ENVIRONMENT=production` (automatically set)
- `SHOPIFY_STORE=09fe59-3.myshopify.com` (default)
- `SHOPIFY_TOKEN=your_token_here` (set in Render dashboard)

## Google Apps Script Integration

Update your Google Apps Script to use the production URL:

```javascript
const LOCAL_BACKEND_URL = "https://barsbackend.onrender.com";
```

The script will automatically:
- Send CSV data to `/leadership/addTags` endpoint
- Display formatted results from `result.display_text`

## Development

### Adding New Services

1. Create a new service in `services/` directory
2. Follow the pattern of existing services
3. Add appropriate router in `routers/`
4. Register router in `main.py`

### Testing

```bash
# Test services (unit tests)
make test-services

# Test API endpoints (integration tests)
make test-api

# Test basic health endpoints
make test
```

The modular structure makes it easy to test individual components:
- **Service Tests**: Located next to service files (`services/test_*.py`)
- **API Tests**: Integration tests in `routers/test_*.py`
- **Mock-Free**: Tests work with real Shopify API (ensure valid token)

## Security

- Store sensitive data (Shopify tokens) in environment variables
- Configure CORS appropriately for production
- Use HTTPS in production
- Consider rate limiting for API endpoints

#!/usr/bin/env python3
"""
Generate a valid Shopify webhook signature for testing
"""

import hmac
import hashlib
import base64
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('../.env')

def generate_signature(body: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook body"""
    signature = hmac.new(
        secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    return base64.b64encode(signature).decode('utf-8')

if __name__ == "__main__":
    webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
    
    if not webhook_secret:
        print("❌ SHOPIFY_WEBHOOK_SECRET not found in environment")
        exit(1)
    
    # Example webhook body
    test_body = '{"id": 123, "title": "Test Product", "variants": [{"inventory_quantity": 5}]}'
    
    # Generate signature
    signature = generate_signature(test_body, webhook_secret)
    
    print("🔐 Generated webhook signature for testing:")
    print(f"Body: {test_body}")
    print(f"Signature: {signature}")
    print()
    print("🧪 Test command:")
    print(f'curl -X POST http://127.0.0.1:8000/webhooks/shopify \\')
    print(f'  -H "Content-Type: application/json" \\')
    print(f'  -H "x-shopify-topic: products/update" \\')
    print(f'  -H "x-shopify-hmac-sha256: {signature}" \\')
    print(f'  -d \'{test_body}\'')

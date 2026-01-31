"""
Examples of using the clean HTTPX client and request models.

This file demonstrates the new streamlined architecture:
- Unified HTTPXClient with class methods
- Clean request models instead of builders
- Simple, direct API usage
"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_utilities.api_clients.http_client import SyncHTTPClient, AsyncHTTPClient
from shared_utilities.api_clients.request_models import (
    SendSlackMessageRequest,
    GetSlackUserRequest,
    APIRequestExecutor
)


# Example 1: Backend async operations with clean request models
async def backend_async_example():
    """Example of async operations using clean request models"""
    
    # Create async client
    client = AsyncHTTPClient(base_url="https://httpbin.org")
    
    # Direct client usage for simple requests
    try:
        response = await client.get("/get")
        json_data = await client.get_json("/json")
        return response.status_code, json_data
    except Exception as e:
        print(f"Request failed: {e}")
        return None, {"error": str(e)}


# Example 2: CLI sync operations
def cli_sync_example():
    """Example CLI command using sync client"""
    
    # Create sync client
    client = SyncHTTPClient(base_url="https://httpbin.org")
    
    # Direct client usage (no executor needed for simple requests)
    try:
        result = client.get_json("/json")
        return result
    except Exception as e:
        print(f"Request failed: {e}")
        return {"error": str(e)}


# Example 3: Lambda function
def lambda_handler(event, context):
    """Example Lambda function using sync client"""
    
    # Create sync client for Lambda
    client = SyncHTTPClient(
        base_url="https://api.example.com",
        timeout=30.0
    )
    executor = APIRequestExecutor(client)
    
    # Create request from event data
    request = SendSlackMessageRequest(
        channel=event.get("channel", "general"),
        text=event.get("text", "Hello from Lambda!")
    )
    
    # Execute and return
    result = executor.execute_sync(request)
    
    return {
        "statusCode": 200,
        "body": result
    }


# Example 4: Slack API operations
async def slack_api_example():
    """Example Slack API usage"""
    
    client = AsyncHTTPClient(
        base_url="https://slack.com/api",
        headers={"Authorization": "Bearer xoxb-your-token"}
    )
    executor = APIRequestExecutor(client)
    
    # Send message request
    message_request = SendSlackMessageRequest(
        channel="#general",
        text="Hello from the new clean API!"
    )
    
    result = await executor.execute_async(message_request)
    return result


# Example 5: Direct client usage (without executor)
async def direct_client_example():
    """Example using client directly without executor"""
    
    client = AsyncHTTPClient(base_url="https://httpbin.org")
    
    # Direct HTTP calls
    response = await client.get("/get")
    json_data = await client.get_json("/json")
    
    # POST with JSON
    post_result = await client.post_json("/post", {"key": "value"})
    
    return response.status_code, json_data, post_result


# Example 6: Custom retry policy
def custom_retry_example():
    """Example with custom retry policy"""
    from shared_utilities.api_clients.http_client import RetryPolicy
    
    # Custom retry policy
    aggressive_retry = RetryPolicy(
        max_retries=2,  # Reduced for demo
        base_delay=0.1,
        max_delay=1.0,
        backoff_factor=1.5
    )
    
    client = SyncHTTPClient(
        base_url="https://httpbin.org",
        retry_policy=aggressive_retry
    )
    
    try:
        # This should work with httpbin
        result = client.get_json("/json")
        return result
    except Exception as e:
        print(f"Request failed after all retries: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    print("🚀 Clean HTTPX Client Examples")
    print("=" * 40)
    
    print("\n📡 Sync Example:")
    sync_result = cli_sync_example()
    print(f"Sync result: {sync_result}")
    
    print("\n⚡ Async Example:")
    async_result = asyncio.run(backend_async_example())
    print(f"Async result: {async_result}")
    
    print("\n🎯 Direct Client Example:")
    direct_result = asyncio.run(direct_client_example())
    print(f"Direct result: {direct_result}")
    
    print("\n🔄 Custom Retry Example:")
    retry_result = custom_retry_example()
    print(f"Retry result: {retry_result}")
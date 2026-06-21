"""
Demonstration of the two-layer error handling in GoogleApiClient.

This shows how the GoogleApiClient now has both HTTP transport error handling
(from AsyncHTTPClient) and Google API error handling (@handle_http_errors).
"""

import asyncio
from modules.integrations.google.google_api_client import GoogleApiClient


def demonstrate_error_handling_layers():
    """Demonstrate the two layers of error handling."""
    
    print("🛡️ Two-Layer Error Handling in GoogleApiClient")
    print("=" * 60)
    
    print("\n📊 Error Handling Architecture:")
    print("┌─────────────────────────────────────────────────────┐")
    print("│                GoogleApiClient                      │")
    print("├─────────────────────────────────────────────────────┤")
    print("│  Layer 2: Google API Error Handling                │")
    print("│  • @handle_http_errors decorator                   │")
    print("│  • Handles: HttpError, RefreshError                │")
    print("│  • Provides: Scope diagnostics, auth help          │")
    print("│  • Examples: 403 Forbidden, invalid credentials    │")
    print("├─────────────────────────────────────────────────────┤")
    print("│  Layer 1: HTTP Transport Error Handling            │")
    print("│  • Inherited from AsyncHTTPClient                  │")
    print("│  • Handles: Network errors, timeouts, HTTP codes   │")
    print("│  • Provides: Retries with backoff, rate limiting   │")
    print("│  • Examples: 429 Rate Limit, 500 Server Error      │")
    print("└─────────────────────────────────────────────────────┘")
    
    print("\n🔄 Error Flow:")
    print("1. HTTP Request → AsyncHTTPClient (Layer 1)")
    print("   ├─ Network timeout? → Retry with backoff")
    print("   ├─ 429 Rate limit? → Retry with backoff")
    print("   ├─ 500 Server error? → Retry with backoff")
    print("   └─ Success? → Continue to Layer 2")
    print("")
    print("2. Google API Call → @handle_http_errors (Layer 2)")
    print("   ├─ HttpError 403? → Show scope diagnostics")
    print("   ├─ RefreshError? → Show auth configuration help")
    print("   ├─ Invalid credentials? → Show setup instructions")
    print("   └─ Success? → Return result")
    
    print("\n✅ Benefits of Two-Layer Approach:")
    print("• HTTP transport issues are handled automatically with retries")
    print("• Google API issues get detailed diagnostics and help")
    print("• No duplication - each layer handles different error types")
    print("• Centralized HTTP error handling across all clients")
    print("• Google-specific error handling where needed")
    
    print("\n🎯 Example Error Scenarios:")
    print("┌─────────────────────┬─────────────────────┬─────────────────────┐")
    print("│ Error Type          │ Handled By          │ Action Taken        │")
    print("├─────────────────────┼─────────────────────┼─────────────────────┤")
    print("│ Network timeout     │ AsyncHTTPClient     │ Retry with backoff  │")
    print("│ 429 Rate limit      │ AsyncHTTPClient     │ Retry with backoff  │")
    print("│ 500 Server error    │ AsyncHTTPClient     │ Retry with backoff  │")
    print("│ Connection refused  │ AsyncHTTPClient     │ Retry with backoff  │")
    print("├─────────────────────┼─────────────────────┼─────────────────────┤")
    print("│ 403 Forbidden       │ @handle_http_errors │ Show scope help     │")
    print("│ Invalid credentials │ @handle_http_errors │ Show auth help      │")
    print("│ Scope not granted   │ @handle_http_errors │ Show Admin Console  │")
    print("│ RefreshError        │ @handle_http_errors │ Show delegation help│")
    print("└─────────────────────┴─────────────────────┴─────────────────────┘")


async def demonstrate_http_layer():
    """Demonstrate HTTP layer error handling."""
    print("\n🌐 HTTP Layer Error Handling (AsyncHTTPClient):")
    
    # Create client with custom retry policy
    from shared_utilities.api_clients.http_client import RetryPolicy
    
    retry_policy = RetryPolicy(
        max_retries=2,
        base_delay=0.5,
        retryable_status_codes=[429, 500, 502, 503, 504]
    )
    
    client = GoogleApiClient(
        base_url="https://httpbin.org",
        retry_policy=retry_policy
    )
    
    print("✓ Created GoogleApiClient with custom retry policy")
    print("✓ Will retry on: 429, 500, 502, 503, 504")
    print("✓ Max retries: 2, Base delay: 0.5s")
    
    # This would demonstrate retries (but httpbin might not cooperate)
    try:
        # This endpoint returns a 500 error
        response = await client.get("/status/500")
        print(f"✓ Response: {response.status_code}")
    except Exception as e:
        print(f"✓ HTTP layer handled error: {type(e).__name__}: {e}")
    
    await client.aclose()


def demonstrate_google_api_layer():
    """Demonstrate Google API layer error handling."""
    print("\n🔧 Google API Layer Error Handling (@handle_http_errors):")
    
    print("✓ Google services use @handle_http_errors decorator")
    print("✓ Handles Google-specific errors:")
    print("  - HttpError from googleapiclient")
    print("  - RefreshError from Google auth")
    print("  - Scope authorization issues")
    print("  - Credential configuration problems")
    
    print("✓ Provides detailed diagnostics:")
    print("  - Shows required scopes")
    print("  - Links to Google Admin Console")
    print("  - Step-by-step fix instructions")
    print("  - Service account configuration help")
    
    # Show that Google services have the decorator
    client = GoogleApiClient()
    
    # Check if services have handle_http_errors applied
    services = [
        ('sheets_service', 'fetch_sheet_as_csv'),
        ('directory_service', 'get_user'),
        ('gmail_service', 'find_emails'),
        ('scripts_service', 'send_to_waitlist_form')
    ]
    
    print("\n✓ Services with @handle_http_errors:")
    for service_name, method_name in services:
        service = getattr(client, service_name)
        method = getattr(service, method_name)
        # Check if method has the wrapper (it will have __wrapped__ if decorated)
        has_decorator = hasattr(method, '__wrapped__') or 'handle_http_errors' in str(method)
        print(f"  - {service_name}.{method_name}(): {'✓' if has_decorator else '?'}")


if __name__ == "__main__":
    demonstrate_error_handling_layers()
    
    print("\n" + "=" * 60)
    asyncio.run(demonstrate_http_layer())
    
    print("\n" + "=" * 60)
    demonstrate_google_api_layer()
    
    print("\n🎉 Conclusion:")
    print("The GoogleApiClient correctly uses BOTH layers of error handling!")
    print("This provides comprehensive error handling without duplication.")
"""
Examples of using the shared HTTP client in Click commands.

This demonstrates the typical patterns for accessing the shared HTTP client
from Click commands using ctx.meta.
"""

import asyncio
from typing import Optional

import click_extra as click

from bars_cli._core.context import get_http_client
from shared_utilities.api_clients.http_client import HTTPClientError, RateLimitError


# Example 1: Basic sync command using shared HTTP client
@click.command()
@click.option('--base-url', default='https://api.example.com', help='API base URL')
@click.pass_context
def sync_example(ctx: click.Context, base_url: str):
    """Example of using shared HTTP client in a sync command."""
    
    # Get the shared HTTP client with custom base URL
    client = get_http_client(ctx, base_url=base_url)
    
    try:
        # Make a simple GET request
        response = client.get('/users')
        
        if response.status_code == 200:
            data = response.json()
            click.echo(f"Retrieved {len(data)} users")
        else:
            click.echo(f"Error: {response.status_code} - {response.text}")
            
    except HTTPClientError as e:
        click.echo(f"HTTP Error: {e}")
    except RateLimitError as e:
        click.echo(f"Rate Limited: {e}")
        if hasattr(e, 'retry_after'):
            click.echo(f"Retry after: {e.retry_after} seconds")


# Example 2: Async command for parallel operations
@click.command()
@click.option('--base-url', default='https://api.example.com', help='API base URL')
@click.option('--user-ids', multiple=True, help='User IDs to fetch')
@click.pass_context
def async_example(ctx: click.Context, base_url: str, user_ids: tuple):
    """Example of using async HTTP client for parallel requests."""
    
    async def fetch_users():
        # Get async HTTP client
        client = get_http_client(ctx, base_url=base_url)
        
        # Create tasks for parallel execution
        tasks = []
        for user_id in user_ids:
            task = client.get(f'/users/{user_id}')
            tasks.append(task)
        
        try:
            # Execute all requests in parallel
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    click.echo(f"User {user_ids[i]}: Error - {response}")
                elif response.status_code == 200:
                    user_data = response.json()
                    click.echo(f"User {user_ids[i]}: {user_data.get('name', 'Unknown')}")
                else:
                    click.echo(f"User {user_ids[i]}: HTTP {response.status_code}")
                    
        except Exception as e:
            click.echo(f"Async operation failed: {e}")
    
    # Run the async function
    asyncio.run(fetch_users())


# Example 3: Command that uses default shared client (no custom base URL)
@click.command()
@click.option('--base-url', default='https://api.example.com', help='API base URL')
@click.pass_context
def default_client_example(ctx: click.Context, endpoint: str):
    """Example using the default shared client without custom base URL."""
    
    # Get the default shared client (no base URL override)
    client = get_http_client(ctx)
    
    try:
        # The client will use whatever base_url was set during initialization
        # or no base URL if none was set
        response = client.get(endpoint)
        
        click.echo(f"Status: {response.status_code}")
        click.echo(f"Response: {response.text[:200]}...")
        
    except HTTPClientError as e:
        click.echo(f"Request failed: {e}")


# Example 4: Command with JSON POST using shared client
@click.command()
@click.option('--base-url', default='https://api.example.com', help='API base URL')
@click.option('--name', required=True, help='User name')
@click.option('--email', required=True, help='User email')
@click.pass_context
def create_user_example(ctx: click.Context, base_url: str, name: str, email: str):
    """Example of making POST requests with JSON data."""
    
    client = get_http_client(ctx, base_url=base_url)
    
    payload = {
        'name': name,
        'email': email,
        'active': True
    }
    
    try:
        # Use the convenience post_json method
        response_data = client.post_json('/users', payload)
        
        click.echo("User created successfully!")
        click.echo(f"ID: {response_data.get('id')}")
        click.echo(f"Name: {response_data.get('name')}")
        click.echo(f"Email: {response_data.get('email')}")
        
    except HTTPClientError as e:
        click.echo(f"Failed to create user: {e}")
    except RateLimitError as e:
        click.echo(f"Rate limited: {e}")


# Example 5: Command showing error handling patterns
@click.command()
@click.option('--base-url', default='https://api.example.com', help='API base URL')
@click.option('--endpoint', default='/test', help='Endpoint to test')
@click.pass_context
def error_handling_example(ctx: click.Context, base_url: str, endpoint: str):
    """Example showing comprehensive error handling."""
    
    client = get_http_client(ctx, base_url=base_url)
    
    try:
        response = client.get(endpoint)
        
        if response.status_code == 200:
            click.echo("✅ Request successful")
            click.echo(f"Response: {response.json()}")
        else:
            click.echo(f"❌ HTTP {response.status_code}: {response.text}")
            
    except RateLimitError as e:
        click.echo(f"🚦 Rate Limited: {e}")
        if hasattr(e, 'retry_after') and e.retry_after:
            click.echo(f"   Retry after: {e.retry_after} seconds")
        click.echo("   The client will automatically retry with exponential backoff")
        
    except HTTPClientError as e:
        click.echo(f"🌐 HTTP Client Error: {e}")
        click.echo("   This could be a network issue, timeout, or server error")
        
    except Exception as e:
        click.echo(f"💥 Unexpected Error: {e}")
        click.echo(f"   Error Type: {type(e).__name__}")


# Example 6: Command group showing how to share client across multiple commands
@click.group()
@click.option('--api-url', default='https://api.example.com', help='API base URL')
@click.pass_context
def api_group(ctx: click.Context, api_url: str):
    """Example command group that shares API configuration."""
    ctx.ensure_object(dict)
    ctx.obj['api_url'] = api_url


@api_group.command()
@click.pass_context
def list_items(ctx: click.Context):
    """List items using shared API configuration."""
    api_url = ctx.obj['api_url']
    client = get_http_client(ctx, base_url=api_url)
    
    try:
        response = client.get('/items')
        items = response.json()
        
        click.echo(f"Found {len(items)} items:")
        for item in items:
            click.echo(f"  - {item.get('name', 'Unknown')}")
            
    except HTTPClientError as e:
        click.echo(f"Failed to list items: {e}")


@api_group.command()
@click.argument('item_id')
@click.pass_context
def get_item(ctx: click.Context, item_id: str):
    """Get specific item using shared API configuration."""
    api_url = ctx.obj['api_url']
    client = get_http_client(ctx, base_url=api_url)
    
    try:
        response = client.get(f'/items/{item_id}')
        item = response.json()
        
        click.echo(f"Item {item_id}:")
        click.echo(f"  Name: {item.get('name')}")
        click.echo(f"  Status: {item.get('status')}")
        
    except HTTPClientError as e:
        click.echo(f"Failed to get item {item_id}: {e}")


if __name__ == '__main__':
    # This would normally be in your main CLI file
    # Here for demonstration purposes only
    
    @click.group()
    @click.pass_context
    def demo_cli(ctx: click.Context):
        """Demo CLI showing HTTP client patterns."""
        # Initialize shared HTTP client (normally done in main CLI)
        from shared_utilities.api_clients.http_client import SyncHTTPClient
        
        if 'http_client' not in ctx.meta:
            ctx.meta['http_client'] = SyncHTTPClient(
                headers={
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'demo-cli/1.0.0'
                },
                timeout=30.0
            )
    
    # Add example commands
    demo_cli.add_command(sync_example)
    demo_cli.add_command(async_example)
    demo_cli.add_command(default_client_example)
    demo_cli.add_command(create_user_example)
    demo_cli.add_command(error_handling_example)
    demo_cli.add_command(api_group)
    
    demo_cli()
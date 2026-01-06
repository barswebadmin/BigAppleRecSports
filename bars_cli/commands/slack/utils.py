"""
Shared utilities for Slack CLI commands.
"""
from typing import Optional, Dict, Any, List

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Import from backend (sys.path is set in main.py)
from config import config


def get_bot_token(bot_name: str) -> str:
    """
    Get Slack bot token by bot name.
    
    Args:
        bot_name: Name of the bot (dev, exec, leadership, etc.)
        
    Returns:
        Bot token string
        
    Raises:
        click.BadParameter: If bot name is invalid
    """
    bot_name = bot_name.lower()
    
    bot_map = {
        'dev': config.Slack.Bots.Dev,
        'exec': config.Slack.Bots.Exec,
        'leadership': config.Slack.Bots.Leadership,
        'payment_assistance': config.Slack.Bots.PaymentAssistance,
        'refunds': config.Slack.Bots.Refunds,
        'registrations': config.Slack.Bots.Registrations,
        'web': config.Slack.Bots.Web,
    }
    
    bot = bot_map.get(bot_name)
    if not bot:
        available = ', '.join(bot_map.keys())
        raise click.BadParameter(
            f"Unknown bot: {bot_name}. Available: {available}",
            param_hint='--bot'
        )
    
    return bot.token


def list_all_channels(
    client: WebClient,
    display: bool = True
) -> list:
    """
    List all public channels visible to the bot.
    
    Note: Only lists public channels. Private channels would require 'groups:read' scope.
    
    Args:
        client: Initialized Slack WebClient
        display: If True, print status messages
        
    Returns:
        List of channel dicts
    """
    try:
        channels = []
        cursor = None
        
        while True:
            response = client.conversations_list(
                types="public_channel",
                cursor=cursor,
                limit=200
            )
            
            if response['ok']:
                response_channels = response.get('channels', [])
                if response_channels:
                    channels.extend(response_channels)
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            else:
                if display:
                    click.echo(f"❌ Error listing channels: {response.get('error', 'Unknown error')}", err=True)
                return []
        
        return channels
        
    except SlackApiError as e:
        if display:
            error_msg = e.response['error']
            click.echo(f"❌ Error listing channels: {error_msg}", err=True)
            if error_msg == 'missing_scope':
                click.echo(f"   Full response: {e.response}", err=True)
        return []


def lookup_channel_by_name(
    client: WebClient,
    channel_name: str,
    display: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack channel by name.
    
    Args:
        client: Initialized Slack WebClient
        channel_name: Channel name (with or without # prefix)
        display: If True, print status messages
        
    Returns:
        Channel dict if found, None otherwise
    """
    channel_name = channel_name.lstrip('#').lower()
    
    channels = list_all_channels(client, display=False)
    
    for channel in channels:
        if channel.get('name', '').lower() == channel_name:
            return channel
    
    if display:
        click.echo(f"❌ Channel not found: {channel_name}", err=True)
    return None


def lookup_channel_by_id(
    client: WebClient,
    channel_id: str,
    display: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack channel by ID.
    
    Args:
        client: Initialized Slack WebClient
        channel_id: Slack channel ID
        display: If True, print status messages
        
    Returns:
        Channel dict if found, None otherwise
    """
    try:
        response = client.conversations_info(channel=channel_id)
        if response['ok']:
            return response['channel']
        else:
            if display:
                click.echo(f"❌ Channel not found: {channel_id}", err=True)
            return None
    except SlackApiError as e:
        if display:
            error_msg = e.response['error']
            click.echo(f"❌ Error looking up channel ID: {error_msg}", err=True)
            if error_msg == 'missing_scope':
                click.echo(f"   Full response: {e.response}", err=True)
        return None


def get_token_scopes(token: str) -> Dict[str, Any]:
    """
    Get token scopes and type from Slack API.
    
    Args:
        token: Slack token (bot or user)
        
    Returns:
        Dict with 'scopes', 'token_type', 'token_preview'
    """
    try:
        import requests
        headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
        auth_response = requests.post('https://slack.com/api/auth.test', headers=headers)
        scopes_str = auth_response.headers.get('x-oauth-scopes', '')
        scopes = [s.strip() for s in scopes_str.split(',')] if scopes_str else []
        
        # Detect token type (including Enterprise Grid tokens)
        if token.startswith('xoxb-'):
            token_type = 'Bot Token'
        elif token.startswith('xoxp-'):
            token_type = 'User Token'
        elif token.startswith('xoxe.xoxb-'):
            token_type = 'Enterprise Grid Bot Token'
        elif token.startswith('xoxe.xoxp-'):
            token_type = 'Enterprise Grid User Token'
        else:
            token_type = 'Unknown'
        token_preview = f"{token[:10]}...{token[-4:]}" if token and len(token) > 14 else "***"
        
        return {
            'scopes': scopes,
            'scopes_str': scopes_str,
            'token_type': token_type,
            'token_preview': token_preview
        }
    except Exception:
        return {
            'scopes': [],
            'scopes_str': 'unknown',
            'token_type': 'Unknown',
            'token_preview': '***'
        }


def get_required_scope_for_error(error_code: str, api_method: Optional[str] = None) -> Optional[str]:
    """
    Determine required scope based on error code and API method.
    
    Delegates to SlackClient.get_required_scope_for_error for consistency.
    
    Args:
        error_code: Slack API error code (e.g., 'missing_scope', 'not_allowed_token_type')
        api_method: Optional API method name (e.g., 'users.profile.set')
        
    Returns:
        Required scope name if known, None otherwise
    """
    # Import from backend (sys.path is set in main.py)
    from modules.integrations.slack.client import SlackClient
    return SlackClient.get_required_scope_for_error(error_code, api_method)


def format_scope_error_info(
    error_code: str,
    token: str,
    api_method: Optional[str] = None,
    json_output: bool = False
) -> Dict[str, Any]:
    """
    Get formatted scope error information.
    
    Args:
        error_code: Slack API error code
        token: Slack token
        api_method: Optional API method name
        json_output: If True, return JSON-serializable format
        
    Returns:
        Dict with error info, token scopes, and missing scopes
    """
    scope_errors = ['missing_scope', 'not_allowed_token_type', 'invalid_auth']
    
    if error_code not in scope_errors:
        return {}
    
    token_info = get_token_scopes(token)
    required_scope = get_required_scope_for_error(error_code, api_method)
    
    missing_scopes = []
    if required_scope and required_scope not in token_info['scopes']:
        missing_scopes = [required_scope]
    
    result = {
        'error_type': 'scope_error',
        'error_code': error_code,
        'token_type': token_info['token_type'],
        'token_preview': token_info['token_preview'],
        'current_scopes': token_info['scopes'],
        'missing_scopes': missing_scopes,
    }
    
    if api_method:
        result['api_method'] = api_method
    if required_scope:
        result['required_scope'] = required_scope
    
    return result


def handle_slack_api_error(
    e: SlackApiError,
    json_output: bool = False,
    token: Optional[str] = None,
    api_method: Optional[str] = None
) -> None:
    """
    Handle SlackApiError consistently across commands with scope information.
    
    Args:
        e: SlackApiError exception
        json_output: If True, output JSON format
        token: Optional token to check scopes (if None, tries to extract from client)
        api_method: Optional API method name for scope detection
    """
    import json
    
    # Get error response data
    error_response = e.response.data if hasattr(e.response, 'data') else dict(e.response) if hasattr(e.response, '__dict__') else {'error': str(e.response)}
    error_msg = error_response.get('error', 'Unknown error') if isinstance(error_response, dict) else str(e.response)
    
    # Get response headers for additional debugging info
    response_headers = {}
    if hasattr(e.response, 'headers'):
        response_headers = dict(e.response.headers) if hasattr(e.response.headers, 'items') else e.response.headers
    
    # Try to get token if not provided
    if not token:
        # Try to extract from exception if available
        if hasattr(e, 'response') and hasattr(e.response, 'req_args'):
            # Check req_args for headers
            req_args = e.response.req_args if hasattr(e.response, 'req_args') else {}
            req_headers = req_args.get('headers', {}) if isinstance(req_args, dict) else {}
            auth_header = req_headers.get('Authorization', '') if isinstance(req_headers, dict) else ''
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
    
    # Check if this is a scope-related error
    scope_info = {}
    if token and error_msg in ['missing_scope', 'not_allowed_token_type', 'invalid_auth']:
        scope_info = format_scope_error_info(error_msg, token, api_method, json_output)
    
    if json_output:
        # JSON output format
        output = {
            'error': error_msg,
            'error_type': 'slack_api_error',
            'response': error_response
        }
        if response_headers:
            # Include relevant headers (filter out sensitive info)
            filtered_headers = {k: v for k, v in response_headers.items() 
                               if k.lower() in ['x-slack-req-id', 'x-slack-failure', 'x-oauth-scopes', 'content-type']}
            if filtered_headers:
                output['response_headers'] = filtered_headers
        if scope_info:
            output['scope_info'] = scope_info
        click.echo(json.dumps(output, indent=2, default=str))
    else:
        # Human-readable output
        click.echo(f"❌ Slack API error: {error_msg}", err=True)
    
        if scope_info:
            click.echo(f"\n🔑 Token Type: {scope_info['token_type']}", err=True)
            click.echo(f"🔑 Token: {scope_info['token_preview']}", err=True)
            click.echo(f"📋 Current Scopes: {', '.join(scope_info['current_scopes']) if scope_info['current_scopes'] else 'none'}", err=True)
            
            if scope_info.get('required_scope'):
                click.echo(f"⚠️  Required Scope: {scope_info['required_scope']}", err=True)
            
            if scope_info.get('missing_scopes'):
                click.echo(f"❌ Missing Scopes: {', '.join(scope_info['missing_scopes'])}", err=True)
                click.echo("\n💡 To fix:", err=True)
                if scope_info['token_type'] == 'Bot Token' and scope_info.get('required_scope') == 'users.profile:write':
                    click.echo("   ⚠️  CRITICAL: users.profile:write requires a User Token (xoxp-...), not a Bot Token (xoxb-...)", err=True)
                    click.echo("   Bot Tokens cannot use User Token Scopes - this is a Slack API limitation.", err=True)
                    click.echo("", err=True)
                    click.echo("   To fix:", err=True)
                    click.echo("   1. Go to your Slack app settings → OAuth & Permissions", err=True)
                    click.echo("   2. Under 'User Token Scopes' (NOT 'Bot Token Scopes'), add 'users.profile:write'", err=True)
                    click.echo("   3. Click 'Reinstall to Workspace' to trigger OAuth flow", err=True)
                    click.echo("   4. After reinstall, you'll get a User Token (xoxp-...) - use that instead of the Bot Token", err=True)
                    click.echo("", err=True)
                    click.echo("   Note: User Tokens are tied to the user who installed the app.", err=True)
                    click.echo("   You may need to set SLACK_USER_TOKEN_LEADERSHIP instead of SLACK_BOT_TOKEN_LEADERSHIP", err=True)
                else:
                    scope_type = 'User Token Scopes' if scope_info['token_type'] == 'User Token' else 'Bot Token Scopes'
                    click.echo(f"   1. Go to OAuth & Permissions → {scope_type}", err=True)
                    click.echo(f"   2. Add the missing scope(s): {', '.join(scope_info['missing_scopes'])}", err=True)
                    click.echo("   3. Reinstall the app to get a new token", err=True)
            
            # Show response headers if available (especially x-slack-failure)
            if response_headers:
                relevant_headers = {k: v for k, v in response_headers.items() 
                                  if k.lower() in ['x-slack-req-id', 'x-slack-failure', 'x-oauth-scopes']}
                if relevant_headers:
                    click.echo(f"\n📋 Response Headers:", err=True)
                    click.echo(json.dumps(relevant_headers, indent=2, default=str), err=True)
            
            click.echo(f"\n📋 Full Error Response:", err=True)
            click.echo(json.dumps(error_response, indent=2, default=str), err=True)
        else:
            # Fallback for non-scope errors
            # Show response headers if available
            if response_headers:
                relevant_headers = {k: v for k, v in response_headers.items() 
                                  if k.lower() in ['x-slack-req-id', 'x-slack-failure', 'x-oauth-scopes']}
                if relevant_headers:
                    click.echo(f"\n📋 Response Headers:", err=True)
                    click.echo(json.dumps(relevant_headers, indent=2, default=str), err=True)
            
            click.echo(f"\n📋 Error Response:", err=True)
            click.echo(json.dumps(error_response, indent=2, default=str), err=True)


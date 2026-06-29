#!/usr/bin/env python3
"""
Identify which Slack app a token belongs to.
Usage: python identify_slack_token.py <token>
"""
import sys
import json
import requests


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python identify_slack_token.py <token>")
        print("Example: python identify_slack_token.py xoxe.xoxp-...")
        sys.exit(1)

    token = sys.argv[1]

    print(f"🔍 Testing token: {token[:15]}...{token[-4:] if len(token) > 19 else '***'}")
    print()

    # Detect token type
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

    print(f"Token Type: {token_type}")
    print()

    # Call auth.test to get app/team info
    try:
        response = requests.post(
            'https://slack.com/api/auth.test',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            timeout=10
        )
        
        data = response.json()
        
        if data.get('ok'):
            print("✅ Token is valid!")
            print()
            print("📋 Token Information:")
            print(f"   User: {data.get('user', 'N/A')} ({data.get('user_id', 'N/A')})")
            print(f"   Team: {data.get('team', 'N/A')} ({data.get('team_id', 'N/A')})")
            print(f"   Team URL: {data.get('url', 'N/A')}")
            
            # Enterprise Grid specific info
            if 'enterprise_id' in data:
                print(f"   Enterprise ID: {data.get('enterprise_id', 'N/A')}")
                print(f"   Enterprise Name: {data.get('enterprise_name', 'N/A')}")
            
            # App info (if available)
            if 'app_id' in data:
                print(f"   App ID: {data.get('app_id', 'N/A')}")
            
            # Scopes
            scopes_str = response.headers.get('x-oauth-scopes', '')
            scopes = [s.strip() for s in scopes_str.split(',')] if scopes_str else []
            print()
            print(f"📋 Scopes ({len(scopes)} total):")
            if scopes:
                for scope in scopes:
                    print(f"   • {scope}")
            else:
                print("   (no scopes found in response headers)")
            
            print()
            print("🔗 To manage this app:")
            if data.get('team_id'):
                print(f"   https://api.slack.com/apps (search for team: {data.get('team', 'N/A')})")
                print(f"   Or go to: {data.get('url', 'N/A')}/apps")
            
            print()
            print("📋 Full Response:")
            print(json.dumps(data, indent=2))
            
        else:
            error = data.get('error', 'Unknown error')
            print(f"❌ Token validation failed: {error}")
            print()
            
            if error == 'invalid_auth':
                print("💡 Possible reasons for 'invalid_auth':")
                print("   1. Token has expired or been revoked")
                print("   2. Token was copied incorrectly (missing characters)")
                print("   3. Token is from a different workspace/organization")
                print("   4. Token requires reinstallation after scope changes")
                print()
                print("🔍 To find which app this token belongs to:")
                print("   1. Go to https://api.slack.com/apps")
                print("   2. Check all apps you have access to")
                print("   3. For each app, go to 'OAuth & Permissions'")
                print("   4. Look at 'OAuth Tokens for Your Workspace' section")
                print("   5. Compare token prefixes (first 10-15 characters)")
                print()
                print("   For Enterprise Grid:")
                print("   - Check organization-level apps in Enterprise Admin settings")
                print("   - Look for apps installed at org level, not workspace level")
                print()
                print("   Token prefix to search for:")
                print(f"   {token[:20]}...")
            
            print()
            print("📋 Error Response:")
            print(json.dumps(data, indent=2))
            
            # Try to get response headers for more info
            print()
            print("📋 Response Headers:")
            relevant_headers = {
                'x-slack-req-id': response.headers.get('x-slack-req-id'),
                'x-slack-failure': response.headers.get('x-slack-failure'),
                'x-oauth-scopes': response.headers.get('x-oauth-scopes'),
            }
            print(json.dumps({k: v for k, v in relevant_headers.items() if v}, indent=2))
            
    except Exception as e:
        print(f"❌ Error calling auth.test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


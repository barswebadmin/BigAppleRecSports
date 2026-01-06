#!/usr/bin/env python3
"""
Test script to verify User Token can update other users' profiles.
Run this after creating a User Token with users.profile:write scope.
"""
import os
import sys
import json
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Get token from environment variable or command-line argument
import sys
user_token = os.getenv("TEST_USER_TOKEN")
if not user_token and len(sys.argv) > 1:
    user_token = sys.argv[1]
if not user_token:
    print("Usage: python test_user_token.py <xoxp-token>")
    print("   OR: TEST_USER_TOKEN=xoxp-... python test_user_token.py")
    sys.exit(1)

if not user_token.startswith("xoxp-"):
    print("❌ Error: Token must start with 'xoxp-' (User Token)")
    sys.exit(1)

# Test the token
import requests

print("🔍 Testing User Token...")
print(f"Token (first 15): {user_token[:15]}...")
print()

# 1. Test auth.test to see who the token belongs to
print("1. Testing auth.test...")
auth_response = requests.post(
    'https://slack.com/api/auth.test',
    headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
    timeout=10
)
auth_data = auth_response.json()
if auth_data.get('ok'):
    print(f"✅ Token belongs to: {auth_data.get('user')} ({auth_data.get('user_id')})")
    print(f"   Team: {auth_data.get('team')} ({auth_data.get('team_id')})")
    scopes = auth_response.headers.get('x-oauth-scopes', '')
    print(f"   Scopes: {scopes}")
else:
    print(f"❌ Auth test failed: {auth_data.get('error')}")
    sys.exit(1)

print()

# 2. Test users.profile.set on another user
test_user_id = os.getenv("TEST_USER_ID")
if not test_user_id and len(sys.argv) > 2:
    test_user_id = sys.argv[2]
if not test_user_id:
    test_user_id = input("Enter user ID to test update (e.g., U077SQCUMGE) or email: ").strip()

# If email, look it up first
if '@' in test_user_id:
    print(f"\n2. Looking up user by email: {test_user_id}")
    lookup_response = requests.post(
        'https://slack.com/api/users.lookupByEmail',
        headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
        json={'email': test_user_id},
        timeout=10
    )
    lookup_data = lookup_response.json()
    if lookup_data.get('ok'):
        test_user_id = lookup_data['user']['id']
        print(f"✅ Found user: {lookup_data['user']['name']} ({test_user_id})")
    else:
        print(f"❌ Lookup failed: {lookup_data.get('error')}")
        sys.exit(1)
else:
    print(f"\n2. Using user ID: {test_user_id}")

# Get current profile
print(f"\n3. Getting current profile for {test_user_id}...")
info_response = requests.post(
    'https://slack.com/api/users.info',
    headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
    json={'user': test_user_id},
    timeout=10
)
info_data = info_response.json()
if info_data.get('ok'):
    current_title = info_data['user']['profile'].get('title', '(none)')
    print(f"✅ Current title: '{current_title}'")
    if 'fields' in info_data['user']['profile']:
        print(f"   Custom fields: {list(info_data['user']['profile']['fields'].keys())}")
else:
    print(f"❌ Failed to get user info: {info_data.get('error')}")
    sys.exit(1)

# 4. Try updating title
new_title = os.getenv("TEST_TITLE", "Test Title")
if len(sys.argv) > 3:
    new_title = sys.argv[3]
if not new_title:
    new_title = input(f"\n4. Enter new title to test (or press Enter to use 'Test Title'): ").strip() or "Test Title"
print(f"\n5. Updating title to '{new_title}'...")
update_response = requests.post(
    'https://slack.com/api/users.profile.set',
    headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
    json={
        'user': test_user_id,
        'profile': {
            'title': new_title
        }
    },
    timeout=10
)
update_data = update_response.json()
print(f"Response: {json.dumps(update_data, indent=2)}")

if update_data.get('ok'):
    returned_title = update_data.get('profile', {}).get('title')
    if returned_title == new_title:
        print(f"✅ Update succeeded! Title is now '{returned_title}'")
    else:
        print(f"⚠️  API returned ok=true but title is '{returned_title}' (expected '{new_title}')")
        if 'fields' in update_data.get('profile', {}):
            print(f"   Custom fields in response: {list(update_data['profile']['fields'].keys())}")
            # Check if we need to update via custom field
            for field_id, field_data in update_data['profile']['fields'].items():
                if isinstance(field_data, dict) and field_data.get('value') == current_title:
                    print(f"\n   🔄 Trying update via custom field {field_id}...")
                    custom_update_response = requests.post(
                        'https://slack.com/api/users.profile.set',
                        headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
                        json={
                            'user': test_user_id,
                            'profile': {
                                'fields': {
                                    field_id: {
                                        'value': new_title
                                    }
                                }
                            }
                        },
                        timeout=10
                    )
                    custom_update_data = custom_update_response.json()
                    print(f"   Custom field update response: {json.dumps(custom_update_data, indent=2)}")
                    if custom_update_data.get('ok'):
                        print(f"   ✅ Custom field update succeeded!")
else:
    print(f"❌ Update failed: {update_data.get('error')}")

print("\n6. Verifying update...")
import time
time.sleep(0.5)
verify_response = requests.post(
    'https://slack.com/api/users.info',
    headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
    json={'user': test_user_id},
    timeout=10
)
verify_data = verify_response.json()
if verify_data.get('ok'):
    verified_title = verify_data['user']['profile'].get('title', '(none)')
    if verified_title == new_title:
        print(f"✅ Verification: Title is now '{verified_title}'")
    else:
        print(f"❌ Verification: Title is still '{verified_title}' (expected '{new_title}')")


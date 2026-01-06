#!/usr/bin/env python3
"""
Test script to verify if adding 'type' attribute to custom field update works.
"""
import os
import sys
import json
import time
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Get tokens from environment or command-line arguments
bot_token = os.getenv("SLACK_BOT_TOKEN_LEADERSHIP")
user_token = os.getenv("SLACK_BOT_USER_TOKEN_LEADERSHIP")

if len(sys.argv) > 1:
    user_token = sys.argv[1]
if len(sys.argv) > 2:
    bot_token = sys.argv[2]

if not bot_token:
    print("Usage: python test_custom_field_type.py [xoxp-user-token] [xoxb-bot-token]")
    print("   OR: SLACK_BOT_TOKEN_LEADERSHIP=xoxb-... SLACK_BOT_USER_TOKEN_LEADERSHIP=xoxp-... python test_custom_field_type.py")
    print("\nNote: Bot token is required for reading user info (users:read scope)")
    print("      User token is required for updating profile (users.profile:write scope)")
    sys.exit(1)

if not user_token:
    print("⚠️  Warning: No user token provided, update will fail")
    print("   Provide user token as first argument or SLACK_BOT_USER_TOKEN_LEADERSHIP env var")

if user_token and not user_token.startswith("xoxp-"):
    print("❌ Error: User Token must start with 'xoxp-'")
    sys.exit(1)

if bot_token and not bot_token.startswith("xoxb-"):
    print("⚠️  Warning: Bot token should start with 'xoxb-', using anyway")

import requests

print("🔍 Testing custom field update with 'type' attribute...")
print(f"Token (first 15): {user_token[:15]}...")
print()

# Test user
test_user_id = "U077SQCUMGE"  # nico.ramirez
custom_field_id = "Xf03VDUS6D17"
new_title = "Treasurer (API Test)"

# 1. Get current profile (use bot token for reading)
print(f"1. Getting current profile for {test_user_id}...")
info_response = requests.post(
    'https://slack.com/api/users.info',
    headers={'Authorization': f'Bearer {bot_token}', 'Content-Type': 'application/json'},
    json={'user': test_user_id},
    timeout=10
)
info_data = info_response.json()
if info_data.get('ok'):
    current_title = info_data['user']['profile'].get('title', '(none)')
    current_custom_field = info_data['user']['profile'].get('fields', {}).get(custom_field_id, {})
    current_custom_value = current_custom_field.get('value', '(none)') if isinstance(current_custom_field, dict) else '(none)'
    print(f"✅ Current title: '{current_title}'")
    print(f"✅ Current custom field {custom_field_id}: '{current_custom_value}'")
    if 'fields' in info_data['user']['profile']:
        print(f"   All custom fields: {list(info_data['user']['profile']['fields'].keys())}")
        # Check the structure of the custom field
        if custom_field_id in info_data['user']['profile']['fields']:
            field_structure = info_data['user']['profile']['fields'][custom_field_id]
            print(f"   Custom field structure: {json.dumps(field_structure, indent=2)}")
else:
    print(f"❌ Failed to get user info: {info_data.get('error')}")
    sys.exit(1)

print()

# 2. Try updating with 'type' attribute
print(f"2. Updating custom field {custom_field_id} with 'type' attribute...")
print(f"   New value: '{new_title}'")

# Test payload with 'type' attribute
payload_with_type = {
    'user': test_user_id,
    'profile': {
        'fields': {
            custom_field_id: {
                'value': new_title,
                'type': 'text'  # Adding type attribute
            }
        }
    }
}

print(f"\n📤 Payload with 'type':")
print(json.dumps(payload_with_type, indent=2))
print()

if not user_token:
    print("❌ Cannot test update: No user token provided")
    sys.exit(1)

update_response = requests.post(
    'https://slack.com/api/users.profile.set',
    headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
    json=payload_with_type,
    timeout=10
)
update_data = update_response.json()
print(f"📥 Response:")
print(json.dumps(update_data, indent=2))
print()

if update_data.get('ok'):
    returned_profile = update_data.get('profile', {})
    returned_title = returned_profile.get('title', '(none)')
    returned_custom_field = returned_profile.get('fields', {}).get(custom_field_id, {})
    returned_custom_value = returned_custom_field.get('value', '(none)') if isinstance(returned_custom_field, dict) else '(none)'
    
    print(f"✅ API returned ok=true")
    print(f"   Returned title: '{returned_title}'")
    print(f"   Returned custom field value: '{returned_custom_value}'")
    
    if returned_custom_value == new_title:
        print(f"✅ Custom field update succeeded! Value is now '{returned_custom_value}'")
    else:
        print(f"⚠️  Custom field value is '{returned_custom_value}' (expected '{new_title}')")
else:
    print(f"❌ Update failed: {update_data.get('error')}")

# 3. Verify by fetching user again (use bot token for reading)
print(f"\n3. Verifying update by fetching user again...")
time.sleep(0.5)
verify_response = requests.post(
    'https://slack.com/api/users.info',
    headers={'Authorization': f'Bearer {bot_token}', 'Content-Type': 'application/json'},
    json={'user': test_user_id},
    timeout=10
)
verify_data = verify_response.json()
if verify_data.get('ok'):
    verified_profile = verify_data['user']['profile']
    verified_title = verified_profile.get('title', '(none)')
    verified_custom_field = verified_profile.get('fields', {}).get(custom_field_id, {})
    verified_custom_value = verified_custom_field.get('value', '(none)') if isinstance(verified_custom_field, dict) else '(none)'
    
    print(f"✅ Verified title: '{verified_title}'")
    print(f"✅ Verified custom field value: '{verified_custom_value}'")
    
    if verified_custom_value == new_title:
        print(f"✅ Verification: Custom field is now '{verified_custom_value}' - UPDATE WORKED!")
    else:
        print(f"❌ Verification: Custom field is still '{verified_custom_value}' (expected '{new_title}')")
else:
    print(f"❌ Verification failed: {verify_data.get('error')}")


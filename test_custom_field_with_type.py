#!/usr/bin/env python3
"""
Direct API test: Update custom field with 'type' attribute.
Usage: python test_custom_field_with_type.py <xoxp-user-token>
"""
import sys
import json
import requests
import time

if len(sys.argv) < 2:
    print("Usage: python test_custom_field_with_type.py <xoxp-user-token>")
    sys.exit(1)

user_token = sys.argv[1]
test_user_id = "U077SQCUMGE"
custom_field_id = "Xf03VDUS6D17"
new_title = "Treasurer (Type Test)"

print(f"🔍 Testing custom field update with 'type' attribute...")
print(f"User: {test_user_id}")
print(f"Field: {custom_field_id}")
print(f"New value: '{new_title}'")
print()

# Payload with 'type' attribute
payload = {
    'user': test_user_id,
    'profile': {
        'fields': {
            custom_field_id: {
                'value': new_title,
                'type': 'text'  # Adding type attribute as suggested
            }
        }
    }
}

print("📤 Payload:")
print(json.dumps(payload, indent=2))
print()

# Make the API call
print("📡 Calling users.profile.set...")
response = requests.post(
    'https://slack.com/api/users.profile.set',
    headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
    json=payload,
    timeout=10
)

result = response.json()
print("📥 Response:")
print(json.dumps(result, indent=2))
print()

if result.get('ok'):
    print("✅ API returned ok=true")
    returned_fields = result.get('profile', {}).get('fields', {})
    if custom_field_id in returned_fields:
        returned_value = returned_fields[custom_field_id].get('value', '')
        print(f"   Returned field value: '{returned_value}'")
        if returned_value == new_title:
            print(f"   ✅ Value matches! Update appears successful")
        else:
            print(f"   ⚠️  Value doesn't match (expected '{new_title}')")
    
    # Verify by fetching again
    print("\n🔄 Verifying by fetching user again...")
    time.sleep(0.5)
    verify_response = requests.post(
        'https://slack.com/api/users.info',
        headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'},
        json={'user': test_user_id},
        timeout=10
    )
    verify_data = verify_response.json()
    if verify_data.get('ok'):
        verified_fields = verify_data['user']['profile'].get('fields', {})
        if custom_field_id in verified_fields:
            verified_value = verified_fields[custom_field_id].get('value', '')
            print(f"   Verified field value: '{verified_value}'")
            if verified_value == new_title:
                print(f"   ✅ VERIFICATION SUCCESS: Field is now '{verified_value}'")
            else:
                print(f"   ❌ VERIFICATION FAILED: Field is still '{verified_value}'")
    else:
        print(f"   ⚠️  Could not verify: {verify_data.get('error')}")
else:
    print(f"❌ API call failed: {result.get('error')}")




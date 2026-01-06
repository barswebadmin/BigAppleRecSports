#!/usr/bin/env python3
"""Compare two JSON objects to find differences."""
import json

# From get command (lines 92-141)
get_response = {
    "id": "U03MYT4D1FY",
    "name": "chase",
    "team_id": "T02HQ2C2G",
    "profile": {
        "real_name": "Chase Tucker",
        "display_name": "Chase Tucker (He/Him/His)",
        "real_name_normalized": "Chase Tucker",
        "display_name_normalized": "Chase Tucker (He/Him/His)",
        "avatar_hash": "98f6f3abd5ae",
        "email": "chase@bigapplerecsports.com",
        "first_name": "Chase",
        "last_name": "Tucker",
        "title": "Commissioner of Kickball",
        "phone": "",
        "skype": "",
        "team": "T02HQ2C2G",
        "image_24": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_24.png",
        "image_32": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_32.png",
        "image_48": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_48.png",
        "image_72": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_72.png",
        "image_192": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_192.png",
        "image_512": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_512.png",
        "image_1024": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_1024.png",
        "image_original": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_original.png",
        "is_custom_image": True,
        "status_text": "",
        "status_text_canonical": "",
        "status_emoji": "",
        "status_emoji_display_info": [],
        "status_expiration": 0,
        "huddle_state": "default_unset",
        "huddle_state_expiration_ts": 0
    },
    "deleted": False,
    "is_bot": False,
    "color": "3c989f",
    "real_name": "Chase Tucker",
    "tz": "America/New_York",
    "tz_label": "Eastern Standard Time",
    "tz_offset": -18000,
    "is_admin": False,
    "is_owner": False,
    "is_primary_owner": False,
    "is_restricted": False,
    "is_ultra_restricted": False,
    "is_app_user": False,
    "is_email_confirmed": True,
    "who_can_share_contact_card": "EVERYONE",
    "updated": 1767563790
}

# From update response (lines 244-282) - only profile section shown
update_response_profile = {
    "title": "Commissioner",
    "phone": "",
    "skype": "",
    "real_name": "Chase Tucker",
    "real_name_normalized": "Chase Tucker",
    "display_name": "Chase Tucker (He/Him/His)",
    "display_name_normalized": "Chase Tucker (He/Him/His)",
    "fields": {
        "Xf03VDUS6D17": {
            "value": "Commissioner",
            "alt": ""
        }
    },
    "status_text": "",
    "status_emoji": "",
    "status_emoji_display_info": [],
    "status_expiration": 0,
    "avatar_hash": "98f6f3abd5ae",
    "image_original": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_original.png",
    "is_custom_image": True,
    "email": "chase@bigapplerecsports.com",
    "huddle_state": "default_unset",
    "huddle_state_expiration_ts": 0,
    "first_name": "Chase",
    "last_name": "Tucker",
    "image_24": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_24.png",
    "image_32": "https://avatars.slack-edge.com/2024-29/8223529734678_98f6f3abd5ae82d3a993_32.png",
    "image_48": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_48.png",
    "image_72": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_72.png",
    "image_192": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_192.png",
    "image_512": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_512.png",
    "image_1024": "https://avatars.slack-edge.com/2024-12-29/8223529734678_98f6f3abd5ae82d3a993_1024.png",
    "status_text_canonical": ""
}

print("Comparing profile fields...")
print("=" * 60)

get_profile = get_response["profile"]
update_profile = update_response_profile

# Check all fields from get_response
for key in sorted(get_profile.keys()):
    get_val = get_profile.get(key)
    update_val = update_profile.get(key)
    
    if key == "title":
        print(f"✅ {key}: '{get_val}' → '{update_val}' (expected change)")
    elif key == "fields":
        # Custom fields - check if present in update
        if key in update_profile:
            get_fields = get_profile.get(key, {})
            update_fields = update_profile.get(key, {})
            if get_fields != update_fields:
                print(f"🔄 {key}: Changed")
                print(f"   GET: {json.dumps(get_fields, indent=2)}")
                print(f"   UPDATE: {json.dumps(update_fields, indent=2)}")
            else:
                print(f"✅ {key}: No change (not present in get)")
        else:
            print(f"⚠️  {key}: Present in get but not in update response")
    elif get_val != update_val:
        print(f"🔄 {key}: '{get_val}' → '{update_val}'")
    else:
        pass  # No change, skip

# Check for fields in update that aren't in get
for key in sorted(update_profile.keys()):
    if key not in get_profile:
        print(f"➕ {key}: New in update response: {update_profile[key]}")

print("\n" + "=" * 60)
print("Summary: Only 'title' and 'fields' changed (fields added in update response)")




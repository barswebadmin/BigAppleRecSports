#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "httpx",
# ]
# ///
"""
Create Shopify metaobject definition for league/program metadata.

Based on schema in shared_utilities/schemas/sport-programs/

Usage: ./create_league_metaobject_definition.py [--dry-run]
"""

import json
import sys
from pathlib import Path

import httpx

SHOPIFY_STORE = "09fe59-3.myshopify.com"
GRAPHQL_URL = f"https://{SHOPIFY_STORE}/admin/api/2026-07/graphql.json"
TOKEN_FILE = Path.home() / ".config" / "bars" / "bars_shopify_token_admin"

VENUE_TYPE = "venue"
VENUE_NAME = "Venue"

LEAGUE_TYPE = "league_program_info"
LEAGUE_NAME = "League Program Info"

VENUE_FIELD_DEFINITIONS = [
    {"key": "key", "name": "Venue Key", "type": "single_line_text_field"},
    {"key": "display_name", "name": "Display Name", "type": "single_line_text_field"},
    {"key": "street", "name": "Street Address", "type": "single_line_text_field"},
    {"key": "cross_streets", "name": "Cross Streets (JSON array)", "type": "multi_line_text_field"},
    {"key": "neighborhood", "name": "Neighborhood", "type": "single_line_text_field"},
    {"key": "city", "name": "City", "type": "single_line_text_field"},
    {"key": "state", "name": "State", "type": "single_line_text_field"},
    {"key": "zip", "name": "Zip Code", "type": "single_line_text_field"},
]

LEAGUE_FIELD_DEFINITIONS = [
    # Core identification (matches RegularSeason.key)
    {"key": "key", "name": "Season Key", "type": "single_line_text_field", "description": "year-season-sport-day-division format"},
    {"key": "shopify_product_id", "name": "Shopify Product ID", "type": "single_line_text_field"},
    
    # League properties (from _league.yaml)
    {"key": "sport", "name": "Sport", "type": "single_line_text_field", "description": "Capitalized: Kickball, Dodgeball, Bowling, Pickleball"},
    {"key": "division", "name": "Division", "type": "single_line_text_field", "description": "lowercase: open, wtnb"},
    {"key": "day_of_play", "name": "Day of Play", "type": "single_line_text_field", "description": "Capitalized: Monday, Tuesday, etc."},
    {"key": "level_of_play", "name": "Level of Play", "type": "single_line_text_field"},
    {"key": "team_assignment", "name": "Team Assignment (JSON array)", "type": "multi_line_text_field", "description": "Array: draft, randomized, buddy, buddyNewbieOnly, ladder"},
    {"key": "game_duration", "name": "Game Duration", "type": "single_line_text_field"},
    {"key": "dodgeball_ball_type", "name": "Dodgeball Ball Type", "type": "single_line_text_field"},
    {"key": "contact_email", "name": "Contact Email", "type": "single_line_text_field"},
    
    # Venue reference
    {"key": "venue", "name": "Venue", "type": "metaobject_reference"},
    
    # Season metadata
    {"key": "year", "name": "Year", "type": "number_integer"},
    {"key": "season", "name": "Season", "type": "single_line_text_field", "description": "lowercase: winter, spring, summer, fall"},
    {"key": "status", "name": "Status", "type": "single_line_text_field"},
    
    # Team/capacity details
    {"key": "players_per_team", "name": "Players per Team", "type": "number_integer"},
    {"key": "max_teams", "name": "Max Teams", "type": "number_integer"},
    {"key": "minimum_total_players", "name": "Minimum Total Players", "type": "number_integer"},
    {"key": "max_capacity", "name": "Max Capacity", "type": "number_integer"},
    
    # Schedule details (from _schedule-details.yaml)
    {"key": "start_date", "name": "Start Date (YYYY-MM-DD)", "type": "date"},
    {"key": "end_date", "name": "End Date (YYYY-MM-DD)", "type": "date"},
    {"key": "start_time", "name": "Start Time (HH:MM:SS)", "type": "single_line_text_field"},
    {"key": "end_time", "name": "End Time (HH:MM:SS)", "type": "single_line_text_field"},
    {"key": "number_of_weeks", "name": "Number of Weeks", "type": "number_integer"},
    {"key": "off_dates", "name": "Off Dates (JSON array of YYYY-MM-DD)", "type": "multi_line_text_field"},
    {"key": "adjusted_schedules", "name": "Adjusted Schedules (JSON)", "type": "multi_line_text_field"},
    {"key": "sessions", "name": "Sessions (JSON object)", "type": "multi_line_text_field", "description": "For multi-session leagues like bowling"},
    
    # Special dates (FlexibleDate: can be date or datetime)
    {"key": "newbie_orientation", "name": "Newbie Orientation", "type": "single_line_text_field", "description": "YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ"},
    {"key": "scout_night", "name": "Scout Night", "type": "single_line_text_field"},
    {"key": "opening_party", "name": "Opening Party", "type": "single_line_text_field"},
    {"key": "closing_party", "name": "Closing Party", "type": "single_line_text_field"},
    {"key": "rain_date", "name": "Rain Date (YYYY-MM-DD)", "type": "date"},
    
    # Registration periods (from RegularSeason.registrationPeriods)
    {"key": "veteran_registration_start", "name": "Veteran Registration Start (ISO 8601)", "type": "single_line_text_field"},
    {"key": "veteran_registration_variant_id", "name": "Veteran Shopify Variant ID", "type": "single_line_text_field"},
    {"key": "early_registration_start", "name": "Early Registration Start (ISO 8601)", "type": "single_line_text_field"},
    {"key": "early_registration_variant_id", "name": "Early Shopify Variant ID", "type": "single_line_text_field"},
    {"key": "general_start", "name": "General Registration Start (ISO 8601)", "type": "single_line_text_field"},
    {"key": "general_variant_id", "name": "General Registration Shopify Variant ID", "type": "single_line_text_field"},
    {"key": "waitlist_registration_start", "name": "Waitlist Registration Start (ISO 8601)", "type": "single_line_text_field"},
    {"key": "waitlist_registration_variant_id", "name": "Waitlist Shopify Variant ID", "type": "single_line_text_field"},
]


def load_token() -> str:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit(f"❌ No token found at {TOKEN_FILE}")
    return token


def create_metaobject_definition(token: str, name: str, type_key: str, field_definitions: list, dry_run: bool = False) -> dict:
    """Create a metaobject definition via GraphQL."""
    
    field_defs_graphql = []
    for field in field_definitions:
        field_defs_graphql.append(
            f'{{key: "{field["key"]}", name: "{field["name"]}", type: "{field["type"]}"}}'
        )
    
    field_defs_str = "\n      ".join(field_defs_graphql)
    
    mutation = f"""
    mutation CreateMetaobjectDefinition {{
      metaobjectDefinitionCreate(definition: {{
        name: "{name}"
        type: "{type_key}"
        fieldDefinitions: [
      {field_defs_str}
        ]
      }}) {{
        metaobjectDefinition {{
          id
          name
          type
          fieldDefinitions {{
            key
            name
            type {{
              name
            }}
          }}
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    print(f"\n🔍 Creating metaobject definition: {name}")
    print(f"   Type: {type_key}")
    print(f"   Fields: {len(field_definitions)}")
    
    if dry_run:
        print("\n🔍 DRY RUN - Would execute mutation:")
        print(mutation)
        return {}
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
    }
    
    response = httpx.post(
        GRAPHQL_URL,
        json={"query": mutation},
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    
    data = response.json()
    
    if "errors" in data:
        print(f"\n❌ GraphQL errors: {json.dumps(data['errors'], indent=2)}")
        sys.exit(1)
    
    result = data.get("data", {}).get("metaobjectDefinitionCreate", {})
    
    if result.get("userErrors"):
        print(f"\n❌ User errors: {json.dumps(result['userErrors'], indent=2)}")
        sys.exit(1)
    
    definition = result.get("metaobjectDefinition")
    if definition:
        print(f"\n✅ Created metaobject definition!")
        print(f"   ID: {definition['id']}")
        print(f"   Type: {definition['type']}")
        print(f"   Fields created: {len(definition['fieldDefinitions'])}")
        print(f"\n📋 Field list:")
        for field in definition['fieldDefinitions']:
            print(f"   - {field['key']}: {field['name']} ({field['type']['name']})")
    
    return definition


def main():
    dry_run = "--dry-run" in sys.argv
    
    token = load_token()
    
    print(f"🏪 Store: {SHOPIFY_STORE}")
    print(f"🔧 Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    # Create Venue definition first
    print(f"\n{'='*80}")
    print(f"STEP 1: Creating Venue metaobject definition")
    venue_def = create_metaobject_definition(token, VENUE_NAME, VENUE_TYPE, VENUE_FIELD_DEFINITIONS, dry_run)
    
    # Create League Program Info definition (references Venue)
    print(f"\n{'='*80}")
    print(f"STEP 2: Creating League Program Info metaobject definition")
    league_def = create_metaobject_definition(token, LEAGUE_NAME, LEAGUE_TYPE, LEAGUE_FIELD_DEFINITIONS, dry_run)
    
    if not dry_run and venue_def and league_def:
        print(f"\n{'='*80}")
        print(f"✅ Both definitions created successfully!")
        print(f"\n📝 Next steps:")
        print(f"   1. Create Venue entries (VCS, Elliott, DeWitt, etc.)")
        print(f"   2. Create League Program Info entries (reference venues)")
        print(f"   3. Link league entries to products via metafield")
        print(f"\n💡 Use populate_league_metaobjects.py to automate steps 1-3")


if __name__ == "__main__":
    main()

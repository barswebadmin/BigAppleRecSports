#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "httpx",
#   "beautifulsoup4",
# ]
# ///
"""
Parse product descriptions and create league metaobject entries.

Fetches products from Shopify, parses descriptionHtml for structured data,
creates metaobject entries, and links them to products via metafields.

Usage: ./populate_league_metaobjects.py [--dry-run] [--product-id ID]

Options:
  --dry-run       Show what would be created without executing
  --product-id    Process single product by Shopify ID (for testing)
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup

SHOPIFY_STORE = "09fe59-3.myshopify.com"
GRAPHQL_URL = f"https://{SHOPIFY_STORE}/admin/api/2025-01/graphql.json"
TOKEN_FILE = Path.home() / ".config" / "bars" / "bars_shopify_token_admin"

VENUE_TYPE = "venue"
LEAGUE_TYPE = "league_program_info"

# Cache for created venue metaobject IDs
VENUE_CACHE = {}

# Location mapping from common names to structured venue data
LOCATION_MAP = {
    "village community school": {
        "key": "vcs",
        "display_name": "Village Community School",
        "street": "272 W 10th Street",
        "cross_streets": ["10th St", "Greenwich St"],
        "neighborhood": "West Village",
    },
    "vcs": {
        "key": "vcs",
        "display_name": "Village Community School",
        "street": "272 W 10th Street",
        "cross_streets": ["10th St", "Greenwich St"],
        "neighborhood": "West Village",
    },
    "elliott houses": {
        "key": "elliott",
        "display_name": "Elliott Center",
        "street": "420 W 26th St",
        "cross_streets": ["26th St", "9th Ave"],
        "neighborhood": "Chelsea",
    },
    "elliott": {
        "key": "elliott",
        "display_name": "Elliott Center",
        "street": "420 W 26th St",
        "cross_streets": ["26th St", "9th Ave"],
        "neighborhood": "Chelsea",
    },
    "dewitt": {
        "key": "dewitt",
        "display_name": "DeWitt Clinton Park",
        "street": "DeWitt Clinton Park",
        "cross_streets": ["52nd St", "11th Ave"],
        "neighborhood": "Hell's Kitchen",
    },
    "chelsea park": {
        "key": "chelsea-park",
        "display_name": "Chelsea Park",
        "street": "Chelsea Park",
        "cross_streets": ["27th St", "9th Ave"],
        "neighborhood": "Chelsea",
    },
    "pier 40": {
        "key": "pier40",
        "display_name": "Pier 40",
        "street": "353 West St",
        "cross_streets": ["Houston St", "West St"],
        "neighborhood": "West Village",
    },
}

# Division mapping
DIVISION_MAP = {
    "wtnb+": "wtnb",
    "wtnb": "wtnb",
    "open": "open",
}

# Ball type extraction for dodgeball
BALL_TYPE_MAP = {
    "foam": "Foam",
    "big ball": "Big Ball",
    "small ball": "Small Ball",
}


def load_token() -> str:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        sys.exit(f"❌ No token found at {TOKEN_FILE}")
    return token


def generate_season_key(sport: str, day: str, division: str, season: str, year: int) -> str:
    """Generate season key matching RegularSeason.key format."""
    sport_lower = sport.lower()
    day_lower = day.lower()
    division_suffix = f"{division}div"
    return f"{year}-{season}-{sport_lower}-{day_lower}-{division_suffix}"


def parse_product_description(html: str, title: str, product_handle: str) -> dict:
    """
    Parse product description HTML to extract structured league data.
    
    Expected format in HTML:
    - Season Dates: 1/11/25 – 3/8/25 (8 weeks, off 1/18/25)
    - Day/Time: Sundays 3:30 PM – 5:30 PM
    - Location: Village Community School (address)
    - Price: $120
    - Type: ... Division, Team Assignment
    """
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    
    data = {}
    
    # Parse title for sport/division/day (match _league.yaml enum values)
    title_lower = title.lower()
    if "kickball" in title_lower:
        data["sport"] = "Kickball"
    elif "dodgeball" in title_lower:
        data["sport"] = "Dodgeball"
    elif "bowling" in title_lower:
        data["sport"] = "Bowling"
    elif "pickleball" in title_lower:
        data["sport"] = "Pickleball"
    
    # Extract ball type for dodgeball
    if data.get("sport") == "Dodgeball":
        for ball_type_key, ball_type_val in BALL_TYPE_MAP.items():
            if ball_type_key in title_lower:
                data["dodgeball_ball_type"] = ball_type_val
                break
    
    # Day of play from title or description (match _league.yaml enum: capitalized)
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    for day in days:
        if day in title_lower:
            data["day_of_play"] = day.capitalize()
            break
    
    # Division from title
    if "wtnb" in title_lower:
        data["division"] = "wtnb"
    elif "open" in title_lower:
        data["division"] = "open"
    
    # Level of play from title or Type line
    level_patterns = [
        (r"social", "Social"),
        (r"advanced", "Advanced"),
        (r"competitive", "Competitive/Advanced"),
        (r"intermediate", "Intermediate/Advanced"),
    ]
    for pattern, level in level_patterns:
        if re.search(pattern, title_lower):
            data["level_of_play"] = level
            break
    
    # Season dates: "Season Dates: 1/11/25 – 3/8/25 (8 weeks, off 1/18/25)"
    season_match = re.search(r"Season Dates:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*[–-]\s*(\d{1,2}/\d{1,2}/\d{2,4})", text)
    if season_match:
        start_raw = season_match.group(1)
        end_raw = season_match.group(2)
        data["start_date"] = parse_date(start_raw)
        data["end_date"] = parse_date(end_raw)
    
    # Number of weeks: "(8 weeks"
    weeks_match = re.search(r"\((\d+)\s+weeks", text)
    if weeks_match:
        data["number_of_weeks"] = int(weeks_match.group(1))
    
    # Off dates: "off 1/18/25" or "off 1/18/25, 2/15/25"
    off_dates = []
    off_match = re.search(r"off\s+([\d/,\s&]+)\)", text)
    if off_match:
        off_str = off_match.group(1)
        date_parts = re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", off_str)
        off_dates = [parse_date(d) for d in date_parts]
    
    if off_dates:
        data["off_dates"] = json.dumps(off_dates)
    
    # Day/Time: "Sundays 3:30 PM – 5:30 PM"
    time_match = re.search(r"Day/Time:\s*\w+\s+(\d{1,2}:\d{2}\s*[AP]M)\s*[–-]\s*(\d{1,2}:\d{2}\s*[AP]M)", text)
    if time_match:
        data["start_time"] = parse_time(time_match.group(1))
        data["end_time"] = parse_time(time_match.group(2))
    
    # Location: "Village Community School (10th St & Greenwich St)"
    location_match = re.search(r"Location:\s*([^\(]+)", text)
    if location_match:
        loc_raw = location_match.group(1).strip().lower()
        for loc_key, venue_data in LOCATION_MAP.items():
            if loc_key in loc_raw:
                data["venue_key"] = venue_data["key"]
                data["venue_data"] = venue_data
                break
    
    # Price: "$120"
    price_match = re.search(r"Price:\s*\$(\d+)", text)
    if price_match:
        data["price"] = int(price_match.group(1))
    
    # Type line: "Type: Created for our Women/Trans/Non-Binary (WTNB+) Community, Advanced, Draft"
    # teamAssignment is an array in schema, can have multiple values
    type_match = re.search(r"Type:\s*([^\n]+)", text)
    team_assignments = []
    if type_match:
        type_line = type_match.group(1).lower()
        if "draft" in type_line:
            team_assignments.append("draft")
        if "randomized" in type_line:
            team_assignments.append("randomized")
        if "buddy" in type_line:
            if "newbie" in type_line:
                team_assignments.append("buddyNewbieOnly")
            else:
                team_assignments.append("buddy")
        if "ladder" in type_line:
            team_assignments.append("ladder")
    
    if team_assignments:
        data["team_assignment"] = json.dumps(team_assignments)
    
    # Contact email from description
    email_match = re.search(r"questions\?\s*Email\s+([\w\.-]+@[\w\.-]+)", text, re.IGNORECASE)
    if email_match:
        data["contact_email"] = email_match.group(1)
    
    # Registration dates: "Vet Registration: 12/15/25 at 6:00 PM"
    vet_reg_match = re.search(r"Vet Registration:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)", text)
    if vet_reg_match:
        data["veteran_registration_start"] = parse_datetime(vet_reg_match.group(1), vet_reg_match.group(2))
    
    # Early registration (TNB+/BIPOC): "TNB+ & BIPOC Early Registration: 12/16/25 at 6:00 PM"
    early_reg_match = re.search(r"(?:TNB\+|WTNB|BIPOC).*Early Registration:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)", text, re.IGNORECASE)
    if early_reg_match:
        data["early_registration_start"] = parse_datetime(early_reg_match.group(1), early_reg_match.group(2))
    
    # Open registration: "Open Registration: 12/17/25 at 6:00 PM"
    open_reg_match = re.search(r"Open Registration:\s*(\d{1,2}/\d{1,2}/\d{2,4})\s+at\s+(\d{1,2}:\d{2}\s*[AP]M)", text)
    if open_reg_match:
        data["general_start"] = parse_datetime(open_reg_match.group(1), open_reg_match.group(2))
    
    # Infer season from start date
    if data.get("start_date"):
        month = int(data["start_date"].split("-")[1])
        if month in [12, 1, 2]:
            data["season"] = "winter"
        elif month in [3, 4, 5]:
            data["season"] = "spring"
        elif month in [6, 7, 8]:
            data["season"] = "summer"
        elif month in [9, 10, 11]:
            data["season"] = "fall"
        
        year = int(data["start_date"].split("-")[0])
        data["year"] = year
    
    # Generate season key (matches RegularSeason.key format)
    if all(k in data for k in ["sport", "day_of_play", "division", "season", "year"]):
        data["key"] = generate_season_key(
            data["sport"],
            data["day_of_play"],
            data["division"],
            data["season"],
            data["year"]
        )
    else:
        # Fallback to product handle if parsing incomplete
        data["key"] = product_handle
    
    return data


def parse_date(date_str: str) -> str:
    """Convert M/D/YY or M/D/YYYY to YYYY-MM-DD (UtcDate format)."""
    parts = date_str.split("/")
    month = int(parts[0])
    day = int(parts[1])
    year = int(parts[2])
    
    if year < 100:
        year += 2000
    
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_time(time_str: str) -> str:
    """Convert '3:30 PM' to '15:30:00' (UtcTime format HH:MM:SS)."""
    time_str = time_str.strip().upper()
    
    # Extract time and period
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", time_str)
    if not match:
        return time_str
    
    hour = int(match.group(1))
    minute = int(match.group(2))
    period = match.group(3)
    
    # Convert to 24-hour format
    if period == "PM" and hour != 12:
        hour += 12
    elif period == "AM" and hour == 12:
        hour = 0
    
    return f"{hour:02d}:{minute:02d}:00"


def parse_datetime(date_str: str, time_str: str) -> str:
    """
    Convert date and time to UtcDateTime format (YYYY-MM-DDTHH:MM:SSZ).
    
    Args:
        date_str: M/D/YY format (e.g., "12/15/25")
        time_str: "7:00 PM" format
    
    Returns:
        ISO 8601 datetime string (e.g., "2025-12-15T19:00:00Z")
    """
    date_iso = parse_date(date_str)
    time_iso = parse_time(time_str)
    return f"{date_iso}T{time_iso}Z"


def fetch_product(token: str, product_id: str) -> dict:
    """Fetch single product with description and title."""
    query = f"""
    query {{
      product(id: "gid://shopify/Product/{product_id}") {{
        id
        title
        handle
        descriptionHtml
        tags
      }}
    }}
    """
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
    }
    
    response = httpx.post(
        GRAPHQL_URL,
        json={"query": query},
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    
    data = response.json()
    if "errors" in data:
        sys.exit(f"❌ GraphQL errors: {json.dumps(data['errors'], indent=2)}")
    
    return data["data"]["product"]


def fetch_all_products(token: str, limit: int = 50) -> list[dict]:
    """Fetch all products that match league format (not test products)."""
    query = f"""
    query {{
      products(first: {limit}, query: "-tag:test") {{
        edges {{
          node {{
            id
            title
            handle
            descriptionHtml
            tags
          }}
        }}
        pageInfo {{
          hasNextPage
          endCursor
        }}
      }}
    }}
    """
    
    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": token,
    }
    
    response = httpx.post(
        GRAPHQL_URL,
        json={"query": query},
        headers=headers,
        timeout=30.0,
    )
    response.raise_for_status()
    
    data = response.json()
    if "errors" in data:
        sys.exit(f"❌ GraphQL errors: {json.dumps(data['errors'], indent=2)}")
    
    edges = data["data"]["products"]["edges"]
    return [edge["node"] for edge in edges]


def get_or_create_venue(token: str, venue_data: dict, dry_run: bool = False) -> Optional[str]:
    """Get or create venue metaobject and return its ID."""
    
    venue_key = venue_data["key"]
    
    # Check cache
    if venue_key in VENUE_CACHE:
        return VENUE_CACHE[venue_key]
    
    # Check if venue already exists
    query = f"""
    query {{
      metaobjects(type: "{VENUE_TYPE}", first: 1, query: "key:{venue_key}") {{
        edges {{
          node {{
            id
            handle
          }}
        }}
      }}
    }}
    """
    
    if not dry_run:
        headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": token,
        }
        
        response = httpx.post(
            GRAPHQL_URL,
            json={"query": query},
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        
        data = response.json()
        edges = data.get("data", {}).get("metaobjects", {}).get("edges", [])
        
        if edges:
            venue_id = edges[0]["node"]["id"]
            VENUE_CACHE[venue_key] = venue_id
            print(f"   ℹ️  Venue '{venue_key}' already exists: {venue_id}")
            return venue_id
    
    # Create new venue
    fields = [
        f'{{key: "key", value: "{venue_data["key"]}"}}',
        f'{{key: "display_name", value: "{venue_data["display_name"]}"}}',
        f'{{key: "street", value: "{venue_data["street"]}"}}',
        f'{{key: "cross_streets", value: "{json.dumps(venue_data["cross_streets"]).replace(chr(34), chr(92)+chr(34))}"}}',
        f'{{key: "neighborhood", value: "{venue_data["neighborhood"]}"}}',
        f'{{key: "city", value: "New York"}}',
        f'{{key: "state", value: "NY"}}',
    ]
    
    fields_str = "\n      ".join(fields)
    
    mutation = f"""
    mutation {{
      metaobjectCreate(metaobject: {{
        type: "{VENUE_TYPE}"
        fields: [
      {fields_str}
        ]
      }}) {{
        metaobject {{
          id
          handle
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    if dry_run:
        print(f"   Would create venue: {venue_key} ({venue_data['display_name']})")
        return f"venue-{venue_key}"
    
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
    
    result_data = response.json()
    
    if "errors" in result_data:
        print(f"❌ GraphQL errors: {json.dumps(result_data['errors'], indent=2)}")
        return None
    
    result = result_data["data"]["metaobjectCreate"]
    
    if result.get("userErrors"):
        print(f"❌ User errors: {json.dumps(result['userErrors'], indent=2)}")
        return None
    
    venue_id = result["metaobject"]["id"]
    VENUE_CACHE[venue_key] = venue_id
    print(f"   ✅ Created venue: {venue_key} ({venue_data['display_name']}) → {venue_id}")
    
    return venue_id


def create_metaobject_entry(token: str, fields: dict, venue_id: Optional[str], dry_run: bool = False) -> Optional[str]:
    """Create league metaobject entry and return its ID."""
    
    field_list = []
    for key, value in fields.items():
        if key == "venue_key" or key == "venue_data":
            continue
        if value is not None:
            if isinstance(value, int):
                field_list.append(f'{{key: "{key}", value: "{value}"}}')
            else:
                escaped = str(value).replace('"', '\\"').replace('\n', '\\n')
                field_list.append(f'{{key: "{key}", value: "{escaped}"}}')
    
    # Add venue reference
    if venue_id:
        field_list.append(f'{{key: "venue", value: "{venue_id}"}}')
    
    fields_str = "\n      ".join(field_list)
    
    mutation = f"""
    mutation {{
      metaobjectCreate(metaobject: {{
        type: "{LEAGUE_TYPE}"
        fields: [
      {fields_str}
        ]
      }}) {{
        metaobject {{
          id
          handle
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    if dry_run:
        print(f"\n🔍 Would create metaobject entry:")
        print(json.dumps(fields, indent=2))
        return None
    
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
        print(f"❌ GraphQL errors: {json.dumps(data['errors'], indent=2)}")
        return None
    
    result = data["data"]["metaobjectCreate"]
    
    if result.get("userErrors"):
        print(f"❌ User errors: {json.dumps(result['userErrors'], indent=2)}")
        return None
    
    return result["metaobject"]["id"]


def link_metaobject_to_product(token: str, product_id: str, metaobject_id: str, dry_run: bool = False) -> bool:
    """Link metaobject entry to product via metafield."""
    
    mutation = f"""
    mutation {{
      productUpdate(input: {{
        id: "{product_id}"
        metafields: [{{
          namespace: "custom"
          key: "league_program_info"
          type: "metaobject_reference"
          value: "{metaobject_id}"
        }}]
      }}) {{
        product {{
          id
        }}
        userErrors {{
          field
          message
        }}
      }}
    }}
    """
    
    if dry_run:
        print(f"   Would link metaobject {metaobject_id} to product {product_id}")
        return True
    
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
        print(f"❌ GraphQL errors: {json.dumps(data['errors'], indent=2)}")
        return False
    
    result = data["data"]["productUpdate"]
    
    if result.get("userErrors"):
        print(f"❌ User errors: {json.dumps(result['userErrors'], indent=2)}")
        return False
    
    return True


def process_product(token: str, product: dict, dry_run: bool = False) -> bool:
    """Process a single product: parse, create venue, create metaobject, link."""
    
    product_id = product["id"]
    title = product["title"]
    handle = product["handle"]
    description_html = product.get("descriptionHtml", "")
    
    print(f"\n{'='*80}")
    print(f"📦 Product: {title}")
    print(f"   Handle: {handle}")
    print(f"   ID: {product_id}")
    
    if not description_html:
        print("   ⚠️  No description - skipping")
        return False
    
    # Parse description
    try:
        parsed_data = parse_product_description(description_html, title, handle)
    except Exception as e:
        print(f"   ❌ Parse error: {e}")
        return False
    
    # Add shopify_product_id
    parsed_data["shopify_product_id"] = product_id.split("/")[-1]
    
    if not parsed_data:
        print("   ⚠️  No structured data found - skipping")
        return False
    
    print(f"   ✅ Parsed {len(parsed_data)} fields")
    
    # Get or create venue if location found
    venue_id = None
    if "venue_data" in parsed_data:
        venue_id = get_or_create_venue(token, parsed_data["venue_data"], dry_run)
        if not venue_id and not dry_run:
            print(f"   ❌ Failed to create venue")
            return False
    
    # Create league metaobject entry
    metaobject_id = create_metaobject_entry(token, parsed_data, venue_id, dry_run)
    
    if not metaobject_id and not dry_run:
        print(f"   ❌ Failed to create metaobject")
        return False
    
    if not dry_run:
        print(f"   ✅ Created metaobject: {metaobject_id}")
    
    # Link to product
    if not dry_run:
        success = link_metaobject_to_product(token, product_id, metaobject_id, dry_run)
        if success:
            print(f"   ✅ Linked to product")
        else:
            print(f"   ❌ Failed to link")
            return False
    
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    product_id_arg = None
    
    if "--product-id" in sys.argv:
        idx = sys.argv.index("--product-id")
        if idx + 1 < len(sys.argv):
            product_id_arg = sys.argv[idx + 1]
    
    token = load_token()
    
    print(f"🏪 Store: {SHOPIFY_STORE}")
    print(f"🔧 Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    if product_id_arg:
        print(f"🎯 Single product mode: {product_id_arg}")
        product = fetch_product(token, product_id_arg)
        process_product(token, product, dry_run)
    else:
        print(f"📋 Fetching all products...")
        products = fetch_all_products(token)
        print(f"   Found {len(products)} products")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for product in products:
            result = process_product(token, product, dry_run)
            if result:
                success_count += 1
            elif result is False:
                fail_count += 1
            else:
                skip_count += 1
        
        print(f"\n{'='*80}")
        print(f"✅ Success: {success_count}")
        print(f"⚠️  Skipped: {skip_count}")
        print(f"❌ Failed: {fail_count}")


if __name__ == "__main__":
    main()

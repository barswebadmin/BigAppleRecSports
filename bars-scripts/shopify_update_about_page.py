#!/usr/bin/env python3
"""
Update Shopify About Us page leadership images and content.

Supports three modes:
1. Bulk update from CSV (name -> image URL mappings)
2. Single block update by block ID
3. Upload images to Shopify, then update blocks

Usage:
    # Bulk update from CSV
    shopify-update-about-page --bulk-update leadership_images.csv
    
    # Single block update
    shopify-update-about-page --block-id abc123 --image shopify://shop_images/new_photo.jpg
    
    # Upload images and update
    shopify-update-about-page --upload-and-update images_folder/
"""

import os
import sys
import json
import csv
import argparse
import requests
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# Add bars-scripts to path for shared utilities
sys.path.insert(0, str(Path(__file__).parent))

from shared_utils import load_environment, get_shopify_config


def get_ssl_verification():
    """Get SSL verification setting."""
    ssl_cert_file = os.getenv('SSL_CERT_FILE', '/opt/homebrew/etc/openssl@3/cert.pem')
    return ssl_cert_file if os.path.exists(ssl_cert_file) else True


def fetch_template(theme_id: str, asset_key: str, environment: str = "production") -> Optional[Dict[str, Any]]:
    """
    Fetch the About Us template JSON.
    
    Args:
        theme_id: Shopify theme ID
        asset_key: Template asset key
        environment: Environment (production/staging/dev)
    
    Returns:
        Template data as dict, or None if failed
    """
    load_environment(environment)
    shopify_config = get_shopify_config(environment)
    
    store_url = f"https://{shopify_config['store_id']}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": shopify_config['token'],
        "Content-Type": "application/json"
    }
    params = {"asset[key]": asset_key}
    
    verify_ssl = get_ssl_verification()
    
    try:
        response = requests.get(api_url, headers=headers, params=params, verify=verify_ssl, timeout=10)
        response.raise_for_status()
        
        asset = response.json().get('asset', {})
        content = asset.get('value', '')
        
        if not content:
            print(f"❌ Asset '{asset_key}' has no content", file=sys.stderr)
            return None
        
        template_data = json.loads(content)
        return template_data
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error fetching template: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print(json.dumps(error_details, indent=2), file=sys.stderr)
            except json.JSONDecodeError:
                print(e.response.text, file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Unexpected error fetching template: {e}", file=sys.stderr)
        return None


def update_template(theme_id: str, asset_key: str, template_data: Dict[str, Any], environment: str = "production", dry_run: bool = False) -> bool:
    """
    Update the About Us template JSON.
    
    Args:
        theme_id: Shopify theme ID
        asset_key: Template asset key
        template_data: Updated template data
        environment: Environment (production/staging/dev)
        dry_run: If True, print request details without sending
    
    Returns:
        True if successful, False otherwise
    """
    load_environment(environment)
    shopify_config = get_shopify_config(environment)
    
    store_url = f"https://{shopify_config['store_id']}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": shopify_config['token'],
        "Content-Type": "application/json"
    }
    
    payload = {
        "asset": {
            "key": asset_key,
            "value": json.dumps(template_data)
        }
    }
    
    if dry_run:
        print(f"\n{'=' * 80}")
        print(f"🔍 DRY RUN - Request that would be sent to Shopify:")
        print(f"{'=' * 80}")
        print(f"\n📍 URL: PUT {api_url}")
        print(f"\n📋 Headers:")
        for key, value in headers.items():
            if key == "X-Shopify-Access-Token":
                print(f"   {key}: {value[:10]}...{value[-4:]} (redacted)")
            else:
                print(f"   {key}: {value}")
        print(f"\n📦 Body (first 1000 chars of JSON):")
        body_json = json.dumps(payload, indent=2)
        if len(body_json) > 1000:
            print(body_json[:1000])
            print(f"   ... (truncated, total length: {len(body_json)} chars)")
        else:
            print(body_json)
        print(f"\n{'=' * 80}")
        return True
    
    verify_ssl = get_ssl_verification()
    
    try:
        response = requests.put(api_url, headers=headers, json=payload, verify=verify_ssl, timeout=30)
        response.raise_for_status()
        
        print(f"✅ Successfully updated template: {asset_key}")
        return True
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error updating template: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print(json.dumps(error_details, indent=2), file=sys.stderr)
            except json.JSONDecodeError:
                print(e.response.text, file=sys.stderr)
        return False
    except Exception as e:
        print(f"❌ Unexpected error updating template: {e}", file=sys.stderr)
        return False


def upload_image(theme_id: str, image_path: str, shopify_path: str, environment: str = "production") -> Optional[str]:
    """
    Upload an image file to Shopify theme assets.
    
    Args:
        theme_id: Shopify theme ID
        image_path: Local path to image file
        shopify_path: Path in Shopify (e.g., "assets/leadership/john_doe.jpg")
        environment: Environment (production/staging/dev)
    
    Returns:
        Shopify URL reference (e.g., "shopify://shop_images/john_doe.jpg") or None if failed
    """
    load_environment(environment)
    shopify_config = get_shopify_config(environment)
    
    # Read image file as base64
    import base64
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ Image file not found: {image_path}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Error reading image: {e}", file=sys.stderr)
        return None
    
    store_url = f"https://{shopify_config['store_id']}.myshopify.com"
    api_url = f"{store_url}/admin/api/2024-10/themes/{theme_id}/assets.json"
    
    headers = {
        "X-Shopify-Access-Token": shopify_config['token'],
        "Content-Type": "application/json"
    }
    
    payload = {
        "asset": {
            "key": shopify_path,
            "attachment": image_data
        }
    }
    
    verify_ssl = get_ssl_verification()
    
    try:
        response = requests.put(api_url, headers=headers, json=payload, verify=verify_ssl, timeout=30)
        response.raise_for_status()
        
        # Extract filename for shopify:// reference
        filename = Path(shopify_path).name
        shopify_reference = f"shopify://shop_images/{filename}"
        
        print(f"✅ Uploaded: {image_path} → {shopify_reference}")
        return shopify_reference
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ Error uploading image: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json()
                print(json.dumps(error_details, indent=2), file=sys.stderr)
            except json.JSONDecodeError:
                print(e.response.text, file=sys.stderr)
        return None
    except Exception as e:
        print(f"❌ Unexpected error uploading image: {e}", file=sys.stderr)
        return None


def find_blocks_by_name(template_data: Dict[str, Any], name: str) -> List[Tuple[str, str, Dict]]:
    """
    Find all blocks matching a person's name.
    
    Args:
        template_data: Template JSON data
        name: Person's name to search for
    
    Returns:
        List of (section_id, block_id, block_data) tuples
    """
    matches = []
    
    if 'sections' not in template_data:
        return matches
    
    for section_id, section_data in template_data['sections'].items():
        if 'blocks' not in section_data:
            continue
        
        for block_id, block_data in section_data['blocks'].items():
            if block_data.get('type') == 'Text':
                settings = block_data.get('settings', {})
                block_name = settings.get('text', '').strip()
                
                if block_name.lower() == name.lower():
                    matches.append((section_id, block_id, block_data))
    
    return matches


def bulk_update_from_csv(csv_path: str, theme_id: str, asset_key: str, environment: str = "production", dry_run: bool = False):
    """
    Bulk update images from CSV file.
    
    CSV format: name,image_url
    Example:
        Chase Tucker,shopify://shop_images/Chase_Tucker2026.jpg
        Stephen Torres,shopify://shop_images/Stephen_Torres2026.jpg
    
    Args:
        csv_path: Path to CSV file
        theme_id: Shopify theme ID
        asset_key: Template asset key
        environment: Environment
        dry_run: If True, show changes without applying
    """
    print(f"📄 Reading CSV: {csv_path}\n")
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            updates = [(row['name'], row['image_url']) for row in reader]
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_path}", file=sys.stderr)
        return
    except KeyError as e:
        print(f"❌ CSV missing required column: {e}", file=sys.stderr)
        print("Required columns: name,image_url", file=sys.stderr)
        return
    except Exception as e:
        print(f"❌ Error reading CSV: {e}", file=sys.stderr)
        return
    
    if not updates:
        print("⚠️  No updates found in CSV", file=sys.stderr)
        return
    
    print(f"📊 Found {len(updates)} update(s) in CSV\n")
    
    # Fetch current template
    print(f"📥 Fetching template: {asset_key}")
    template_data = fetch_template(theme_id, asset_key, environment)
    
    if not template_data:
        return
    
    print(f"{'='*80}\n")
    
    # Apply updates
    updates_applied = 0
    not_found = []
    
    for name, new_image_url in updates:
        matches = find_blocks_by_name(template_data, name)
        
        if not matches:
            not_found.append(name)
            print(f"⚠️  Not found: {name}")
            continue
        
        for section_id, block_id, block_data in matches:
            old_image = block_data['settings'].get('image', 'N/A')
            
            if dry_run:
                print(f"🔄 Would update: {name}")
                print(f"   Section: {section_id}, Block: {block_id}")
                print(f"   Old: {old_image}")
                print(f"   New: {new_image_url}")
            else:
                template_data['sections'][section_id]['blocks'][block_id]['settings']['image'] = new_image_url
                print(f"✅ Updated: {name}")
                print(f"   Old: {old_image}")
                print(f"   New: {new_image_url}")
            
            updates_applied += 1
    
    print(f"\n{'='*80}\n")
    print(f"📊 Summary:")
    print(f"   ✅ Updated: {updates_applied}")
    print(f"   ⚠️  Not found: {len(not_found)}")
    
    if not_found:
        print(f"\n⚠️  Names not found in template:")
        for name in not_found:
            print(f"   - {name}")
    
    # Upload changes
    if updates_applied > 0:
        if dry_run:
            print(f"\n📤 Would upload changes to Shopify (dry-run mode)...")
        else:
            print(f"\n📤 Uploading changes to Shopify...")
        
        success = update_template(theme_id, asset_key, template_data, environment, dry_run)
        
        if success:
            if dry_run:
                print(f"\n🔍 Dry run complete. No changes were made.")
            else:
                print(f"\n🎉 Bulk update complete!")
        else:
            print(f"\n❌ Failed to upload changes", file=sys.stderr)
    elif dry_run:
        print(f"\n🔍 Dry run complete. No updates needed.")


def single_update(block_id: str, new_image_url: str, theme_id: str, asset_key: str, environment: str = "production", dry_run: bool = False):
    """
    Update a single block by its ID.
    
    Args:
        block_id: Block ID to update
        new_image_url: New image URL
        theme_id: Shopify theme ID
        asset_key: Template asset key
        environment: Environment
        dry_run: If True, show changes without applying
    """
    print(f"🎯 Updating block: {block_id}\n")
    
    # Fetch current template
    print(f"📥 Fetching template: {asset_key}")
    template_data = fetch_template(theme_id, asset_key, environment)
    
    if not template_data:
        return
    
    print(f"{'='*80}\n")
    
    # Find block
    found = False
    for section_id, section_data in template_data.get('sections', {}).items():
        if 'blocks' not in section_data:
            continue
        
        if block_id in section_data['blocks']:
            block_data = section_data['blocks'][block_id]
            old_image = block_data.get('settings', {}).get('image', 'N/A')
            name = block_data.get('settings', {}).get('text', 'Unknown')
            
            print(f"✅ Found block in section: {section_id}")
            print(f"   Name: {name}")
            print(f"   Old image: {old_image}")
            print(f"   New image: {new_image_url}")
            
            # Apply change to template data (even in dry-run for request body generation)
            template_data['sections'][section_id]['blocks'][block_id]['settings']['image'] = new_image_url
            
            found = True
            break
    
    if not found:
        print(f"❌ Block ID not found: {block_id}", file=sys.stderr)
        return
    
    print(f"\n{'='*80}\n")
    
    # Upload changes (or show what would be uploaded in dry-run)
    if dry_run:
        print(f"📤 Would upload changes to Shopify (dry-run mode)...")
    else:
        print(f"📤 Uploading changes to Shopify...")
    
    success = update_template(theme_id, asset_key, template_data, environment, dry_run)
    
    if success:
        if dry_run:
            print(f"\n🔍 Dry run complete. No changes were made.")
        else:
            print(f"\n🎉 Update complete!")
    else:
        print(f"\n❌ Failed to upload changes", file=sys.stderr)


def upload_and_update(images_folder: str, theme_id: str, asset_key: str, environment: str = "production", dry_run: bool = False):
    """
    Upload images from a folder and update template blocks.
    
    Image filenames should match person names (e.g., "Chase_Tucker.jpg", "Stephen_Torres.png")
    
    Args:
        images_folder: Path to folder containing images
        theme_id: Shopify theme ID
        asset_key: Template asset key
        environment: Environment
        dry_run: If True, show changes without applying
    """
    print(f"📁 Scanning folder: {images_folder}\n")
    
    folder_path = Path(images_folder)
    
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"❌ Folder not found: {images_folder}", file=sys.stderr)
        return
    
    # Find image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    image_files = [f for f in folder_path.iterdir() if f.suffix.lower() in image_extensions]
    
    if not image_files:
        print(f"⚠️  No image files found in folder", file=sys.stderr)
        return
    
    print(f"📊 Found {len(image_files)} image(s)\n")
    
    # Fetch current template
    print(f"📥 Fetching template: {asset_key}")
    template_data = fetch_template(theme_id, asset_key, environment)
    
    if not template_data:
        return
    
    print(f"{'='*80}\n")
    
    # Process each image
    updates_applied = 0
    not_found = []
    
    for image_file in image_files:
        # Extract name from filename (remove extension and replace underscores with spaces)
        name = image_file.stem.replace('_', ' ')
        
        print(f"\n🖼️  Processing: {image_file.name} (Name: {name})")
        
        # Upload image to Shopify
        shopify_path = f"assets/leadership/{image_file.name}"
        
        if dry_run:
            shopify_reference = f"shopify://shop_images/{image_file.name}"
            print(f"   Would upload to: {shopify_reference}")
        else:
            shopify_reference = upload_image(theme_id, str(image_file), shopify_path, environment)
            
            if not shopify_reference:
                print(f"   ⚠️  Skipping block update due to upload failure")
                continue
        
        # Find matching blocks
        matches = find_blocks_by_name(template_data, name)
        
        if not matches:
            not_found.append(name)
            print(f"   ⚠️  No matching block found for: {name}")
            continue
        
        # Update blocks
        for section_id, block_id, block_data in matches:
            old_image = block_data['settings'].get('image', 'N/A')
            
            if dry_run:
                print(f"   Would update block: {block_id}")
            else:
                template_data['sections'][section_id]['blocks'][block_id]['settings']['image'] = shopify_reference
                print(f"   ✅ Updated block: {block_id}")
            
            updates_applied += 1
    
    print(f"\n{'='*80}\n")
    print(f"📊 Summary:")
    print(f"   ✅ Updated: {updates_applied}")
    print(f"   ⚠️  Not matched: {len(not_found)}")
    
    if not_found:
        print(f"\n⚠️  No matching blocks found for:")
        for name in not_found:
            print(f"   - {name}")
    
    # Upload template changes
    if updates_applied > 0:
        if dry_run:
            print(f"\n📤 Would upload template changes to Shopify (dry-run mode)...")
        else:
            print(f"\n📤 Uploading template changes to Shopify...")
        
        success = update_template(theme_id, asset_key, template_data, environment, dry_run)
        
        if success:
            if dry_run:
                print(f"\n🔍 Dry run complete. No changes were made.")
            else:
                print(f"\n🎉 Upload and update complete!")
        else:
            print(f"\n❌ Failed to upload template changes", file=sys.stderr)
    elif dry_run:
        print(f"\n🔍 Dry run complete. No updates needed.")


def main():
    parser = argparse.ArgumentParser(
        description="Update Shopify About Us page leadership images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bulk update from CSV
  shopify-update-about-page --bulk-update leadership_images.csv
  
  # Single block update
  shopify-update-about-page --block-id abc123 --image shopify://shop_images/new.jpg
  
  # Upload images and update
  shopify-update-about-page --upload-and-update images_folder/
  
  # Dry run (preview changes)
  shopify-update-about-page --bulk-update leaders.csv --dry-run
"""
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--bulk-update",
        metavar="CSV_FILE",
        help="Bulk update from CSV (columns: name,image_url)"
    )
    mode_group.add_argument(
        "--single-update",
        action="store_true",
        help="Update a single block by ID (requires --block-id and --image)"
    )
    mode_group.add_argument(
        "--upload-and-update",
        metavar="IMAGES_FOLDER",
        help="Upload images and update blocks (filename must match person name)"
    )
    
    # Single update options
    parser.add_argument(
        "--block-id",
        help="Block ID to update (for --single-update)"
    )
    parser.add_argument(
        "--image",
        help="New image URL (for --single-update)"
    )
    
    # Common options
    parser.add_argument(
        "--theme",
        default="134424232030",
        help="Theme ID (default: 134424232030)"
    )
    parser.add_argument(
        "--asset",
        default="templates/page.template-about-us-2.json",
        help="Template asset key (default: templates/page.template-about-us-2.json)"
    )
    parser.add_argument(
        "--env",
        "--environment",
        choices=["production", "staging", "dev"],
        default="production",
        help="Environment (default: production)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    
    args = parser.parse_args()
    
    # Validate single update args
    if args.single_update:
        if not args.block_id or not args.image:
            parser.error("--single-update requires both --block-id and --image")
    
    # Execute selected mode
    if args.bulk_update:
        bulk_update_from_csv(args.bulk_update, args.theme, args.asset, args.env, args.dry_run)
    elif args.single_update:
        single_update(args.block_id, args.image, args.theme, args.asset, args.env, args.dry_run)
    elif args.upload_and_update:
        upload_and_update(args.upload_and_update, args.theme, args.asset, args.env, args.dry_run)


if __name__ == "__main__":
    main()


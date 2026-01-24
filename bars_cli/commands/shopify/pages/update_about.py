"""Update Shopify About page leadership images command."""

from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import csv
import json

import click
from rich.console import Console

from bars_cli._core.context import get_display_context, get_service
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_error_response
from bars_cli._core.prompts import prompt_confirmation, prompt_select_from_options, prompt_text_input

from backend.modules.integrations.shopify.models.theme_template_models import ThemeTemplate


def validate_and_normalize_image(image_input: str, shopify_service: Any) -> str:
    """
    Validate and normalize image input.
    
    Accepts image name, ID, or URL and validates the image exists in Shopify.
    
    Args:
        image_input: Image name, ID, or URL
        shopify_service: Shopify service instance
    
    Returns:
        Normalized shopify:// reference
    
    Raises:
        ValueError: If image doesn't exist or input is invalid
    """
    if not image_input or not image_input.strip():
        return image_input
    
    image_input = image_input.strip()
    
    # If already a shopify:// reference, validate it exists
    if image_input.startswith("shopify://"):
        file_info = shopify_service.get_file_admin_url(image_input)
        if file_info:
            return image_input
        else:
            raise ValueError(f"Image not found: {image_input}")
    
    # If it's an admin URL, extract the file ID and validate
    if image_input.startswith("https://admin.shopify.com"):
        shopify_reference = shopify_service.convert_admin_url_to_shopify_reference(image_input)
        if not shopify_reference:
            raise ValueError(f"Failed to convert admin URL to shopify:// reference: {image_input}")
        
        file_info = shopify_service.get_file_admin_url(shopify_reference)
        if file_info:
            return shopify_reference
        else:
            raise ValueError(f"Image not found: {shopify_reference}")
    
    # Try to find image by name or ID
    shopify_reference = _find_image_by_name_or_id(image_input, shopify_service)
    if shopify_reference:
        return shopify_reference
    else:
        raise ValueError(f"Image not found: {image_input}. Please provide a valid image name, ID, or shopify:// reference.")


def _find_image_by_name_or_id(identifier: str, shopify_service: Any) -> Optional[str]:
    """
    Find image by name or ID and return shopify:// reference.
    
    Args:
        identifier: Image name or ID
        shopify_service: Shopify service instance
    
    Returns:
        Shopify reference if found, None otherwise
    """
    try:
        # Try as filename first
        shopify_reference = f"shopify://shop_images/{identifier}"
        file_info = shopify_service.get_file_admin_url(shopify_reference)
        if file_info:
            return shopify_reference
        
        # Try with common extensions if no extension provided
        if '.' not in identifier:
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                test_reference = f"shopify://shop_images/{identifier}{ext}"
                file_info = shopify_service.get_file_admin_url(test_reference)
                if file_info:
                    return test_reference
        
        # Try as file ID (construct admin URL and convert)
        if identifier.isdigit():
            store_id = shopify_service.client.config.get('store_id')
            admin_url = f"https://admin.shopify.com/store/{store_id}/content/files/{identifier}"
            shopify_reference = shopify_service.convert_admin_url_to_shopify_reference(admin_url)
            if shopify_reference:
                file_info = shopify_service.get_file_admin_url(shopify_reference)
                if file_info:
                    return shopify_reference
        
        return None
    except Exception:
        return None
    """
    Validate and normalize pronouns by wrapping in parentheses if not already wrapped.
    
    Args:
        pronouns: Raw pronouns input (e.g., "he/him", "(she/her)", "they/them")
    
    Returns:
        Normalized pronouns with parentheses (e.g., "(he/him)", "(she/her)", "(they/them)")
    
    Raises:
        ValueError: If pronouns format is invalid
    """
    if not pronouns:
        return pronouns
    
    # Don't modify whitespace-only strings
    if not pronouns.strip():
        return pronouns
    
    pronouns = pronouns.strip()
    
    # Remove parentheses for validation if present
    validation_pronouns = pronouns
    if pronouns.startswith('(') and pronouns.endswith(')'):
        validation_pronouns = pronouns[1:-1].strip()
    
    # Validate format: at least 1 letter + '/' + at least 1 letter
    import re
    if not re.match(r'^[a-zA-Z]+/[a-zA-Z]+', validation_pronouns):
        raise ValueError(f"Invalid pronouns format: '{pronouns}'. Must be at least 1 letter + '/' + at least 1 letter (e.g., 'he/him', 'she/her', 'they/them')")
    
    # If already wrapped in parentheses, return as-is
    if pronouns.startswith('(') and pronouns.endswith(')'):
        return pronouns
    
    # Otherwise, wrap in parentheses
    return f"({pronouns})"


@click.command('update-about')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--bulk-update', type=click.Path(exists=True), help='CSV file with name,image_url columns')
@click.option('--single-update', is_flag=True, default=False, help='Update single block by ID')
@click.option('--block-id', type=str, help='Block ID for single update')
@click.option('--image', type=str, help='Image URL (shopify:// format) for single update')
@click.option('--upload-and-update', type=click.Path(exists=True, file_okay=False, dir_okay=True), help='Upload images from folder and update blocks')
@click.option('--interactive', is_flag=True, default=False, help='Interactive mode: select block and field to edit')
@click.option('--theme', type=str, default='134424232030', help='Theme ID (default: 134424232030)')
@click.option('--asset', type=str, default='templates/page.template-about-us-2.json', help='Template asset key (default: templates/page.template-about-us-2.json)')
@click.option('--dry-run', is_flag=True, default=False, help='Preview changes without applying')
@click.pass_context
def update_about_cmd(
    ctx: click.Context,
    bulk_update: Optional[str] = None,
    single_update: bool = False,
    block_id: Optional[str] = None,
    image: Optional[str] = None,
    upload_and_update: Optional[str] = None,
    interactive: bool = False,
    theme: Optional[str] = None,
    asset: Optional[str] = None,
    dry_run: bool = False
) -> None:
    """
    Update leadership images on the Shopify About Us page.
    
    Supports three modes:
    1. Bulk CSV updates: Update multiple images from CSV file
    2. Single block update: Update one specific block by ID
    3. Upload and update: Upload images from folder and automatically update blocks
    
    Examples:
      bars shopify page update-about --bulk-update leadership_images.csv
      bars shopify page update-about --bulk-update leaders.csv --dry-run
      bars shopify page update-about --single-update --block-id abc123 --image shopify://shop_images/new.jpg
      bars shopify page update-about --upload-and-update images_folder/
      bars shopify page update-about --bulk-update leaders.csv --theme 134424232030
    """
    console = Console()
    shopify_service = get_service(ctx, 'shopify_service')
    json_output, should_display = get_display_context(ctx)
    
    # Validate arguments - if no specific mode is provided, default to interactive
    if not any([bulk_update, single_update, upload_and_update, interactive]):
        interactive = True
    
    if single_update and (not block_id or not image):
        click.echo("❌ --single-update requires --block-id and --image", err=True)
        raise click.ClickException("Invalid arguments")
    
    theme_id = theme or '134424232030'
    asset_key = asset or 'templates/page.template-about-us-2.json'
    
    # Fetch current template as typed model
    if should_display and not json_output:
        console.print(f"[cyan]📥 Fetching template: {asset_key}[/cyan]")
    
    try:
        from backend.modules.integrations.shopify.services.theme_template_service import ThemeTemplateService
        template_service = ThemeTemplateService(shopify_service)
        template_model = template_service.get_template_model(theme_id, asset_key)
    except (RuntimeError, ValueError) as e:
        handle_shopify_error_response(e, json_output, should_display)
        return
    except Exception as e:
        if json_output:
            from bars_cli._core.utils.json_output import output_json_error
            output_json_error(str(e))
        else:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.ClickException(str(e)) from e
    
    if not template_model:
        click.echo(f"❌ Template '{asset_key}' not found in theme {theme_id}", err=True)
        raise click.ClickException("Template not found")
    
    if should_display and not json_output:
        console.print(f"{'='*80}\n")
    
    # Process updates based on mode
    result = None
    try:
        if bulk_update:
            result = _handle_bulk_update(
                bulk_update, template_model, shopify_service, theme_id, asset_key,
                dry_run, console, should_display, json_output
            )
        elif single_update:
            assert block_id is not None and image is not None, "block_id and image required for single_update"
            result = _handle_single_update(
                block_id, image, template_model, shopify_service, theme_id, asset_key,
                dry_run, console, should_display, json_output
            )
        elif upload_and_update:
            result = _handle_upload_and_update(
                upload_and_update, template_model, shopify_service, theme_id, asset_key,
                dry_run, console, should_display, json_output
            )
        elif interactive:
            result = _handle_interactive_update(
                template_model, shopify_service, theme_id, asset_key,
                dry_run, console, should_display, json_output
            )
    except (RuntimeError, ValueError) as e:
        handle_shopify_error_response(e, json_output, should_display)
        raise click.ClickException(str(e)) from e
    except Exception as e:
        if json_output:
            from bars_cli._core.utils.json_output import output_json_error
            output_json_error(str(e))
        else:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            raise click.ClickException(str(e)) from e
    
    return result


def _handle_bulk_update(
    csv_path: str,
    template_model: ThemeTemplate,
    shopify_service: Any,
    theme_id: str,
    asset_key: str,
    dry_run: bool,
    console: Console,
    should_display: bool,
    json_output: bool
) -> bool:
    """Handle bulk CSV update mode."""
    if should_display and not json_output:
        console.print(f"[cyan]📄 Reading CSV: {csv_path}[/cyan]\n")
    
    # Parse CSV
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            updates = [(row['name'], row['image_url']) for row in reader]
    except FileNotFoundError:
        click.echo(f"❌ CSV file not found: {csv_path}", err=True)
        raise click.ClickException("CSV file not found")
    except KeyError as e:
        click.echo(f"❌ CSV missing required column: {e}", err=True)
        click.echo("Required columns: name,image_url", err=True)
        raise click.ClickException("Invalid CSV format")
    except Exception as e:
        click.echo(f"❌ Error reading CSV: {e}", err=True)
        raise click.ClickException(f"CSV read error: {e}")
    
    if not updates:
        click.echo("⚠️  No updates found in CSV", err=True)
        return
    
    if should_display and not json_output:
        console.print(f"[green]📊 Found {len(updates)} update(s) in CSV[/green]\n")
    
    # Apply updates
    updates_applied = 0
    not_found = []
    
    for name, new_image_url in updates:
        # Find matching blocks using template model
        matches = []
        for section in template_model.sections:
            for block in section.blocks:
                if block.settings.text and block.settings.text.lower().strip() == name.lower().strip():
                    matches.append((section.id, block.id, block))
        
        if not matches:
            not_found.append(name)
            if should_display and not json_output:
                console.print(f"[yellow]⚠️  Not found: {name}[/yellow]")
            continue
        
        for section_id, block_id, block in matches:
            old_image = block.settings.image or 'N/A'
            
            if dry_run:
                if should_display and not json_output:
                    console.print(f"[cyan]🔄 Would update: {name}[/cyan]")
                    console.print(f"   Section: {section_id}, Block: {block_id}")
                    console.print(f"   Old: {old_image}")
                    console.print(f"   New: {new_image_url}")
            else:
                block.settings.image = new_image_url
                if should_display and not json_output:
                    console.print(f"[green]✅ Updated: {name}[/green]")
                    console.print(f"   Old: {old_image}")
                    console.print(f"   New: {new_image_url}")
            
            updates_applied += 1
    
    if should_display and not json_output:
        console.print(f"\n{'='*80}\n")
        console.print(f"[cyan]📊 Summary:[/cyan]")
        console.print(f"   ✅ Updated: {updates_applied}")
        console.print(f"   ⚠️  Not found: {len(not_found)}")
        
        if not_found:
            console.print(f"\n[yellow]⚠️  Names not found in template:[/yellow]")
            for name in not_found:
                console.print(f"   - {name}")
    
    # Upload changes
    if updates_applied > 0:
        updated_template_data = template_model.to_shopify_dict()
        success = _upload_template_changes(
            shopify_service, theme_id, asset_key, updated_template_data,
            dry_run, console, should_display, json_output
        )
        return success
    elif dry_run and should_display and not json_output:
        console.print(f"\n[cyan]🔍 Dry run complete. No updates needed.[/cyan]")
        return True
    else:
        return False


def _handle_single_update(
    block_id: str,
    new_image_url: str,
    template_model: ThemeTemplate,
    shopify_service: Any,
    theme_id: str,
    asset_key: str,
    dry_run: bool,
    console: Console,
    should_display: bool,
    json_output: bool
) -> bool:
    """Handle single block update mode."""
    if should_display and not json_output:
        console.print(f"[cyan]🎯 Updating block: {block_id}[/cyan]\n")
    
    # Find block in model
    found = False
    for section in template_model.sections:
        for block in section.blocks:
            if block.id == block_id:
                old_image = block.settings.image or 'N/A'
                name = block.settings.text or 'Unknown'
                
                if should_display and not json_output:
                    console.print(f"[green]✅ Found block in section: {section.id}[/green]")
                    console.print(f"   Name: {name}")
                    console.print(f"   Old image: {old_image}")
                    console.print(f"   New image: {new_image_url}")
                
                block.settings.image = new_image_url
                found = True
                break
        if found:
            break
    
    if not found:
        click.echo(f"❌ Block ID not found: {block_id}", err=True)
        raise click.ClickException("Block not found")
    
    if should_display and not json_output:
        console.print(f"\n{'='*80}\n")
    
    # Upload changes
    updated_template_data = template_model.to_shopify_dict()
    return _upload_template_changes(
        shopify_service, theme_id, asset_key, updated_template_data,
        dry_run, console, should_display, json_output
    )


def _handle_upload_and_update(
    images_folder: str,
    template_model: ThemeTemplate,
    shopify_service: Any,
    theme_id: str,
    asset_key: str,
    dry_run: bool,
    console: Console,
    should_display: bool,
    json_output: bool
) -> bool:
    """Handle upload and update mode."""
    if should_display and not json_output:
        console.print(f"[cyan]📁 Scanning folder: {images_folder}[/cyan]\n")
    
    folder_path = Path(images_folder)
    
    if not folder_path.exists() or not folder_path.is_dir():
        click.echo(f"❌ Folder not found: {images_folder}", err=True)
        raise click.ClickException("Folder not found")
    
    # Find image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    image_files = [f for f in folder_path.iterdir() if f.suffix.lower() in image_extensions]
    
    if not image_files:
        click.echo("⚠️  No image files found in folder", err=True)
        return
    
    if should_display and not json_output:
        console.print(f"[green]📊 Found {len(image_files)} image(s)[/green]\n")
    
    # Process each image
    updates_applied = 0
    not_found = []
    
    for image_file in image_files:
        # Extract name from filename (remove extension and replace underscores with spaces)
        name = image_file.stem.replace('_', ' ')
        
        if should_display and not json_output:
            console.print(f"\n[cyan]🖼️  Processing: {image_file.name} (Name: {name})[/cyan]")
        
        # Upload image to Shopify
        shopify_path = f"assets/leadership/{image_file.name}"
        
        if dry_run:
            shopify_reference = f"shopify://shop_images/{image_file.name}"
            if should_display and not json_output:
                console.print(f"   [cyan]Would upload to: {shopify_reference}[/cyan]")
        else:
            shopify_reference = shopify_service.upload_theme_image(theme_id, str(image_file), shopify_path)  # type: ignore[attr-defined]
            
            if not shopify_reference:
                if should_display and not json_output:
                    console.print(f"   [yellow]⚠️  Skipping block update due to upload failure[/yellow]")
                continue
            
            if should_display and not json_output:
                console.print(f"   [green]✅ Uploaded: {shopify_reference}[/green]")
        
        # Find matching blocks using template model
        matches = []
        for section in template_model.sections:
            for block in section.blocks:
                if block.settings.text and block.settings.text.lower().strip() == name.lower().strip():
                    matches.append((section.id, block.id, block))
        
        if not matches:
            not_found.append(name)
            if should_display and not json_output:
                console.print(f"   [yellow]⚠️  No matching block found for: {name}[/yellow]")
            continue
        
        # Update blocks
        for section_id, block_id, block in matches:
            old_image = block.settings.image or 'N/A'
            
            if dry_run:
                if should_display and not json_output:
                    console.print(f"   [cyan]Would update block: {block_id}[/cyan]")
            else:
                # Update block settings in model
                block.settings.image = shopify_reference
                if should_display and not json_output:
                    console.print(f"   [green]✅ Updated block: {block_id}[/green]")
            
            updates_applied += 1
    
    if should_display and not json_output:
        console.print(f"\n{'='*80}\n")
        console.print(f"[cyan]📊 Summary:[/cyan]")
        console.print(f"   ✅ Updated: {updates_applied}")
        console.print(f"   ⚠️  Not matched: {len(not_found)}")
        
        if not_found:
            console.print(f"\n[yellow]⚠️  No matching blocks found for:[/yellow]")
            for name in not_found:
                console.print(f"   - {name}")
    
    # Upload template changes
    if updates_applied > 0:
        # Convert model back to dict for upload
        updated_template_data = template_model.to_shopify_dict()
        success = _upload_template_changes(
            shopify_service, theme_id, asset_key, updated_template_data,
            dry_run, console, should_display, json_output
        )
        return success
    elif dry_run and should_display and not json_output:
        console.print(f"\n[cyan]🔍 Dry run complete. No updates needed.[/cyan]")
        return True
    else:
        return False


def _upload_template_changes(
    shopify_service: Any,
    theme_id: str,
    asset_key: str,
    template_data: Dict[str, Any],
    dry_run: bool,
    console: Console,
    should_display: bool,
    json_output: bool
) -> bool:
    """Upload template changes to Shopify."""
    if dry_run:
        if should_display and not json_output:
            console.print(f"\n[cyan]📤 Would upload changes to Shopify (dry-run mode)...[/cyan]")
            console.print(f"[cyan]🔍 Dry run complete. No changes were made.[/cyan]\n")
        return True
    
    # Prompt for confirmation
    if should_display and not json_output:
        if not prompt_confirmation("Apply changes to theme asset?", default_value="y"):
            console.print("[yellow]Update cancelled[/yellow]\n")
            return False
        
        console.print(f"\n[cyan]📤 Uploading changes to Shopify...[/cyan]")
    
    success = shopify_service.update_theme_asset(theme_id, asset_key, template_data, dry_run=False)  # type: ignore[attr-defined]
    
    if success:
        if should_display and not json_output:
            console.print(f"[green]✅ Successfully updated template: {asset_key}[/green]")
            console.print(f"[green]🎉 Update complete![/green]\n")
        return True
    else:
        click.echo("❌ Failed to upload changes", err=True)
        return False


def _handle_interactive_update(
    template_model: ThemeTemplate,
    shopify_service: Any,
    theme_id: str,
    asset_key: str,
    dry_run: bool,
    console: Console,
    should_display: bool,
    json_output: bool
) -> bool:
    """Handle interactive update mode - select block and field to edit."""
    from bars_cli.commands.shopify.pages.get import get_page_cmd
    from backend.modules.integrations.shopify.services.theme_template_service import ThemeTemplateService
    
    # Create a mock context to call get_page_cmd with return_all=True
    # Actually, we should call the internal logic directly
    from backend.modules.integrations.shopify.models.theme_template_models import Block
    from bars_cli.commands.shopify._shared.shopify_formatters import format_block_option
    from bars_cli._core.prompts import prompt_select_from_options
    
    # Get all blocks
    all_blocks: List[Block] = []
    for section in sorted(template_model.sections, key=lambda s: s.order):
        sorted_section_blocks = sorted(section.blocks, key=lambda b: b.order)
        all_blocks.extend(sorted_section_blocks)
    
    if not all_blocks:
        click.echo("⚠️  No blocks found in template", err=True)
        return
    
    # Filter out empty blocks
    empty_blocks = []
    filled_blocks = []
    for block in all_blocks:
        is_empty = (
            (not block.settings.description or block.settings.description.strip() == "") and
            (not block.settings.text or block.settings.text.strip() == "") and
            (not block.settings.subtitle or block.settings.subtitle.strip() == "")
        )
        if is_empty:
            empty_blocks.append(block)
        else:
            filled_blocks.append(block)
    
    if empty_blocks:
        click.echo(f"⚠️  {len(empty_blocks)} block(s) found to be empty and are being filtered out", err=True)
    
    if not filled_blocks:
        click.echo("⚠️  No blocks with content found in template", err=True)
        return
    
    # Prompt for block selection
    block_options = [format_block_option(block) for block in filled_blocks]
    selected_option = prompt_select_from_options(
        display_text=f"Select Leadership Entry ({len(filled_blocks)} found)",
        options=block_options,
        display_all=True,
        display_exit=True,
        autocomplete=True
    )
    
    if selected_option is None:
        return
    
    # Determine selected blocks
    if selected_option == "All":
        selected_blocks = filled_blocks
    else:
        selected_block = None
        for i, opt in enumerate(block_options):
            if opt == selected_option:
                selected_block = filled_blocks[i]
                break
        
        if selected_block is None:
            click.echo("❌ Invalid selection", err=True)
            return
        
        selected_blocks = [selected_block]
    
    # Prompt for field selection
    field_options = ["Name", "Pronouns", "Position", "Image"]
    selected_field = prompt_select_from_options(
        display_text="Select field to edit",
        options=field_options,
        display_all=False,
        display_exit=True,
        autocomplete=True
    )
    
    if selected_field is None:
        return
    
    # Map display names to field names
    field_map = {
        "Name": "text",
        "Pronouns": "subtitle",
        "Position": "description",
        "Image": "image"
    }
    field_name = field_map.get(selected_field)
    if not field_name:
        click.echo("❌ Invalid field selection", err=True)
        return
    
    # Get current value for display
    if selected_blocks:
        current_value = getattr(selected_blocks[0].settings, field_name, None) or "N/A"
        if should_display and not json_output:
            console.print(f"\n[cyan]Current {selected_field}: {current_value}[/cyan]")
    
    # Prompt for new value
    if field_name == "image":
        new_value = prompt_text_input(
            f"Enter new {selected_field} (image name, ID, admin URL, or shopify:// reference)",
            default_value=current_value if current_value != "N/A" else None
        )
        
        # Validate and normalize image
        try:
            # Use the service validation which handles all formats
            normalized_image = validate_and_normalize_image(new_value, shopify_service)
            if normalized_image != new_value:
                new_value = normalized_image
                if should_display and not json_output:
                    console.print(f"[green]Resolved to: {new_value}[/green]")
        except ValueError as e:
            if should_display and not json_output:
                console.print(f"[red]❌ {e}[/red]")
            else:
                click.echo(f"❌ {e}", err=True)
            return False
    else:
        new_value = prompt_text_input(
            f"Enter new {selected_field}",
            default_value=current_value if current_value != "N/A" else None
        )
        
        # Normalize pronouns by wrapping in parentheses if needed
        if field_name == "subtitle":  # subtitle is the pronouns field
            try:
                normalized_value = normalize_pronouns(new_value)
                if normalized_value != new_value:
                    new_value = normalized_value
                    if should_display and not json_output:
                        console.print(f"[green]Normalized pronouns to: {new_value}[/green]")
            except ValueError as e:
                if should_display and not json_output:
                    console.print(f"[red]❌ {e}[/red]")
                else:
                    click.echo(f"❌ {e}", err=True)
                return False
    
    # Update blocks using backend service
    template_service = ThemeTemplateService(shopify_service)
    
    updates_applied = 0
    for block in selected_blocks:
        # Find section for this block
        section_id = None
        for section in template_model.sections:
            if any(b.id == block.id for b in section.blocks):
                section_id = section.id
                break
        
        if not section_id:
            if should_display and not json_output:
                console.print(f"[yellow]⚠️  Could not find section for block {block.id}[/yellow]")
            continue
        
        if dry_run:
            if should_display and not json_output:
                console.print(f"[cyan]Would update block {block.id}: {field_name} = {new_value}[/cyan]")
        else:
            try:
                success = template_service.update_block_field(
                    theme_id, asset_key, section_id, block.id, field_name, new_value
                )
                if success:
                    updates_applied += 1
                    if should_display and not json_output:
                        console.print(f"[green]✅ Updated block {block.id}[/green]")
                else:
                    if should_display and not json_output:
                        console.print(f"[yellow]⚠️  Failed to update block {block.id}[/yellow]")
            except ValueError as e:
                if should_display and not json_output:
                    console.print(f"[red]❌ Validation error for block {block.id}: {e}[/red]")
                else:
                    click.echo(f"❌ Validation error: {e}", err=True)
                return False
    
    if updates_applied > 0 and not dry_run:
        if should_display and not json_output:
            console.print(f"\n[green]✅ Successfully updated {updates_applied} block(s)[/green]")
        return True
    elif dry_run:
        if should_display and not json_output:
            console.print(f"\n[cyan]🔍 Dry run complete. No changes were made.[/cyan]")
        return True
    else:
        if should_display and not json_output:
            console.print(f"\n[yellow]⚠️  No updates were applied[/yellow]")
        return False

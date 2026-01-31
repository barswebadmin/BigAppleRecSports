"""Get Shopify page or theme asset command."""

from typing import Optional, Any, List
import json

import click_extra as click
from rich.console import Console

from bars_cli._core.legacy_services import get_service
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli.commands.shopify._shared.command_helpers import handle_shopify_error_response
from bars_cli.commands.shopify._shared.shopify_formatters import (
    display_page,
    display_theme_asset,
    display_theme_assets_list,
    format_block_option,
)
from bars_cli._core.prompts import prompt_select_from_options
from bars_cli.backend_services.shopify.services import ShopifyService
from rich.console import Console
from rich.theme import Theme
from rich.json import JSON
from rich.text import Text

# Theme for block display with yellow keys
BLOCK_THEME = Theme({
    "key": "yellow",
    "value": "white",
})


def _get_display_name(model_class: type, field_name: str) -> str:
    """Get display_name for a field from ApiModel's json_schema_extra.
    
    Args:
        model_class: The ApiModel class (e.g., BlockSettings)
        field_name: The field name (e.g., "text", "description")
    
    Returns:
        Display name from model_config, or field_name if not found
    """
    try:
        json_schema_extra = model_class.model_config.get('json_schema_extra', {})
        fields = json_schema_extra.get('fields', {})
        field_info = fields.get(field_name, {})
        return field_info.get('display_name', field_name)
    except (AttributeError, KeyError, TypeError):
        return field_name


def _format_blocks_for_display(
    blocks: List[Any],
    shopify_service: ShopifyService,
    console: Console
) -> None:
    """Format and display blocks using display_name from ApiModel.
    
    Args:
        blocks: List of Block instances
        shopify_service: ShopifyService instance for getting file admin URLs
        console: Rich Console instance with theme
    """
    # Import here to avoid circular imports
    from bars_cli.backend_services.shopify.models.theme_template_models import BlockSettings
    
    # Fields to display (in order)
    display_fields = ["description", "text", "subtitle", "image"]
    
    for block in blocks:
        console.print()
        settings = block.settings
        
        for field_name in display_fields:
            # Get display_name from model
            display_name = _get_display_name(BlockSettings, field_name)
            
            # Get field value
            field_value = getattr(settings, field_name, None) or "N/A"
            
            # Special handling for image field
            if field_name == "image" and field_value != "N/A":
                file_info = shopify_service.get_file_admin_url(field_value)  # type: ignore[attr-defined]
                if file_info:
                    # Format as hyperlink
                    link_text = Text()
                    link_text.append(file_info['display_text'], style=f"blue underline link {file_info['url']}")
                    console.print(f"[key]{display_name}[/key]: ", end="")
                    console.print(link_text)
                    continue
            
            # Regular field display
            console.print(f"[key]{display_name}[/key]: [value]{field_value}[/value]")
        
        console.print()


@click.command(name='get-page', aliases=['get'])
@handle_display_options(display=True, exit_on_error=True)
@click.option('--page', type=str, help='Page handle (e.g., "contact", "about")')
@click.option('--theme', type=str, help='Theme ID (optional, will auto-detect for template pages)')
@click.option('--asset', type=str, help='Asset path (e.g., "templates/page.about-us-2.json")')
@click.option('--list', is_flag=True, default=False, help='List all assets in theme')
@click.option('--filter', type=str, help='Filter assets by pattern (use with --list)')
@click.option('--extract-positions', is_flag=True, default=False, help='Extract leadership positions from About page')
@click.option('--extract-positions-raw', is_flag=True, default=False, help='Show raw API response for position extraction')
@click.option('--no-auto-template', is_flag=True, default=False, help='Disable automatic template fetching for custom template pages')
@click.option('--return-all', is_flag=True, default=False, help='Return selected blocks instead of displaying (for programmatic use)')
@click.pass_context
def get_page_cmd(
    ctx: click.Context,
    page: Optional[str] = None,
    theme: Optional[str] = None,
    asset: Optional[str] = None,
    list: bool = False,
    filter: Optional[str] = None,
    extract_positions: bool = False,
    extract_positions_raw: bool = False,
    no_auto_template: bool = False,
    return_all: bool = False
) -> None:
    """
    Get Shopify page content or theme asset.
    
    Can fetch:
    - Page by handle (e.g., "contact", "about")
    - Theme asset by theme ID and asset path
    - List all assets in a theme
    - Extract leadership positions from About page template
    
    Examples:
      bars shopify page get --page contact
      bars shopify page get --theme 134424232030 --asset templates/page.about-us-2.json
      bars shopify page get --theme 134424232030 --list
      bars shopify page get --theme 134424232030 --list --filter templates/page
      bars shopify page get --extract-positions
    """
    shopify_service: ShopifyService = get_service(ctx, 'shopify_service')
    json_output = ctx.obj.get('json_output', False)
    
    # Initialize console with theme
    console = Console(theme=BLOCK_THEME)
    
    # Default theme ID for extract-positions
    default_theme_id = "134424232030"
    default_asset_key = "templates/page.template-about-us-2.json"
    
    try:
        if extract_positions or extract_positions_raw:
            theme_id = theme or default_theme_id
            asset_key = asset or default_asset_key
            
            if extract_positions_raw:
                result = shopify_service.extract_leadership_positions(theme_id, asset_key, raw=True)  # type: ignore[attr-defined]
                
                if json_output:
                    console = Console()
                    console.print(JSON.from_data(result))
                    return result
                
                console = Console()
                console.print(f"[cyan]📄 Raw API Response for: {asset_key}[/cyan]\n")
                console.print(f"{'='*80}\n")
                console.print(json.dumps(result, indent=2))
                console.print(f"\n{'='*80}\n")
                return result
            
            result = shopify_service.extract_leadership_positions(theme_id, asset_key, raw=False)  # type: ignore[attr-defined]
            
            if not result:
                click.echo("❌ Failed to extract leadership positions", err=True)
                raise click.ClickException("Template not found or invalid")
            
            console = Console()
            if json_output:
                console.print(JSON.from_data(result))
                return result
            
            console.print(f"[cyan]🎯 Extracting leadership positions from: {asset_key}[/cyan]\n")
            console.print(f"{'='*80}\n")
            
            positions = result.get('positions', [])
            unique_positions = result.get('unique_positions', [])
            total_count = result.get('total_count', 0)
            unique_count = result.get('unique_count', 0)
            
            console.print(f"[green]📊 Found {total_count} total leadership entries[/green]")
            console.print(f"[green]📊 Found {unique_count} unique position titles[/green]\n")
            console.print(f"{'='*80}\n")
            
            for idx, position in enumerate(unique_positions, 1):
                console.print(f"{idx:3}. {position}")
            
            console.print(f"\n{'='*80}\n")
            return result
        
        if theme and list:
            assets = shopify_service.list_theme_assets(theme, filter)  # type: ignore[attr-defined]
            
            console = Console()
            if json_output:
                console.print(JSON.from_data(assets))
                return assets
            
            display_theme_assets_list(assets, theme, console)
            return assets
        
        if theme and asset:
            content = shopify_service.get_theme_asset(theme, asset)  # type: ignore[attr-defined]
            
            if content is None:
                click.echo(f"❌ Asset '{asset}' not found in theme {theme}", err=True)
                raise click.ClickException("Asset not found")
            
            console = Console()
            if json_output:
                if asset.endswith('.json'):
                    try:
                        parsed = json.loads(content)
                        console.print(JSON.from_data(parsed))
                        return parsed
                    except json.JSONDecodeError:
                        console.print(JSON.from_data({"content": content}))
                        return {"content": content}
                else:
                    console.print(JSON.from_data({"content": content}))
                    return {"content": content}
            
            display_theme_asset(theme, asset, content, console)
            return content
        
        if page:
            page_data = shopify_service.get_page(
                page,
                theme_id=theme,
                auto_fetch_template=not no_auto_template
            )  # type: ignore[attr-defined]
            
            if page_data is None or not isinstance(page_data, dict):
                click.echo(f"❌ Page '{page}' not found", err=True)
                click.echo("\nAvailable pages:", err=True)
                # Fetch all pages to show available options
                all_pages = shopify_service.list_theme_assets("134424232030", None)  # type: ignore[attr-defined]
                # This won't work for pages, but we'll show error message
                raise click.ClickException("Page not found")
            
            # Check if page has template content (custom template)
            template_content = page_data.get('template_content')
            theme_id_from_page = page_data.get('theme_id')
            template_asset_key = page_data.get('template_asset_key')
            template_suffix = page_data.get('template_suffix')
            
            # If page has template_suffix but template wasn't auto-fetched, try to fetch it manually
            if template_suffix and not template_content:
                # Build template asset key
                template_asset_key = f"templates/page.{template_suffix}.json"
                
                # Get theme ID if not provided
                if not theme_id_from_page:
                    theme_id_from_page = theme or "134424232030"  # Use provided theme or default
                
                # Try to fetch template content
                try:
                    template_content = shopify_service.get_theme_asset(theme_id_from_page, template_asset_key)  # type: ignore[attr-defined]
                except Exception:
                    template_content = None
            
            if template_content and theme_id_from_page and template_asset_key:
                # Parse template and extract blocks
                try:
                    from bars_cli.backend_services.shopify.services.theme_template_service import ThemeTemplateService
                    from bars_cli.backend_services.shopify.models.theme_template_models import Block
                    
                    template_service = ThemeTemplateService(shopify_service)
                    template_model = template_service.get_template_model(theme_id_from_page, template_asset_key)
                    
                    if not template_model:
                        # Fallback to old display if template parsing fails
                        console = Console()
                        if json_output:
                            console.print(JSON.from_data(page_data))
                            return page_data
                        display_page(page_data, 'text', console)
                        return page_data
                    
                    # Extract all blocks from all sections, preserving section order
                    all_blocks: List[Block] = []
                    for section in sorted(template_model.sections, key=lambda s: s.order):
                        # Sort blocks within each section by block order
                        sorted_section_blocks = sorted(section.blocks, key=lambda b: b.order)
                        all_blocks.extend(sorted_section_blocks)
                    
                    if not all_blocks:
                        click.echo("⚠️  No blocks found in template", err=True)
                        return template_model
                    
                    # Filter out empty blocks (where all three fields are N/A)
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
                    
                    # Warn about filtered blocks
                    if empty_blocks:
                        click.echo(f"⚠️  {len(empty_blocks)} block(s) found to be empty and are being filtered out", err=True)
                    
                    if not filled_blocks:
                        click.echo("⚠️  No blocks with content found in template", err=True)
                        return template_model
                    
                    # Format blocks for selection (only filled blocks)
                    block_options = []
                    block_map = {}
                    for i, block in enumerate(filled_blocks):
                        display_text = format_block_option(block)
                        block_key = f"block_{i}"
                        block_options.append({"value": block_key, "display": display_text})
                        block_map[block_key] = block

                    # Prompt user to select block(s)
                    selected_option = prompt_select_from_options(
                        display_text=f"Select Leadership Entry ({len(filled_blocks)} found)",
                        options=block_options,
                        display_all=True,
                        display_cancel=True
                    )

                    if selected_option is None:
                        # User selected Exit
                        return None
                    
                    # Determine which blocks to display
                    if selected_option == "All":
                        selected_blocks = filled_blocks
                    else:
                        # Find the selected block using the block_map
                        selected_block = block_map.get(selected_option)
                        if selected_block is None:
                            click.echo("❌ Invalid selection", err=True)
                            return None
                        
                        selected_blocks = [selected_block]
                    
                    # If return_all is True, return blocks without displaying
                    if return_all:
                        return selected_blocks
                    
                    # Output based on json_output flag
                    if json_output:
                        # JSON output - print raw block objects as JSON
                        blocks_json = [block.model_dump() for block in selected_blocks]
                        console.print(JSON.from_data(blocks_json))
                        return blocks_json
                    else:
                        # Formatted output - use helper function with display_name
                        _format_blocks_for_display(selected_blocks, shopify_service, console)
                    
                    return template_model
                    
                except Exception as e:
                    # If template parsing fails, fall back to old display
                    console = Console()
                    if json_output:
                        console.print(JSON.from_data(page_data))
                        return page_data
                    display_page(page_data, 'text', console)
                    return page_data
            
            # No template content - use old display logic
            console = Console()
            if json_output:
                console.print(JSON.from_data(page_data))
                return page_data
            
            display_page(page_data, 'text', console)
            return page_data
        
        click.echo("❌ Must specify --page, --theme + --asset, --theme + --list, or --extract-positions", err=True)
        raise click.ClickException("Invalid arguments")
    
    except (RuntimeError, ValueError) as e:
        handle_shopify_error_response(e, json_output, True)

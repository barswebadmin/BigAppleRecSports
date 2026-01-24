"""
Theme Template API Router

Provides REST endpoints for editing Shopify theme templates with typed models.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging

from backend.modules.integrations.shopify.services.shopify_service import ShopifyService
from backend.modules.integrations.shopify.services.theme_template_service import ThemeTemplateService
from backend.modules.integrations.shopify.models.theme_template_models import (
    ThemeTemplate,
    Section,
    Block,
    SectionSettings,
    BlockSettings,
    FontConfig,
    PaddingConfig,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/theme-templates", tags=["theme-templates"])

# Initialize services
shopify_service = ShopifyService()
template_service = ThemeTemplateService(shopify_service)


@router.get("/{theme_id}/{asset_key:path}", response_model=ThemeTemplate)
async def get_template(
    theme_id: str,
    asset_key: str
) -> ThemeTemplate:
    """
    Get theme template as typed model.
    
    Returns ordered list of sections and blocks for frontend editing.
    """
    template = template_service.get_template_model(theme_id, asset_key)
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Template not found: {asset_key}")
    
    return template


@router.get("/{theme_id}/{asset_key:path}/sections", response_model=List[Section])
async def get_sections(
    theme_id: str,
    asset_key: str
) -> List[Section]:
    """
    Get ordered list of sections.
    
    Returns sections sorted by display order.
    """
    sections = template_service.get_ordered_sections(theme_id, asset_key)
    
    if not sections:
        raise HTTPException(status_code=404, detail=f"Template not found: {asset_key}")
    
    return sections


@router.get("/{theme_id}/{asset_key:path}/blocks", response_model=List[Block])
async def get_blocks(
    theme_id: str,
    asset_key: str,
    section_id: Optional[str] = Query(None, description="Filter blocks by section ID")
) -> List[Block]:
    """
    Get ordered list of blocks.
    
    Returns blocks sorted by display order, optionally filtered by section.
    """
    blocks = template_service.get_ordered_blocks(theme_id, asset_key, section_id)
    
    if not blocks:
        raise HTTPException(status_code=404, detail=f"Template not found: {asset_key}")
    
    return blocks


@router.put("/{theme_id}/{asset_key:path}/sections/order")
async def update_section_order(
    theme_id: str,
    asset_key: str,
    section_orders: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Update section display order.
    
    Request body: [{"section_id": "main", "order": 0}, ...]
    """
    orders = [(item["section_id"], item["order"]) for item in section_orders]
    success = template_service.update_section_order(theme_id, asset_key, orders)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update section order")
    
    return {"success": True, "message": "Section order updated"}


@router.put("/{theme_id}/{asset_key:path}/sections/{section_id}/settings")
async def update_section_settings(
    theme_id: str,
    asset_key: str,
    section_id: str,
    settings: SectionSettings
) -> Dict[str, Any]:
    """
    Update section settings (title, font, columns, padding).
    """
    success = template_service.update_section_settings(theme_id, asset_key, section_id, settings)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update section settings")
    
    return {"success": True, "message": "Section settings updated"}


@router.put("/{theme_id}/{asset_key:path}/sections/{section_id}/blocks/order")
async def update_block_order(
    theme_id: str,
    asset_key: str,
    section_id: str,
    block_orders: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Update block display order within a section.
    
    Request body: [{"block_id": "block_123", "order": 0}, ...]
    """
    orders = [(item["block_id"], item["order"]) for item in block_orders]
    success = template_service.update_block_order(theme_id, asset_key, section_id, orders)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update block order")
    
    return {"success": True, "message": "Block order updated"}


@router.post("/{theme_id}/{asset_key:path}/sections/{section_id}/blocks/swap")
async def swap_blocks(
    theme_id: str,
    asset_key: str,
    section_id: str,
    block_ids: Dict[str, str]
) -> Dict[str, Any]:
    """
    Swap the order of two blocks.
    
    Request body: {"block_id_1": "block_123", "block_id_2": "block_456"}
    """
    success = template_service.swap_blocks(
        theme_id,
        asset_key,
        section_id,
        block_ids["block_id_1"],
        block_ids["block_id_2"]
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to swap blocks")
    
    return {"success": True, "message": "Blocks swapped"}


@router.post("/{theme_id}/{asset_key:path}/sections/{section_id}/blocks/{block_id}/move")
async def move_block_to_position(
    theme_id: str,
    asset_key: str,
    section_id: str,
    block_id: str,
    position: Dict[str, int]
) -> Dict[str, Any]:
    """
    Move a block to a specific position.
    
    Request body: {"position": 2}
    """
    success = template_service.move_block_to_position(
        theme_id,
        asset_key,
        section_id,
        block_id,
        position["position"]
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to move block")
    
    return {"success": True, "message": "Block moved"}


@router.put("/{theme_id}/{asset_key:path}/sections/{section_id}/blocks/{block_id}/settings")
async def update_block_settings(
    theme_id: str,
    asset_key: str,
    section_id: str,
    block_id: str,
    settings: BlockSettings
) -> Dict[str, Any]:
    """
    Update block settings (name, image, dimensions, pronouns, position, fonts).
    """
    success = template_service.update_block_settings(
        theme_id,
        asset_key,
        section_id,
        block_id,
        settings
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update block settings")
    
    return {"success": True, "message": "Block settings updated"}


@router.put("/{theme_id}/{asset_key:path}")
async def update_template(
    theme_id: str,
    asset_key: str,
    template: ThemeTemplate
) -> Dict[str, Any]:
    """
    Update entire template (full replacement).
    
    Use this for bulk updates or when you've modified the entire template structure.
    """
    shopify_dict = template.to_shopify_dict()
    success = shopify_service.update_theme_asset(theme_id, asset_key, shopify_dict, dry_run=False)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update template")
    
    return {"success": True, "message": "Template updated"}

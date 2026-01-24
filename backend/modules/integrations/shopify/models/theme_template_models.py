"""
Pydantic models for Shopify theme template editing.

These models represent the structure of Shopify theme templates (specifically page templates)
with typed fields that match Shopify's API structure exactly, plus display names for UI.
"""

from typing import Optional, Dict, Any, List
from pydantic import Field, ConfigDict
from enum import Enum

from shared.model_config import ApiModel


class FontWeight(str, Enum):
    """Font weight options."""
    NORMAL = "normal"
    BOLD = "bold"
    BOLDER = "bolder"
    LIGHTER = "lighter"
    _100 = "100"
    _200 = "200"
    _300 = "300"
    _400 = "400"
    _500 = "500"
    _600 = "600"
    _700 = "700"
    _800 = "800"
    _900 = "900"


class FontStyle(str, Enum):
    """Font style options."""
    NORMAL = "normal"
    ITALIC = "italic"
    OBLIQUE = "oblique"


class FontConfig(ApiModel):
    """Font configuration for text elements."""
    family: Optional[str] = Field(None, description="Font family/type")
    size_desktop: Optional[int] = Field(None, description="Font size (desktop)")
    size_mobile: Optional[int] = Field(None, description="Font size (mobile)")
    weight: Optional[str] = Field(None, description="Font weight")
    style: Optional[str] = Field(None, description="Font style (normal, italic, oblique)")
    color: Optional[str] = Field(None, description="Font color")
    line_height: Optional[int] = Field(None, description="Line height")
    
    model_config = ConfigDict(
        json_schema_extra={
            "display_name": "Font Configuration",
            "fields": {
                "family": {"display_name": "Font Family"},
                "size_desktop": {"display_name": "Font Size (Desktop)"},
                "size_mobile": {"display_name": "Font Size (Mobile)"},
                "weight": {"display_name": "Font Weight"},
                "style": {"display_name": "Font Style"},
                "color": {"display_name": "Font Color"},
                "line_height": {"display_name": "Line Height"},
            }
        }
    )


class PaddingConfig(ApiModel):
    """Padding configuration for elements."""
    top: Optional[int] = Field(None, description="Padding top")
    bottom: Optional[int] = Field(None, description="Padding bottom")
    left: Optional[int] = Field(None, description="Padding left")
    right: Optional[int] = Field(None, description="Padding right")
    left_right: Optional[int] = Field(None, description="Padding left/right (symmetric)")
    full_width: Optional[int] = Field(None, description="Padding full width")
    
    model_config = ConfigDict(
        json_schema_extra={
            "display_name": "Padding Configuration",
            "fields": {
                "top": {"display_name": "Padding Top"},
                "bottom": {"display_name": "Padding Bottom"},
                "left": {"display_name": "Padding Left"},
                "right": {"display_name": "Padding Right"},
                "left_right": {"display_name": "Padding Left/Right"},
                "full_width": {"display_name": "Padding Full Width"},
            }
        }
    )


class BlockSettings(ApiModel):
    """Block settings - represents a person/leadership entry. Matches Shopify JSON exactly."""
    # Text content
    text: Optional[str] = Field(None, description="Name")
    subtitle: Optional[str] = Field(None, description="Pronouns")
    description: Optional[str] = Field(None, description="Position")
    
    # Image
    image: Optional[str] = Field(None, description="Image URL (shopify:// format)")
    width_icon: Optional[int] = Field(None, description="Image width in pixels")
    height_icon: Optional[int] = Field(None, description="Image height in pixels")
    icon_type: Optional[str] = Field(None, description="Icon type (e.g., 'image')")
    icon: Optional[str] = Field(None, description="Icon")
    mg_bottom_icon: Optional[int] = Field(None, description="Margin bottom for icon")
    color_icon: Optional[str] = Field(None, description="Icon color")
    
    # Name (text) font settings
    type_tab_font: Optional[str] = Field(None, description="Font type tab")
    fontsize_title_block: Optional[int] = Field(None, description="Name font size (desktop)")
    fontsize_title_block_mb: Optional[int] = Field(None, description="Name font size (mobile)")
    title_block_font_weight: Optional[str] = Field(None, description="Name font weight")
    
    # Subtitle (pronouns) font settings
    color_subtitle: Optional[str] = Field(None, description="Pronouns color")
    fontsize_subtitle: Optional[int] = Field(None, description="Pronouns font size (desktop)")
    fontsize_subtitle_mb: Optional[int] = Field(None, description="Pronouns font size (mobile)")
    fontweight_subtitle: Optional[str] = Field(None, description="Pronouns font weight")
    italic_subtitle: Optional[bool] = Field(None, description="Pronouns italic")
    mg_bottom_subtitle: Optional[int] = Field(None, description="Margin bottom for pronouns")
    
    # Description (position) font settings
    fontsize_des_block: Optional[int] = Field(None, description="Position font size (desktop)")
    fontsize_des_block_mb: Optional[int] = Field(None, description="Position font size (mobile)")
    lineheight_des_block: Optional[int] = Field(None, description="Position line height")
    mg_bottom_des: Optional[int] = Field(None, description="Margin bottom for position")
    color_des_block: Optional[str] = Field(None, description="Position color")
    
    # Block styling
    bg_color_block: Optional[str] = Field(None, description="Background color")
    border_block: Optional[str] = Field(None, description="Border color")
    
    # Button settings
    button: Optional[str] = Field(None, description="Button text")
    link: Optional[str] = Field(None, description="Button link")
    button_style: Optional[str] = Field(None, description="Button style")
    fontsize_button: Optional[int] = Field(None, description="Button font size")
    button_width: Optional[int] = Field(None, description="Button width")
    
    model_config = ConfigDict(
        json_schema_extra={
            "display_name": "Block Settings",
            "fields": {
                "text": {"display_name": "Name"},
                "subtitle": {"display_name": "Pronouns"},
                "description": {"display_name": "Position"},
                "image": {"display_name": "Image"},
                "width_icon": {"display_name": "Image Width"},
                "height_icon": {"display_name": "Image Height"},
                "fontsize_title_block": {"display_name": "Name Font Size"},
                "title_block_font_weight": {"display_name": "Name Font Weight"},
                "color_subtitle": {"display_name": "Pronouns Color"},
                "fontsize_subtitle": {"display_name": "Pronouns Font Size"},
                "fontweight_subtitle": {"display_name": "Pronouns Font Weight"},
                "italic_subtitle": {"display_name": "Pronouns Italic"},
                "fontsize_des_block": {"display_name": "Position Font Size"},
                "color_des_block": {"display_name": "Position Color"},
            }
        }
    )


class Block(ApiModel):
    """A single block within a section (represents one person/leadership entry)."""
    id: str = Field(..., description="Block ID (e.g., 'block_abc123')")
    type: str = Field(..., description="Block type (e.g., 'text')")
    settings: BlockSettings = Field(..., description="Block settings")
    order: int = Field(..., description="Display order within section")
    
    model_config = ConfigDict(
        json_schema_extra={
            "display_name": "Block",
            "fields": {
                "id": {"display_name": "Block ID"},
                "type": {"display_name": "Block Type"},
                "settings": {"display_name": "Settings"},
                "order": {"display_name": "Order"},
            }
        }
    )


class SectionSettings(ApiModel):
    """Section/Container settings. Matches Shopify JSON exactly."""
    # Container
    container: Optional[str] = Field(None, description="Container width (e.g., 'container', '1170')")
    padding_full_width: Optional[int] = Field(None, description="Padding full width")
    
    # Borders
    display_border_top: Optional[bool] = Field(None, description="Display top border")
    display_border_bottom: Optional[bool] = Field(None, description="Display bottom border")
    border_color: Optional[str] = Field(None, description="Border color")
    
    # Title
    service_block_title: Optional[str] = Field(None, description="Department/Section title")
    color_title: Optional[str] = Field(None, description="Title color")
    fontsize_title: Optional[int] = Field(None, description="Title font size (desktop)")
    fontsize_title_mb: Optional[int] = Field(None, description="Title font size (mobile)")
    mg_bottom_title_service_block: Optional[int] = Field(None, description="Margin bottom for title (desktop)")
    mg_bottom_title_service_block_mb: Optional[int] = Field(None, description="Margin bottom for title (mobile)")
    
    # Description
    service_block_des: Optional[str] = Field(None, description="Section description")
    service_block_des_pos: Optional[str] = Field(None, description="Description position (e.g., 'top')")
    color_des: Optional[str] = Field(None, description="Description color")
    fontsize_des: Optional[int] = Field(None, description="Description font size")
    
    # Columns
    desktop_columns: Optional[int] = Field(None, description="Number of columns on desktop")
    tablet_columns: Optional[int] = Field(None, description="Number of columns on tablet")
    mobile_columns: Optional[int] = Field(None, description="Number of columns on mobile")
    
    # Margins
    mg_top_desktop: Optional[int] = Field(None, description="Margin top (desktop)")
    mg_top_tablet: Optional[int] = Field(None, description="Margin top (tablet)")
    mg_top_mobile: Optional[int] = Field(None, description="Margin top (mobile)")
    mg_bottom_desktop: Optional[int] = Field(None, description="Margin bottom (desktop)")
    mg_bottom_tablet: Optional[int] = Field(None, description="Margin bottom (tablet)")
    mg_bottom_mobile: Optional[int] = Field(None, description="Margin bottom (mobile)")
    
    # Item padding
    item_padding_top: Optional[int] = Field(None, description="Item padding top")
    item_padding_bottom: Optional[int] = Field(None, description="Item padding bottom")
    item_padding_left_right: Optional[int] = Field(None, description="Item padding left/right")
    
    # Background
    policies_bg: Optional[str] = Field(None, description="Background color")
    policies_bg_gradient: Optional[str] = Field(None, description="Background gradient")
    
    # Layout
    grid_gap: Optional[int] = Field(None, description="Grid gap")
    item_radius: Optional[int] = Field(None, description="Item border radius")
    
    model_config = ConfigDict(
        json_schema_extra={
            "display_name": "Section Settings",
            "fields": {
                "service_block_title": {"display_name": "Department Title"},
                "color_title": {"display_name": "Title Color"},
                "fontsize_title": {"display_name": "Title Font Size"},
                "desktop_columns": {"display_name": "Desktop Columns"},
                "tablet_columns": {"display_name": "Tablet Columns"},
                "mobile_columns": {"display_name": "Mobile Columns"},
                "item_padding_top": {"display_name": "Item Padding Top"},
                "item_padding_bottom": {"display_name": "Item Padding Bottom"},
                "item_padding_left_right": {"display_name": "Item Padding Left/Right"},
            }
        }
    )


class Section(ApiModel):
    """A section/container within a template (represents a department)."""
    id: str = Field(..., description="Section ID (e.g., 'main', 'leadership_section')")
    type: str = Field(..., description="Section type (e.g., 'custom-service-block')")
    settings: SectionSettings = Field(default_factory=lambda: SectionSettings(), description="Section settings")
    blocks: List[Block] = Field(default_factory=list, description="Ordered list of blocks")
    order: int = Field(..., description="Display order of section")
    
    model_config = ConfigDict(
        json_schema_extra={
            "display_name": "Section",
            "fields": {
                "id": {"display_name": "Section ID"},
                "type": {"display_name": "Section Type"},
                "settings": {"display_name": "Settings"},
                "blocks": {"display_name": "Blocks"},
                "order": {"display_name": "Order"},
            }
        }
    )


class ThemeTemplate(ApiModel):
    """Root model for a Shopify theme template."""
    theme_id: str = Field(..., description="Theme ID")
    asset_key: str = Field(..., description="Asset key (e.g., 'templates/page.template-about-us-2.json')")
    sections: List[Section] = Field(default_factory=list, description="Ordered list of sections")
    
    model_config = ConfigDict(
        json_schema_extra={
            "display_name": "Theme Template",
            "fields": {
                "theme_id": {"display_name": "Theme ID"},
                "asset_key": {"display_name": "Asset Key"},
                "sections": {"display_name": "Sections"},
            }
        }
    )
    
    def to_shopify_dict(self) -> Dict[str, Any]:
        """Convert model back to Shopify template JSON format."""
        shopify_data = {
            "sections": {},
            "order": []
        }
        
        # Sort sections by order and build both sections dict and order array
        sorted_sections = sorted(self.sections, key=lambda s: s.order)
        
        for section in sorted_sections:
            section_dict = {
                "type": section.type,
                "settings": section.settings.model_dump(exclude_none=True),
                "blocks": {},
                "block_order": []
            }
            
            # Sort blocks by order and build block_order array
            sorted_blocks = sorted(section.blocks, key=lambda b: b.order)
            for block in sorted_blocks:
                block_dict = {
                    "type": block.type,
                    "settings": block.settings.model_dump(exclude_none=True)
                }
                section_dict["blocks"][block.id] = block_dict
                section_dict["block_order"].append(block.id)
            
            shopify_data["sections"][section.id] = section_dict
            shopify_data["order"].append(section.id)
        
        return shopify_data
    
    @classmethod
    def from_shopify_dict(
        cls,
        shopify_data: Dict[str, Any],
        theme_id: str,
        asset_key: str
    ) -> "ThemeTemplate":
        """Parse Shopify template JSON into model instances."""
        sections = []
        section_order = 0
        
        if "sections" not in shopify_data:
            return cls(theme_id=theme_id, asset_key=asset_key, sections=[])
        
        # Get block_order from section data if available
        for section_id, section_data in shopify_data["sections"].items():
            section_type = section_data.get("type", "page")
            section_settings = SectionSettings(**section_data.get("settings", {}))
            
            blocks = []
            block_order_map = {}
            
            # Get block order from section's block_order array if present
            if "block_order" in section_data:
                for idx, block_id in enumerate(section_data["block_order"]):
                    block_order_map[block_id] = idx
            
            if "blocks" in section_data:
                for block_id, block_data in section_data["blocks"].items():
                    block_type = block_data.get("type", "Text")
                    block_settings = BlockSettings(**block_data.get("settings", {}))
                    
                    # Use block_order if available, otherwise use insertion order
                    block_order = block_order_map.get(block_id, len(blocks))
                    
                    block = Block(
                        id=block_id,
                        type=block_type,
                        settings=block_settings,
                        order=block_order
                    )
                    blocks.append(block)
            
            # Sort blocks by order
            blocks = sorted(blocks, key=lambda b: b.order)
            
            section = Section(
                id=section_id,
                type=section_type,
                settings=section_settings,
                blocks=blocks,
                order=section_order
            )
            sections.append(section)
            section_order += 1
        
        return cls(
            theme_id=theme_id,
            asset_key=asset_key,
            sections=sections
        )

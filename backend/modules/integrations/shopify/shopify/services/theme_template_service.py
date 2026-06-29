"""
Service for working with Shopify theme templates as typed models.

Provides methods to:
- Parse Shopify template JSON into typed models
- Return ordered lists of sections and blocks for frontend editing
- Apply updates from models back to Shopify
"""

from typing import List, Optional, Dict, Any, Tuple
import logging

from modules.integrations.shopify.models.theme_template_models import (
    ThemeTemplate,
    Section,
    Block,
    SectionSettings,
    BlockSettings,
    FontConfig,
    PaddingConfig,
)
from modules.integrations.shopify.services.shopify_service import ShopifyService

logger = logging.getLogger(__name__)


class ThemeTemplateService:
    """Service for theme template operations using typed models."""
    
    def __init__(self, shopify_service: ShopifyService):
        """Initialize with ShopifyService instance."""
        self.shopify_service = shopify_service
    
    def get_template_model(
        self,
        theme_id: str,
        asset_key: str
    ) -> Optional[ThemeTemplate]:
        """
        Fetch and parse a theme template into typed models.
        
        This is the primary method for getting templates - always returns typed models.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key (e.g., 'templates/page.template-about-us-2.json')
        
        Returns:
            ThemeTemplate model instance, or None if not found
        """
        template_data = self.shopify_service._get_theme_template_dict(theme_id, asset_key)
        
        if not template_data:
            return None
        
        return ThemeTemplate.from_shopify_dict(template_data, theme_id, asset_key)
    
    def get_ordered_sections(
        self,
        theme_id: str,
        asset_key: str
    ) -> List[Section]:
        """
        Get ordered list of sections for frontend editing.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
        
        Returns:
            Ordered list of Section models
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return []
        
        return sorted(template.sections, key=lambda s: s.order)
    
    def get_ordered_blocks(
        self,
        theme_id: str,
        asset_key: str,
        section_id: Optional[str] = None
    ) -> List[Block]:
        """
        Get ordered list of blocks for frontend editing.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_id: Optional section ID to filter blocks. If None, returns all blocks from all sections.
        
        Returns:
            Ordered list of Block models
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return []
        
        all_blocks = []
        for section in template.sections:
            if section_id is None or section.id == section_id:
                for block in section.blocks:
                    all_blocks.append(block)
        
        return sorted(all_blocks, key=lambda b: b.order)
    
    def update_section_order(
        self,
        theme_id: str,
        asset_key: str,
        section_orders: List[Tuple[str, int]]
    ) -> bool:
        """
        Update section display order.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_orders: List of (section_id, new_order) tuples
        
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return False
        
        order_map = {section_id: order for section_id, order in section_orders}
        
        for section in template.sections:
            if section.id in order_map:
                section.order = order_map[section.id]
        
        return self._save_template(template)
    
    def update_section_settings(
        self,
        theme_id: str,
        asset_key: str,
        section_id: str,
        settings: SectionSettings
    ) -> bool:
        """
        Update section settings.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_id: Section ID to update
            settings: Updated section settings
        
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return False
        
        for section in template.sections:
            if section.id == section_id:
                section.settings = settings
                return self._save_template(template)
        
        return False
    
    def update_block_order(
        self,
        theme_id: str,
        asset_key: str,
        section_id: str,
        block_orders: List[Tuple[str, int]]
    ) -> bool:
        """
        Update block display order within a section.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_id: Section ID containing the blocks
            block_orders: List of (block_id, new_order) tuples
        
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return False
        
        order_map = {block_id: order for block_id, order in block_orders}
        
        for section in template.sections:
            if section.id == section_id:
                for block in section.blocks:
                    if block.id in order_map:
                        block.order = order_map[block.id]
                return self._save_template(template)
        
        return False
    
    def swap_blocks(
        self,
        theme_id: str,
        asset_key: str,
        section_id: str,
        block_id_1: str,
        block_id_2: str
    ) -> bool:
        """
        Swap the order of two blocks.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_id: Section ID containing the blocks
            block_id_1: First block ID
            block_id_2: Second block ID
        
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return False
        
        for section in template.sections:
            if section.id == section_id:
                block1 = next((b for b in section.blocks if b.id == block_id_1), None)
                block2 = next((b for b in section.blocks if b.id == block_id_2), None)
                
                if block1 and block2:
                    block1.order, block2.order = block2.order, block1.order
                    return self._save_template(template)
        
        return False
    
    def move_block_to_position(
        self,
        theme_id: str,
        asset_key: str,
        section_id: str,
        block_id: str,
        target_position: int
    ) -> bool:
        """
        Move a block to a specific position.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_id: Section ID containing the block
            block_id: Block ID to move
            target_position: Target position (0-based index)
        
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return False
        
        for section in template.sections:
            if section.id == section_id:
                block = next((b for b in section.blocks if b.id == block_id), None)
                if not block:
                    return False
                
                # Reorder all blocks
                sorted_blocks = sorted(section.blocks, key=lambda b: b.order)
                sorted_blocks.remove(block)
                sorted_blocks.insert(target_position, block)
                
                # Reassign orders
                for idx, b in enumerate(sorted_blocks):
                    b.order = idx
                
                return self._save_template(template)
        
        return False
    
    def update_block_settings(
        self,
        theme_id: str,
        asset_key: str,
        section_id: str,
        block_id: str,
        settings: BlockSettings
    ) -> bool:
        """
        Update block settings.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_id: Section ID containing the block
            block_id: Block ID to update
            settings: Updated block settings
        
        Returns:
            True if successful, False otherwise
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return False
        
        for section in template.sections:
            if section.id == section_id:
                block = next((b for b in section.blocks if b.id == block_id), None)
                if block:
                    block.settings = settings
                    return self._save_template(template)
        
        return False
    
    def update_block_field(
        self,
        theme_id: str,
        asset_key: str,
        section_id: str,
        block_id: str,
        field_name: str,
        field_value: str
    ) -> bool:
        """
        Update a single field in block settings.
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            section_id: Section ID containing the block
            block_id: Block ID to update
            field_name: Field name to update (e.g., 'text', 'subtitle', 'description', 'image')
            field_value: New value for the field
        
        Returns:
            True if successful, False otherwise
        
        Raises:
            ValueError: If validation fails for the field value
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return False
        
        # Validate and normalize field values
        if field_name == "subtitle":
            field_value = self._validate_and_normalize_pronouns(field_value)
        elif field_name == "image":
            field_value = self._validate_and_normalize_image(field_value)
        
        for section in template.sections:
            if section.id == section_id:
                block = next((b for b in section.blocks if b.id == block_id), None)
                if block:
                    # Update the specific field
                    if hasattr(block.settings, field_name):
                        setattr(block.settings, field_name, field_value)
                        return self._save_template(template)
        
        return False
    
    def _normalize_pronouns(self, pronouns: str) -> str:
        """
        Normalize pronouns by wrapping in parentheses if not already wrapped.
        
        Args:
            pronouns: Raw pronouns input (e.g., "he/him", "(she/her)", "they/them")
        
        Returns:
            Normalized pronouns with parentheses (e.g., "(he/him)", "(she/her)", "(they/them)")
        """
        if not pronouns:
            return pronouns
        
        # Don't modify whitespace-only strings
        if not pronouns.strip():
            return pronouns
        
        pronouns = pronouns.strip()
        
        # If already wrapped in parentheses, return as-is
        if pronouns.startswith('(') and pronouns.endswith(')'):
            return pronouns
        
        # Otherwise, wrap in parentheses
        return f"({pronouns})"
    
    def _validate_and_normalize_pronouns(self, pronouns: str) -> str:
        """
        Validate and normalize pronouns.
        
        Args:
            pronouns: Raw pronouns input
        
        Returns:
            Normalized pronouns with parentheses
        
        Raises:
            ValueError: If pronouns format is invalid
        """
        if not pronouns or not pronouns.strip():
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
        
        # Normalize by wrapping in parentheses
        return self._normalize_pronouns(pronouns)
    
    def _validate_and_normalize_image(self, image_input: str) -> str:
        """
        Validate and normalize image input.
        
        Accepts image name, ID, or URL and validates the image exists in Shopify.
        
        Args:
            image_input: Image name, ID, or URL
        
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
            if self._validate_shopify_image_exists(image_input):
                return image_input
            else:
                raise ValueError(f"Image not found: {image_input}")
        
        # If it's an admin URL, extract the file ID and validate
        if image_input.startswith("https://admin.shopify.com"):
            shopify_reference = self.shopify_service.convert_admin_url_to_shopify_reference(image_input)
            if not shopify_reference:
                raise ValueError(f"Failed to convert admin URL to shopify:// reference: {image_input}")
            
            if self._validate_shopify_image_exists(shopify_reference):
                return shopify_reference
            else:
                raise ValueError(f"Image not found: {shopify_reference}")
        
        # Try to find image by name or ID
        shopify_reference = self._find_image_by_name_or_id(image_input)
        if shopify_reference:
            return shopify_reference
        else:
            raise ValueError(f"Image not found: {image_input}. Please provide a valid image name, ID, or shopify:// reference.")
    
    def _validate_shopify_image_exists(self, shopify_reference: str) -> bool:
        """
        Validate that a shopify:// image reference exists.
        
        Args:
            shopify_reference: Shopify image reference (e.g., "shopify://shop_images/filename.jpg")
        
        Returns:
            True if image exists, False otherwise
        """
        try:
            file_info = self.shopify_service.get_file_admin_url(shopify_reference)
            return file_info is not None
        except Exception:
            return False
    
    def _find_image_by_name_or_id(self, identifier: str) -> Optional[str]:
        """
        Find image by name or ID and return shopify:// reference.
        
        Args:
            identifier: Image name or ID
        
        Returns:
            Shopify reference if found, None otherwise
        """
        try:
            # Try as filename first
            shopify_reference = f"shopify://shop_images/{identifier}"
            if self._validate_shopify_image_exists(shopify_reference):
                return shopify_reference
            
            # Try with common extensions if no extension provided
            if '.' not in identifier:
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                    test_reference = f"shopify://shop_images/{identifier}{ext}"
                    if self._validate_shopify_image_exists(test_reference):
                        return test_reference
            
            # Try as file ID (construct admin URL and convert)
            if identifier.isdigit():
                store_id = self.shopify_service.client.config.get('store_id')
                admin_url = f"https://admin.shopify.com/store/{store_id}/content/files/{identifier}"
                shopify_reference = self.shopify_service.convert_admin_url_to_shopify_reference(admin_url)
                if shopify_reference and self._validate_shopify_image_exists(shopify_reference):
                    return shopify_reference
            
            return None
        except Exception:
            return None
        return False
    
    def find_blocks_by_name(
        self,
        theme_id: str,
        asset_key: str,
        name: str
    ) -> List[Tuple[str, str, Block]]:
        """
        Find blocks in template by person name (using typed models).
        
        Args:
            theme_id: Theme ID
            asset_key: Asset key
            name: Person name to search for (matched against block settings.text)
        
        Returns:
            List of (section_id, block_id, block) tuples for matching blocks
        """
        template = self.get_template_model(theme_id, asset_key)
        if not template:
            return []
        
        matches = []
        name_lower = name.lower().strip()
        
        for section in template.sections:
            for block in section.blocks:
                if block.settings.text and block.settings.text.lower().strip() == name_lower:
                    matches.append((section.id, block.id, block))
        
        return matches
    
    def _save_template(self, template: ThemeTemplate) -> bool:
        """Save template back to Shopify."""
        shopify_dict = template.to_shopify_dict()
        return self.shopify_service.update_theme_asset(
            template.theme_id,
            template.asset_key,
            shopify_dict,
            dry_run=False
        )

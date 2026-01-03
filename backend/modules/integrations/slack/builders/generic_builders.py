"""
Generic, business-agnostic Slack message building utilities.

These utilities can be used across all domains (refunds, orders, leadership, etc.)
without any domain-specific knowledge.

Uses Slack SDK's typed models to ensure valid block structure and prevent
"invalid_blocks" errors at type-check time.
"""

from typing import List, Optional, Union
from slack_sdk.models.blocks import (
    Block,
    HeaderBlock,
    SectionBlock,
    DividerBlock,
    ContextBlock,
    ActionsBlock,
    ButtonElement,
    PlainTextObject,
    MarkdownTextObject,
)
from slack_sdk.models.blocks.block_elements import BlockElement, InteractiveElement
from slack_sdk.models.blocks.basic_components import ConfirmObject


class GenericMessageBuilder:
    """
    Business-agnostic Slack message building utilities.
    
    Provides pure Slack Block Kit building functions with zero business logic.
    Uses Slack SDK's typed models for compile-time safety.
    All methods are static - no state required.
    """
    
    @staticmethod
    def header(text: str) -> HeaderBlock:
        """
        Build a header block for Slack.
        
        Args:
            text: Header text (plain text, max 150 chars)
            
        Returns:
            Typed Slack header block
        """
        return HeaderBlock(text=text)
    
    @staticmethod
    def section(
        text: str, 
        fields: Optional[List[str]] = None,
        block_id: Optional[str] = None
    ) -> SectionBlock:
        """
        Build a section block for Slack.
        
        Args:
            text: Section text (markdown supported)
            fields: Optional list of field texts (markdown supported)
            block_id: Optional block identifier
            
        Returns:
            Typed Slack section block
        """
        text_obj = MarkdownTextObject(text=text)
        
        if fields:
            field_objs = [MarkdownTextObject(text=f) for f in fields]
            return SectionBlock(text=text_obj, fields=field_objs, block_id=block_id)
        
        return SectionBlock(text=text_obj, block_id=block_id)
    
    @staticmethod
    def divider() -> DividerBlock:
        """
        Build a divider block for Slack.
        
        Returns:
            Typed Slack divider block
        """
        return DividerBlock()
    
    @staticmethod
    def context(elements: List[str]) -> ContextBlock:
        """
        Build a context block for Slack (small, muted text).
        
        Args:
            elements: List of text elements (markdown supported)
            
        Returns:
            Typed Slack context block
        """
        element_objs = [MarkdownTextObject(text=e) for e in elements]
        return ContextBlock(elements=element_objs)
    
    @staticmethod
    def button(
        text: str, 
        action_id: str, 
        value: Optional[str] = None, 
        style: Optional[str] = None,
        url: Optional[str] = None,
        confirm: Optional[ConfirmObject] = None
    ) -> ButtonElement:
        """
        Build a button for Slack.
        
        Args:
            text: Button label
            action_id: Unique action identifier
            value: Value to send when clicked (required unless url provided)
            style: Optional style ("primary", "danger", or None for default)
            url: Optional URL (creates link button instead of action)
            confirm: Optional confirmation dialog to show before action
            
        Returns:
            Typed Slack button element
        """
        text_obj = PlainTextObject(text=text)
        
        return ButtonElement(
            text=text_obj,
            action_id=action_id,
            value=value,
            url=url,
            style=style,
            confirm=confirm
        )
    
    @staticmethod
    def confirm_button(
        text: str,
        action_id: str,
        value: Optional[str] = None,
        url: Optional[str] = None,
        confirm: Optional[ConfirmObject] = None
    ) -> ButtonElement:
        """
        Build a primary-styled confirmation button.
        
        Args:
            text: Button label
            action_id: Unique action identifier
            value: Value to send when clicked
            url: Optional URL (creates link button instead of action)
            confirm: Optional confirmation dialog to show before action
            
        Returns:
            Typed Slack button element with primary style
        """
        return GenericMessageBuilder.button(
            text=text,
            action_id=action_id,
            value=value,
            style="primary",
            url=url,
            confirm=confirm
        )
    
    @staticmethod
    def cancel_button(
        text: str,
        action_id: str,
        value: Optional[str] = None,
        url: Optional[str] = None,
        confirm: Optional[ConfirmObject] = None
    ) -> ButtonElement:
        """
        Build a danger-styled cancel button.
        
        Args:
            text: Button label
            action_id: Unique action identifier
            value: Value to send when clicked
            url: Optional URL (creates link button instead of action)
            confirm: Optional confirmation dialog to show before action
            
        Returns:
            Typed Slack button element with danger style
        """
        return GenericMessageBuilder.button(
            text=text,
            action_id=action_id,
            value=value,
            style="danger",
            url=url,
            confirm=confirm
        )
    
    @staticmethod
    def actions(elements: List[Union[ButtonElement, InteractiveElement]]) -> ActionsBlock:
        """
        Build an actions block containing buttons or other interactive elements.
        
        Args:
            elements: List of typed button/select/etc elements
            
        Returns:
            Typed Slack actions block
        """
        return ActionsBlock(elements=elements)
    
    @staticmethod
    def confirmation_dialog(
        title: str,
        text: str,
        confirm_text: str = "Confirm",
        deny_text: str = "Cancel",
        style: Optional[str] = None
    ) -> ConfirmObject:
        """
        Build a confirmation dialog to attach to buttons or other actions.
        
        Args:
            title: Dialog title (max 100 chars)
            text: Dialog text/description (max 300 chars, markdown supported)
            confirm_text: Confirm button text (max 30 chars)
            deny_text: Cancel button text (max 30 chars)
            style: Optional style ("primary" or "danger")
            
        Returns:
            Typed Slack confirmation object
            
        Example:
            confirm = builder.confirmation_dialog(
                title="Delete Item?",
                text="Are you sure you want to delete this item?",
                confirm_text="Yes, delete",
                deny_text="Cancel",
                style="danger"
            )
            button = builder.cancel_button(
                text="Delete",
                action_id="delete_item",
                confirm=confirm
            )
        """
        title_obj = PlainTextObject(text=title)
        text_obj = MarkdownTextObject(text=text)
        confirm_obj = PlainTextObject(text=confirm_text)
        deny_obj = PlainTextObject(text=deny_text)
        
        return ConfirmObject(
            title=title_obj,
            text=text_obj,
            confirm=confirm_obj,
            deny=deny_obj,
            style=style
        )
    
    # ========================================================================
    # TEXT FORMATTING HELPERS (Markdown strings for use in blocks)
    # ========================================================================
    
    @staticmethod
    def hyperlink(url: str, text: str) -> str:
        """
        Build a hyperlink for Slack (markdown format).
        
        Args:
            url: URL to link to
            text: Display text
            
        Returns:
            Formatted Slack hyperlink string
        """
        return f"<{url}|{text}>"
    
    @staticmethod
    def user_mention(user_id: str) -> str:
        """
        Build a user mention for Slack.
        
        Args:
            user_id: Slack user ID (e.g., "U12345")
            
        Returns:
            Formatted Slack user mention
        """
        return f"<@{user_id}>"
    
    @staticmethod
    def channel_mention(channel_id: str) -> str:
        """
        Build a channel mention for Slack.
        
        Args:
            channel_id: Slack channel ID (e.g., "C12345")
            
        Returns:
            Formatted Slack channel mention
        """
        return f"<#{channel_id}>"
    
    @staticmethod
    def usergroup_mention(usergroup_id: str) -> str:
        """
        Build a usergroup mention for Slack.
        
        Args:
            usergroup_id: Slack usergroup ID (e.g., "S12345")
            
        Returns:
            Formatted Slack usergroup mention
        """
        return f"<!subteam^{usergroup_id}>"
    
    @staticmethod
    def bold(text: str) -> str:
        """Format text as bold."""
        return f"*{text}*"
    
    @staticmethod
    def italic(text: str) -> str:
        """Format text as italic."""
        return f"_{text}_"
    
    @staticmethod
    def code(text: str) -> str:
        """Format text as inline code."""
        return f"`{text}`"
    
    @staticmethod
    def code_block(text: str, language: Optional[str] = None) -> str:
        """
        Format text as code block.
        
        Args:
            text: Code text
            language: Optional language for syntax highlighting
            
        Returns:
            Formatted code block
        """
        if language:
            return f"```{language}\n{text}\n```"
        return f"```\n{text}\n```"
    
    @staticmethod
    def quote(text: str) -> str:
        """Format text as quote."""
        return f"> {text}"
    
    @staticmethod
    def ordered_list(items: List[str]) -> str:
        """
        Build an ordered list.
        
        Args:
            items: List of item texts
            
        Returns:
            Formatted ordered list
        """
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    
    @staticmethod
    def unordered_list(items: List[str]) -> str:
        """
        Build an unordered list.
        
        Args:
            items: List of item texts
            
        Returns:
            Formatted unordered list
        """
        return "\n".join(f"• {item}" for item in items)
    
    # ========================================================================
    # CONVERSION HELPERS (for backward compatibility)
    # ========================================================================
    
    @staticmethod
    def blocks_to_dict(blocks: List[Block]) -> List[dict]:
        """
        Convert typed Block objects to dict format for API calls.
        
        Args:
            blocks: List of typed Block objects
            
        Returns:
            List of block dicts ready for Slack API
        """
        return [block.to_dict() for block in blocks]


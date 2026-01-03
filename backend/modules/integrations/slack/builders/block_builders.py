"""
Slack Block Kit building utilities for complex blocks.

Provides utilities for building more complex Slack blocks like modals,
input fields, select menus, etc.

Uses Slack SDK's typed models to ensure valid structure and prevent
"invalid_blocks" errors at type-check time.
"""

from typing import List, Optional
from slack_sdk.models.blocks import (
    Block,
    InputBlock,
    SectionBlock,
)
from slack_sdk.models.blocks.block_elements import (
    PlainTextInputElement,
    StaticSelectElement,
    CheckboxesElement,
)
from slack_sdk.models.views import View
from slack_sdk.models.blocks.basic_components import (
    PlainTextObject,
    MarkdownTextObject,
    Option,
    ConfirmObject,
)


class SlackBlockBuilder:
    """
    Utilities for building complex Slack blocks (modals, inputs, selects).
    Uses Slack SDK's typed models for compile-time safety.
    All methods are static - no state required.
    """
    
    @staticmethod
    def text_input(
        action_id: str,
        label: str,
        placeholder: Optional[str] = None,
        initial_value: Optional[str] = None,
        multiline: bool = False,
        optional: bool = False,
        block_id: Optional[str] = None
    ) -> InputBlock:
        """
        Build a text input block for modals.
        
        Args:
            action_id: Unique action identifier
            label: Input label
            placeholder: Optional placeholder text
            initial_value: Optional initial value
            multiline: If True, creates a textarea
            optional: If True, input is optional
            block_id: Optional block identifier (defaults to action_id)
            
        Returns:
            Typed Slack input block
        """
        label_obj = PlainTextObject(text=label)
        placeholder_obj = PlainTextObject(text=placeholder) if placeholder else None
        
        element = PlainTextInputElement(
            action_id=action_id,
            placeholder=placeholder_obj,
            initial_value=initial_value,
            multiline=multiline
        )
        
        return InputBlock(
            block_id=block_id or action_id,
            label=label_obj,
            element=element,
            optional=optional
        )
    
    @staticmethod
    def static_select(
        action_id: str,
        label: str,
        options: List[tuple[str, str]],  # (text, value) pairs
        placeholder: Optional[str] = None,
        initial_option: Optional[tuple[str, str]] = None,
        optional: bool = False,
        block_id: Optional[str] = None
    ) -> InputBlock:
        """
        Build a static select menu block.
        
        Args:
            action_id: Unique action identifier
            label: Select label
            options: List of (text, value) tuples
            placeholder: Optional placeholder text
            initial_option: Optional initially selected (text, value) tuple
            optional: If True, selection is optional
            block_id: Optional block identifier (defaults to action_id)
            
        Returns:
            Typed Slack input block with static select
        """
        label_obj = PlainTextObject(text=label)
        placeholder_obj = PlainTextObject(text=placeholder) if placeholder else None
        
        option_objs = [
            Option(text=PlainTextObject(text=text), value=value)
            for text, value in options
        ]
        
        initial_option_obj = None
        if initial_option:
            text, value = initial_option
            initial_option_obj = Option(text=PlainTextObject(text=text), value=value)
        
        element = StaticSelectElement(
            action_id=action_id,
            options=option_objs,
            placeholder=placeholder_obj,
            initial_option=initial_option_obj
        )
        
        return InputBlock(
            block_id=block_id or action_id,
            label=label_obj,
            element=element,
            optional=optional
        )
    
    @staticmethod
    def checkbox_group(
        action_id: str,
        label: str,
        options: List[tuple[str, str]],  # (text, value) pairs
        initial_options: Optional[List[tuple[str, str]]] = None,
        optional: bool = False,
        block_id: Optional[str] = None
    ) -> InputBlock:
        """
        Build a checkbox group block.
        
        Args:
            action_id: Unique action identifier
            label: Group label
            options: List of (text, value) tuples
            initial_options: Optional initially selected (text, value) tuples
            optional: If True, selection is optional
            block_id: Optional block identifier (defaults to action_id)
            
        Returns:
            Typed Slack input block with checkbox group
        """
        label_obj = PlainTextObject(text=label)
        
        option_objs = [
            Option(text=PlainTextObject(text=text), value=value)
            for text, value in options
        ]
        
        initial_option_objs = None
        if initial_options:
            initial_option_objs = [
                Option(text=PlainTextObject(text=text), value=value)
                for text, value in initial_options
            ]
        
        element = CheckboxesElement(
            action_id=action_id,
            options=option_objs,
            initial_options=initial_option_objs
        )
        
        return InputBlock(
            block_id=block_id or action_id,
            label=label_obj,
            element=element,
            optional=optional
        )
    
    @staticmethod
    def modal(
        title: str,
        blocks: List[Block],
        submit_text: str = "Submit",
        close_text: str = "Cancel",
        callback_id: Optional[str] = None,
        private_metadata: Optional[str] = None
    ) -> View:
        """
        Build a modal view.
        
        Args:
            title: Modal title (max 24 chars)
            blocks: List of typed Block objects
            submit_text: Submit button text (max 24 chars)
            close_text: Close button text (max 24 chars)
            callback_id: Optional callback identifier
            private_metadata: Optional metadata to pass through
            
        Returns:
            Typed Slack modal View
        """
        title_obj = PlainTextObject(text=title)
        submit_obj = PlainTextObject(text=submit_text)
        close_obj = PlainTextObject(text=close_text)
        
        return View(
            type="modal",
            title=title_obj,
            blocks=blocks,
            submit=submit_obj,
            close=close_obj,
            callback_id=callback_id,
            private_metadata=private_metadata
        )
    
    @staticmethod
    def loading_modal(
        title: str = "Loading...",
        message: str = "Please wait while we process your request."
    ) -> View:
        """
        Build a simple loading modal.
        
        Args:
            title: Modal title
            message: Loading message
            
        Returns:
            Typed Slack modal View
        """
        from .generic_builders import GenericMessageBuilder
        
        title_obj = PlainTextObject(text=title)
        close_obj = PlainTextObject(text="Close")
        
        # Create loading section block
        loading_block = GenericMessageBuilder.section(f"⏳ {message}")
        
        return View(
            type="modal",
            title=title_obj,
            blocks=[loading_block],
            close=close_obj
        )
    
    @staticmethod
    def confirmation_dialog(
        title: str,
        text: str,
        confirm_text: str = "Confirm",
        deny_text: str = "Cancel",
        style: Optional[str] = None
    ) -> ConfirmObject:
        """
        Build a confirmation dialog.
        
        Args:
            title: Dialog title (max 100 chars)
            text: Dialog text (max 300 chars)
            confirm_text: Confirm button text (max 30 chars)
            deny_text: Deny button text (max 30 chars)
            style: Optional style ("primary" or "danger")
            
        Returns:
            Typed Slack confirmation object
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


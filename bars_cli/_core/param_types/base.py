"""Base classes for Click parameter types with validation."""

from typing import Any, Callable, Optional

import click

from bars_cli._core.decorators import retry_until_valid
from bars_cli._core.prompts import prompt_text_input
from bars_cli._core.validators import ValidationResult


class ValidatedParamType(click.ParamType):
    """Base class for parameter types with converter and retry logic.
    
    Takes a converter function that returns a model instance (or any type)
    on success, or raises ValueError on failure.
    """
    
    def __init__(self, converter_function: Callable[[str], Any], prompt_text: str, allow_empty: bool = False):
        self.converter = converter_function
        self.prompt_text = prompt_text
        self.allow_empty = allow_empty
    
    def convert(self, value: Any, param: Optional[click.Parameter], ctx: Optional[click.Context]) -> Any:
        if not value and self.allow_empty:
            return None
            
        if value:
            try:
                result = self.converter(value)
                if result is not None:
                    return result
            except (ValueError, Exception) as e:
                styled_input = click.style(str(value), fg='blue')
                styled_message = click.style(str(e), fg='red')
                formatted = f"\n{click.style('Invalid Input:', fg='red', bold=True)} {styled_input}\n{styled_message}"
                click.echo(formatted, err=True)
        
        def get_input():
            return prompt_text_input(self.prompt_text)
        
        def validate_wrapper(val):
            try:
                model_instance = self.converter(val)
                return ValidationResult.success(model_instance)
            except (ValueError, Exception) as e:
                return ValidationResult.failure(str(e))
        
        return retry_until_valid(get_input, validate_wrapper)


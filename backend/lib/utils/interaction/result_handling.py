"""Typed enum for cyclopts result_action values."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypeVar

from pydantic import BaseModel

from utils.func_utils import bind

_M = TypeVar("_M", bound=BaseModel)
DisplayMode = Literal["json", "display"] | None


@dataclass
class DisplayOrReturnPayload:
    result: dict[str, Any]
    display_mode: DisplayMode | None = None
    target_model: type[BaseModel] | None = None


def serialize_for_display_mode(payload: DisplayOrReturnPayload) -> Any:
    """Shape a raw API JSON dict for CLI output.

    - ``display_mode`` ``"json"``: return ``payload.result`` unchanged.
    - ``display_mode`` ``"display"``: ``model.model_validate(result).to_display()``.
    - ``display_mode`` ``None``: ``model.model_validate(result).model_dump()``.
    """
    if payload.display_mode == "json":
        return payload.result
    if payload.target_model is None:
        raise ValueError("target_model is required when display_mode is 'display' or None")
    validated = payload.target_model.model_validate(payload.result)
    return validated.model_dump()


class ResultAction(Enum):
    Default = "print_non_int_sys_exit"
    ReturnValue = "return_value"
    TryCallback = ["call_if_callable", "print_non_none_return_zero"]

    # Remaining actions, alphabetical
    CallIfCallable = "call_if_callable"
    PrintNonIntReturnIntAsExitCode = "print_non_int_return_int_as_exit_code"
    PrintNonIntSysExit = "print_non_int_sys_exit"
    PrintNonNoneReturnIntAsExitCode = "print_non_none_return_int_as_exit_code"
    PrintNonNoneReturnZero = "print_non_none_return_zero"
    PrintReturnZero = "print_return_zero"
    PrintStrReturnIntAsExitCode = "print_str_return_int_as_exit_code"
    PrintStrReturnZero = "print_str_return_zero"
    PrintSysExitZero = "print_sys_exit_zero"
    ReturnIntAsExitCodeElseZero = "return_int_as_exit_code_else_zero"
    ReturnNone = "return_none"
    ReturnZero = "return_zero"
    SysExit = "sys_exit"
    SysExitZero = "sys_exit_zero"

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Callable:
        """Return func pre-bound to args/kwargs for use as a result_action callable."""
        return bind(func, *args, **kwargs)


# =============================================================================
# SANDBOX — decorator factory pattern using partial + ResultAction
# =============================================================================
# Usage example:
#
#   from functools import partial
#   from cyclopts import App
#   from _cli_infrastructure.result_handling import ResultAction, make_callback_command
#
#   app = App()
#   callback_command = make_callback_command(app)
#
#   @app.command(result_action=ResultAction.ReturnValue.value)
#   def echo(msg: str) -> str:
#       return msg
#
#   @callback_command
#   def shout(msg: str) -> str:
#       return msg.upper()
#
#   if __name__ == "__main__":
#       result = app(["echo", "hello"], result_action="return_value")
#       print(f"returned: {result!r}")
#       app(["shout", "hello"])   # prints HELLO, exits 0
# =============================================================================

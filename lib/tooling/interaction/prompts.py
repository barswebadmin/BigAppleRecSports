"""User input prompt utilities (questionary + prompt_toolkit + Rich console output).

Decomposes into four registries and three composable pipeline stages:

  1. ACTION_OPTIONS  — sentinel options (All, Done, Custom, Cancel) as data
  2. DISPLAY_STYLES  — how an option renders in Rich given its style category
  3. INPUT_PARSERS   — ordered chain that resolves raw user input → option
  4. QUESTIONARY_STYLE — prompt_toolkit style tokens (single source)

  build_choices  →  render_display  →  resolve_input
  (data)            (Rich output)      (user string → option value)
"""

import re
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

import questionary
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from infrastructure.interaction.displays import KeyLabel

ANSI_ESCAPE_PATTERN = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


@warnings.deprecated(
    "Temporary: these prompt functions will accept structured key/label input "
    "instead of pre-rendered ANSI strings, after which stripping ANSI is unnecessary."
)
def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return ANSI_ESCAPE_PATTERN.sub("", text)

# ── Types ─────────────────────────────────────────────────────────────────

ActionKey = Literal["all", "done", "custom"]

# actions param: plain key uses default label, tuple overrides display text.
#   actions=["all", "done"]
#   actions=["all", ("done", "Finish selecting")]
ActionEntry = ActionKey | tuple[ActionKey, str]

# Column spec for table mode: plain string means key==label,
# tuple separates the dict key from the display header.
#   columns=["name", "id"]                      → key "name", header "name"
#   columns=[("name", "Account Name"), "id"]     → key "name", header "Account Name"
ColumnSpec = str | tuple[str, str]


class TableOptions(TypedDict):
    """Table-mode options: records + column definitions."""
    items: list[dict[str, Any]]
    columns: list[ColumnSpec]


# ── Structures ────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ActionOption:
    """One sentinel option (All, Done, Cancel, Custom) as a data row.

    To add a new action: add one entry to ``ACTION_OPTIONS``. No other code changes.
    """

    default_label: str
    style: str
    aliases: tuple[str, ...]
    returns: str


# ── Singletons ────────────────────────────────────────────────────────────

CONSOLE = Console()


# ── 1. ACTION_OPTIONS registry ────────────────────────────────────────────
# Each sentinel option is a row of data, not a conditional branch.
# ``style`` drives DISPLAY_STYLES lookup. ``aliases`` are shortcut strings
# users can type instead of the full label.
#
# Callers pass ``actions=["all", "custom", "done"]``. Cancel is always appended last.
# Return values checked via: ``result == ACTION_OPTIONS["cancel"].returns``

ACTION_OPTIONS: dict[str, ActionOption] = {
    "all":    ActionOption("All",          "action_highlight", ("a",),                  "__ALL__"),
    "done":   ActionOption("Done",         "action_success",   ("d",),                  "__DONE__"),
    "cancel": ActionOption("Cancel/Exit",  "action_danger",    ("exit", "c", "e", "q"), "__CANCEL__"),
    "custom": ActionOption("Other/Custom", "action_highlight", ("other", "o"),           "__CUSTOM__"),
}


# ── 2. DISPLAY_STYLES registry ───────────────────────────────────────────
# Maps a style category to Rich markup template. Eliminates if/elif chains.

DISPLAY_STYLES: dict[str, str] = {
    "option":           "[blue]{label}[/]",
    "action_highlight": "[yellow bold]{label}[/]",
    "action_success":   "[green bold]{label}[/]",
    "action_danger":    "[red bold]{label}[/]",
}

# Precomputed lookups for sentinel rendering — computed once at import.
RETURN_TO_STYLE: dict[str, str] = {opt.returns: opt.style for opt in ACTION_OPTIONS.values()}
LABEL_TO_STYLE: dict[str, str] = {opt.default_label: opt.style for opt in ACTION_OPTIONS.values()}


# ── 3. INPUT_PARSERS registry ────────────────────────────────────────────
# Ordered chain of parse strategies. Each is a pure function:
#   (raw_input: str, options: list[str]) → str | None
# First non-None wins. To add a new input format: append one function here.


def parse_numeric(text: str, options: list[str]) -> str | None:
    """'3' → options[2]"""
    try:
        n = int(text)
        return options[n - 1] if 1 <= n <= len(options) else None
    except (ValueError, IndexError):
        return None


def parse_parenthesized(text: str, options: list[str]) -> str | None:
    """'(3) some label' → options[2]"""
    m = re.match(r"\((\d+)\)", text)
    if not m:
        return None
    try:
        n = int(m.group(1))
        return options[n - 1] if 1 <= n <= len(options) else None
    except (ValueError, IndexError):
        return None


def parse_name_match(text: str, options: list[str]) -> str | None:
    """Case-insensitive match against option labels (ANSI-stripped)."""
    low = text.lower()
    for opt in options:
        if strip_ansi(opt).strip().lower() == low:
            return opt
    return None


def parse_alias(text: str, options: list[str]) -> str | None:
    """Match ACTION_OPTIONS aliases (e.g. 'c', 'q', 'exit' → Cancel/Exit)."""
    low = text.lower()
    for opt in ACTION_OPTIONS.values():
        if low in opt.aliases and opt.default_label in options:
            return opt.default_label
    return None


INPUT_PARSERS: list = [parse_numeric, parse_parenthesized, parse_name_match, parse_alias]


def resolve_input(raw: str, options: list[str]) -> str | None:
    """Run raw user input through the parser chain. First non-None wins."""
    stripped = raw.strip()
    if not stripped:
        return None
    for parser in INPUT_PARSERS:
        result = parser(stripped, options)
        if result is not None:
            return result
    return None


# ── 4. QUESTIONARY_STYLE ─────────────────────────────────────────────────

QUESTIONARY_STYLE = Style.from_dict({
    "qmark":       "fg:yellow italic nobold",
    "question":    "fg:yellow italic nobold",
    "answer":      "fg:white bg:black",
    "pointer":     "fg:yellow bold",
    "selected":    "fg:white bg:black",
    "instruction": "",
    "text":        "",
})

INVALID_SELECTION_MESSAGE = "Invalid input. Please try again."


# ── Build stage ──────────────────────────────────────────────────────────


def build_display_options(
    options: list[str] | TableOptions,
    actions: Sequence[ActionEntry] = (),
) -> tuple[list[str], dict[str, str]]:
    """Build the flat display list and a label→sentinel mapping.

    Returns:
        (display_options, label_to_sentinel) where display_options is the
        full list including action labels, and label_to_sentinel maps
        each action's display label to its sentinel return value.
    """
    base_options = (
        [str(item.get(KeyLabel.of(options["columns"][0]).key, "")) for item in options["items"]]
        if isinstance(options, dict)
        else list(options)
    )

    display = list(base_options)
    label_to_sentinel: dict[str, str] = {}

    for entry in actions:
        kl = KeyLabel.of(entry)
        opt = ACTION_OPTIONS[kl.key]
        label = kl.label if isinstance(entry, tuple) else opt.default_label
        display.append(label)
        label_to_sentinel[label] = opt.returns

    cancel = ACTION_OPTIONS["cancel"]
    display.append(cancel.default_label)
    label_to_sentinel[cancel.default_label] = cancel.returns

    return display, label_to_sentinel


# ── Render stage ─────────────────────────────────────────────────────────


def render_list(
    display_options: list[str],
    label_to_sentinel: dict[str, str],
    *,
    option_groups: list[tuple[str, list[str]]] | None = None,
) -> None:
    """Print a numbered list with styled sentinels."""
    styles = LABEL_TO_STYLE | {label: RETURN_TO_STYLE[ret] for label, ret in label_to_sentinel.items()}

    if option_groups is None:
        for i, choice in enumerate(display_options, 1):
            CONSOLE.print(f"  ({i}) {DISPLAY_STYLES[styles.get(choice, 'option')].format(label=escape(choice))}")
        CONSOLE.print()
        return

    lines: list[str] = []
    num = 1
    for name, opts in option_groups:
        lines.append(f"  [bold]{escape(name)}[/]")
        lines.extend(f"    ({num + i}) {DISPLAY_STYLES['option'].format(label=escape(c))}" for i, c in enumerate(opts))
        num += len(opts)
    sentinel_start = sum(len(opts) for _, opts in option_groups)
    lines.extend(
        f"  ({num + i}) {DISPLAY_STYLES[styles.get(c, 'option')].format(label=escape(c))}"
        for i, c in enumerate(display_options[sentinel_start:])
    )
    for line in lines:
        CONSOLE.print(line)
    CONSOLE.print()


def render_table(
    options: TableOptions,
    display_options: list[str],
    label_to_sentinel: dict[str, str],
) -> None:
    """Print a Rich Table with numbered rows and sentinel action rows."""
    items = options["items"]
    cols = [KeyLabel.of(c) for c in options["columns"]]

    table = Table(show_header=True, header_style="bold", show_lines=False)
    table.add_column("#", style="cyan", no_wrap=True, width=4, justify="right")
    for c in cols:
        table.add_column(c.label, no_wrap=True)

    for i, item in enumerate(items, 1):
        table.add_row(str(i), *(str(item.get(c.key, "")) for c in cols))

    sentinels = display_options[len(items):]
    if sentinels:
        table.add_section()
    styles = LABEL_TO_STYLE | {label: RETURN_TO_STYLE[ret] for label, ret in label_to_sentinel.items()}
    empty_cols = [""] * (len(cols) - 1)
    for i, label in enumerate(sentinels, len(items) + 1):
        markup = DISPLAY_STYLES[styles.get(label, "option")].format(label=escape(label))
        table.add_row(str(i), Text.from_markup(markup), *empty_cols)

    CONSOLE.print()
    CONSOLE.print(table)
    CONSOLE.print()


# ── Resolve stage ────────────────────────────────────────────────────────


def resolve_selection(
    raw_input: str,
    display_options: list[str],
    label_to_sentinel: dict[str, str],
) -> str:
    """Map raw user input → resolved option string or sentinel value."""
    matched = resolve_input(raw_input, display_options)
    return ACTION_OPTIONS["cancel"].returns if matched is None else label_to_sentinel.get(matched, matched)


# ── Question builder ─────────────────────────────────────────────────────


def build_question(
    display_options: list[str],
    default_value: str | None = None,
) -> questionary.Question:
    """Build a questionary autocomplete Question (not yet asked)."""
    numbered = [f"({i}) {strip_ansi(o)}" for i, o in enumerate(display_options, 1)]

    default_choice = ""
    if default_value:
        default_lower = default_value.strip().lower()
        for i, opt in enumerate(display_options, 1):
            if strip_ansi(opt).strip().lower() == default_lower:
                default_choice = f"({i}) {strip_ansi(opt)}"
                break

    validator = Validator.from_callable(
        lambda text: not text.strip() or resolve_input(text, display_options) is not None,
        error_message=INVALID_SELECTION_MESSAGE,
    )

    CONSOLE.print(
        "[italic bright_yellow]Type an option number, or start typing the option itself "
        "(press TAB to autocomplete), then ENTER to select that option:[/]"
    )
    return questionary.autocomplete(
        "- ",
        numbered,
        default=default_choice,
        qmark="",
        ignore_case=True,
        match_middle=True,
        style=QUESTIONARY_STYLE,
        validate=validator,
    )


# ── Shared prompt logic ─────────────────────────────────────────────────


def prepare_prompt(
    prompt_text: str,
    options: list[str] | TableOptions,
    *,
    actions: Sequence[ActionEntry] = (),
    default_value: str | None = None,
    show_current: str | None = None,
    option_groups: list[tuple[str, list[str]]] | None = None,
    hide_options: bool = False,
) -> tuple[list[str], dict[str, str], questionary.Question]:
    """Build display options, render them, and return the question."""
    display_options, label_to_sentinel = build_display_options(options, actions)

    CONSOLE.print()
    CONSOLE.print(f"[bold underline]{escape(prompt_text)}[/]")
    if show_current:
        CONSOLE.print(f"  [italic cyan]Current: {escape(str(show_current))}[/]")
        CONSOLE.print()

    if not hide_options:
        if isinstance(options, dict):
            render_table(options, display_options, label_to_sentinel)
        else:
            render_list(display_options, label_to_sentinel, option_groups=option_groups)

    question = build_question(display_options, default_value)
    return display_options, label_to_sentinel, question


def finalize_result(
    raw: str | None,
    display_options: list[str],
    label_to_sentinel: dict[str, str],
    default_value: str | None,
) -> str:
    """Resolve raw questionary output to a final selection or sentinel."""
    if not raw or not raw.strip():
        return default_value or ACTION_OPTIONS["cancel"].returns
    return resolve_selection(raw, display_options, label_to_sentinel)


# ── Public API ───────────────────────────────────────────────────────────


def get_input(
    prompt_text: str,
    *,
    default_value: str | None = None,
    sensitive: bool = False,
) -> str | None:
    """Prompt user for free-text input. Returns ``None`` on cancel (Ctrl+C).

    ``sensitive=True`` masks typed characters with asterisks (questionary's
    password prompt) — for credentials and tokens.
    """
    asker = questionary.password if sensitive else questionary.text
    result = asker(prompt_text, default=default_value or "").ask()
    return None if result is None else result


def resolve_or_prompt(value: str | int | None, label: str, *, numeric: bool = False) -> str:
    """Return str(value) if truthy, otherwise prompt the user.

    Args:
        value: Existing value from CLI args — skips prompt when truthy.
        label: Prompt text shown to the user.
        numeric: When True, validates that input is digits only.
    """
    if value:
        return str(value)
    if numeric:
        from prompt_toolkit import prompt as _prompt
        from prompt_toolkit.validation import Validator
        raw = _prompt(label, validator=Validator.from_callable(lambda t: t.strip().isdigit()), in_thread=True)
        return str(raw).strip()
    return get_input(label) or ""


def prompt_confirmation(prompt_text: str | None = None) -> bool:
    """Blocking yes/no prompt. Default is yes; cancel returns ``False``."""
    label = prompt_text or "Continue? [Y/n]"
    result = questionary.confirm(label, default=True).ask()
    return bool(result) if result is not None else False


CANCEL_SENTINEL = ACTION_OPTIONS["cancel"].returns


def select_from_options(
    prompt_text: str,
    options: list[str] | TableOptions,
    *,
    actions: Sequence[ActionEntry] = (),
    default_value: str | None = None,
    show_current: str | None = None,
    option_groups: list[tuple[str, list[str]]] | None = None,
    hide_options: bool = False,
) -> str:
    """Prompt user to select from options with autocomplete.

    Args:
        prompt_text: Header label (rendered bold + underlined).
        options: ``list[str]`` for flat list, or ``TableOptions`` dict
            with ``items`` (records) and ``columns`` (key or (key, header) specs)
            for tabular display.
        actions: Sentinel actions to append (e.g. ``["all", "done"]`` or
            ``[("done", "Finish")]``). Cancel is always appended last.
        default_value: Pre-filled in the input field.
        show_current: Display "Current: X" below the header.
        option_groups: Grouped sections ``[(name, [options]), ...]``.
            Only valid when ``options`` is ``list[str]``.
        hide_options: Skip rendering the options list (input only).

    .. TODO: no equivalent of the old ``preselect_default_in_input=False`` toggle.
       The new module always seeds the questionary input buffer with ``(N) label`` when
       ``default_value`` is set. The old toggle existed to avoid an autocomplete bug where
       typing a digit after a preselected ``(1) none`` would append into the buffer and produce
       ``(1) none2``. Any caller that wants "accept default on empty submit, but don't seed the
       buffer" will hit this — add the toggle back when the first such caller surfaces.

    Returns:
        The selected option string, or a sentinel value from ACTION_OPTIONS
        (e.g. ``"__ALL__"``, ``"__DONE__"``, ``"__CANCEL__"``).
    """
    display_options, label_to_sentinel, question = prepare_prompt(
        prompt_text, options,
        actions=actions, default_value=default_value, show_current=show_current,
        option_groups=option_groups, hide_options=hide_options,
    )
    raw = question.unsafe_ask()
    return finalize_result(raw, display_options, label_to_sentinel, default_value)


if __name__ == "__main__":
    # ── B. List mode via new API ──
    print("=" * 60)
    print("  B. select_from_options — list mode + actions")
    print("=" * 60)

    result_b = select_from_options(
        "Pick a schema (list mode):",
        [
            "DemandSubAccount",
            "DemandSubAccountCreateData",
            "DemandSubAccountDeactivation",
            "SupplySubAccount",
            "SupplySubAccountCreateData",
            "LegacySubAccount",
            "RateTable",
            "RateTableRecord",
        ],
        actions=["all", "done"],
    )
    print(f"\n  → result: {result_b!r}")
    print(f"    is cancel? {result_b == ACTION_OPTIONS['cancel'].returns}")
    print(f"    is done?   {result_b == ACTION_OPTIONS['done'].returns}")
    print(f"    is all?    {result_b == ACTION_OPTIONS['all'].returns}")

    # ── E. Table mode via new API ──
    print("\n" + "=" * 60)
    print("  E. select_from_options — table mode + actions")
    print("=" * 60)

    result_e = select_from_options(
        "Pick a subaccount (table mode):",
        {
            "items": [
                {"id": "1001", "name": "DemandSubAccount",                        "uuid": "a1b2c3d4-e5f6-7890-abcd"},
                {"id": "1002", "name": "DemandSubAccountData",                    "uuid": "f6e5d4c3-b2a1-0987-dcba"},
                {"id": "1003", "name": "SupplySubAccount",                        "uuid": "11223344-5566-7788-99aa"},
                {"id": "1004", "name": "LegacySubAccount",                        "uuid": "aabbccdd-eeff-0011-2233"},
                {"id": "1005", "name": "RateTable",                               "uuid": "deadbeef-cafe-babe-f00d"},
                {"id": "1006", "name": "RateTableRecord",                         "uuid": "faceb00d-dead-beef-cafe"},
                {"id": "1007", "name": "DemandDataImportConfiguration",           "uuid": "abcd1234-5678-9012-ef34"},
                {"id": "1008", "name": "DemandDataImportConfigurationCreateData", "uuid": "5678abcd-ef01-2345-6789"},
                {"id": "1009", "name": "DemandDataImport",                        "uuid": "9012ef34-abcd-5678-0123"},
                {"id": "1010", "name": "DemandDataImportCreateData",              "uuid": "ef345678-9012-abcd-4567"},
                {"id": "1011", "name": "SupplyDataImportConfiguration",           "uuid": "01234567-89ab-cdef-0123"},
                {"id": "1012", "name": "SupplyDataImportConfigurationCreateData", "uuid": "456789ab-cdef-0123-4567"},
                {"id": "1013", "name": "SupplyDataImport",                        "uuid": "89abcdef-0123-4567-89ab"},
                {"id": "1014", "name": "SupplyDataImportCreateData",              "uuid": "cdef0123-4567-89ab-cdef"},
                {"id": "1015", "name": "LegacyDataImportConfiguration",           "uuid": "01234567-cdef-89ab-0123"},
                {"id": "1016", "name": "LegacyDataImportConfigurationCreateData", "uuid": "456789ab-0123-cdef-4567"},
                {"id": "1017", "name": "LegacyDataImport",                        "uuid": "89abcdef-4567-0123-89ab"},
                {"id": "1018", "name": "LegacyDataImportCreateData",              "uuid": "cdef0123-89ab-4567-cdef"},
            ],
            "columns": [
                ("name", "Account Name"),
                "id",
                ("uuid", "UUID"),
            ],
        },
        actions=["all", "done"],
    )
    print(f"\n  → result: {result_e!r}")
    print(f"    is cancel? {result_e == ACTION_OPTIONS['cancel'].returns}")
    print(f"    is done?   {result_e == ACTION_OPTIONS['done'].returns}")

    # ── F. Grouped list mode via new API ──
    print("\n" + "=" * 60)
    print("  F. select_from_options — grouped list + custom done text")
    print("=" * 60)

    result_f = select_from_options(
        "Pick an account type (grouped):",
        [
            "DemandSubAccount", "DemandSubAccountCreateData", "DemandSubAccountDeactivation",
            "SupplySubAccount", "SupplySubAccountCreateData",
            "LegacySubAccount", "RateTable", "RateTableRecord",
        ],
        actions=[("done", "Finish selecting")],
        option_groups=[
            ("Demand", ["DemandSubAccount", "DemandSubAccountCreateData", "DemandSubAccountDeactivation"]),
            ("Supply", ["SupplySubAccount", "SupplySubAccountCreateData"]),
            ("Other",  ["LegacySubAccount", "RateTable", "RateTableRecord"]),
        ],
    )
    print(f"\n  → result: {result_f!r}")
    print(f"    is cancel? {result_f == ACTION_OPTIONS['cancel'].returns}")
    print(f"    is done?   {result_f == ACTION_OPTIONS['done'].returns}")

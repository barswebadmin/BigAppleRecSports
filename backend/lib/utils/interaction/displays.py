# ── Rich paradigms reference ───────────────────────────────────────────────
#
# Console        — terminal I/O: width/height detection, print, rule, export
# Table          — tabular data with column sizing, styles, sections, overflow
#   add_column   — width / min_width / max_width / ratio (proportional flex),
#                  justify, vertical, overflow ("ellipsis" | "fold" | "crop"),
#                  no_wrap, header_style / style / footer_style
#   add_row      — *renderables (str | Text | any Renderable), style, end_section
#   expand       — fill available Console.width; ratio columns need this
#   row_styles   — list of styles to alternate per row (zebra striping for free)
#   box          — box.SIMPLE / box.ROUNDED / box.HEAVY_HEAD / None for border style
# Text           — styled strings; .from_markup("[bold red]x[/]"),
#                  Style(link="url") for clickable hyperlinks in supported terminals
#                  Text.assemble(*parts) to combine styled spans in one cell
# Style          — color, bgcolor, bold/dim/italic/underline/strike, link, composable via +
# Panel          — bordered box around any renderable
# Tree           — hierarchical display (e.g. dependency graphs, file trees)
# Columns        — side-by-side renderable layout
# Progress       — auto-updating progress bars with task tracking
# Live           — live-updating display of any renderable
# Status         — spinner + message while waiting
# Spinner        — animation for indeterminate progress
# Prompt         — blocking interactive input (Prompt.ask / Confirm.ask)
# Layout         — split fixed height into rows/columns
# Syntax         — syntax-highlighted code blocks
# Markdown       — render markdown in terminal
# Traceback      — pretty Python tracebacks
# Align          — center / right-align any renderable
# JSON / Pretty  — formatted JSON or Python object rendering
# Rule           — horizontal divider with optional centered title (Console.rule)
# ───────────────────────────────────────────────────────────────────────────

"""Display and rendering utilities (Rich tables, data formatting, text helpers)."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Self

from rich.console import Console, ConsoleRenderable, JustifyMethod, RenderableType, RichCast
from rich.json import JSON
from rich.pretty import Pretty
from rich.style import Style, StyleType
from rich.table import Table
from rich.text import Text

# TODO: evaluate whether this singleton is needed or should be deleted.
# Active consoles (console, error_console) live in terminal.py and are imported from there.
console = Console()


# ── Type aliases ──────────────────────────────────────────────────────────

DataRenderMode = Literal["json", "dict"]


# ── KeyLabel ───────────────────────────────────────────────────────────────


@dataclass(slots=True)
class KeyLabel:
    """Normalized key–label pair from ``str | tuple[str, str]``.

    Plain string: key and label are identical.
    Tuple: first element is the lookup key, second is the display label.
    """

    key: str
    label: str

    @classmethod
    def of(cls, spec: str | tuple[str, str]) -> Self:
        """Normalize ``str | tuple[str, str]`` into key + label."""
        return cls(key=spec[0], label=spec[1]) if isinstance(spec, tuple) else cls(key=spec, label=spec)


# ── ColumnInfo ──────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ColumnInfo:
    """Rich column definition. ``format_table`` handles the handoff to
    ``Table.add_column`` — callers only specify what they care about.

    Rich internals not yet surfaced (add as fields if needed):

    - ``footer_style: StyleType`` — style for a footer row.
    - ``vertical: "top" | "middle" | "bottom"`` — vertical alignment within
      a cell when adjacent cells are taller.
    - ``highlight: bool | None`` — enable Rich syntax highlighting within cells.
    - ``min_width: int | None`` — floor; never narrower than N chars, but can grow.
    - ``max_width: int | None`` — ceiling; never wider than N chars, but can shrink.
    """

    label: str
    header_style: StyleType | None = None
    style: StyleType | None = None
    justify: JustifyMethod = "left"
    width: int | None = None
    ratio: int | None = None
    truncate: Literal["ellipsis", "crop"] | None = None


# ── Behavior ───────────────────────────────────────────────────────────────


def format_table(
    columns: list[ColumnInfo],
    *,
    rows: Sequence[tuple[RenderableType, ...]] | None = None,
    sections: Sequence[Sequence[tuple[RenderableType, ...]]] | None = None,
    title: str | None = None,
) -> Table:
    """Build a :class:`~rich.table.Table` from column definitions and row data.

    Provide exactly one of ``rows`` (flat) or ``sections`` (grouped, with horizontal
    rules between groups).

    Rich internals not yet surfaced (add as parameters if needed):

    - ``box: box.SIMPLE | box.ROUNDED | ... | None`` — border style around
      the table. Currently uses Rich's default (``box.HEAVY_HEAD``).
    - ``row_styles: list[str]`` — alternating row styles for zebra striping.
    - ``expand: bool`` — whether the table fills available terminal width.
      Currently hardcoded to ``True``.
    - ``show_header / show_footer / show_edge / show_lines: bool`` —
      toggle visibility of table chrome.
    - ``pad_edge: bool`` — padding between table edge and terminal edge.
    - ``caption: str`` — text rendered below the table.
    - ``add_row(..., style=, end_section=)`` — per-row style override and
      manual section breaks (currently driven by ``sections`` parameter).
    """
    n = len(columns)
    if (rows is None) == (sections is None):
        raise ValueError("Specify exactly one of `rows` or `sections`.")

    table = Table(title=title, expand=True)
    for c in columns:
        table.add_column(
            c.label,
            header_style=c.header_style,
            style=c.style,
            justify=c.justify,
            overflow=c.truncate or "fold",
            no_wrap=c.truncate is not None,
            width=c.width,
            ratio=c.ratio,
        )

    def add_validated_row(row: tuple[RenderableType, ...]) -> None:
        if len(row) != n:
            raise ValueError(
                f"Row length {len(row)} must match column count {n}: {row!r}",
            )
        table.add_row(*row)

    if rows is not None:
        for row in rows:
            add_validated_row(row)
    else:
        assert sections is not None
        n_sec = len(sections)
        for i, section in enumerate(sections):
            for row in section:
                add_validated_row(row)
            if i < n_sec - 1 and table.rows:
                table.add_section()
    return table


DATA_RENDERERS: dict[DataRenderMode, Callable[[Any], RenderableType]] = {
    "json": lambda o: JSON.from_data(o, indent=2),
    "dict": lambda o: Pretty(o, indent_size=2),
}


def format_data(data: Any, *, mode: DataRenderMode = "json") -> RenderableType | None:
    """Render data as a rich renderable per output mode.

    Values that are already Rich renderables (``Text``, ``Table``, ``Panel``, …)
    pass through untouched so commands can return styled output directly.
    """
    if data is None:
        return None
    if isinstance(data, (ConsoleRenderable, RichCast)):
        return data
    return DATA_RENDERERS[mode](data)


def labeled_lines(items: dict[str, Any]) -> Text:
    """Rich renderable with one ``label: value`` line per item."""
    return Text("\n".join(f"{label}: {value}" for label, value in items.items()))


def hyperlink(text: str, href: str | None = None, *, style: StyleType | None = None) -> Text:
    """Rich ``Text`` span with an embedded terminal hyperlink (OSC 8).

    ``href`` defaults to ``text`` — for displaying a clickable URL as itself.
    ``style`` composes with the link (e.g. table cells needing color AND a link).
    """
    target = href if href is not None else text
    base = Style.parse(style) if isinstance(style, str) else (style or Style())
    return Text(text, style=base + Style(link=target))

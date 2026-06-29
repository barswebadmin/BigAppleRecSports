"""Nested, stateful interactive shell for cyclopts ``App`` trees.

cyclopts' built-in :meth:`App.interactive_shell` re-parses every line against the
*root* app, so control returns to the top after each command. This shell keeps a
navigation **stack** instead: typing a sub-app's name descends into it and *stays*
there; ``back`` pops one level. Commands execute relative to the current node by
delegating to ``node(...)`` — cyclopts awaits async, prints non-int returns, and
(via the result-action below) returns the exit code instead of ``sys.exit``-ing.

Every handler has the same ``(stack, tokens, console) -> should_exit`` shape, so the
loop is a single registry lookup: typed verbs come from ``verbs``, descendable
namespaces map to ``enter``, and everything else falls through to ``execute``.
"""

import shlex
import sys

from autoregistry import Registry
from cyclopts import App
from cyclopts.exceptions import CycloptsError
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.console import Console


# ── Constants ─────────────────────────────────────────────────────────────

# cyclopts auto-registers a `help` command on every App; it is not a navigable sub-app.
AUTO_COMMANDS = {"help"}

# ANSI cursor save/restore + clear-to-end. Used so each `print_help` call
# erases the previous help block in place rather than stacking. The "anchor"
# is saved at the cursor position immediately before the help text is written;
# the next call restores to that anchor and clears everything from there to
# the end of the visible screen, replays the captured interaction history
# (prompt lines + command output), then writes the new help below.
_ANSI_SAVE_CURSOR = "\033[s"
_ANSI_RESTORE_CURSOR_AND_CLEAR = "\033[u\033[J"

# Module-level interaction tape — one shell session at a time. Each entry is
# raw text (including ANSI styling) to be replayed in order above the next
# help block. Populated by:
#   - the prompt loop (every accepted input line)
#   - ``execute`` (captured Rich output from each command)
# Only Rich output routed through the passed ``console`` is captured; direct
# ``print(...)`` calls in command bodies stream live but won't survive a redraw.
_help_anchor_set = False
_captured_outputs: list[str] = []


# ── Verb registry ────────────────────────────────────────────────────────

# Typed navigation verbs, keyed by function name. The registry *is* the verb table.
verbs = Registry()


def print_help(stack: list[App], console: Console) -> None:
    """Render the current node's help; replace the previous help block in place.

    Sequence on each call:
      1. Restore cursor to the saved anchor (above the previous help) and clear
         from there to the end of the visible screen.
      2. Replay :data:`_captured_outputs` — the running interaction history
         (prompt lines + Rich command output) — at that anchor position.
      3. Write the new help block below the replayed history.

    First call sets the anchor without restoring (no prior position to go back to).
    """
    global _help_anchor_set
    if _help_anchor_set:
        sys.stdout.write(_ANSI_RESTORE_CURSOR_AND_CLEAR)
    sys.stdout.write(_ANSI_SAVE_CURSOR)
    if _captured_outputs:
        sys.stdout.write("".join(_captured_outputs))
    sys.stdout.flush()
    stack[-1].help_print(console=console)
    _help_anchor_set = True


@verbs
def back(stack: list[App], tokens: list[str], console: Console, inject: dict[str, object]) -> None:
    """Pop one level; show the new current node's help. No-op at the root."""
    if len(stack) > 1:
        stack.pop()
    print_help(stack, console)


@verbs
def help(stack: list[App], tokens: list[str], console: Console, inject: dict[str, object]) -> None:
    print_help(stack, console)


verbs["q"] = lambda *_: True  # quit the shell

VERB_WORDS = sorted(verbs)


# ── Navigation helpers ───────────────────────────────────────────────────


def children(node: App) -> list[str]:
    """Navigable command names on ``node`` (drops cyclopts' auto help/version flags)."""
    return sorted(c for c in node if not c.startswith("-") and c not in AUTO_COMMANDS)


def namespaces(node: App) -> list[str]:
    """Children of ``node`` that are themselves namespaces — i.e. things to descend into."""
    return [c for c in children(node) if children(node[c])]


def enter(stack: list[App], tokens: list[str], console: Console, inject: dict[str, object]) -> None:
    """Push the named sub-app onto the navigation stack; show its help."""
    stack.append(stack[-1][tokens[0]])
    print_help(stack, console)


def execute(stack: list[App], tokens: list[str], console: Console, inject: dict[str, object]) -> None:
    """Run tokens as a command against the current stack node.

    Injected dependencies (e.g. the Engine ``HttpClient``) are filled into any
    ``parse=False`` parameter the resolved command declares — same contract as
    the root meta launcher.

    Captures Rich output via ``console.capture()`` so command results survive
    the next help redraw — the captured text is appended to
    :data:`_captured_outputs` and replayed by :func:`print_help`. Output is
    written to stdout immediately so the user sees it live.

    Cyclopts parse/validation errors (unknown command, bad args, etc.) are
    swallowed here — cyclopts has already rendered its Error panel into the
    captured stream, so we just need to keep the shell loop alive. Genuine
    exceptions from command handler bodies still propagate.
    """
    with console.capture() as captured:
        try:
            command, bound, ignored = stack[-1].parse_args(tokens, exit_on_error=False, console=console)
            kwargs = dict(bound.kwargs)
            kwargs |= {name: value for name, value in inject.items() if name in ignored}
            result = command(*bound.args, **kwargs)
            if result is not None and not isinstance(result, int):
                console.print(result)
        except CycloptsError:
            pass
    output = captured.get()
    if output:
        sys.stdout.write(output)
        sys.stdout.flush()
        _captured_outputs.append(output)


# ── Shell loop ───────────────────────────────────────────────────────────


def interactive_shell(app: App, *, console: Console | None = None, inject: dict[str, object] | None = None) -> None:
    """Run a nested shell rooted at ``app`` until the user quits.

    A bare sub-app name descends; ``back`` ascends one level; ``help`` lists the
    current level; ``q`` quits. Anything else is executed against the current node.
    ``inject`` maps parameter names to runtime dependencies filled into any
    ``parse=False`` command parameter (see :func:`execute`).
    """
    console = console or Console()
    inject = inject or {}
    session: PromptSession[str] = PromptSession()
    stack = [app]

    # Initial help panel — padded so it sits near the top of the viewport with
    # the prompt at the bottom. The anchor is saved BEFORE the padding so a
    # subsequent navigation clears both the padding and the old help (the new
    # help then renders directly under the user's last command line).
    # Known limitation: VSCode's integrated terminal may misreport visible
    # height, causing the layout to shift. See shutil.get_terminal_size() or
    # prompt_toolkit's print_formatted_text as potential improvements.
    global _help_anchor_set
    with console.capture() as captured:
        app.help_print(console=console)
    help_lines = captured.get().splitlines()
    pad = console.size.height - len(help_lines) - 2
    sys.stdout.write(_ANSI_SAVE_CURSOR)
    sys.stdout.flush()
    print("\n" * max(pad, 0) + "\n".join(help_lines))
    console.print("Nested shell — 'back' up · 'help' list · 'q' quit.")
    _help_anchor_set = True

    while True:
        node = stack[-1]
        completer = WordCompleter(children(node) + VERB_WORDS, ignore_case=True)
        prompt_text = "/".join(n.name[0] for n in stack) + "> "
        try:
            line = session.prompt(prompt_text, completer=completer, reserve_space_for_menu=2)
        except (KeyboardInterrupt, EOFError):
            break

        # Save the prompt + accepted input so it's preserved when the next help
        # redraw clears the region. Prompt_toolkit writes the prompt itself
        # directly to the terminal, but that text is lost across the restore;
        # re-emit it as part of the captured tape.
        _captured_outputs.append(f"{prompt_text}{line}\n")

        tokens = shlex.split(line)
        dispatch = {**dict.fromkeys(namespaces(node), enter), **verbs}
        if dispatch.get(tokens[0], execute)(stack, tokens, console, inject):
            break

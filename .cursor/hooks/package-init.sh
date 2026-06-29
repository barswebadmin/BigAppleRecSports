#!/usr/bin/env bash
# Package __init__.py gate — .claude/rules/package-init.md
#
# Fires on Edit / Write / StrReplace when the target path is __init__.py.
# Always injects the no-re-export rule. Denies edits that add imports or __all__.
#
# Exit codes:
#   0 + {}              → not an __init__.py edit
#   0 + agent_message   → __init__.py edit allowed (docstring-only / no imports in diff)
#   2 + permission deny → proposed content adds import / __all__ (re-export)

set -euo pipefail

input=$(cat)

tool=$(echo "$input" | jq -r '.tool_name // .tool // empty')
case "$tool" in
  Edit|Write|StrReplace) ;;
  *) echo '{}'; exit 0 ;;
esac

params=$(echo "$input" | jq -c '.tool_input // .input // {}')
path=$(echo "$params" | jq -r '.file_path // .path // .target_notebook // empty')
content=$(echo "$params" | jq -r '.new_string // .contents // .content // empty')

case "$path" in
  */__init__.py|__init__.py) ;;
  *) echo '{}'; exit 0 ;;
esac

reminder='PACKAGE __init__.py EDIT — read .claude/rules/package-init.md. Re-exports forbidden: do not add imports to re-export, alias, or populate __all__. Import from the defining module. Exception only after you ask the user and they explicitly approve in this thread.'

reexport_pattern='(^|[[:space:]])(from[[:space:]]|[[:space:]]import[[:space:]])|__all__[[:space:]]*='

if [ -n "$content" ] && echo "$content" | grep -qE "$reexport_pattern"; then
  jq -n \
    --arg msg "[package-init-reexport] $reminder" \
    '{permission: "deny", agent_message: $msg, user_message: "package-init gate blocked this __init__.py edit (imports/__all__). Ask the user for approval or import from the defining module instead."}'
  exit 2
fi

jq -n --arg msg "[package-init] $reminder" '{agent_message: $msg}'

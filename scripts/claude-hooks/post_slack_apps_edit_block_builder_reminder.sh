#!/usr/bin/env bash
# PostToolUse: after Write/Edit under slack-apps/, remind Claude to prefer slack-block-builder.
# Canonical copy; .claude/hooks/ entry is a symlink to this file.
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
    exit 0
fi

input=$(cat) || exit 0
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
if [[ -z "$file_path" || "$file_path" == "null" ]]; then
    exit 0
fi

normalized=${file_path//\\/\/}
if [[ "$normalized" != *"/slack-apps/"* && "$normalized" != *"/slack-apps" ]]; then
    exit 0
fi

msg=$'slack-apps edit policy: Prefer slack-block-builder for Block Kit (modals, messages, home views).\n'
msg+=$'- Import via the Deno import map key `slack-block-builder` (npm:slack-block-builder).\n'
msg+=$'- Use Surfaces, Blocks, Elements, Bits, Utilities from the library where they fit; see https://blockbuilder.dev\n'
msg+=$'- Hand-rolled block JSON is a last resort when the library cannot express the shape.\n'
msg+=$'- Keep Slack API payloads typed and consistent at boundaries (e.g. .build() where applicable).'

jq -nc --arg msg "$msg" '{
  hookSpecificOutput: {
    hookEventName: "PostToolUse",
    additionalContext: $msg
  }
}'

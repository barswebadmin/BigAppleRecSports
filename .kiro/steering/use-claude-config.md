---
inclusion: always
---
# Canonical rules location

All project rules, hooks, and skills are maintained in `.claude/`. This steering file ensures Kiro reads them.

## Project context and structure

#[[file:.claude/CLAUDE.md]]

## Antipatterns (learned failure modes)

#[[file:.claude/antipatterns.md]]

## Rules (always-apply policies)

#[[file:.claude/rules/package-init.md]]
#[[file:.claude/rules/domain-logic-placement.mdc]]
#[[file:.claude/rules/surgical-revert.mdc]]

## Skills (workflow guides)

#[[file:.claude/skills/python-uv-run/SKILL.md]]
#[[file:.claude/skills/slack-app-deploy/SKILL.md]]
#[[file:.claude/skills/shopify-eventbridge-golive/SKILL.md]]

---

**Note:** Kiro hooks (`.kiro/hooks/`) should wrap the same shell scripts as Claude hooks (`.claude/hooks/`, `.cursor/hooks/`) to enforce rules proactively. However, Kiro passes different environment/input formats to hooks than Claude/Cursor, so adapter scripts or askAgent-based hooks are needed instead of directly running Claude's hook scripts.

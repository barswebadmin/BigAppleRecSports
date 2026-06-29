# Stage 5 design refresh — progress log

This file tracks Substage B1 corrections to `design-stage-5.md`.
Append-only; one line per save. Format mirrors `progress-stage-4-design.md`.

The orchestrator polls the `Final status B1: COMPLETED` line as the green
light for Agent A's Stage 5 implementation.

- [x] B1.1 Drop "full" from restockTo (deliverables checklist + § 5.b deltas + ADDED bullet) — saved at 2026-06-21T15:02:00Z
- [x] B1.2 Inline factory wrappers (one-line note added to § 5.d) — saved at 2026-06-21T15:03:30Z
- [x] B1.3 Invariant — separate calls, no combined wrapper (added in § 5.d above the controller code block; deliverables checklist extended) — saved at 2026-06-21T15:06:00Z
- [x] B1.4 Add § 5.b.1 — Casing conventions section (Python snake_case, TS camelCase, wire JSON camelCase; reconciles with § 5.casing/D32 — § 5.b.1 is now authoritative) — saved at 2026-06-21T15:08:00Z
- [x] B1.5 Stage 1-3 fix-ups (added § 5.k.4 step 5 — normalizeRefundOrCredit move into sheet*loader.ts; added § 5.k.8 search/destroy for `get*<x>\_service()` one-liners; added § 5.k.9 — Stage 5 covers only new files for casing, Stage 6 owns full retroactive cleanup) — saved at 2026-06-21T15:11:30Z
- [x] B1.6 Final read-through (no remaining "full" mentions in restockTo authoritative context — the only `"full"` hits are in § 5.k.1 / 5.k.2 BEFORE examples showing what's being removed, which correctly stay there; § 5.b.1 + § 5.k.9 sections exist; cross-references at § 5.j intact; no markdown diagnostics) — saved at 2026-06-21T15:13:00Z
- Final status B1: COMPLETED

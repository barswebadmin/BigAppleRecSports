# <library-or-api-name>

**Kind:** <npm package | deno module | REST/GraphQL API | Apps Script service>
**Version / API version:** <X.Y.Z or v4 etc.>
**Last touched:** <YYYY-MM-DD>
**Official docs:** <https://...>          ← required when it has them
**Source root:** `<node_modules/<lib>/ | deno cache | vendor path | n/a for hosted API>`

## What it is (one sentence)

<one-line description, no marketing>

## Confirmed facts

Each entry cites its source. Citations are **lookup pointers**: a future agent
or the user must be able to re-locate the exact sentence in seconds without
re-reading the whole page. Bare URLs are not acceptable.

Citation forms:

- (`<path>/<file>.ts:<line>`) — fact verified by reading source
- (verified by working call site `<path>:<symbol>`, <YYYY-MM-DD>) — fact backed by our own code that runs
- (docs: <URL>, search: "<verbatim ≥6-word phrase>", fetched <YYYY-MM-DD>) — fact from official docs
- (source: user-confirmed <YYYY-MM-DD>) — fact asserted by the user this session

## Quirks / gotchas

Same citation rules. Quirks are usually source/empirically verified.

## Common usage in this repo

- `path/to/file.ts:<line>` — how we call it; only entries verified to exist.

## Open questions / unverified

Claims awaiting confirmation, OR claims from non-authoritative input (web blog,
SO, memory, prior agent). A claim moves to `Confirmed facts` only after a valid
citation is added.

- [ ] (claim, original source: web/memory/agent) — needs verification by reading <file/docs>

## Cross-references

- Other libraries/APIs this interacts with in our codebase.
- Project docs that depend on facts here.

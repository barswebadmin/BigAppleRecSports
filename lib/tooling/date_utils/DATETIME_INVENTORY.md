# Date / Time Logic — Monorepo Inventory

Every Python function that **parses, formats, or serializes** dates and times.
Organized by file. Behavior-driven, not name-driven.

**10 files · 31 functions/classes · 15 duplicates · 16 deprecated**

> ⚠ Probable bug: `format_time_only` (schedule_product_updates.py L174) silently
> passes `"6:30 PM"` to Lambda unchanged. `format_time_for_lambda` (L423, same file)
> correctly converts to `"18:30"`. L710 wires the broken version into the payload.

---

## Table of Contents

1. [lib/tooling/date_utils/parse_date.py](#1-libtoolingdate_utilsparse_datepy)
2. [lib/tooling/date_utils/parse_time.py](#2-libtoolingdate_utilsparse_timepy)
3. [lib/tooling/date_utils/parse_iso_datetime.py](#3-libtoolingdate_utilsparse_iso_datetimepy)
4. [lib/tooling/date_utils/parse_off_dates.py](#4-libtoolingdate_utilsparse_off_datespy)
5. [lib/tooling/date_utils/parse_timestamp_string.py](#5-libtoolingdate_utilsparse_timestamp_stringpy)  ← stub
6. [lib/tooling/datetime/date_utils.py](#6-libtoolingdatetimedate_utilspy)  ← **ENTIRE FILE DEPRECATED**
7. [backend/shared/date_utils.py](#7-backendshareddate_utilspy)
8. [scripts/load_refunds_to_dynamo.py](#8-scriptsload_refunds_to_dynamopy)
9. [scripts/load_waitlist_to_dynamo.py](#9-scriptsload_waitlist_to_dynamopy)
10. [scripts/migrate_waitlist_sheet.py](#10-scriptsmigrate_waitlist_sheetpy)
11. [lib/domain/registrations/refunds/analyze_refunds.py](#11-libdomainregistrationsrefundsanalyze_refundspy)
12. [backend/modules/products/.../schedule_product_updates.py](#12-backendmodulesproductsschedule_product_updatespy)

---

## 1. lib/tooling/date_utils/parse_date.py

Module: `lib.tooling.date_utils.parse_date`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `parse_date` | 6–21 | `parse_date(date_str: str, default_century: int = 2000) → datetime` | split on `/`; map to int; if `year < 100`: add `default_century`; return `datetime(y, m, d)` | `datetime` (naive, no tz) | `lib/tooling/date_utils/parse_off_dates.py` · `lib/tooling/datetime/date_utils.py` (deprecated copy) | — |

---

## 2. lib/tooling/date_utils/parse_time.py

Module: `lib.tooling.date_utils.parse_time`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `parse_time` | 7–19 | `parse_time(time_str: str) → datetime.time` | `strptime(strip(time_str), "%I:%M %p").time()` | `datetime.time` | `parse_off_dates.py` · `datetime/date_utils.py` (deprecated copy) · `schedule_product_updates.py` (re-implemented) | `datetime/date_utils.py::parse_time` (deprecated copy) · `format_time_for_lambda` (behavioral overlap) |

---

## 3. lib/tooling/date_utils/parse_iso_datetime.py

Module: `lib.tooling.date_utils.parse_iso_datetime`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `parse_iso_datetime` | 7–21 | `parse_iso_datetime(datetime_str: str) → datetime` | if ends `"Z"`: replace `"+00:00"`; `fromisoformat`; if naive: add UTC | `datetime` (UTC-aware) | `datetime/date_utils.py` (deprecated copy) | `datetime/date_utils.py::parse_iso_datetime` |

---

## 4. lib/tooling/date_utils/parse_off_dates.py

Module: `lib.tooling.date_utils.parse_off_dates`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `parse_off_dates` | 10–28 | `parse_off_dates(dates_str: str \| None, sport_time: dt_time) → list[datetime]` | split on `,`; for each: try `strptime("%Y-%m-%d")` else `parse_date().date()`; `combine(date, sport_time)` | `list[datetime]` (naive, local) | `datetime/date_utils.py::get_discount_dates_and_prices` (via lazy import from `shared_utilities`) | `datetime/date_utils.py::parse_off_dates` (deprecated copy) |

---

## 5. lib/tooling/date_utils/parse_timestamp_string.py

Module: `lib.tooling.date_utils.parse_timestamp_string`  
**Status: STUB — raises `NotImplementedError`**

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `parse_timestamp_string` | 13–32 | `parse_timestamp_string(raw_string: str) → ParsedTimestamp` | raises `NotImplementedError` — designed to support ISO, M/D/YY, time-only, and natural-language inputs | `ParsedTimestamp { input_type: "date"\|"datetime"\|"time", value: datetime }` — never reached | none yet | — (intended canonical replacement for all ad-hoc parsers below) |

---

## 6. lib/tooling/datetime/date_utils.py

Module: `lib.tooling.datetime.date_utils`  
**⚠ ENTIRE FILE DEPRECATED — regex parsing to be replaced by Dynamo records**

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `get_eastern_timezone` | 49–51 | `get_eastern_timezone() → ZoneInfo` | `return ZoneInfo("America/New_York")` | `ZoneInfo` | `convert_to_eastern_time`, `parse_shopify_datetime` (same file) · `backend/shared/date_utils.py` (re-exported) | `ZoneInfo("America/New_York")` directly — one-liner no-arg wrapper anti-pattern |
| `convert_to_eastern_time` | 54–70 | `convert_to_eastern_time(dt: datetime) → datetime` | if None: return `now(ET)`; if naive: add UTC tz; `astimezone(ET)` | `datetime` (Eastern-aware) | `format_date_only`, `format_date_and_time` (same file) · `backend/shared/date_utils.py` (re-exported) | — |
| `parse_shopify_datetime` | 77–116 | `parse_shopify_datetime(date_str: str) → datetime \| None` | replace `"Z"→"+00:00"`; `fromisoformat`; if naive: add UTC; **midnight-correction heuristic** (UTC 04:00 → ET midnight, adjust back 1 day); return `None` on failure | `datetime` (UTC-aware) or `None` | `format_date_only`, `format_date_and_time`, `calculate_weeks_between_dates` (same file) · `backend/shared/date_utils.py` (re-exported) → `create_product.py`, `modal_handlers.py`, `product_update_handler.py` | — |
| `parse_iso_datetime` | 120–133 | `parse_iso_datetime(datetime_str: str) → datetime` | if ends `"Z"`: replace `"+00:00"`; `fromisoformat`; if naive: add UTC | `datetime` (UTC-aware) | none (canonical in `lib/tooling/date_utils/parse_iso_datetime.py`) | `lib/tooling/date_utils/parse_iso_datetime.py` |
| `parse_date` | 136–149 | `parse_date(date_str: str, default_century: int = 2000) → datetime` | split `/`; map int; if `year < 100`: add century; `datetime(y, m, d)` | `datetime` (naive) | `parse_off_dates` (same file) | `lib/tooling/date_utils/parse_date.py` |
| `parse_time` | 153–161 | `parse_time(time_str: str) → datetime.time` | `strptime(strip, "%I:%M %p").time()` | `datetime.time` | `parse_off_dates` (same file) | `lib/tooling/date_utils/parse_time.py` |
| `parse_off_dates` | 164–183 | `parse_off_dates(dates_str: str \| None, sport_time: dt_time) → list[datetime]` | split `,`; try `"%Y-%m-%d"` else `parse_date()`; `combine(date, sport_time)` | `list[datetime]` (naive) | `get_discount_dates_and_prices` uses `shared_utilities` version instead | `lib/tooling/date_utils/parse_off_dates.py` |
| `format_date_only` | 190–214 | `format_date_only(date: Any) → str \| None` | if str: `parse_shopify_datetime`; elif int/float: `fromtimestamp(UTC)`; `convert_to_eastern`; `strftime("%m/%d/%y")`; `None` for empty | `str "MM/DD/YY"` or `None` | `backend/shared/date_utils.py` (re-exported) → `create_product.py` | — |
| `format_date_and_time` | 217–238 | `format_date_and_time(date: Any) → str` | if str: `parse_shopify_datetime`; elif int/float: `fromtimestamp(UTC)`; `convert_to_eastern`; strftime date + time `lstrip("0")` | `str "MM/DD/YY at H:MM AM/PM"` | `backend/shared/date_utils.py` (re-exported) → `create_product.py`, `modal_handlers.py`, `product_update_handler.py` | — |
| `format_schedule_time` | 241–259 | `format_schedule_time(datetime_str: str, tz: str = "America/New_York", offset_minutes: int = 0) → str` | `strptime("%Y-%m-%dT%H:%M:%S")`; add UTC tz; `astimezone(ZoneInfo(tz))`; add offset; `strftime("%Y-%m-%dT%H:%M:%S")` | `str "YYYY-MM-DDTHH:MM:SS"` in target tz (no offset suffix) | EventBridge schedule creation (SchedulerAPI) | — |
| `normalize_date_str` | 262–280 | `normalize_date_str(date_str: str \| None) → str \| None` | try `strptime("%m/%d/%y")` then `"%m/%d/%Y"`; format `"{m}/{d}/{yy}"` — no zero-padding | `str "M/D/YY"` (no leading zeros) or `None` | `lib/tooling/datetime/__init__.py` (re-exported) | — |
| `extract_season_dates` | 287–296 | `extract_season_dates(description_html: str) → tuple[str \| None, str \| None]` | strip HTML tags + `&nbsp;`; regex `"Season Dates START – END (N weeks, off DATES)"`; return `(start_str, off_dates_csv)` | `tuple (start_date: str\|None, off_dates_csv: str\|None)` | `lib/tooling/datetime/__init__.py` (re-exported) | — |
| `split_off_dates` | 299–303 | `split_off_dates(off_dates_comma_separated: str \| None) → list[str]` | split on `,`; strip each; filter empty | `list[str]` | `lib/tooling/datetime/__init__.py` (re-exported) | — |
| `calculate_weeks_between_dates` | 310–326 | `calculate_weeks_between_dates(start_date: Any, end_date: Any) → int` | if str: `parse_shopify_datetime`; `(end - start).days / 7` rounded; `max(1, n)` if positive else 0 | `int` (≥ 0) | `backend/shared/date_utils.py` (re-exported) | — |
| `calculate_discounted_schedule` | 329–357 | `calculate_discounted_schedule(season_start_date, off_dates, base_price, discount_tiers?) → list[dict]` | build week_dates list (start + 7d intervals); for each off_date shift subsequent weeks +7d **(4-level nested loop — anti-pattern)**; zip weeks × tiers → `{timestamp, updated_price}` | `list[{timestamp: ISO str, updated_price: float}]` | `get_discount_dates_and_prices` uses `shared_utilities` version instead | `shared_utilities.calculate_discounted_schedule` (same logic; this copy adds the nested loop anti-pattern) |
| `get_discount_dates_and_prices` | 360–414 | `get_discount_dates_and_prices(season_start_date, off_dates_comma_separated, sport_start_time, price) → list[dict]` | lazy-import `shared_utilities`; `strptime("%Y-%m-%d")` else `parse_date`; `parse_time`; `combine`; `parse_off_dates`; `_calc()` | `list[{timestamp: ISO str, updated_price: float}]` | `SchedulerAPI/price_change_scheduler.py` | — |

---

## 7. backend/shared/date_utils.py

Module: `backend.shared.date_utils`  
Re-exports `lib.tooling.datetime` functions; adds backend-specific season/time helpers.

| Function / Class | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `SeasonBound` (TypedDict) | 29–35 | `class SeasonBound(TypedDict): start_month, start_day, start_year_offset, end_month, end_day, end_year_offset` | data schema only — drives `SEASON_BOUNDS` table | TypedDict type | `get_season_start_and_end` (same file) | — |
| `get_season_start_and_end` | 46–58 | `get_season_start_and_end(season: str, year: int) → tuple[str, str]` | lookup `SEASON_BOUNDS[season]`; `datetime(year+offset, month, day).strftime("%Y-%m-%dT00:00:00Z")` for start and end | `tuple ("YYYY-MM-DDTHH:MM:SSZ", "YYYY-MM-DDTHH:MM:SSZ")` | `backend/routers/orders.py` | — |
| `format_league_play_times` | 61–71 | `format_league_play_times(start_time: str, end_time: str) → str` | strip inputs; if both end `" PM"`: drop PM from start; join with ` – ` | `str "8:00 – 11:00 PM"` or `"8:00 PM – 11:00 AM"` | `backend/modules/products/services/.../create_product.py` (HTML product description) | — |

---

## 8. scripts/load_refunds_to_dynamo.py

Module: `scripts.load_refunds_to_dynamo`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `attempt_strptime` | 84–88 | `attempt_strptime(raw: str, fmt: str) → datetime \| None` | `strptime(raw, fmt)`; return `None` on `ValueError` | `datetime` (naive) or `None` | `parse_timestamp` (same file) | `scripts/load_waitlist_to_dynamo.py::attempt_strptime` (identical body) |
| `parse_timestamp` | 91–94 | `parse_timestamp(raw: str) → str` | strip; try 3 formats (`"%m/%d/%Y %H:%M:%S"`, 12h, 1-digit); `.replace(tzinfo=UTC).isoformat()` or raw passthrough | `str` ISO 8601 UTC, or original string on failure | DynamoDB item builder → `TABLE="refunds"` | `scripts/load_waitlist_to_dynamo.py::parse_timestamp` (identical logic and formats) |

---

## 9. scripts/load_waitlist_to_dynamo.py

Module: `scripts.load_waitlist_to_dynamo`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `attempt_strptime` | 93–97 | `attempt_strptime(raw: str, fmt: str) → datetime \| None` | `strptime(raw, fmt)`; return `None` on `ValueError` | `datetime` (naive) or `None` | `parse_timestamp` (same file) | `scripts/load_refunds_to_dynamo.py::attempt_strptime` (identical body) |
| `parse_timestamp` | 100–103 | `parse_timestamp(raw: str) → str` | strip; `next(attempt_strptime(raw, fmt) for fmt in TIMESTAMP_FORMATS)`; `.replace(tzinfo=UTC).isoformat()` or raw | `str` ISO 8601 UTC, or raw passthrough | DynamoDB item builder → `TABLE="waitlists"` | `scripts/load_refunds_to_dynamo.py::parse_timestamp` (identical logic) |

---

## 10. scripts/migrate_waitlist_sheet.py

Module: `scripts.migrate_waitlist_sheet`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `parse_ts` | 142–150 | `parse_ts(ts: str) → datetime` | for fmt in 3 inline formats: `strptime`; return `datetime.max` as sort-sentinel on total failure | `datetime` (naive) or `datetime.max` | row sort key in `step_migrate()` (same script) | `scripts/load_refunds_to_dynamo.py::parse_timestamp` (same 3 formats; differs: returns `datetime.max` instead of raw string passthrough) |

---

## 11. lib/domain/registrations/refunds/analyze_refunds.py

Module: `lib.domain.registrations.refunds.analyze_refunds`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `parse_season` | 65–105 | `parse_season(html: str) → tuple[SeasonDates, str]` | `SeasonDates.from_html(html)`; if no `start_date`: regex `"Regular Season starts on"`; extract off-weeks from `"Off Week(s)"` block; return `(SeasonDates, parser_name)` | `tuple (SeasonDates, str)` where str is `"season_dates"\|"important_dates"\|"none"` | refund calculator (same domain) | — |
| `parse_ts` | 108–115 | `parse_ts(ts: str) → datetime \| None` | try `"%m/%d/%Y %H:%M:%S"` then `"%m/%d/%Y %H:%M"`; `naive.replace(tzinfo=ET).astimezone(UTC)`; return `None` on failure | `datetime` (UTC-aware) or `None` | refund record timestamp normalization (same file) | `scripts/migrate_waitlist_sheet.py::parse_ts` (same formats; this one converts ET→UTC; migrate_waitlist returns naive `datetime.max` on failure) |

---

## 12. backend/modules/products/.../schedule_product_updates.py

Module: `backend.modules.products.services.create_product_complete_process.schedule_product_updates.schedule_product_updates`

| Function | Lines | Signature | Process | Output | Consumers | Duplicate of |
|---|---|---|---|---|---|---|
| `format_time_only` | 174–181 | `format_time_only(time_value) → str` | if `datetime`: `strftime("%H:%M")`; **if str: return unchanged**; else `str()` or `""` | `str "%H:%M"` or passthrough of `"6:30 PM"` unchanged | L710 — sportStartTime in Lambda payload builder — **⚠ LIKELY BUG** | `format_time_for_lambda` (same file) — contradictory behavior for str inputs |
| `format_date_for_lambda` | 184–206 | `format_date_for_lambda(date_value) → str` | if `datetime`: `strftime("%Y-%m-%d")`; if str: `fromisoformat(replace "Z"→"+00:00").strftime("%Y-%m-%d")`; else `str()` | `str "YYYY-MM-DD"` | Lambda price-schedule payload builder (same file) | — |
| `format_time_for_lambda` | 423–450 | `format_time_for_lambda(time_str: str) → str` | `strptime(strip, "%I:%M %p").strftime("%H:%M")`; fallback `strptime("%H:%M").strftime("%H:%M")`; passthrough on failure | `str "HH:MM"` (24-hour) or original string | L391 — sportStartTime in Lambda payload builder (correctly converts `"6:30 PM"` → `"18:30"`) | `lib/tooling/date_utils/parse_time.py` (parse half) + strftime (format half); `format_time_only` in same file contradicts this |

---

## Consolidation targets — ranked by blast radius

### #1 — Sheet timestamp parsing (4 copies)

**Locations:** `load_refunds_to_dynamo` · `load_waitlist_to_dynamo` · `migrate_waitlist_sheet` · `analyze_refunds`

**Issue:** `TIMESTAMP_FORMATS` + `attempt_strptime` + `parse_timestamp` copied verbatim 3–4×.
Timezone handling is inconsistent: naive / UTC / ET→UTC.
Failure modes differ: `None`, raw string passthrough, `datetime.max`.

**Action:** Extract to `lib/tooling/date_utils/parse_sheet_timestamp.py` with a single API that returns `datetime | None` (UTC-aware). Delete all copies.

---

### #2 — `format_time_only` vs `format_time_for_lambda` (same file, likely bug)

**Locations:** `schedule_product_updates.py` L174 vs L423

**Issue:** L710 uses `format_time_only` which passes `"6:30 PM"` to Lambda unchanged.
L391 uses `format_time_for_lambda` which correctly converts to `"18:30"`.
Lambda almost certainly fails silently on the L710 payload.

**Action:** Delete `format_time_only`. Route all callers to `format_time_for_lambda`. Audit Lambda payload at L710.

---

### #3 — `parse_time` (12h → `dt.time`) — 3 copies

**Locations:** `lib/tooling/date_utils/parse_time.py` (canonical) · `lib/tooling/datetime/date_utils.py` (deprecated copy) · `schedule_product_updates.py` (re-implemented inline in `format_time_for_lambda`)

**Issue:** Identical `strptime("%I:%M %p")` logic in three places. Deprecated copy still reached by callers via `backend/shared/date_utils.py` re-exports.

**Action:** All callers migrate to `lib/tooling/date_utils/parse_time`. Delete deprecated copy when the deprecated file is removed.

---

### #4 — `lib/tooling/datetime/date_utils.py` whole-file deprecation

**Locations:** 8 functions are direct copies of `lib/tooling/date_utils/*` counterparts

**Issue:** Deprecated file re-exported by `backend/shared/date_utils.py` and consumed by `create_product.py`, `modal_handlers.py`, `product_update_handler.py`. Cannot delete until those callers migrate.

**Action:** Migrate 3 callers to `lib/tooling/date_utils/*` imports. Delete this file. Update `backend/shared/date_utils.py` re-exports to point at canonical sources.

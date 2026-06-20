---
name: shopify-eventbridge-golive
description: Schedule BARS registration-management actions (go live, move inventory between variants, close registration, price updates) on Shopify products via AWS EventBridge Scheduler. Use when asked to make a product go live / open registration / release inventory, move inventory between variants for a phase transition (vet → early, early → open, etc.), close registration into waitlist, or update variant prices at a specific ET time. The production Lambda is `updateRegistrationStatus` (v2.3.0+) for lifecycle actions; `ShopifyProductUpdates` is the in-repo successor (DynamoDB-driven, consolidated). `setProductLiveByAddingInventory`, `MoveInventoryLambda`, and `changePricesOfOpenAndWaitlistVariants` are retired and must not be scheduled against.
---

# Schedule a registration phase transition (EventBridge → updateRegistrationStatus)

Account `084375563770`, region `us-east-1`. All AWS calls require Granted —
prefix every command with `assume bars --exec --` (see `~/.claude/rules/aws-credentials.md`; the user-level hook auto-injects for `Bash(aws *)` but compound shell needs manual wrapping).

## Which Lambda

**`updateRegistrationStatus`** (v2.3.0, version 1.0.18 as of 2026-06-09) — one
Lambda, three actions, dispatched on the event's `action` field:

| `action` | Effect |
|---|---|
| `set-reg-live` | Add `inventoryToAdd` to `targetVariant`; rewrite title bracket + tags by target variant name; Slack post. **Required**: `product`, `targetVariant`, `inventoryToAdd`. |
| `update-reg-status` | Move **all** inventory `sourceVariant` → `targetVariant`; rewrite title bracket + tags; Slack post. **Required**: `product`, `sourceVariant`, `targetVariant`. |
| `close-reg` | Move all inventory to waitlist variant, add `waitlist-only` tag, set waitlist image; Slack post. **Required**: `product`, `sourceVariant`, `targetVariant`. |

Optional on all three: `dryRun`, `fast`, `slackConfig` (auto-derived from
product handle `{year}-{season}-{sport}-{day}-{division}div` if omitted).

The Lambda calls `wait_until_next_minute()` before touching Shopify, so set the
EventBridge fire time **one minute before** the public-visible time (18:00
public → fire at 17:59).

### Retired Lambdas

The following are **retired** — source deleted from the repo. Do not schedule
new jobs against them; contact the team to migrate existing schedules.

| Lambda | Retired | Replacement |
|--------|---------|-------------|
| `setProductLiveByAddingInventory` | 2026-06-16 | `updateRegistrationStatus` action `set-reg-live` |
| `MoveInventoryLambda` | 2026-06-16 | `updateRegistrationStatus` actions `update-reg-status` / `close-reg` |
| `changePricesOfOpenAndWaitlistVariants` | 2026-06-16 | `ShopifyProductUpdates` action `update-prices` (in-repo v1.0.0, deploy pending) |
| `shopifyProductUpdateHandler` | 2026-06-16 | `ShopifyProductUpdates` action `sold-out-image-check` (in-repo v1.0.0, deploy pending) |

Schedule names beginning with `move-…` still target `MoveInventoryLambda`; those
beginning with `update-…` / `reg-status-…` target `updateRegistrationStatus`.
Migrate any `move-…` schedules before decommissioning `MoveInventoryLambda` in the account.

Confirm a Lambda's current deployed contract any time with:

```bash
assume bars --exec -- aws lambda get-function --function-name updateRegistrationStatus --query Code.Location --output text
# download + unzip the URL → main.py, version.json
```

## Recipe (preferred: helper script)

```bash
uv run --project scripts python scripts/aws/create_schedule.py update-reg-status \
    --product 7678746132574 \
    --source-variant 42896444325982 \
    --target-variant 42896444358750 \
    --at 2026-06-16T18:00 \
    --sport pb \
    --name update-tue-pb-summer-2026-vet-to-early
```

The script picks the right schedule group, subtracts the 1-minute fire offset,
fills in `slackConfig` from the product handle, and matches the production
retry policy (`MaximumEventAgeInSeconds=1800`, `MaximumRetryAttempts=5`). Pass
`--dry-run` to preview the JSON without creating.

`--sport` must be one of `pb`, `kb`, `db`, `bowl`, `misc` — chooses the group
suffix. `set-reg-live` uses the unified `set-product-live` group regardless
of sport.

## Manual recipe (when you need an option the script doesn't expose)

1. **Resolve product + variants** before scheduling — never guess the variant.

   ```bash
   uv run --project scripts python scripts/shopify/_get_product_details.py <productId>
   ```

2. **Build the schedule JSON** and create it. Fire time = public time − 1 min.

   ```jsonc
   // /tmp/sched.json
   {
     "Name": "update-tue-pb-summer-2026-vet-to-early",
     "GroupName": "move-inventory-between-variants-pb",
     "ScheduleExpression": "at(2026-06-16T17:59:00)",
     "ScheduleExpressionTimezone": "America/New_York",
     "FlexibleTimeWindow": {"Mode": "OFF"},
     "ActionAfterCompletion": "NONE",
     "State": "ENABLED",
     "Description": "...",
     "Target": {
       "Arn": "arn:aws:lambda:us-east-1:084375563770:function:updateRegistrationStatus",
       "RoleArn": "arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",
       "Input": "{\"action\":\"update-reg-status\",\"product\":\"...\",\"sourceVariant\":...,\"targetVariant\":...,\"slackConfig\":{...}}",
       "RetryPolicy": {"MaximumEventAgeInSeconds": 1800, "MaximumRetryAttempts": 5}
     }
   }
   ```

   `Target.Input` is a **JSON string** (escaped). Generate the file with Python
   (`json.dumps` the inner dict) to avoid shell-escaping pain.

3. **Create + verify:**

   ```bash
   assume bars --exec -- aws scheduler create-schedule --cli-input-json file:///tmp/sched.json --query ScheduleArn --output text
   assume bars --exec -- aws scheduler get-schedule --group-name move-inventory-between-variants-pb --name <Name> \
     --query '{when:ScheduleExpression,tz:ScheduleExpressionTimezone,state:State,input:Target.Input,arn:Target.Arn,retry:Target.RetryPolicy}'
   ```

## Schedule groups (existing)

| Group | Use for |
|---|---|
| `set-product-live` | `set-reg-live` action (any sport) |
| `move-inventory-between-variants-{pb,kb,db,bowl,misc}` | `update-reg-status` and `close-reg`, by sport |
| `adjust-prices-week-{1-4}` | `changePricesOfOpenAndWaitlistVariants` in prod (retiring); successor `ShopifyProductUpdates` action `update-prices` — update `Target.Arn` when deploying v1.0.0 |
| `add-remaining-inventory-to-live-product` | `addRemainingInventoryToLiveProduct` Lambda (separate) |

`ActionAfterCompletion: NONE` matches the 2026 production pattern — schedule
remains visible after firing. Use `DELETE` for true one-shots you want
auto-cleaned.

## Gotchas

- Run one `create-schedule` per call; a multiline `bash -c '... \ ...'` under
  `assume --exec` mangles quoting. Use single-line commands, `--cli-input-json
  file://...`, or the helper script.
- The `set-product-live` group **mixes targets** — some schedules in it still
  point at `setProductLiveByAddingInventory`. When updating an existing
  schedule, double-check the `Target.Arn` before assuming it's the modern
  Lambda.
- Confirm current ET vs target before creating:
  `assume bars --exec -- bash -c 'TZ=America/New_York date'`.
- `slackConfig` is optional — the Lambda auto-derives `channelName` and
  `tagTarget` from the product handle. Override only when the product handle
  doesn't follow `{year}-{season}-{sport}-{day}-{division}div`.

## Keep this skill current

Update this file on any **material** change: new Lambda action, Lambda
deprecation, new schedule group, payload-format change in `updateRegistrationStatus`,
or a change to the helper script's flags.

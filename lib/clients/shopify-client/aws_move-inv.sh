move_product_inventory_between_variants() {
  local name="open-pb-thu-summer-2026"
  local datetime="2026-06-24T19:59:00"
  local product_id="7678746230878"
  local source_variant_id=42896444719198
  local target_variant_id=42896444751966
  local slack_channel="pickleball-thursday-open"
  local slack_group_to_tag="@pickleball-thursday-open-team"

  local input
  input=$(jq -cn \
    --arg  product "$product_id" \
    --argjson src   "$source_variant_id" \
    --argjson tgt   "$target_variant_id" \
    --arg  channel  "$slack_channel" \
    --arg  tag      "$slack_group_to_tag" \
    '{action:"update-reg-status",product:$product,sourceVariant:$src,targetVariant:$tgt,slackConfig:{botName:"registrations",channelName:$channel,tagTarget:$tag}}')

  local target
  target=$(jq -cn \
    --arg input "$input" \
    '{Arn:"arn:aws:lambda:us-east-1:084375563770:function:updateRegistrationStatus",RoleArn:"arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",Input:$input,RetryPolicy:{MaximumEventAgeInSeconds:1800,MaximumRetryAttempts:5}}')

  aws scheduler create-schedule \
    --name "$name" \
    --group-name "move-inventory-between-variants-pb" \
    --schedule-expression "at(${datetime})" \
    --schedule-expression-timezone "America/New_York" \
    --flexible-time-window '{"Mode": "OFF"}' \
    --action-after-completion NONE \
    --target "$target"
}

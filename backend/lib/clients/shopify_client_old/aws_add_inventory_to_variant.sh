add_product_inventory_to_variant() {
  local name="add-pb-thu-general-summer-2026"
  local datetime="2026-06-24T19:59:00"
  local product_id="7678746230878"
  local variant_id="42896444751966"
  local qty=  # fill in when known

  local input
  input=$(jq -cn \
    --arg    product "$product_id" \
    --arg    variant "$variant_id" \
    --argjson qty    "$qty" \
    '{productId:$product,variantId:$variant,inventoryToAdd:$qty}')

  local target
  target=$(jq -cn \
    --arg input "$input" \
    '{Arn:"arn:aws:lambda:us-east-1:084375563770:function:setProductLiveByAddingInventory",RoleArn:"arn:aws:iam::084375563770:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_3bc414251c",Input:$input,RetryPolicy:{MaximumRetryAttempts:0}}')

  aws scheduler create-schedule \
    --name "$name" \
    --group-name "add-remaining-inventory-to-live-product" \
    --schedule-expression "at(${datetime})" \
    --schedule-expression-timezone "America/New_York" \
    --flexible-time-window '{"Mode": "OFF"}' \
    --action-after-completion DELETE \
    --target "$target"
}

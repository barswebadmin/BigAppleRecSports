# Slack API Refactoring Plan

## 🎯 Goal
Replace fragmented Slack API patterns with a single, unified interface that eliminates channel ID mismatches and provides consistent behavior across all Slack operations.

## 🔍 Current Problems
1. **Channel ID Confusion**: Hardcoded channels vs dynamic interaction channels
2. **Fragmented Patterns**: 3+ different ways to send/update Slack messages
3. **Inconsistent Error Handling**: Different SSL, retry, and fallback logic
4. **Mock/Real Client Switching**: Scattered test mode detection
5. **Maintenance Burden**: Changes require updates in multiple places

## ✅ New Unified Approach

### Single Import
```python
from services.slack.unified_slack_client import slack_client
```

### Explicit Parameters (No More Hidden State)
```python
# OLD (fragmented, error-prone)
self.api_client.send_message(message_text, action_buttons)  # Uses hardcoded channel
dynamic_client = self._create_dynamic_api_client(channel_id, token)  # Ad-hoc creation
dynamic_client.update_message(ts, text, buttons)  # Inconsistent patterns

# NEW (unified, explicit)
slack_client.send_message(
    channel_id=channel_id,      # Always explicit
    bearer_token=bot_token,     # Always explicit
    message_text=text,
    action_buttons=buttons,
    metadata=metadata           # Optional, explicit
)

slack_client.update_message(
    channel_id=channel_id,      # Always explicit - no more mismatches!
    bearer_token=bot_token,     # Always explicit
    message_ts=message_ts,
    message_text=text,
    action_buttons=buttons
)
```

## 🔄 Migration Strategy

### Phase 1: Core Infrastructure (This PR)
- [x] Create `UnifiedSlackClient` with all Slack operations
- [x] Maintain backward compatibility during transition
- [ ] Update `SlackRefundsUtils.update_slack_on_shopify_success()` to use unified client
- [ ] Update `SlackService.send_refund_request_notification()` to use unified client

### Phase 2: Button Interactions (Next PR)
- [ ] Update all button handler methods to use unified client
- [ ] Remove `_create_dynamic_api_client()` method
- [ ] Update modal handlers to use unified client

### Phase 3: Cleanup (Final PR)
- [ ] Remove old `SlackApiClient` and `MockSlackApiClient` classes
- [ ] Remove hardcoded channel logic from `SlackService.__init__()`
- [ ] Update tests to use unified patterns

## 🛡️ Risk Mitigation

### Message Format Consistency
- ✅ `_create_standard_blocks()` method preserves existing Block Kit structure
- ✅ All existing message formatting preserved in `SlackMessageBuilder`
- ✅ No changes to button definitions or modal structures

### Test Mode Handling
- ✅ Automatic test mode detection (same logic as before)
- ✅ Mock behavior identical to existing `MockSlackApiClient`
- ✅ Production behavior identical to existing `SlackApiClient`

### SSL Certificate Handling
- ✅ Same SSL logic as existing code (production vs development paths)
- ✅ Same fallback behavior on SSL errors
- ✅ No changes to certificate bundle configuration

### Error Handling
- ✅ Same error response format as existing clients
- ✅ Same retry logic and fallback behavior
- ✅ Same logging patterns and debug output

## 📋 Example Refactor

### Before (Fragmented)
```python
# In SlackRefundsUtils
def update_slack_on_shopify_success(self, message_ts, success_message, action_buttons, channel_id=None):
    if channel_id:
        # Create dynamic client
        bot_token = settings.active_slack_bot_token or ""
        dynamic_api_client = self._create_dynamic_api_client(channel_id, bot_token)
        result = dynamic_api_client.update_message(...)
    else:
        # Use default client (wrong channel!)
        result = self.api_client.update_message(...)
```

### After (Unified)
```python
# In SlackRefundsUtils
def update_slack_on_shopify_success(self, message_ts, success_message, action_buttons, channel_id, bearer_token):
    # Always explicit, no fallbacks, no confusion
    return slack_client.update_message(
        channel_id=channel_id,
        bearer_token=bearer_token,
        message_ts=message_ts,
        message_text=success_message,
        action_buttons=action_buttons
    )
```

## 🎯 Benefits

### Immediate Benefits
- ✅ **No More Channel ID Mismatches**: Every call explicitly specifies channel
- ✅ **Consistent Error Handling**: Same SSL, retry, and logging logic everywhere
- ✅ **Clear Test/Production Switching**: Single point of test mode detection
- ✅ **Reduced Complexity**: One way to send/update messages, not three

### Long-term Benefits
- 🔧 **Easier Maintenance**: Changes in one place affect all Slack operations
- 🐛 **Fewer Bugs**: Explicit parameters prevent hidden state issues
- 📊 **Better Debugging**: Consistent logging and error messages
- 🧪 **Easier Testing**: Single mock behavior, not multiple client types

## 🚀 Implementation Order

1. **Create unified client** (✅ Done)
2. **Update core message update logic** (Next)
3. **Update button interaction handlers**
4. **Update initial message sending**
5. **Remove old client classes**
6. **Update tests and documentation**

This approach ensures we can migrate incrementally while maintaining full backward compatibility until the transition is complete.

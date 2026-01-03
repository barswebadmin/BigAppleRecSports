# Typed Slack Block Builders - Usage Guide

## Overview

The `GenericMessageBuilder` and `SlackBlockBuilder` classes now use **Slack SDK's typed models** to provide compile-time safety and prevent "invalid_blocks" errors.

### Benefits

✅ **Type Safety**: Your IDE/type checker will catch invalid block structures  
✅ **Auto-completion**: IDE suggests valid fields and methods  
✅ **Required vs Optional**: Type system enforces required fields  
✅ **Prevents Runtime Errors**: Catches mistakes before sending to Slack API  

---

## GenericMessageBuilder - Basic Blocks

### Creating Typed Blocks

```python
from modules.integrations.slack.builders import GenericMessageBuilder

builder = GenericMessageBuilder()

# ✅ Returns HeaderBlock (typed)
header = builder.header("🎉 Welcome!")

# ✅ Returns SectionBlock (typed)
section = builder.section("This is *markdown* text")

# ✅ Returns SectionBlock with fields (typed)
section_with_fields = builder.section(
    "Main text",
    fields=["Field 1", "Field 2"]
)

# ✅ Returns DividerBlock (typed)
divider = builder.divider()

# ✅ Returns ContextBlock (typed)
context = builder.context(["Last updated: 2025-01-02"])
```

### Creating Buttons and Actions

```python
# ✅ Returns ButtonElement (typed)
primary_button = builder.button(
    text="Approve",
    action_id="approve_action",
    value="order_123",
    style="primary"
)

danger_button = builder.button(
    text="Reject",
    action_id="reject_action",
    value="order_123",
    style="danger"
)

# ✅ Returns ActionsBlock (typed)
actions = builder.actions([primary_button, danger_button])
```

### Converting to Dict for Slack API

```python
# Slack API expects dicts, not typed objects
# Use blocks_to_dict() to convert

blocks = [header, section, divider, actions]
blocks_dict = builder.blocks_to_dict(blocks)

# Now send to Slack
client.chat_postMessage(
    channel="C12345",
    blocks=blocks_dict,  # ← List[dict]
    text="Fallback text"
)
```

### Text Formatting Helpers

```python
# These return formatted strings for use in block text
hyperlink = builder.hyperlink("https://example.com", "Click here")
user_mention = builder.user_mention("U12345")
channel_mention = builder.channel_mention("C12345")
bold_text = builder.bold("Important")
code_block = builder.code_block("print('hello')", language="python")
```

---

## SlackBlockBuilder - Complex Blocks

### Text Input

```python
from modules.integrations.slack.builders import SlackBlockBuilder

# ✅ Returns InputBlock (typed)
text_input = SlackBlockBuilder.text_input(
    action_id="feedback_input",
    label="Your Feedback",
    placeholder="Tell us what you think...",
    multiline=True,
    optional=False
)
```

### Static Select Menu

```python
# ✅ Returns InputBlock with StaticSelectElement (typed)
# Options are (text, value) tuples
select = SlackBlockBuilder.static_select(
    action_id="priority_select",
    label="Priority Level",
    options=[
        ("🔴 High", "high"),
        ("🟡 Medium", "medium"),
        ("🟢 Low", "low")
    ],
    initial_option=("🟡 Medium", "medium"),
    optional=False
)
```

### Checkbox Group

```python
# ✅ Returns InputBlock with CheckboxesElement (typed)
checkboxes = SlackBlockBuilder.checkbox_group(
    action_id="features_checkbox",
    label="Select Features",
    options=[
        ("Feature A", "feat_a"),
        ("Feature B", "feat_b"),
        ("Feature C", "feat_c")
    ],
    initial_options=[("Feature A", "feat_a")]
)
```

### Modal View

```python
from modules.integrations.slack.builders import GenericMessageBuilder, SlackBlockBuilder

builder = GenericMessageBuilder()

# Build modal blocks
header = builder.header("Submit Feedback")
description = builder.section("Please provide your feedback below")
feedback_input = SlackBlockBuilder.text_input(
    action_id="feedback",
    label="Feedback",
    multiline=True
)
rating_select = SlackBlockBuilder.static_select(
    action_id="rating",
    label="Rating",
    options=[("⭐" * i, str(i)) for i in range(1, 6)]
)

# ✅ Returns View (typed)
modal = SlackBlockBuilder.modal(
    title="Feedback Form",
    blocks=[header, description, feedback_input, rating_select],
    submit_text="Submit",
    close_text="Cancel",
    callback_id="feedback_modal"
)

# Open modal
client.views_open(
    trigger_id=trigger_id,
    view=modal.to_dict()  # ← Convert to dict for API
)
```

### Loading Modal

```python
# ✅ Returns View (typed)
loading = SlackBlockBuilder.loading_modal(
    title="Processing...",
    message="Please wait while we process your request"
)

client.views_open(trigger_id=trigger_id, view=loading.to_dict())
```

### Confirmation Dialog

```python
# ✅ Returns ConfirmObject (typed)
confirm = SlackBlockBuilder.confirmation_dialog(
    title="Are you sure?",
    text="This action cannot be undone.",
    confirm_text="Yes, delete",
    deny_text="Cancel",
    style="danger"
)

# Use with button
delete_button = builder.button(
    text="Delete",
    action_id="delete_action",
    value="item_123"
)
# Attach confirmation (note: need to manually add to button dict)
button_dict = delete_button.to_dict()
button_dict["confirm"] = confirm.to_dict()
```

---

## Complete Example: Order Approval Flow

```python
from modules.integrations.slack.builders import GenericMessageBuilder, SlackBlockBuilder

def build_order_approval_message(order_number: str, customer_name: str, total: str):
    """Build a typed Slack message for order approval."""
    builder = GenericMessageBuilder()
    
    # Build blocks with typed objects
    header = builder.header(f"📦 Order #{order_number}")
    
    customer_section = builder.section(
        f"*Customer:* {customer_name}\n*Total:* ${total}"
    )
    
    divider = builder.divider()
    
    approve_button = builder.button(
        text="Approve Order",
        action_id="approve_order",
        value=order_number,
        style="primary"
    )
    
    reject_button = builder.button(
        text="Reject Order",
        action_id="reject_order",
        value=order_number,
        style="danger"
    )
    
    actions = builder.actions([approve_button, reject_button])
    
    context = builder.context([
        f"Requested at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    ])
    
    # Convert to dicts for Slack API
    blocks = [header, customer_section, divider, actions, context]
    return builder.blocks_to_dict(blocks)

# Use it
blocks = build_order_approval_message("1001", "John Doe", "149.99")
client.chat_postMessage(channel="C12345", blocks=blocks, text="Order approval")
```

---

## Type Safety Examples

### ❌ Before (Dict-based - No Type Safety)

```python
# No type checking - errors at runtime only
section = {
    "type": "seciton",  # ❌ Typo! Runtime error
    "text": {
        "type": "mrkdwn",
        "txt": "Hello"  # ❌ Wrong key! Runtime error
    }
}

button = {
    "type": "button",
    "text": "Click me",  # ❌ Missing required structure! Runtime error
    "action_id": "test"
}
```

### ✅ After (Typed - Compile-time Safety)

```python
from modules.integrations.slack.builders import GenericMessageBuilder

builder = GenericMessageBuilder()

# ✅ IDE autocompletes method names
# ✅ Type checker validates parameters
# ✅ Returns typed SectionBlock
section = builder.section("Hello")  # Can't typo method name

# ✅ IDE autocompletes parameter names
# ✅ Type checker enforces required parameters
# ✅ Returns typed ButtonElement
button = builder.button(
    text="Click me",
    action_id="test",
    value="test_value"  # Required parameter enforced by type system
)

# ✅ Type system ensures blocks are valid
# IDE will show error if you try to pass incompatible types
blocks = [section, button]  # ❌ Type error: button is not a Block
```

---

## Migration from Dict-based Builders

### If you have existing dict-based code:

```python
# Old dict-based code
old_blocks = [
    {"type": "header", "text": {"type": "plain_text", "text": "Title"}},
    {"type": "section", "text": {"type": "mrkdwn", "text": "Content"}}
]

# Migrate to typed builders
builder = GenericMessageBuilder()
new_blocks = [
    builder.header("Title"),
    builder.section("Content")
]

# Convert to dicts when needed
blocks_dict = builder.blocks_to_dict(new_blocks)
```

---

## Best Practices

1. **Use typed builders everywhere** - They prevent "invalid_blocks" errors
2. **Convert to dict only at the API boundary** - Keep types as long as possible
3. **Let IDE autocomplete guide you** - Typed models provide great IDE support
4. **Run type checker** - `mypy` or `pyright` will catch errors before runtime
5. **Use tuple syntax for options** - Simpler than dicts: `("Text", "value")`

---

## Troubleshooting

### "invalid_blocks" Error

If you still get this error:
1. Check the typed object with `.to_dict()` to see the structure
2. Verify all required fields are provided
3. Check Slack's Block Kit documentation for field limits (e.g., title max 150 chars)

### Type Errors

If your type checker complains:
1. Make sure you're using the correct typed object (Block, not dict)
2. Use `blocks_to_dict()` when passing to Slack API
3. Check imports - make sure you're importing from the right module

---

## Further Reading

- [Slack Block Kit Documentation](https://api.slack.com/block-kit)
- [slack-sdk Python Documentation](https://slack.dev/python-slack-sdk/)
- [Slack Block Kit Builder](https://app.slack.com/block-kit-builder/) (Interactive tool)


# Google API Models

Focused, minimal Pydantic models extracted from official Google API schemas.

## Design Principles

1. **Extract on-demand** - Only models needed for active workflows
2. **Encapsulate logically** - Group related models in single file
3. **Minimal documentation** - Field names self-document
4. **Type-safe** - Full Pydantic v2 validation with Annotated fields
5. **Scalable** - Add files per workflow, not per model

## Current Coverage

### send_as.py (47 lines)
**Gmail Settings API** - Signature retrieval

- `SendAs` - Send-as alias configuration
- `SmtpMsa` - Custom SMTP relay settings
- `SecurityMode` - SMTP security protocol enum
- `VerificationStatus` - Alias verification state enum

**Used by:** `scripts/google_api/send_email.py`

### message.py (62 lines)
**Gmail Messages API** - Email sending/receiving

- `Message` - Email message resource
- `MessagePart` - MIME message part structure (recursive)
- `MessagePartHeader` - Email headers (To, From, Subject, etc.)
- `MessagePartBody` - MIME part body content
- `ClassificationLabelValue` - Google Workspace classification labels
- `ClassificationLabelFieldValue` - Label field values

**Used by:** `scripts/google_api/send_email.py`

## Adding New Models

Extract from `shared_utilities/generated_models/google/` as needed:

1. Identify API calls in your workflow
2. Find models in `generated_models/google/{api}.py`
3. Trace dependencies (nested models, enums)
4. Create focused file in this directory
5. Strip verbose docstrings
6. Update `__init__.py` exports

## File Organization Rules

**Combine in one file when:**
- Nested dependency used only by parent (e.g., `MessagePart` only used in `Message`)
- Related enums (e.g., `SecurityMode` only for SMTP)
- Logically cohesive (e.g., all send-as settings)

**Separate into files when:**
- Model used by multiple parents
- Distinct API namespace (messages vs labels vs drafts)
- Would exceed ~150 lines

## Source

Full generated models available at `shared_utilities/generated_models/google/` (604 models across 7 APIs).

# Google API Schemas

Official JSON Schemas exported from Google's Discovery API for type-safe Pydantic model generation.

**Total Coverage:** 7 APIs | 604 resource schemas | 344 method definitions

## Directory Structure

```
google/
├── gmail/                          # Gmail API v1
│   ├── messages/                   # Message, MessagePart, Thread schemas
│   ├── settings/                   # SendAs, IMAP, filters, vacation
│   ├── methods/                    # API operations with scopes
│   │   └── users/
│   │       ├── messages/
│   │       │   ├── send.yaml      # Scopes, params, request/response
│   │       │   └── get.yaml
│   │       └── settings/
│   │           └── sendAs/
│   │               └── get.yaml
│   └── _metadata.yaml
│
├── drive/                          # Drive API v3
├── sheets/                         # Sheets API v4
├── calendar/                       # Calendar API v3
├── admin/                          # Admin Directory API directory_v1
├── script/                         # Apps Script API v1
├── forms/                          # Forms API v1
└── README.md                       # This file
```

## API Coverage Summary

| API | Version | Schemas | Methods | Key Use Cases |
|-----|---------|---------|---------|---------------|
| **Gmail** | v1 | 56 | 79 | Email sending, signature retrieval |
| **Drive** | v3 | 43 | 57 | File management, permissions |
| **Sheets** | v4 | 262 | 17 | Spreadsheet operations, data sync |
| **Calendar** | v3 | 39 | 37 | Event management, availability |
| **Admin Directory** | directory_v1 | 109 | 128 | User/group management |
| **Apps Script** | v1 | 31 | 16 | Script deployment, execution |
| **Forms** | v1 | 64 | 10 | Form creation, responses |

### Gmail API (v1)
- **Schemas:** Message, MessagePart, Thread, Draft, Label, SendAs, Filter
- **Methods:** `users/messages/send`, `users/settings/sendAs/get`, `users/labels/list`
- **Code:** `scripts/google_api/send_email.py`, `lambda/functions/WaitlistManager/email_operations.py`

### Drive API (v3)
- **Schemas:** File, FileList, Permission, Comment, Revision, Drive (shared)
- **Methods:** `files/create`, `files/list`, `permissions/create`
- **Code:** `scripts/google_api/drive_utils.py`, `shared_utilities/clients/google_client_v2/services/drive.py`

### Sheets API (v4)
- **Schemas:** Spreadsheet, Sheet, ValueRange, CellData, 35+ chart types, 80 batch operations
- **Methods:** `spreadsheets/values/append`, `spreadsheets/batchUpdate`, `spreadsheets/values/get`
- **Code:** `lambda/functions/WaitlistManager/sheets_operations.py`

### Admin Directory API (directory_v1)
- **Schemas:** User, Group, Member, ChromeOsDevice, Domain, Role
- **Methods:** `groups/list`, `members/insert`, `users/get`
- **Code:** `scripts/google_api/update_google_groups.py`, `backend/modules/integrations/google/services/google_directory_service.py`

## Using Method Definitions

Method YAML files contain complete operation metadata:

```yaml
# gmail/methods/users/messages/send.yaml
description: Sends the specified message...
httpMethod: POST
path: gmail/v1/users/{userId}/messages/send
scopes:
  - https://mail.google.com/
  - https://www.googleapis.com/auth/gmail.send
  - https://www.googleapis.com/auth/gmail.compose
parameters:
  userId:
    type: string
    required: true
    default: me
request:
  $ref: Message
response:
  $ref: Message
```

**Finding required scopes:**
```bash
cat gmail/methods/users/messages/send.yaml | grep -A5 scopes
# Shows all valid OAuth2 scopes (any one works)
```

**Understanding parameters:**
```bash
cat drive/methods/files/list.yaml
# Shows: q, pageSize, fields, etc. with types and descriptions
```

## Tooling

All tooling is in `shared_utilities/schemas/_tooling/`:
- `google/` - Google API discovery export and inspection
- `codegen/` - Code generation from JSON Schema

### Export Schemas from Google

```bash
cd shared_utilities/schemas/_tooling/google

# Export all schemas + methods
uv run --with google-api-python-client --with PyYAML --with httpx \
  export.py <api> <version> --methods

# Examples
uv run export.py gmail v1 --methods
uv run export.py drive v3 --methods
uv run export.py admin directory_v1 --methods
```

**Options:**
- `--methods` - Include method definitions (scopes, params)
- `--resources Message Thread` - Export specific schemas only
- `--list` - Show available schemas without exporting

### Inspect API Methods and Scopes

```bash
cd shared_utilities/schemas/_tooling/google

# List all available Google APIs
uv run inspect.py --list

# Show all methods and scopes for an API
uv run inspect.py gmail v1

# Filter to specific methods
uv run inspect.py gmail v1 users.messages.send
```

### Generate Pydantic Models

Generate type-safe Python models from schemas:

```bash
cd ../../../..  # Back to repo root

# Single API (recommended)
datamodel-codegen \
  --input shared_utilities/schemas/google/gmail \
  --output shared_utilities/generated_models/google/gmail.py \
  --input-file-type jsonschema \
  --collapse-root-models \
  --exclude */methods/*

# All APIs (creates large monolith files)
datamodel-codegen \
  --input shared_utilities/schemas/google \
  --output shared_utilities/generated_models/google \
  --input-file-type jsonschema \
  --exclude */methods/*
```

**Why exclude `*/methods/*`?**  
Method YAMLs document operations (scopes, params), not data structures. Only resource schemas become Pydantic models.

### Extract Focused Models

Generated models are comprehensive but large. For production use:

1. **Generate full models** (step 2 above)
2. **Identify needed classes** (e.g., `Message`, `SendAs` for email sending)
3. **Extract to curated location**:
   ```bash
   # Copy specific classes to:
   shared_utilities/clients/google_client_v2/models/message.py
   shared_utilities/clients/google_client_v2/models/send_as.py
   ```
4. **Trim docstrings** (keep only non-obvious information)
5. **Add re-exports** to generated monolith for backward compatibility

**Example:**
```python
# shared_utilities/clients/google_client_v2/models/message.py
from pydantic import BaseModel, Field
from typing import Any

class MessagePartHeader(BaseModel):
    name: str
    value: str

class MessagePartBody(BaseModel):
    attachmentId: str | None = None
    size: int | None = None
    data: str | None = Field(None, description="Base64url encoded")

class MessagePart(BaseModel):
    partId: str | None = None
    mimeType: str | None = None
    filename: str | None = None
    headers: list[MessagePartHeader] | None = None
    body: MessagePartBody | None = None
    parts: list["MessagePart"] | None = None

class Message(BaseModel):
    id: str | None = None
    threadId: str | None = None
    labelIds: list[str] | None = None
    snippet: str | None = None
    payload: MessagePart | None = None
    raw: str | None = Field(None, description="Base64url encoded RFC 2822 message")
```

### Use in Service Classes

Service builders use schemas for request construction:

```python
# shared_utilities/clients/google_client_v2/services/gmail.py
class Gmail:
    # Reference SCOPES_MAP from method YAMLs
    SCOPES_MAP = {
        "send_message": [
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.send",
            # ... from gmail/methods/users/messages/send.yaml
        ]
    }
    
    def send_message(
        self,
        message_body: dict[str, Any],
        scopes: list[str] | None = None,  # Must be explicit
        subject: str | None = None,
        user_id: str = "me",
    ) -> Any:
        """Build request to send email (caller must execute)."""
        gmail = self.client.service("gmail", "v1", subject, scopes)
        return gmail.users().messages().send(userId=user_id, body=message_body)
```

**Design principles:**
- Service methods build requests, don't execute
- Client handles execution, error handling, pagination
- No default scopes (explicit for security)
- Type hints from generated/extracted models

## Benefits

✅ **Official schemas** - Always accurate, maintained by Google  
✅ **Hierarchical organization** - Resource-based navigation matching API structure  
✅ **Method metadata** - Scopes, parameters, request/response in one place  
✅ **Type-safe** - Generate Pydantic models with full validation  
✅ **Version controlled** - YAML diffs show API changes  
✅ **IDE support** - Auto-complete for all fields and types  
✅ **Reusable** - Share across projects without manual typing  
✅ **Security-first** - Explicit OAuth scope documentation per method

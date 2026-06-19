# Google Client v2

Unified Google API client with service namespaces and credential caching.

**Design:** Thin client with service-specific helpers, no lazy imports, no I/O in service methods.

## Architecture

```
GoogleClient (core)
  ├── Credential caching per (scopes, subject)
  ├── Service caching per (api, version, scopes, subject)
  ├── Core methods: service(), execute(), paginate(), batch()
  └── Service namespaces (instantiated in __init__):
      ├── drive: Drive operations
      ├── sheets: Sheets operations
      └── directory: Admin Directory operations
```

**Key Design:**
- No circular imports (services use `TYPE_CHECKING`)
- Services instantiated in `__init__` (no lazy loading)
- Service methods build requests, client executes them
- Flexible subject/scopes (default or per-call override)

## Environment Setup

**Required environment variables:**
- `GOOGLE__SERVICE_ACCOUNT` - Service account JSON (no "subject" field needed)
- `GOOGLE_DEFAULT_ADMIN_EMAIL` - Default email to impersonate for domain-wide delegation

## Usage

### **Simple (default subject from env):**

```python
from shared_utilities.clients.google_client_v2 import GoogleClient

# Default subject from GOOGLE_DEFAULT_ADMIN_EMAIL env var
client = GoogleClient()

# Use default subject for all operations
files = client.drive.list_folder_files(folder_id="abc123")
metadata = client.drive.get_file(file_id="xyz789")
client.drive.rename_file(file_id="xyz789", new_name="New Name")

# Sheets operations
data = client.sheets.get_values(
    spreadsheet_id="abc123",
    range_name="Sheet1!A1:D10"
)

# Directory operations
groups = client.directory.list_groups()
members = client.directory.list_group_members(group_key="team@example.com")
```

### **Override subject per call:**

```python
# Use different subject for specific call
other_files = client.drive.list_folder_files(
    folder_id="abc123",
    subject="other@bigapplerecsports.com"
)
```

### **Override scopes:**

```python
from shared_utilities.clients.google_client_v2 import DriveScopes

# Use readwrite scope
client.drive.rename_file(
    file_id="xyz",
    new_name="Updated",
    scopes=[DriveScopes.readwrite]  # Explicit scope override
)
```

### **Raw service access (for custom queries):**

```python
# Bypass helpers for edge cases
drive_service = client.service(
    "drive", 
    "v3", 
    "joe@example.com", 
    [DriveScopes.readonly]
)

# Custom query
result = drive_service.files().list(
    q="name contains 'report' and mimeType = 'application/pdf'",
    fields="files(id,name,size)"
).execute()
```

---

## Service Methods

### **Drive**
- `list_folder_files(folder_id, subject?, scopes?, page_size?, fields?, include_trashed?)`
- `get_file(file_id, subject?, scopes?, fields?)`
- `rename_file(file_id, new_name, subject?, scopes?)`
- `delete_file(file_id, subject?, scopes?)`
- `create_label(name, parent_id?, subject?, scopes?)`

### **Sheets**
- `get_values(spreadsheet_id, range_name, subject?, scopes?)`
- `append_values(spreadsheet_id, range_name, values, subject?, scopes?)`
- `update_values(spreadsheet_id, range_name, values, subject?, scopes?)`
- `clear_values(spreadsheet_id, range_name, subject?, scopes?)`

### **Directory**
- `list_groups(customer?, subject?, scopes?, domain?)`
- `get_group(group_key, subject?, scopes?)`
- `list_group_members(group_key, subject?, scopes?)`

## Design Principles

1. **Small, focused methods** - Each does one thing clearly
2. **Request builders** - Services build requests, client executes
3. **Flexible defaults** - subject/scopes can be overridden per call
4. **No circular deps** - Services use TYPE_CHECKING
5. **Standard pattern** - Similar to modern API client libraries

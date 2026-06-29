"""Google API OAuth scope constants and defaults.

Scope Hierarchy & Best Practices:
- OAuth2 scopes must be declared when creating credentials (cannot be dynamic)
- For service accounts, prefer broader scopes over granular ones
- Credentials are cached per (api, version, scopes, subject) combination

Gmail Scope Hierarchy (broadest to narrowest):
  - full access (mail.google.com) > compose > send + modify > send > readonly
  - compose includes: send, modify, insert, settings.basic, settings.sharing
"""


class DirectoryScopes:
    groups_readonly = (
        "https://www.googleapis.com/auth/admin.directory.group.readonly"
    )
    groups_readwrite = (
        "https://www.googleapis.com/auth/admin.directory.group"
    )
    users_readonly = (
        "https://www.googleapis.com/auth/admin.directory.user.readonly"
    )
    users_readwrite = (
        "https://www.googleapis.com/auth/admin.directory.user"
    )
    orgunit_readonly = (
        "https://www.googleapis.com/auth/admin.directory.orgunit.readonly"
    )
    domain_readonly = (
        "https://www.googleapis.com/auth/admin.directory.domain.readonly"
    )


class SheetsScopes:
    readonly = "https://www.googleapis.com/auth/spreadsheets.readonly"
    readwrite = "https://www.googleapis.com/auth/spreadsheets"


class DriveScopes:
    readonly = "https://www.googleapis.com/auth/drive.readonly"
    readwrite = "https://www.googleapis.com/auth/drive"
    metadata_readonly = (
        "https://www.googleapis.com/auth/drive.metadata.readonly"
    )


class GmailScopes:
    full_access = "https://mail.google.com/"
    readonly = "https://www.googleapis.com/auth/gmail.readonly"
    compose = "https://www.googleapis.com/auth/gmail.compose"
    send = "https://www.googleapis.com/auth/gmail.send"
    modify = "https://www.googleapis.com/auth/gmail.modify"
    metadata = "https://www.googleapis.com/auth/gmail.metadata"
    settings_basic = "https://www.googleapis.com/auth/gmail.settings.basic"
    settings_sharing = "https://www.googleapis.com/auth/gmail.settings.sharing"
    addons_current_action_compose = (
        "https://www.googleapis.com/auth/gmail.addons.current.action.compose"
    )
    addons_current_message_action = (
        "https://www.googleapis.com/auth/gmail.addons.current.message.action"
    )
    addons_current_message_metadata = (
        "https://www.googleapis.com/auth/gmail.addons.current.message.metadata"
    )
    addons_current_message_readonly = (
        "https://www.googleapis.com/auth/gmail.addons.current.message.readonly"
    )


class CalendarScopes:
    readonly = "https://www.googleapis.com/auth/calendar.readonly"
    readwrite = "https://www.googleapis.com/auth/calendar"


class ScriptsScopes:
    projects = "https://www.googleapis.com/auth/script.projects"
    deployments = "https://www.googleapis.com/auth/script.deployments"


DEFAULT_SCOPES: dict[str, list[str]] = {
    "gmail": [GmailScopes.full_access],
    "drive": [DriveScopes.readonly],
    "calendar": [CalendarScopes.readonly],
    "sheets": [SheetsScopes.readonly],
    "admin": [DirectoryScopes.users_readonly],
    "script": [ScriptsScopes.projects],
}

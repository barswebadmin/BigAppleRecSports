"""Google API OAuth scope constants."""


class DirectoryScopes:
    """Admin Directory API scopes."""
    groups_readonly = "https://www.googleapis.com/auth/admin.directory.group.readonly"
    groups_readwrite = "https://www.googleapis.com/auth/admin.directory.group"
    users_readonly = "https://www.googleapis.com/auth/admin.directory.user.readonly"
    users_readwrite = "https://www.googleapis.com/auth/admin.directory.user"
    orgunit_readonly = "https://www.googleapis.com/auth/admin.directory.orgunit.readonly"
    domain_readonly = "https://www.googleapis.com/auth/admin.directory.domain.readonly"


class SheetsScopes:
    """Google Sheets API scopes."""
    readonly = "https://www.googleapis.com/auth/spreadsheets.readonly"
    readwrite = "https://www.googleapis.com/auth/spreadsheets"


class DriveScopes:
    """Google Drive API scopes."""
    readonly = "https://www.googleapis.com/auth/drive.readonly"
    readwrite = "https://www.googleapis.com/auth/drive"
    metadata_readonly = "https://www.googleapis.com/auth/drive.metadata.readonly"


class GmailScopes:
    """Gmail API scopes."""
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
    """Google Calendar API scopes."""
    readonly = "https://www.googleapis.com/auth/calendar.readonly"
    readwrite = "https://www.googleapis.com/auth/calendar"


class ScriptsScopes:
    """Apps Script API scopes."""
    projects = "https://www.googleapis.com/auth/script.projects"
    deployments = "https://www.googleapis.com/auth/script.deployments"

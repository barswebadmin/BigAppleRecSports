"""Google API scopes for different services."""


class DirectoryScopes:
    """Google Directory API scopes with dot notation access."""
    
    # Group scopes
    groups_readonly = "https://www.googleapis.com/auth/admin.directory.group.readonly"
    groups_readwrite = "https://www.googleapis.com/auth/admin.directory.group"
    
    # User scopes
    users_readonly = "https://www.googleapis.com/auth/admin.directory.user.readonly"
    users_readwrite = "https://www.googleapis.com/auth/admin.directory.user"
    
    # Organization unit scopes
    orgunit_readonly = "https://www.googleapis.com/auth/admin.directory.orgunit.readonly"
    orgunit_readwrite = "https://www.googleapis.com/auth/admin.directory.orgunit"
    
    # Domain scopes
    domain_readonly = "https://www.googleapis.com/auth/admin.directory.domain.readonly"
    domain_readwrite = "https://www.googleapis.com/auth/admin.directory.domain"


class SheetsScopes:
    """Google Sheets API scopes with dot notation access."""
    
    readonly = "https://www.googleapis.com/auth/spreadsheets.readonly"
    readwrite = "https://www.googleapis.com/auth/spreadsheets"


class DriveScopes:
    """Google Drive API scopes with dot notation access."""
    
    readonly = "https://www.googleapis.com/auth/drive.readonly"
    readwrite = "https://www.googleapis.com/auth/drive"
    metadata_readonly = "https://www.googleapis.com/auth/drive.metadata.readonly"


class GmailScopes:
    """Gmail API scopes with dot notation access."""
    
    readonly = "https://www.googleapis.com/auth/gmail.readonly"
    compose = "https://www.googleapis.com/auth/gmail.compose"
    send = "https://www.googleapis.com/auth/gmail.send"


class ScriptsScopes:
    """Google Apps Script API scopes with dot notation access."""
    
    projects = "https://www.googleapis.com/auth/script.projects"
    deployments = "https://www.googleapis.com/auth/script.deployments"
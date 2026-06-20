"""Directory API service namespace with focused, modular methods."""

from typing import TYPE_CHECKING

from ..scopes import DirectoryScopes

if TYPE_CHECKING:
    from ..client import GoogleClient


class Directory:
    """Admin Directory API operations namespace."""
    
    def __init__(self, client: "GoogleClient"):
        self.client = client
    
    def list_groups(
        self,
        customer: str = "my_customer",
        subject: str | None = None,
        scopes: list[str] | None = None,
        domain: str | None = None,
    ) -> list[dict]:
        """List all groups in the domain with automatic pagination.
        
        Args:
            customer: Customer ID (default: "my_customer" for current domain)
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: groups_readonly)
            domain: Filter by domain (optional)
        
        Returns:
            List of group dicts
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DirectoryScopes.groups_readonly]
        
        admin_service = self.client.service("admin", "directory_v1", subject, scopes)
        
        params = {"customer": customer}
        if domain:
            params["domain"] = domain
        
        return self.client.paginate(
            admin_service.groups().list,
            result_key="groups",
            scopes=scopes,
            **params
        )
    
    def get_group(
        self,
        group_key: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict:
        """Get group details.
        
        Args:
            group_key: Group email or ID
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: groups_readonly)
        
        Returns:
            Group metadata dict
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DirectoryScopes.groups_readonly]
        
        admin_service = self.client.service("admin", "directory_v1", subject, scopes)
        
        return self.client.execute(
            admin_service.groups().get(groupKey=group_key),
            scopes=scopes,
        )
    
    def list_group_members(
        self,
        group_key: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> list[dict]:
        """List all members of a group with automatic pagination.
        
        Args:
            group_key: Group email or ID
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: groups_readonly)
        
        Returns:
            List of member dicts
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DirectoryScopes.groups_readonly]
        
        admin_service = self.client.service("admin", "directory_v1", subject, scopes)
        
        return self.client.paginate(
            admin_service.members().list,
            result_key="members",
            scopes=scopes,
            groupKey=group_key,
        )

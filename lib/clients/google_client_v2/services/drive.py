"""Drive API service namespace with focused, modular methods."""

from typing import TYPE_CHECKING, Any

from ..scopes import DriveScopes

if TYPE_CHECKING:
    from ..client import GoogleClient


class Drive:
    """Drive API operations namespace.

    All methods are small, focused operations that delegate to the client.
    """

    def __init__(self, client: "GoogleClient"):
        self.client = client

    def list_folder_files(
        self,
        folder_id: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
        page_size: int = 100,
        fields: str | None = None,
        include_trashed: bool = False,
    ) -> list[dict]:
        """List all files in a folder with automatic pagination.

        Args:
            folder_id: Google Drive folder ID
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readonly)
            page_size: Results per page (default: 100)
            fields: Custom field selection (default: id,name,mimeType,createdTime,modifiedTime,size)
            include_trashed: Include trashed files (default: False)

        Returns:
            List of file metadata dicts
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DriveScopes.readonly]
        fields = fields or "id,name,mimeType,createdTime,modifiedTime,size"

        query_parts = [f"'{folder_id}' in parents"]
        if not include_trashed:
            query_parts.append("trashed = false")

        drive_service = self.client.service("drive", "v3", subject, scopes)

        return self.client.paginate(
            drive_service.files().list,
            result_key="files",
            scopes=scopes,
            q=" and ".join(query_parts),
            pageSize=page_size,
            fields=f"nextPageToken, files({fields})",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        )

    def get_file(
        self,
        file_id: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
        fields: str = "*",
    ) -> dict:
        """Get detailed file metadata.

        Args:
            file_id: Google Drive file/folder ID
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readonly)
            fields: Field selection (default: all fields)

        Returns:
            File metadata dict
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DriveScopes.readonly]

        drive_service = self.client.service("drive", "v3", subject, scopes)

        return self.client.execute(
            drive_service.files().get(
                fileId=file_id,
                fields=fields if fields != "*" else None,
                supportsAllDrives=True
            ),
            scopes=scopes,
        )

    def rename_file(
        self,
        file_id: str,
        new_name: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict:
        """Rename a file or folder.

        Args:
            file_id: Google Drive file/folder ID
            new_name: New name for the file
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readwrite)

        Returns:
            Updated file metadata dict
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DriveScopes.readwrite]

        drive_service = self.client.service("drive", "v3", subject, scopes)

        return self.client.execute(
            drive_service.files().update(
                fileId=file_id,
                body={"name": new_name},
                supportsAllDrives=True
            ),
            scopes=scopes,
        )

    def delete_file(
        self,
        file_id: str,
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> None:
        """Delete a file (move to trash).

        Args:
            file_id: Google Drive file/folder ID
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readwrite)
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DriveScopes.readwrite]

        drive_service = self.client.service("drive", "v3", subject, scopes)

        self.client.execute(
            drive_service.files().delete(
                fileId=file_id,
                supportsAllDrives=True
            ),
            scopes=scopes,
        )

    def create_label(
        self,
        name: str,
        parent_id: str | None = None,
        subject: str | None = None,
        scopes: list[str] | None = None,
    ) -> dict:
        """Create a new folder.

        Args:
            name: Folder name
            parent_id: Parent folder ID (None for root)
            subject: Email to impersonate (uses client default if not provided)
            scopes: Override scopes (default: readwrite)

        Returns:
            Created folder metadata dict
        """
        subject = subject or self.client.default_subject
        scopes = scopes or [DriveScopes.readwrite]

        body: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            body["parents"] = [parent_id]

        drive_service = self.client.service("drive", "v3", subject, scopes)

        return self.client.execute(
            drive_service.files().create(
                body=body,
                fields="id,name,mimeType,createdTime",
                supportsAllDrives=True
            ),
            scopes=scopes,
        )

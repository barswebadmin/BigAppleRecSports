"""Tests for Google Sheets Client."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from googleapiclient.errors import HttpError

from modules.integrations.google.sheets_client import GoogleSheetsClient


@pytest.fixture
def mock_credentials():
    """Mock Google service account credentials."""
    mock_creds = Mock()
    mock_creds.service_account_email = "test-service@project.iam.gserviceaccount.com"
    return mock_creds


@pytest.fixture
def mock_sheets_service():
    """Mock Google Sheets API service."""
    mock_service = MagicMock()
    return mock_service


@pytest.fixture
def mock_config_with_valid_credentials(tmp_path):
    """Mock config with valid credentials file."""
    credentials_file = tmp_path / "test-credentials.json"
    credentials_file.write_text('{"type": "service_account"}')
    
    with patch('modules.integrations.google.sheets_client.config') as mock_config:
        mock_config.Google.service_account_path = credentials_file
        mock_config.Google.scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
        yield mock_config


class TestGoogleSheetsClientInitialization:
    """Test GoogleSheetsClient initialization."""
    
    def test_init_with_missing_credentials_file(self):
        """Should raise FileNotFoundError when credentials file doesn't exist."""
        with patch('modules.integrations.google.sheets_client.config') as mock_config:
            mock_config.Google.service_account_path = Path("/nonexistent/path.json")
            
            with pytest.raises(FileNotFoundError, match="Google service account credentials not found"):
                GoogleSheetsClient()
    
    def test_init_with_valid_credentials(
        self,
        mock_config_with_valid_credentials,
        mock_credentials,
        mock_sheets_service
    ):
        """Should initialize successfully with valid credentials."""
        with patch('modules.integrations.google.sheets_client.service_account.Credentials') as mock_creds_class:
            mock_creds_class.from_service_account_file.return_value = mock_credentials
            
            with patch('modules.integrations.google.sheets_client.build') as mock_build:
                mock_build.return_value = mock_sheets_service
                
                client = GoogleSheetsClient()
                
                assert client.service_account_email == "test-service@project.iam.gserviceaccount.com"
                mock_creds_class.from_service_account_file.assert_called_once()
                mock_build.assert_called_once_with('sheets', 'v4', credentials=mock_credentials)
    
    def test_init_with_invalid_credentials_format(self, mock_config_with_valid_credentials):
        """Should raise ValueError when credentials file is invalid."""
        with patch('modules.integrations.google.sheets_client.service_account.Credentials') as mock_creds_class:
            mock_creds_class.from_service_account_file.side_effect = ValueError("Invalid JSON")
            
            with pytest.raises(ValueError, match="Invalid Google service account credentials"):
                GoogleSheetsClient()


class TestFetchSheetAsCSV:
    """Test fetching sheet data."""
    
    @pytest.fixture
    def initialized_client(self, mock_config_with_valid_credentials, mock_credentials, mock_sheets_service):
        """Create an initialized GoogleSheetsClient."""
        with patch('modules.integrations.google.sheets_client.service_account.Credentials') as mock_creds_class:
            mock_creds_class.from_service_account_file.return_value = mock_credentials
            
            with patch('modules.integrations.google.sheets_client.build') as mock_build:
                mock_build.return_value = mock_sheets_service
                
                client = GoogleSheetsClient()
                client.service = mock_sheets_service
                return client
    
    def test_fetch_sheet_success(self, initialized_client):
        """Should fetch and return sheet data successfully."""
        mock_response = {
            'values': [
                ['Name', 'Email', 'Phone'],
                ['John Doe', 'john@example.com', '555-1234'],
                ['Jane Smith', 'jane@example.com', '555-5678']
            ]
        }
        
        initialized_client.service.spreadsheets().values().get().execute.return_value = mock_response
        
        result = initialized_client.fetch_sheet_as_csv("test-sheet-id")
        
        assert len(result) == 3
        assert result[0] == ['Name', 'Email', 'Phone']
        assert result[1] == ['John Doe', 'john@example.com', '555-1234']
    
    def test_fetch_sheet_empty(self, initialized_client):
        """Should return empty list when sheet has no data."""
        mock_response = {'values': []}
        
        initialized_client.service.spreadsheets().values().get().execute.return_value = mock_response
        
        result = initialized_client.fetch_sheet_as_csv("test-sheet-id")
        
        assert result == []
    
    def test_fetch_sheet_permission_denied(self, initialized_client):
        """Should raise PermissionError when access is denied (403)."""
        mock_error = Mock()
        mock_error.resp.status = 403
        mock_error.error_details = [{'reason': 'forbidden'}]
        
        initialized_client.service.spreadsheets().values().get().execute.side_effect = HttpError(
            mock_error.resp, b'Permission denied'
        )
        
        with pytest.raises(PermissionError, match="Access denied to spreadsheet"):
            initialized_client.fetch_sheet_as_csv("test-sheet-id")
    
    def test_fetch_sheet_not_found(self, initialized_client):
        """Should raise ValueError when spreadsheet is not found (404)."""
        mock_error = Mock()
        mock_error.resp.status = 404
        mock_error.error_details = [{'reason': 'notFound'}]
        
        initialized_client.service.spreadsheets().values().get().execute.side_effect = HttpError(
            mock_error.resp, b'Not found'
        )
        
        with pytest.raises(ValueError, match="Spreadsheet not found"):
            initialized_client.fetch_sheet_as_csv("invalid-sheet-id")
    
    def test_fetch_sheet_with_custom_range(self, initialized_client):
        """Should use custom range when specified."""
        mock_response = {'values': [['A1', 'B1'], ['A2', 'B2']]}
        
        initialized_client.service.spreadsheets().values().get().execute.return_value = mock_response
        
        result = initialized_client.fetch_sheet_as_csv("test-sheet-id", range_name="Sheet1!A1:B10")
        
        assert len(result) == 2
        initialized_client.service.spreadsheets().values().get.assert_called_with(
            spreadsheetId="test-sheet-id",
            range="Sheet1!A1:B10"
        )


class TestExtractSheetIDFromURL:
    """Test extracting spreadsheet ID from URLs."""
    
    @pytest.fixture
    def initialized_client(self, mock_config_with_valid_credentials, mock_credentials, mock_sheets_service):
        """Create an initialized GoogleSheetsClient."""
        with patch('modules.integrations.google.sheets_client.service_account.Credentials') as mock_creds_class:
            mock_creds_class.from_service_account_file.return_value = mock_credentials
            
            with patch('modules.integrations.google.sheets_client.build') as mock_build:
                mock_build.return_value = mock_sheets_service
                
                return GoogleSheetsClient()
    
    @pytest.mark.parametrize("url,expected_id", [
        (
            "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit",
            "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
        ),
        (
            "https://docs.google.com/spreadsheets/d/ABC123DEF456/edit#gid=0",
            "ABC123DEF456"
        ),
        (
            "https://docs.google.com/spreadsheets/d/TEST-ID-789/edit?usp=sharing",
            "TEST-ID-789"
        ),
        ("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms", "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"),
    ])
    def test_extract_sheet_id_valid_urls(self, initialized_client, url, expected_id):
        """Should extract sheet ID from various valid URL formats."""
        result = initialized_client.extract_sheet_id_from_url(url)
        assert result == expected_id
    
    @pytest.mark.parametrize("invalid_url", [
        "https://docs.google.com/document/d/ABC123/edit",
        "https://drive.google.com/file/d/ABC123/view",
        "not-a-url-at-all",
        "https://docs.google.com/spreadsheets/",
    ])
    def test_extract_sheet_id_invalid_urls(self, initialized_client, invalid_url):
        """Should handle invalid URLs gracefully."""
        if "/spreadsheets/d/" not in invalid_url:
            result = initialized_client.extract_sheet_id_from_url(invalid_url)
            assert result == invalid_url.strip()
        else:
            with pytest.raises(ValueError, match="Invalid Google Sheets URL format"):
                initialized_client.extract_sheet_id_from_url(invalid_url)


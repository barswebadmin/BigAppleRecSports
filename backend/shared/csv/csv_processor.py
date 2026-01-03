"""
General CSV processing utilities.
This module provides reusable CSV processing functionality that can be used across different services.
"""

from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import re

from shared.validators import validate_email_format


class CSVProcessor:
    """General CSV processing utilities."""
    
    def _has_min_rows(self, csv_data: List[List[str]], min_rows: int = 2) -> bool:
        """Check if CSV has minimum required rows."""
        return bool(csv_data and len(csv_data) >= min_rows)
    
    def _is_valid_and_normalize_email(self, email: str) -> Optional[str]:
        """
        Validate and normalize an email address.
        
        Returns:
            Normalized email (lowercase, stripped) if valid, None otherwise
        """
        if not email or "@" not in email:
            return None
        
        email_clean = email.strip()
        if validate_email_format(email_clean)["success"]:
            return email_clean.lower()
        
        return None
    
    def _collect_unique_emails(self, emails: List[str]) -> List[str]:
        """Remove duplicates while preserving order."""
        seen: Set[str] = set()
        unique = []
        for email in emails:
            if email not in seen:
                seen.add(email)
                unique.append(email)
        return unique
    
    def _find_email_column_indices(self, headers: List[str], keywords: Optional[List[str]] = None) -> List[int]:
        """Find column indices that match email keywords."""
        if keywords is None:
            keywords = ['personal email']
        
        indices = []
        for i, header in enumerate(headers):
            if header and any(keyword in header.lower() for keyword in keywords):
                indices.append(i)
        return indices
    
    def _extract_email_from_cell(self, cell: str) -> Optional[str]:
        """Extract and validate email from a single cell."""
        if not cell:
            return None
        return self._is_valid_and_normalize_email(cell.strip())
    
    def _extract_emails_from_columns(
        self,
        data_rows: List[List[str]],
        column_indices: List[int]
    ) -> List[str]:
        """Extract emails from specific columns."""
        emails = []
        for row in data_rows:
            for col_index in column_indices:
                if col_index < len(row):
                    email = self._extract_email_from_cell(row[col_index])
                    if email:
                        emails.append(email)
        return emails
    
    def _scan_all_cells_for_emails(self, data_rows: List[List[str]]) -> List[str]:
        """Scan all cells in data rows for valid emails."""
        emails = []
        for row in data_rows:
            for cell in row:
                email = self._extract_email_from_cell(cell)
                if email:
                    emails.append(email)
        return emails
    
    def process_csv_input(self, csv_data: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Convert CSV data to a list of objects for processing.
        
        Args:
            csv_data: List of rows, where each row is a list of strings
            
        Returns:
            List of dictionaries representing each row
        """
        if not self._has_min_rows(csv_data):
            return []
        
        headers = [header.strip().lower() for header in csv_data[0]]
        
        objects = []
        for row in csv_data[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue
            
            obj = {
                headers[i]: value.strip() if value else ""
                for i, value in enumerate(row)
                if i < len(headers)
            }
            objects.append(obj)
        
        return objects
    
    def extract_emails_from_objects(
        self,
        objects: List[Dict[str, Any]],
        email_column: str = "personal email"
    ) -> List[str]:
        """
        Extract unique email addresses from a list of objects.
        
        Args:
            objects: List of dictionaries representing CSV rows
            email_column: Name of the column containing email addresses
            
        Returns:
            List of unique email addresses
        """
        emails = {
            self._is_valid_and_normalize_email(obj.get(email_column, ""))
            for obj in objects
        }
        return [email for email in emails if email is not None]
    
    def extract_emails_from_csv(self, csv_data: List[List[str]]) -> List[str]:
        """
        Extract email addresses from CSV data.
        Looks for columns that might contain emails and extracts valid email addresses.
        """
        if not self._has_min_rows(csv_data):
            return []
        
        headers = csv_data[0]
        data_rows = csv_data[1:]
        
        email_column_indices = self._find_email_column_indices(headers)
        
        emails = (
            self._extract_emails_from_columns(data_rows, email_column_indices)
            if email_column_indices
            else self._scan_all_cells_for_emails(data_rows)
        )
        
        return self._collect_unique_emails(emails)
    
    def get_csv_info(self, csv_data: List[List[str]]) -> Dict[str, Any]:
        """
        Get information about CSV structure and content.
        
        Args:
            csv_data: List of rows, where each row is a list of strings
            
        Returns:
            Dictionary with CSV information
        """
        if not csv_data:
            return {
                "total_rows": 0,
                "data_rows_count": 0,
                "total_columns": 0,
                "email_columns": []
            }
        
        headers = csv_data[0]
        email_keywords = ["email", "mail", "e-mail"]
        
        email_columns = [
            {
                "index": i,
                "name": header.strip(),
                "type": "email"
            }
            for i, header in enumerate(headers)
            if header and any(keyword in header.strip().lower() for keyword in email_keywords)
        ]
        
        return {
            "total_rows": len(csv_data),
            "data_rows_count": max(0, len(csv_data) - 1),
            "total_columns": len(headers),
            "email_columns": email_columns
        }
    
    def extract_year_from_title(self, title: str) -> Optional[int]:
        """
        Extract year from a title string.
        
        Args:
            title: Title string that may contain a year
            
        Returns:
            Year as integer if found, None otherwise
        """
        if not title:
            return None
        
        matches = re.findall(r'\b(20\d{2})\b', title)
        return max((int(year) for year in matches), default=None) if matches else None
    
    def filter_valid_emails(self, emails: List[str]) -> List[str]:
        """
        Filter a list of emails to only include valid ones.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of valid email addresses
        """
        return [
            normalized
            for email in emails
            if (normalized := self._is_valid_and_normalize_email(email))
        ]
    
    def extract_column_values(self, csv_data: List[List[str]], column_index: int) -> List[str]:
        """
        Extract all non-empty values from a specific column.
        
        Args:
            csv_data: List of rows, where each row is a list of strings
            column_index: Zero-based column index (e.g., 5 for column F)
            
        Returns:
            List of non-empty values from the specified column (excluding header)
        """
        if not self._has_min_rows(csv_data):
            return []
        
        return [
            value
            for row in csv_data[1:]
            if column_index < len(row)
            and (value := row[column_index].strip())
        ]

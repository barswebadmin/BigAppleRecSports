"""
General CSV processing utilities.
This module provides reusable CSV processing functionality that can be used across different services.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import re


class CSVProcessor:
    """General CSV processing utilities."""
    
    def process_csv_input(self, csv_data: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Convert CSV data to a list of objects for processing.
        
        Args:
            csv_data: List of rows, where each row is a list of strings
            
        Returns:
            List of dictionaries representing each row
        """
        if not csv_data or len(csv_data) < 2:
            return []
        
        # First row is headers
        headers = [header.strip().lower() for header in csv_data[0]]
        
        # Process data rows
        objects = []
        for row in csv_data[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue  # Skip empty rows
            
            # Create object with headers as keys
            obj = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    obj[headers[i]] = value.strip() if value else ""
            
            objects.append(obj)
        
        return objects
    
    def extract_emails_from_objects(self, objects: List[Dict[str, Any]], email_column: str = "personal email") -> List[str]:
        """
        Extract unique email addresses from a list of objects.
        
        Args:
            objects: List of dictionaries representing CSV rows
            email_column: Name of the column containing email addresses
            
        Returns:
            List of unique email addresses
        """
        emails = set()
        
        for obj in objects:
            email_value = obj.get(email_column, "").strip()
            if email_value and "@" in email_value:
                # Basic email validation
                if self._is_valid_email(email_value):
                    emails.add(email_value.lower())
        
        return list(emails)
    
    def extract_emails_from_csv(self, csv_data: List[List[str]]) -> List[str]:
        """
        Extract email addresses from CSV data.
        Looks for columns that might contain emails and extracts valid email addresses.
        """
        if not csv_data or len(csv_data) < 2:  # Need at least header + 1 data row
            return []
        
        headers = csv_data[0]
        data_rows = csv_data[1:]
        
        # Find email column(s) - look for column headers that suggest emails
        email_column_indices = []
        for i, header in enumerate(headers):
            if header and any(keyword in header.lower() for keyword in ['personal email']):
                email_column_indices.append(i)
        
        emails = []
        
        # If we found explicit email columns, use those
        if email_column_indices:
            for row in data_rows:
                for col_index in email_column_indices:
                    if col_index < len(row) and row[col_index]:
                        email = row[col_index].strip()
                        if self._is_valid_email(email):
                            emails.append(email.lower())
        else:
            # If no explicit email columns, scan all columns for email-like values
            for row in data_rows:
                for cell in row:
                    if cell and self._is_valid_email(cell.strip()):
                        emails.append(cell.strip().lower())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_emails = []
        for email in emails:
            if email not in seen:
                seen.add(email)
                unique_emails.append(email)
        
        return unique_emails
    
    def _is_valid_email(self, email: str) -> bool:
        """
        Basic email validation.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email appears valid, False otherwise
        """
        # Basic regex for email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(email_pattern, email) is not None
    
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
        
        total_rows = len(csv_data)
        data_rows_count = max(0, total_rows - 1)  # Subtract header row
        total_columns = len(csv_data[0]) if csv_data else 0
        
        # Detect email columns
        email_columns = []
        if csv_data and len(csv_data) > 0:
            headers = csv_data[0]
            for i, header in enumerate(headers):
                header_lower = header.strip().lower()
                if any(keyword in header_lower for keyword in ["email", "mail", "e-mail"]):
                    email_columns.append({
                        "index": i,
                        "name": header.strip(),
                        "type": "email"
                    })
        
        return {
            "total_rows": total_rows,
            "data_rows_count": data_rows_count,
            "total_columns": total_columns,
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
        
        # Look for 4-digit years
        year_pattern = r'\b(20\d{2})\b'
        matches = re.findall(year_pattern, title)
        
        if matches:
            # Return the most recent year found
            years = [int(year) for year in matches]
            return max(years)
        
        return None
    
    def filter_valid_emails(self, emails: List[str]) -> List[str]:
        """
        Filter a list of emails to only include valid ones.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of valid email addresses
        """
        valid_emails = []
        for email in emails:
            if email and email.strip() and "@" in email.strip():
                email_clean = email.strip()
                if self._is_valid_email(email_clean):
                    valid_emails.append(email_clean.lower())
        
        return valid_emails
    
    def extract_column_values(self, csv_data: List[List[str]], column_index: int) -> List[str]:
        """
        Extract all non-empty values from a specific column.
        
        Args:
            csv_data: List of rows, where each row is a list of strings
            column_index: Zero-based column index (e.g., 5 for column F)
            
        Returns:
            List of non-empty values from the specified column (excluding header)
        """
        if not csv_data or len(csv_data) < 2:
            return []
        
        values = []
        for row in csv_data[1:]:
            if column_index < len(row):
                value = row[column_index].strip()
                if value:
                    values.append(value)
        
        return values



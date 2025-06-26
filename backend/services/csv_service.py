import re
from typing import List, Dict, Any, Optional

class CSVService:
    def __init__(self):
        pass
    
    def process_csv_input(self, csv_data: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Convert CSV data into an array of objects for reusable processing.
        Each row becomes an object with column headers as keys.
        
        Returns:
            List of dictionaries where each dict represents a row with header->value mapping
        """
        if not csv_data or len(csv_data) < 2:  # Need at least header + 1 data row
            return []
        
        headers = csv_data[0]
        data_rows = csv_data[1:]
        
        # Convert each row to an object
        objects = []
        for row in data_rows:
            row_object = {}
            for i, header in enumerate(headers):
                # Use header as key, handle cases where row might be shorter than headers
                value = row[i] if i < len(row) else ""
                # Clean up header names (strip whitespace, handle None)
                clean_header = str(header).strip() if header else f"column_{i}"
                row_object[clean_header] = str(value).strip() if value else ""
            objects.append(row_object)
        
        return objects
    
    def extract_emails_from_objects(self, objects: List[Dict[str, Any]], email_column_name: str = "personal email") -> List[str]:
        """
        Extract emails from array of objects based on column name.
        Looks for the specified column name (case-insensitive).
        
        Args:
            objects: Array of objects (from process_csv_input)
            email_column_name: Column name to look for (default: "personal email")
        
        Returns:
            List of valid email addresses
        """
        emails = []
        email_column_name_lower = email_column_name.lower()
        
        for obj in objects:
            # Find the email column (case-insensitive)
            email_value = None
            for key, value in obj.items():
                if key.lower() == email_column_name_lower:
                    email_value = value
                    break
            
            # Validate and add email
            if email_value and self._is_valid_email(email_value):
                emails.append(email_value.lower())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_emails = []
        for email in emails:
            if email not in seen:
                seen.add(email)
                unique_emails.append(email)
        
        return unique_emails

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
        """Simple email validation"""
        if not email or '@' not in email:
            return False
        
        # Basic email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))
    
    def extract_year_from_title(self, title: str) -> Optional[int]:
        """Extract year from spreadsheet title"""
        if not title:
            return None
        
        # Look for 4-digit year at the beginning of the title
        match = re.match(r'^(\d{4})', title.strip())
        if match:
            return int(match.group(1))
        
        # Look for 4-digit year anywhere in the title
        year_match = re.search(r'\b(\d{4})\b', title)
        if year_match:
            year = int(year_match.group(1))
            # Validate it's a reasonable year (e.g., between 2020 and 2030)
            if 2020 <= year <= 2030:
                return year
        
        return None
    
    def get_csv_info(self, csv_data: List[List[str]]) -> Dict[str, Any]:
        """Get information about the CSV data structure"""
        if not csv_data:
            return {
                "total_rows": 0,
                "total_columns": 0,
                "headers": [],
                "email_columns": [],
                "sample_data": []
            }
        
        headers = csv_data[0] if csv_data else []
        data_rows = csv_data[1:] if len(csv_data) > 1 else []
        
        # Find email columns
        email_columns = []
        for i, header in enumerate(headers):
            if header and any(keyword in header.lower() for keyword in ['personal email']):
                email_columns.append({"index": i, "name": header})
        
        # Get sample data (first 3 rows)
        sample_data = data_rows[:3] if data_rows else []
        
        return {
            "total_rows": len(csv_data),
            "total_columns": len(headers),
            "headers": headers,
            "email_columns": email_columns,
            "sample_data": sample_data,
            "data_rows_count": len(data_rows)
        } 
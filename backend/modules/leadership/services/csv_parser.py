"""
Leadership CSV Parser Service.

Extracts leadership hierarchy from CSV data with NO Slack dependencies.
"""
import re
from typing import List, Dict, Optional, Tuple, Any

from modules.leadership.domain.models import LeadershipMember, LeadershipHierarchy
from modules.leadership.domain.csv_patterns import CSVPatternRegistry
from shared.csv import clean_unicode_control_chars, to_snake_case, find_column


class LeadershipCSVParser:
    """Parse CSV data into leadership hierarchy structure."""
    
    def __init__(self):
        self.pattern_registry = CSVPatternRegistry.create_default()
    
    def parse(self, csv_data: List[List[str]]) -> LeadershipHierarchy:
        """Parse CSV data into LeadershipHierarchy domain model."""
        if not csv_data:
            raise ValueError("CSV data is empty")
        
        header_row_idx = self.find_header_row(csv_data)
        if header_row_idx is None:
            raise ValueError("Could not find header row")
        
        header_row = csv_data[header_row_idx]
        position_col, email_col = self.find_header_columns(header_row)
        
        if position_col is None or email_col is None:
            raise ValueError("Could not find required columns (POSITION, BARS EMAIL)")
        
        name_col = find_column(header_row, ["name"])
        if name_col is None:
            raise ValueError("Could not find required column: NAME")
        
        personal_email_col = find_column(header_row, ["personal email", "personal_email"])
        if personal_email_col is None:
            raise ValueError("Could not find required column: PERSONAL EMAIL")
        
        phone_col = find_column(header_row, ["phone"])
        if phone_col is None:
            raise ValueError("Could not find required column: PHONE")
        
        birthday_col = find_column(header_row, ["birthday", "date of birth"])
        if birthday_col is None:
            raise ValueError("Could not find required column: BIRTHDAY")
        
        hierarchy = LeadershipHierarchy()
        current_section = "executive_board"
        
        for row_idx, row in enumerate(csv_data[header_row_idx + 1:], start=header_row_idx + 1):
            if row_idx == header_row_idx or len(row) <= position_col:
                continue
            
            position_text = row[position_col].strip() if position_col < len(row) else ""
            name_text = row[name_col].strip() if name_col < len(row) else ""
            
            if not position_text and not name_text:
                continue
            
            detected_section = self.detect_section(position_text, name_text)
            if detected_section:
                current_section = detected_section
                continue
            
            if position_text.lower() == "position":
                continue
            
            if not position_text or not name_text:
                continue
            
            person = self.extract_personal_info(
                row, position_text,
                name_col=name_col,
                bars_email_col=email_col,
                personal_email_col=personal_email_col,
                phone_col=phone_col,
                birthday_col=birthday_col
            )
            
            if current_section == "committee_members":
                position_key = to_snake_case(position_text)
                member_data = person.model_dump(exclude_none=False)
                member_data["position"] = position_text
                member_data["position_key"] = position_key
                hierarchy.sections["committee_members"].append(member_data)
                continue
            
            matched = self._match_position_to_hierarchy(
                position_text, person, current_section, hierarchy
            )
        
        return hierarchy
    
    def find_header_row(self, csv_data: List[List[str]]) -> Optional[int]:
        """Find row index containing NAME header (POSITION optional for better error messages)."""
        for idx, row in enumerate(csv_data):
            row_str = " ".join(row).upper()
            if "NAME" in row_str:
                return idx
        return None
    
    def find_header_columns(self, header_row: List[str]) -> Tuple[Optional[int], Optional[int]]:
        """Find Position and BARS EMAIL column indices."""
        position_col = find_column(header_row, ["position"])
        
        bars_email_col = None
        for idx, cell in enumerate(header_row):
            cell_lower = cell.strip().lower()
            if "bars email" in cell_lower or "bars_email" in cell_lower:
                bars_email_col = idx
                break
        
        return position_col, bars_email_col
    
    def detect_section(self, position_text: str, name_text: str) -> Optional[str]:
        """Detect if row is a section header."""
        if name_text:
            return None
        
        position_upper = position_text.upper().strip()
        
        section_mappings = {
            "EXECUTIVE BOARD": "executive_board",
            "BOWLING LEADERSHIP TEAM": "bowling",
            "DODGEBALL LEADERSHIP TEAM": "dodgeball",
            "KICKBALL LEADERSHIP TEAM": "kickball",
            "PICKLEBALL LEADERSHIP TEAM": "pickleball",
            "COMMITTEE MEMBERS": "committee_members",
        }
        
        for keyword, section in section_mappings.items():
            if keyword in position_upper:
                return section
        
        if "CROSS" in position_upper and "SPORT" in position_upper:
            return "cross_sport"
        
        return None
    def extract_personal_info(
        self,
        row: List[str],
        position: str,
        name_col: int,
        bars_email_col: int,
        personal_email_col: int,
        phone_col: int,
        birthday_col: int
    ) -> LeadershipMember:
        """Extract LeadershipMember from CSV row."""
        name = row[name_col].strip() if name_col < len(row) else ""
        
        role_placeholder = to_snake_case(position) if position else "unknown.position"
        
        if name.lower().strip() == "vacant":
            return LeadershipMember(
                name="Vacant",
                personal_email="vacant@placeholder.com",
                role=role_placeholder
            )
        
        bars_email = row[bars_email_col].strip() if bars_email_col < len(row) else ""
        personal_email = row[personal_email_col].strip() if personal_email_col < len(row) else ""
        phone = row[phone_col].strip() if phone_col < len(row) else ""
        birthday = row[birthday_col].strip() if birthday_col < len(row) else ""
        
        if phone:
            phone = clean_unicode_control_chars(phone)
        if bars_email:
            bars_email = clean_unicode_control_chars(bars_email)
        if personal_email:
            personal_email = clean_unicode_control_chars(personal_email)
        
        return LeadershipMember(
            name=name,
            personal_email=personal_email or bars_email or "pending@placeholder.com",
            role=role_placeholder,
            bars_email=bars_email or None,
            phone=phone or None,
            birthday=birthday or None
        )
    
    def _match_position_to_hierarchy(
        self,
        position: str,
        person: LeadershipMember,
        section: str,
        hierarchy: LeadershipHierarchy
    ) -> bool:
        """Match position to hierarchy structure and add person."""
        role_key = self.pattern_registry.find_role_in_section(section, position)
        
        if not role_key:
            return False
        
        if "." in role_key:
            parts = role_key.split(".")
            if len(parts) == 2:
                sub_section, role = parts
                hierarchy.add_position(section, role, person, sub_section=sub_section)
            else:
                hierarchy.add_position(section, role_key, person, sub_section=parts[0])
        else:
            hierarchy.add_position(section, role_key, person)
        
        return True

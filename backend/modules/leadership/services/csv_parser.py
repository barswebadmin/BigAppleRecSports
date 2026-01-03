"""
Leadership CSV Parser Service.

Extracts leadership hierarchy from CSV data with NO Slack dependencies.
"""
import re
from typing import List, Dict, Optional, Tuple, Any

from modules.leadership.domain.models import PersonInfo, LeadershipHierarchy


class LeadershipCSVParser:
    """Parse CSV data into leadership hierarchy structure."""
    
    def __init__(self):
        self.position_patterns = self._build_all_patterns()
    
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
        
        name_col = self._find_column(header_row, ["name"])
        personal_email_col = self._find_column(header_row, ["personal email", "personal_email"])
        phone_col = self._find_column(header_row, ["phone"])
        birthday_col = self._find_column(header_row, ["birthday", "date of birth"])
        
        hierarchy = LeadershipHierarchy()
        current_section = "executive_board"
        
        for row_idx, row in enumerate(csv_data[header_row_idx + 1:], start=header_row_idx + 1):
            if row_idx == header_row_idx or len(row) <= position_col:
                continue
            
            position_text = row[position_col].strip() if position_col < len(row) else ""
            name_text = row[name_col].strip() if name_col is not None and name_col < len(row) else ""
            
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
            
            person = self.extract_person_data(
                row, position_text,
                name_col=name_col,
                bars_email_col=email_col,
                personal_email_col=personal_email_col,
                phone_col=phone_col,
                birthday_col=birthday_col
            )
            
            if current_section == "committee_members":
                position_key = self._to_snake_case(position_text)
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
        position_col = self._find_column(header_row, ["position"])
        
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
    
    def fuzzy_match(self, position: str, patterns: List) -> bool:
        """Fuzzy match position against patterns (any order, case-insensitive)."""
        position_lower = position.lower().strip()
        
        if patterns and isinstance(patterns[0], list):
            for term_group in patterns:
                if all(term.lower() in position_lower for term in term_group):
                    return True
            return False
        else:
            return all(term.lower() in position_lower for term in patterns)
    
    def exact_match(self, position: str, exact_value: str) -> bool:
        """Exact match (case-insensitive, whitespace-stripped)."""
        return position.lower().strip() == exact_value.lower().strip()
    
    def extract_person_data(
        self,
        row: List[str],
        position: str,
        name_col: int,
        bars_email_col: int,
        personal_email_col: Optional[int],
        phone_col: Optional[int],
        birthday_col: Optional[int]
    ) -> PersonInfo:
        """Extract PersonInfo from CSV row."""
        name = row[name_col].strip() if name_col < len(row) else ""
        
        if name.lower().strip() == "vacant":
            return PersonInfo(name="Vacant", bars_email="")
        
        bars_email = row[bars_email_col].strip() if bars_email_col < len(row) else ""
        personal_email = row[personal_email_col].strip() if personal_email_col is not None and personal_email_col < len(row) else None
        phone = row[phone_col].strip() if phone_col is not None and phone_col < len(row) else None
        birthday = row[birthday_col].strip() if birthday_col is not None and birthday_col < len(row) else None
        
        if phone:
            phone = self._clean_unicode_control_chars(phone)
        if bars_email:
            bars_email = self._clean_unicode_control_chars(bars_email)
        if personal_email:
            personal_email = self._clean_unicode_control_chars(personal_email)
        
        return PersonInfo(
            name=name,
            bars_email=bars_email or "",
            personal_email=personal_email or None,
            phone=phone or None,
            birthday=birthday or None
        )
    
    def _find_column(self, header_row: List[str], keywords: List[str]) -> Optional[int]:
        """Find column index matching any keyword."""
        for idx, cell in enumerate(header_row):
            cell_lower = cell.strip().lower()
            for keyword in keywords:
                if keyword.lower() in cell_lower:
                    return idx
        return None
    
    def _match_position_to_hierarchy(
        self,
        position: str,
        person: PersonInfo,
        section: str,
        hierarchy: LeadershipHierarchy
    ) -> bool:
        """Match position to hierarchy structure and add person."""
        if section not in self.position_patterns:
            return False
        
        patterns = self.position_patterns[section]
        position_lower = position.lower().strip()
        is_wtnb = "wtnb" in position_lower
        
        all_matches = []
        for key, pattern_def in patterns.items():
            if "exact" in pattern_def:
                if self.exact_match(position, pattern_def["exact"]):
                    all_matches.append((key, pattern_def, 1000, False))
            else:
                for role, terms in pattern_def.items():
                    if self.fuzzy_match(position, terms):
                        is_pattern_wtnb = "wtnb" in str(terms).lower()
                        specificity = len(terms) if not isinstance(terms[0], list) else len(terms[0])
                        if is_pattern_wtnb:
                            specificity += 500
                        all_matches.append((key, {role: terms}, specificity, is_pattern_wtnb))
        
        if not all_matches:
            return False
        
        all_matches.sort(key=lambda x: x[2], reverse=True)
        
        for match_key, match_pattern, _, is_pattern_wtnb in all_matches:
            if is_wtnb and not is_pattern_wtnb:
                continue
            
            if "exact" in match_pattern:
                hierarchy.add_position(section, match_key, person)
                return True
            else:
                for role, _ in match_pattern.items():
                    if "." in match_key:
                        parts = match_key.split(".")
                        if len(parts) == 2:
                            sub_section, role_key = parts
                            hierarchy.add_position(section, role_key, person, sub_section=sub_section)
                        else:
                            hierarchy.add_position(section, role, person, sub_section=match_key)
                    else:
                        hierarchy.add_position(section, match_key, person)
                    return True
        
        return False
    
    def _build_all_patterns(self) -> Dict[str, Any]:
        """Build all position patterns for matching."""
        return {
            "executive_board": self._build_executive_board_patterns(),
            "cross_sport": self._build_cross_sport_patterns(),
            "bowling": self._build_bowling_patterns(),
            "dodgeball": self._build_dodgeball_patterns(),
            "kickball": self._build_kickball_patterns(),
            "pickleball": self._build_pickleball_patterns(),
        }
    
    def _build_executive_board_patterns(self) -> Dict:
        """Build patterns for executive board positions."""
        return {
            "commissioner": {"exact": "commissioner"},
            "vice_commissioner": {"role": ["vice", "commissioner"]},
            "wtnb_commissioner": {"role": ["wtnb", "commissioner"]},
            "secretary": {"role": ["secretary"]},
            "treasurer": {"role": ["treasurer"]},
            "operations_commissioner": {"role": ["operations", "commissioner"]},
            "dei_commissioner": {"role": [["diversity", "commissioner"], ["dei", "commissioner"]]},
            "bowling_commissioner": {"role": ["bowling", "commissioner"]},
            "dodgeball_commissioner": {"role": ["dodgeball", "commissioner"]},
            "kickball_commissioner": {"role": ["kickball", "commissioner"]},
            "pickleball_commissioner": {"role": ["pickleball", "commissioner"]},
        }
    
    def _build_cross_sport_patterns(self) -> Dict:
        """Build patterns for cross-sport leadership."""
        return {
            "communications": {"role": ["communications"]},
            "events.open": {"role": ["events", "open"]},
            "events.wtnb": {"role": ["events", "wtnb"]},
            "dei.open": {"role": [["diversity", "open"], ["dei", "open"]]},
            "dei.wtnb": {"role": [["diversity", "wtnb"], ["dei", "wtnb"]]},
            "marketing": {"role": ["marketing"]},
            "philanthropy": {"role": ["philanthropy"]},
            "social_media.open": {"role": ["social media", "open"]},
            "social_media.wtnb": {"role": ["social media", "wtnb"]},
            "technology": {"role": ["technology"]},
            "permits_equipment": {"role": ["permits", "equipment"]},
        }
    
    def _build_bowling_patterns(self) -> Dict:
        """Build patterns for bowling teams."""
        return {
            "sunday.director": {"role": ["sunday", "director"]},
            "sunday.ops_manager": {"role": ["sunday", "operations manager"]},
            "monday_open.director": {"role": ["monday", "open", "director"]},
            "monday_open.ops_manager": {"role": ["monday", "open", "operations manager"]},
            "monday_wtnb.director": {"role": ["monday", "wtnb", "director"]},
            "monday_wtnb.ops_manager": {"role": ["monday", "wtnb", "operations manager"]},
            "player_experience.open": {"role": ["player experience", "open"]},
            "player_experience.wtnb": {"role": ["player experience", "wtnb"]},
        }
    
    def _build_dodgeball_patterns(self) -> Dict:
        """Build patterns for dodgeball teams."""
        return {
            "smallball_advanced.director": {"role": ["small ball", "advanced", "director"]},
            "smallball_advanced.ops_manager": {"role": ["small ball", "advanced", "operations manager"]},
            "smallball_social.director": {"role": ["small ball", "social", "director"]},
            "smallball_social.ops_manager": {"role": ["small ball", "social", "operations manager"]},
            "wtnb_draft.director": {"role": ["wtnb", "draft", "director"]},
            "wtnb_draft.ops_manager": {"role": ["wtnb", "draft", "operations manager"]},
            "wtnb_social.director": {"role": ["wtnb", "social", "director"]},
            "wtnb_social.ops_manager": {"role": ["wtnb", "social", "operations manager"]},
            "foamball.director": {"role": ["foam ball", "director"]},
            "foamball.ops_manager": {"role": ["foam ball", "operations manager"]},
            "bigball.director": {"role": ["big ball", "director"]},
            "bigball.ops_manager": {"role": ["big ball", "operations manager"]},
            "player_experience.open": {"role": ["player experience", "open"]},
            "player_experience.wtnb": {"role": ["player experience", "wtnb"]},
        }
    
    def _build_kickball_patterns(self) -> Dict:
        """Build patterns for kickball teams."""
        return {
            "sunday.director": {"role": ["sunday", "director"]},
            "sunday.ops_manager": {"role": ["sunday", "operations manager"]},
            "monday.director": {"role": [["monday", "director"], ["weekday", "social", "director"]]},
            "monday.ops_manager": {"role": [["monday", "operations manager"], ["weekday", "social", "operations manager"]]},
            "tuesday.director": {"role": ["tuesday", "director"]},
            "tuesday.ops_manager": {"role": ["tuesday", "operations manager"]},
            "draft_open.director": {"role": ["wednesday", "director"]},
            "draft_open.ops_manager": {"role": ["wednesday", "operations manager"]},
            "draft_wtnb.director": {"role": [["thursday", "director"], ["wtnb", "draft", "director"]]},
            "draft_wtnb.ops_manager": {"role": [["thursday", "operations manager"], ["wtnb", "draft", "operations manager"]]},
            "saturday_open.director": {"role": ["saturday", "open", "director"]},
            "saturday_open.ops_manager": {"role": ["saturday", "open", "operations manager"]},
            "saturday_wtnb.director": {"role": ["saturday", "wtnb", "director"]},
            "saturday_wtnb.ops_manager": {"role": ["saturday", "wtnb", "operations manager"]},
            "player_experience.open": {"role": ["player experience", "open"]},
            "player_experience.wtnb": {"role": ["player experience", "wtnb"]},
        }
    
    def _build_pickleball_patterns(self) -> Dict:
        """Build patterns for pickleball teams."""
        return {
            "advanced.director": {"role": ["advanced", "director"]},
            "advanced.ops_manager": {"role": ["advanced", "operations manager"]},
            "social.director": {"role": ["social", "director"]},
            "social.ops_manager": {"role": ["social", "operations manager"]},
            "wtnb.director": {"role": ["wtnb", "director"]},
            "wtnb.ops_manager": {"role": ["wtnb", "operations manager"]},
            "ladder.director": {"role": ["ladder", "director"]},
            "ladder.ops_manager": {"role": ["ladder", "operations manager"]},
            "player_experience.open": {"role": ["player experience", "open"]},
            "player_experience.wtnb": {"role": ["player experience", "wtnb"]},
        }
    
    def _clean_unicode_control_chars(self, text: str) -> str:
        """Remove invisible Unicode control characters."""
        return re.sub(r'[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e]', '', text)
    
    def _to_snake_case(self, text: str) -> str:
        """Convert string to snake_case."""
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', '_', text)
        return text.lower().strip('_')


from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup


@dataclass
class RoleEntry:
    name: str
    role: str


@dataclass
class GroupAssignment:
    sport: str
    night: Optional[str]
    division: Optional[str]
    role: str  # Director or Operations Manager
    person: str

    @property
    def group_key(self) -> str:
        # Normalize to tags like: dodgeball-monday-big-ball, bowling-sunday, etc.
        parts: List[str] = [self.sport.strip().lower()]
        if self.night:
            parts.append(self.night.strip().lower())
        if self.division:
            parts.append(self.division.strip().lower())
        return "-".join(parts)


class LeadershipContactScraper:
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "lxml")

    def parse(self) -> List[GroupAssignment]:
        assignments: List[GroupAssignment] = []

        # Sections are titled like "<h3><span class="text">Dodgeball Leadership Team</span></h3>"
        for title in self.soup.select(".halo-block-header .title .text"):
            text = (title.get_text(strip=True) or "")
            if not text.endswith("Leadership Team"):
                continue

            sport = text.replace("Leadership Team", "").strip()

            # Within the same section, there is a sibling banner-slider-component containing cards
            section = title.find_parent(class_="halo-block-header")
            if not section:
                continue

            container = section.find_next("banner-slider-component")
            if not container:
                continue

            for card in container.select(".policies-content"):
                name_el = card.select_one(".policies-text")
                role_el = card.select_one(".policies-des")
                if not name_el or not role_el:
                    continue

                person = name_el.get_text(strip=True)
                role_text = role_el.get_text(strip=True)

                # Examples:
                # Director of Dodgeball, Monday Big Ball
                # Operations Manager, Big Ball (Monday)
                role, night, division = self._parse_role_details(role_text)
                if role not in ("Director", "Operations Manager"):
                    # Skip other roles like Player Experience, Player Representative
                    continue

                assignments.append(
                    GroupAssignment(
                        sport=sport,
                        night=night,
                        division=division,
                        role=role,
                        person=person,
                    )
                )

        return assignments

    def _parse_role_details(self, role_text: str) -> Tuple[str, Optional[str], Optional[str]]:
        text = role_text
        role: str
        if text.lower().startswith("director of"):
            role = "Director"
            rest = text[len("Director of"):].strip()
        elif text.lower().startswith("operations manager"):
            role = "Operations Manager"
            rest = text[len("Operations Manager"):].lstrip(", ")
        else:
            return text, None, None

        # Normalize separators and parentheses
        rest = rest.replace(" (", ", ").replace(")", "")

        # Split on commas to find components like: Sport, Night Division OR Division (Night)
        parts = [p.strip() for p in rest.split(",") if p.strip()]

        # Remove leading sport name if present (e.g., "Dodgeball")
        if parts and parts[0].lower() in ("dodgeball", "bowling", "pickleball"):
            parts = parts[1:]

        night: Optional[str] = None
        division: Optional[str] = None

        if len(parts) == 1:
            # Could be "Sunday Small Ball" or just "Monday" or just "Big Ball"
            tokens = parts[0].split()
            if tokens and tokens[0].lower() in self._nights_index():
                night = tokens[0]
                division = " ".join(tokens[1:]) or None
            else:
                division = parts[0]
        elif len(parts) >= 2:
            # Common patterns: "Monday Big Ball" OR "Big Ball", "Monday"
            first, second = parts[0], parts[1]
            if first.split()[0].lower() in self._nights_index():
                night = first.split()[0]
                division = " ".join(first.split()[1:]) or None
            else:
                division = first
            if not night and second.split()[0].lower() in self._nights_index():
                night = second.split()[0]

        # Normalize values
        if night:
            night = night.capitalize()
        if division:
            division = division.replace("  ", " ").strip()

        return role, night, division

    @staticmethod
    def _nights_index() -> set:
        return {"sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"}


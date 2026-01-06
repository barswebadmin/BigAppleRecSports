"""
Leadership Results Formatter for Slack.

Converts domain analysis results into Slack-specific Block Kit messages.
This is part of the Integration Orchestrator layer - thin adapter between
domain logic and Slack transport.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from modules.leadership.domain.models import LeadershipHierarchy, LeadershipMember
from modules.integrations.slack.builders.generic_builders import GenericMessageBuilder
from shared.csv import cell_reference
from slack_sdk.models.blocks import Block


@dataclass
class FieldMissingDetail:
    """Details about a missing field with CSV location."""
    field: str
    cell: str
    value: str


@dataclass
class PositionStatus:
    """Status of a single position in the hierarchy."""
    path: str
    position: str
    name: Optional[str] = None
    fields_present: List[str] = field(default_factory=list)
    fields_missing: List[str] = field(default_factory=list)
    fields_missing_details: List[FieldMissingDetail] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Result of analyzing hierarchy completeness."""
    successes: List[PositionStatus] = field(default_factory=list)
    warnings: List[PositionStatus] = field(default_factory=list)
    failures: List[PositionStatus] = field(default_factory=list)
    vacant_positions: List[PositionStatus] = field(default_factory=list)


class LeadershipResultsFormatter:
    """
    Format leadership hierarchy analysis results for Slack display.
    
    Thin orchestrator that converts domain models into Slack Block Kit messages.
    Uses typed Slack SDK builders for compile-time safety.
    """
    
    def __init__(self, builder: Optional[GenericMessageBuilder] = None):
        """
        Initialize formatter with Slack builder.
        
        Args:
            builder: Optional GenericMessageBuilder instance (uses default if None)
        """
        self.builder = builder or GenericMessageBuilder()
    
    def analyze_completeness(
        self,
        hierarchy: LeadershipHierarchy,
        lookup_results: Dict[str, Optional[str]]
    ) -> AnalysisResult:
        """
        Analyze hierarchy completeness and categorize positions.
        
        Args:
            hierarchy: Leadership hierarchy domain model
            lookup_results: Dict of email -> slack_user_id (or None)
        
        Returns:
            AnalysisResult with categorized positions
        """
        analysis = AnalysisResult()
        
        def check_position(
            person: LeadershipMember,
            position_name: str,
            path: str,
            is_committee_member: bool = False
        ):
            """Check completeness of a single position."""
            if person.is_vacant():
                analysis.vacant_positions.append(
                    PositionStatus(path=path, position=position_name)
                )
                return
            
            slack_user_id = lookup_results.get(person.bars_email) if person.bars_email else None
            
            fields_present = []
            fields_missing = []
            fields_missing_details = []
            
            def add_missing_field(field_name: str, value: str, col_key: str):
                fields_missing.append(field_name)
                pydantic_extra = getattr(person, '__pydantic_extra__', {})
                csv_row = pydantic_extra.get('_csv_row')
                csv_columns = pydantic_extra.get('_csv_columns', {})
                if csv_row and col_key in csv_columns:
                    cell_ref_str = cell_reference(csv_row, csv_columns[col_key])
                    fields_missing_details.append(
                        FieldMissingDetail(
                            field=field_name,
                            cell=cell_ref_str,
                            value=value or "(empty)"
                        )
                    )
            
            if person.name:
                fields_present.append("name")
            else:
                add_missing_field("name", "", "name")
            
            if person.bars_email:
                fields_present.append("bars_email")
            else:
                add_missing_field("bars_email", "", "bars_email")
            
            if not is_committee_member:
                if slack_user_id:
                    fields_present.append("slack_user_id")
                else:
                    add_missing_field(
                        "slack_user_id",
                        f"(lookup failed for {person.bars_email})",
                        "bars_email"
                    )
                
                if person.personal_email:
                    fields_present.append("personal_email")
                else:
                    add_missing_field("personal_email", "", "personal_email")
                
                if person.phone:
                    fields_present.append("phone")
                else:
                    add_missing_field("phone", "", "phone")
                
                if person.birthday:
                    fields_present.append("birthday")
                else:
                    add_missing_field("birthday", "", "birthday")
            else:
                if slack_user_id:
                    fields_present.append("slack_user_id")
                if person.personal_email:
                    fields_present.append("personal_email")
                if person.phone:
                    fields_present.append("phone")
                if person.birthday:
                    fields_present.append("birthday")
            
            position_status = PositionStatus(
                path=path,
                position=position_name,
                name=person.name,
                fields_present=fields_present,
                fields_missing=fields_missing,
                fields_missing_details=fields_missing_details
            )
            
            if is_committee_member:
                if not person.name or not person.bars_email:
                    analysis.failures.append(position_status)
                elif len(fields_missing) == 0:
                    analysis.successes.append(position_status)
                else:
                    analysis.warnings.append(position_status)
            else:
                if not person.bars_email or not slack_user_id:
                    analysis.failures.append(position_status)
                elif len(fields_missing) == 0:
                    analysis.successes.append(position_status)
                else:
                    analysis.warnings.append(position_status)
        
        for vacant_key in hierarchy.vacant_positions:
            parts = vacant_key.split(".")
            position_name = parts[-1] if parts else "Unknown"
            analysis.vacant_positions.append(
                PositionStatus(path=vacant_key, position=position_name)
            )
        
        for section_name, section_data in hierarchy.sections.items():
            if section_name == "committee_members" and section_data:
                for idx, person_dict in enumerate(section_data):
                    person = LeadershipMember(**person_dict)
                    position_name = person_dict.get("position", "Committee Member")
                    check_position(person, position_name, f"committee_members[{idx}]", is_committee_member=True)
                continue
            
            if not isinstance(section_data, dict):
                continue
            
            for key, value in section_data.items():
                if not isinstance(value, dict):
                    continue
                
                if "name" in value:
                    person = LeadershipMember(**value)
                    position_name = value.get("position", key)
                    path = f"{section_name}.{key}"
                    check_position(person, position_name, path, is_committee_member=False)
                else:
                    team_key = key
                    team_data = value
                    for role_key, person_data in team_data.items():
                        if not isinstance(person_data, dict):
                            continue
                        
                        path = f"{section_name}.{team_key}.{role_key}"
                        
                        if isinstance(person_data, list):
                            for idx, p_dict in enumerate(person_data):
                                person = LeadershipMember(**p_dict)
                                position_name = p_dict.get("position", role_key)
                                check_position(person, position_name, f"{path}[{idx}]", is_committee_member=False)
                        else:
                            person = LeadershipMember(**person_data)
                            position_name = person_data.get("position", role_key)
                            check_position(person, position_name, path, is_committee_member=False)
        
        return analysis
    
    def format_results_for_slack(self, analysis: AnalysisResult) -> List[Block]:
        """
        Format analysis results as Slack blocks using typed SDK models.
        
        Args:
            analysis: AnalysisResult from analyze_completeness
        
        Returns:
            List of typed Slack Block objects
        """
        blocks: List[Block] = [
            self.builder.header("✅ Leadership Directory Processing Results"),
            self.builder.section(
                f"*Summary:*\n"
                f"✅ *{len(analysis.successes)}* complete (all fields found)\n"
                f"⚠️ *{len(analysis.warnings)}* partial (missing some fields)\n"
                f"❌ *{len(analysis.failures)}* failed (missing email or Slack user ID)\n"
                f"🔲 *{len(analysis.vacant_positions)}* vacant positions"
            )
        ]
        
        if analysis.warnings:
            warning_text = "*⚠️ Partial Matches (missing some fields):*\n"
            for item in analysis.warnings[:15]:
                name = item.name or "Unknown"
                position = item.position
                
                if item.fields_missing_details:
                    detail_lines = []
                    for detail in item.fields_missing_details:
                        detail_lines.append(
                            f"`{detail.field}` (cell {detail.cell}: {detail.value})"
                        )
                    missing_str = "\n    - " + "\n    - ".join(detail_lines)
                else:
                    missing_str = ", ".join(item.fields_missing)
                
                warning_text += f"• *{name}* - `{position}`{missing_str}\n"
            
            if len(analysis.warnings) > 15:
                warning_text += f"\n_...and {len(analysis.warnings) - 15} more_"
            
            blocks.append(self.builder.section(warning_text))
        
        if analysis.failures:
            failure_text = "*❌ Failed Matches (missing email or Slack user ID):*\n"
            for item in analysis.failures[:15]:
                name = item.name or "Unknown"
                position = item.position
                
                if item.fields_missing_details:
                    detail_lines = []
                    for detail in item.fields_missing_details:
                        detail_lines.append(
                            f"`{detail.field}` (cell {detail.cell}: {detail.value})"
                        )
                    missing_str = "\n    - " + "\n    - ".join(detail_lines)
                else:
                    missing_str = ", ".join(item.fields_missing)
                
                failure_text += f"• *{name}* - `{position}`{missing_str}\n"
            
            if len(analysis.failures) > 15:
                failure_text += f"\n_...and {len(analysis.failures) - 15} more_"
            
            blocks.append(self.builder.section(failure_text))
        
        if analysis.vacant_positions:
            vacant_text = "*🔲 Vacant Positions:*\n"
            for item in analysis.vacant_positions[:15]:
                vacant_text += f"• `{item.position}`\n"
            
            if len(analysis.vacant_positions) > 15:
                vacant_text += f"\n_...and {len(analysis.vacant_positions) - 15} more_"
            
            blocks.append(self.builder.section(vacant_text))
        
        blocks.append(
            self.builder.context(["📊 Full hierarchy saved to result.json."])
        )
        
        return blocks


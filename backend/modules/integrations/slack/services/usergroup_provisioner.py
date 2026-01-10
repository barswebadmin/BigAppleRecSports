"""
Slack Usergroup Bulk Provisioning Service.

Handles bulk usergroup synchronization operations for leadership transitions.
Preserves smart aggregation logic from leadership_slack_sync_cli.py.
"""
import re
from typing import Dict, List, Tuple, Set, Optional
import logging

from .usergroup_service import UsergroupService
from modules.leadership.domain.models import LeadershipHierarchy

logger = logging.getLogger(__name__)


def normalize_handle(text: str) -> str:
    """
    Normalize text to a valid Slack handle.
    
    Lowercase, replace non-alphanumeric with hyphens, collapse repeats.
    
    Args:
        text: Input text
        
    Returns:
        Normalized handle (e.g., "dodgeball-monday-big-ball")
    """
    t = text.strip().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    return t


class UsergroupProvisioner:
    """
    Bulk usergroup provisioning logic.
    
    Handles:
    - Building group plans from leadership hierarchy
    - Smart aggregation (sport-night-division → sport-night)
    - Create vs. Update detection
    - Dry-run mode
    - Diff reporting
    """
    
    def __init__(self, service: UsergroupService):
        """
        Initialize with UsergroupService.
        
        Args:
            service: Initialized UsergroupService for API operations
        """
        self.service = service
    
    def build_group_plans_from_hierarchy(
        self,
        hierarchy: LeadershipHierarchy,
        group_role_mapping: Optional[Dict[str, List[str]]] = None,
        overrides: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, List[str]]:
        """
        Build group membership plans from leadership hierarchy.
        
        This preserves the smart aggregation logic from leadership_slack_sync_cli:
        - Creates specific groups (dodgeball-monday-bigball)
        - Auto-aggregates to parent groups (dodgeball-monday, dodgeball)
        - Applies overrides for special cases
        
        Args:
            hierarchy: LeadershipHierarchy domain model
            group_role_mapping: Optional dict of role_key -> group_handles
                              (if not provided, infers from role structure)
            overrides: Optional dict of handle -> extra user IDs to add
            
        Returns:
            Dict of {group_handle: [slack_user_id, ...]}
        """
        plans: Dict[str, List[str]] = {}
        overrides = overrides or {}
        
        # Track aggregations: {(sport, night): [user_ids]}
        aggregates: Dict[Tuple[str, ...], Set[str]] = {}
        
        # Iterate through all positions
        for position in hierarchy.all_positions():
            if not position.member or position.member.is_vacant():
                continue
            
            slack_id = position.member.slack_user_id
            if not slack_id:
                logger.warning(
                    f"Position {position.title} member {position.member.name} "
                    f"has no Slack ID, skipping"
                )
                continue
            
            # Parse role structure: executive_board.commissioner, bowling.sunday.director
            role_parts = position.member.role.split('.')
            
            if len(role_parts) < 2:
                logger.warning(f"Invalid role structure: {position.member.role}")
                continue
            
            # Build specific group handle from role
            section = role_parts[0]  # e.g., "bowling", "executive_board"
            
            # Skip executive board from sport aggregations
            if section == "executive_board":
                handle = "executive-board"
                if handle not in plans:
                    plans[handle] = []
                plans[handle].append(slack_id)
                continue
            
            # Skip cross-sport from sport aggregations
            if section == "cross_sport":
                handle = "cross-sport-leadership"
                if handle not in plans:
                    plans[handle] = []
                plans[handle].append(slack_id)
                continue
            
            # Sport-based roles: bowling.sunday.director, dodgeball.monday.bigball.ops
            sport = section
            
            if len(role_parts) == 2:
                # Just sport + role: bowling.commissioner
                handle = normalize_handle(sport)
                if handle not in plans:
                    plans[handle] = []
                plans[handle].append(slack_id)
            elif len(role_parts) == 3:
                # Sport + night + role: bowling.sunday.director
                night = role_parts[1]
                handle = normalize_handle(f"{sport}-{night}")
                if handle not in plans:
                    plans[handle] = []
                plans[handle].append(slack_id)
                
                # Aggregate to sport level
                agg_key = (sport,)
                if agg_key not in aggregates:
                    aggregates[agg_key] = set()
                aggregates[agg_key].add(slack_id)
            elif len(role_parts) >= 4:
                # Sport + night + division + role: dodgeball.monday.bigball.director
                night = role_parts[1]
                division = role_parts[2]
                
                # Specific group
                handle = normalize_handle(f"{sport}-{night}-{division}")
                if handle not in plans:
                    plans[handle] = []
                plans[handle].append(slack_id)
                
                # Aggregate to sport-night level
                agg_key = (sport, night)
                if agg_key not in aggregates:
                    aggregates[agg_key] = set()
                aggregates[agg_key].add(slack_id)
                
                # Aggregate to sport level
                sport_agg_key = (sport,)
                if sport_agg_key not in aggregates:
                    aggregates[sport_agg_key] = set()
                aggregates[sport_agg_key].add(slack_id)
        
        # Add aggregates to plans
        for agg_key, user_ids in aggregates.items():
            handle = normalize_handle("-".join(agg_key))
            if handle not in plans:
                plans[handle] = []
            plans[handle].extend(list(user_ids))
        
        # Apply overrides (e.g., add commissioners to all sport groups)
        for handle, extra_ids in overrides.items():
            if handle in plans:
                plans[handle].extend(extra_ids)
            else:
                plans[handle] = extra_ids
        
        # Deduplicate and sort
        for handle in plans:
            plans[handle] = sorted(list(set(plans[handle])))
        
        logger.info(f"Built plans for {len(plans)} usergroups")
        return plans
    
    def sync_groups(
        self,
        plans: Dict[str, List[str]],
        dry_run: bool = False,
        create_missing: bool = True
    ) -> Tuple[int, int, int, List[str]]:
        """
        Sync usergroups based on membership plans.
        
        Args:
            plans: Dict of {handle: [user_ids]}
            dry_run: If True, only report what would be done
            create_missing: If True, create groups that don't exist
            
        Returns:
            Tuple of (created_count, updated_count, skipped_count, errors)
        """
        created = 0
        updated = 0
        skipped = 0
        errors = []
        
        # Get existing groups
        try:
            existing_groups = {
                g['handle']: g['id']
                for g in self.service.list_groups(include_disabled=False)
            }
            logger.info(f"Found {len(existing_groups)} existing usergroups")
        except Exception as e:
            errors.append(f"Failed to list existing groups: {e}")
            return 0, 0, 0, errors
        
        for handle, user_ids in plans.items():
            if not user_ids:
                logger.info(f"Skipping empty group: {handle}")
                skipped += 1
                continue
            
            try:
                if handle in existing_groups:
                    # Update existing group
                    group_id = existing_groups[handle]
                    
                    if dry_run:
                        current_members = self.service.get_group_members(group_id)
                        additions = set(user_ids) - set(current_members)
                        removals = set(current_members) - set(user_ids)
                        logger.info(
                            f"[DRY-RUN] Would update {handle}: "
                            f"+{len(additions)} -{len(removals)} (total: {len(user_ids)})"
                        )
                    else:
                        success = self.service.update_group_members(group_id, user_ids)
                        if success:
                            logger.info(f"Updated {handle} with {len(user_ids)} members")
                        else:
                            errors.append(f"Failed to update {handle}")
                            continue
                    
                    updated += 1
                else:
                    # Create new group
                    if not create_missing:
                        logger.info(f"Skipping non-existent group: {handle}")
                        skipped += 1
                        continue
                    
                    if dry_run:
                        logger.info(
                            f"[DRY-RUN] Would create {handle} with {len(user_ids)} members"
                        )
                    else:
                        name = handle.replace('-', ' ').title()
                        group_id = self.service.create_group(
                            name=name,
                            handle=handle,
                            description="Auto-managed by BARS Leadership System"
                        )
                        
                        if group_id:
                            # Add members to new group
                            self.service.update_group_members(group_id, user_ids)
                            logger.info(f"Created {handle} with {len(user_ids)} members")
                        else:
                            errors.append(f"Failed to create {handle}")
                            continue
                    
                    created += 1
                    
            except Exception as e:
                error_msg = f"{handle}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error processing {handle}: {e}", exc_info=True)
        
        return created, updated, skipped, errors
    
    def generate_diff_report(
        self,
        plans: Dict[str, List[str]]
    ) -> Dict[str, Dict[str, any]]:
        """
        Generate a diff report comparing plans to current state.
        
        Args:
            plans: Proposed group membership plans
            
        Returns:
            Dict with diff information for each group
        """
        report = {}
        
        try:
            existing_groups = {
                g['handle']: {'id': g['id'], 'users': g.get('users', [])}
                for g in self.service.list_groups(include_disabled=False)
            }
        except Exception as e:
            logger.error(f"Failed to list existing groups: {e}")
            return report
        
        for handle, proposed_users in plans.items():
            if handle in existing_groups:
                current_users = set(existing_groups[handle]['users'])
                proposed_set = set(proposed_users)
                
                report[handle] = {
                    'status': 'update',
                    'current_count': len(current_users),
                    'proposed_count': len(proposed_set),
                    'additions': list(proposed_set - current_users),
                    'removals': list(current_users - proposed_set),
                    'unchanged': list(current_users & proposed_set)
                }
            else:
                report[handle] = {
                    'status': 'create',
                    'proposed_count': len(proposed_users),
                    'members': proposed_users
                }
        
        return report


"""Bulk sync Slack usergroups command."""
import sys
import json
from typing import Optional, TextIO

import click
from slack_sdk.errors import SlackApiError


@click.command('sync')
@click.option('--hierarchy-json', type=click.File('r'), help='Leadership hierarchy JSON file')
@click.option('--bot', default='leadership', help='Which bot to use')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
@click.option('--create-missing', is_flag=True, default=True, help='Create groups that don\'t exist')
@click.pass_context
def sync_groups(ctx: click.Context, hierarchy_json: Optional[TextIO], bot: str, dry_run: bool, create_missing: bool):
    """
    Bulk sync usergroups from leadership hierarchy.
    
    Reads leadership hierarchy (exported from /update-bars-leadership) and:
    - Creates missing groups
    - Updates existing group memberships
    - Reports diffs and statistics
    """
    try:
        if not hierarchy_json:
            click.echo("❌ --hierarchy-json is required", err=True)
            sys.exit(1)
        
        # Load hierarchy data
        hierarchy_data = json.load(hierarchy_json)
        
        # Service is guaranteed to be available (initialized in slack group)
        from bars_cli._core.context import get_service
        slack_service = get_service(ctx, 'slack_service')
        
        # Initialize services
        provisioner = slack_service.get_usergroup_provisioner(bot)
        
        # Build group plans
        from modules.leadership.domain.models import LeadershipHierarchy
        hierarchy = LeadershipHierarchy.model_validate(hierarchy_data)
        
        click.echo("📊 Building group membership plans...")
        plans = provisioner.build_group_plans_from_hierarchy(hierarchy)
        
        click.echo(f"\n📋 Plans for {len(plans)} usergroup(s):\n")
        for handle, user_ids in sorted(plans.items()):
            click.echo(f"  • @{handle}: {len(user_ids)} member(s)")
        
        # Generate diff report
        click.echo("\n🔍 Generating diff report...")
        diff_report = provisioner.generate_diff_report(plans)
        
        creates = sum(1 for d in diff_report.values() if d['status'] == 'create')
        updates = sum(1 for d in diff_report.values() if d['status'] == 'update')
        
        click.echo(f"\n📊 Summary:")
        click.echo(f"  ➕ To create: {creates}")
        click.echo(f"  🔄 To update: {updates}")
        
        if dry_run:
            click.echo(f"\n{'='*60}")
            click.echo("🔍 DRY RUN - No changes will be made")
            click.echo(f"{'='*60}\n")
            
            for handle, diff in sorted(diff_report.items()):
                if diff['status'] == 'create':
                    click.echo(f"➕ Would CREATE @{handle} with {diff['proposed_count']} members")
                elif diff['status'] == 'update':
                    adds = len(diff.get('additions', []))
                    removes = len(diff.get('removals', []))
                    if adds > 0 or removes > 0:
                        click.echo(f"🔄 Would UPDATE @{handle}: +{adds} -{removes}")
            
            return
        
        # Confirm before applying
        if not click.confirm('\n❓ Apply these changes?'):
            click.echo("❌ Cancelled.")
            return
        
        # Sync groups
        click.echo("\n🔄 Syncing usergroups...")
        created, updated, skipped, errors = provisioner.sync_groups(
            plans,
            dry_run=False,
            create_missing=create_missing
        )
        
        click.echo(f"\n✅ Sync complete:")
        click.echo(f"  ✅ Created: {created}")
        click.echo(f"  🔄 Updated: {updated}")
        click.echo(f"  ⏭️  Skipped: {skipped}")
        
        if errors:
            click.echo(f"\n❌ Errors ({len(errors)}):")
            for error in errors:
                click.echo(f"  • {error}")
            sys.exit(1)
    
    except SlackApiError as e:
        click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


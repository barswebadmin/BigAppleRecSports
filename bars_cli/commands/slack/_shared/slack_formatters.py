from backend_services.slack.models.slack_user import SlackUser
from backend_services.slack.models.slack_group import SlackGroup

def format_channels(channels: list) -> str:
    """Format channels list for display."""
    if not channels:
        return "No channels found."
    
    output = []
    output.append(f"\n📺 Slack Channels ({len(channels)} total):\n")
    
    # Group by type
    public_channels = [c for c in channels if not c.get('is_private', False)]
    private_channels = [c for c in channels if c.get('is_private', False)]
    
    if public_channels:
        output.append("🌐 Public Channels:")
        for channel in sorted(public_channels, key=lambda c: c.get('name', '')):
            name = channel.get('name', 'N/A')
            channel_id = channel.get('id', 'N/A')
            archived = " [ARCHIVED]" if channel.get('is_archived', False) else ""
            members = channel.get('num_members', '?')
            output.append(f"  • #{name:<30} ({channel_id}) - {members} members{archived}")
    
    if private_channels:
        output.append("\n🔒 Private Channels:")
        for channel in sorted(private_channels, key=lambda c: c.get('name', '')):
            name = channel.get('name', 'N/A')
            channel_id = channel.get('id', 'N/A')
            archived = " [ARCHIVED]" if channel.get('is_archived', False) else ""
            members = channel.get('num_members', '?')
            output.append(f"  • #{name:<30} ({channel_id}) - {members} members{archived}")
    
    return '\n'.join(output)

def format_users(users: list[SlackUser]) -> str:
    """Format users list for display."""
    if not users:
        return "No users found."
    
    output = []
    output.append(f"\n👥 Slack Users ({len(users)} total):\n")
    
    # Group by status
    # deleted and is_bot are always present in API responses, use direct access
    active_users = [u for u in users if not u.deleted and not u.is_bot]
    bots = [u for u in users if u.is_bot]
    deleted_users = [u for u in users if u.deleted]
    
    if active_users:
        output.append("✅ Active Users:")
        for user in sorted(active_users, key=lambda u: u.real_name or ''):
            name = user.real_name or 'N/A'
            user_id = user.id
            email = user.profile.email or 'N/A'
            title = user.profile.title or ''
            title_display = f" - {title}" if title else ""
            output.append(f"  • {name:<30} ({user_id}) {email}{title_display}")
    
    if bots:
        output.append(f"\n🤖 Bots ({len(bots)}):")
        for bot in sorted(bots, key=lambda u: u.real_name or ''):
            name = bot.real_name or 'N/A'
            bot_id = bot.id
            output.append(f"  • {name:<30} ({bot_id})")
    
    if deleted_users:
        output.append(f"\n🗑️  Deleted Users ({len(deleted_users)}):")
        for user in sorted(deleted_users, key=lambda u: u.real_name or ''):
            name = user.real_name or 'N/A'
            user_id = user.id
            output.append(f"  • {name:<30} ({user_id})")
    
    return '\n'.join(output)

def format_group(group: SlackGroup) -> str:
    """Format usergroup data for display."""
    name = group.get('name', 'N/A')
    handle = group.get('handle', 'N/A')
    group_id = group.get('id', 'N/A')
    description = group.get('description', '')
    is_disabled = group.get('date_delete', 0) > 0 if group.get('date_delete') else False
    
    output = []
    output.append("\n👥 Usergroup Details:\n")
    output.append(f"  Name: {name}")
    output.append(f"  Handle: @{handle}")
    output.append(f"  Group ID: {group_id}")
    
    if description:
        output.append(f"  Description: {description}")
    
    if is_disabled:
        output.append("  ⚠️  Status: DISABLED")
    
    users = group.get('users', [])
    user_count = len(users)
    output.append(f"  Members: {user_count}")
    
    if users:
        output.append(f"\n  Member IDs:")
        for user_id in users[:20]:  # Show first 20
            output.append(f"    - {user_id}")
        if len(users) > 20:
            output.append(f"    ... and {len(users) - 20} more")
    
    return '\n'.join(output)
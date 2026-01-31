import click_extra as click


def _format_member_added(member: dict, group_email: str, user_email: str) -> None:
    """Format member addition result for display.
    
    Args:
        member: Member data dict from API
        group_email: Group email address
        user_email: User email address that was added
    """
    output = []
    output.append("\n✅ Member Added Successfully!")
    output.append("=" * 60)
    output.append(f"{'Group':<15} {group_email}")
    output.append(f"{'User':<15} {user_email}")
    output.append(f"{'Role':<15} {member.get('role', 'MEMBER')}")
    output.append(f"{'Member ID':<15} {member.get('id', 'N/A')}")
    output.append("=" * 60)
    click.echo('\n'.join(output))
    click.echo()

def _format_group(group: dict, members: list[dict]) -> None:
    """Format group data for display.
    
    Args:
        group: Group data dict from API
        members: List of member dicts
    """
    output = []
    output.append("\n✅ Group Found!")
    output.append("=" * 60)
    
    output.append(f"{'Alias Email':<15} {group.get('email', 'N/A')}")
    output.append(f"{'Name':<15} {group.get('name', 'N/A')}")
    output.append(f"{'ID':<15} {group.get('id', 'N/A')}")
    
    if group.get('description'):
        output.append(f"{'Description':<15} {group['description']}")
    
    if members:
        output.append(f"\nMembers ({len(members)}):")
        for member in members:
            role = member.get('role', 'MEMBER')
            email = member.get('email', 'N/A')
            output.append(f"  • {email} ({role})")
    
    if group.get('aliases'):
        aliases = group['aliases']
        output.append(f"\nAliases ({len(aliases)}):")
        for alias in aliases:
            output.append(f"  • {alias}")
    
    output.append("=" * 60)
    click.echo('\n'.join(output))

def _format_groups_list(groups: list[dict]) -> None:
    """Format groups list for display.
    
    Args:
        groups: List of group dicts from API
    """
    output = []
    output.append(f"\n✅ Found {len(groups)} group(s)")
    output.append("=" * 80)
    
    for group in groups:
        email = group.get('email', 'N/A')
        name = group.get('name', 'N/A')
        members_count = group.get('direct_members_count', 'N/A')
        output.append(f"{email:<40} {name:<30} ({members_count} members)")
    
    output.append("=" * 80)
    click.echo('\n'.join(output))

def _format_user(user: dict) -> None:
    """Format user data for display.
    
    Args:
        user: User data dict from API
    """
    output = []
    output.append("\n✅ User Found!")
    output.append("=" * 60)
    
    output.append(f"{'Email':<15} {user.get('primary_email', 'N/A')}")
    
    if user.get('name'):
        name_data = user['name']
        full_name = name_data.get('full_name', 'N/A')
        given_name = name_data.get('given_name', '')
        family_name = name_data.get('family_name', '')
        if full_name != 'N/A':
            output.append(f"{'Name':<15} {full_name}")
        elif given_name or family_name:
            output.append(f"{'Name':<15} {given_name} {family_name}".strip())
    
    output.append(f"{'ID':<15} {user.get('id', 'N/A')}")
    
    if user.get('suspended') is not None:
        suspended = "Yes" if user['suspended'] else "No"
        output.append(f"{'Suspended':<15} {suspended}")
    
    if user.get('is_admin') is not None:
        is_admin = "Yes" if user['is_admin'] else "No"
        output.append(f"{'Admin':<15} {is_admin}")
    
    if user.get('org_unit_path'):
        output.append(f"{'Org Unit':<15} {user['org_unit_path']}")
    
    if user.get('aliases'):
        aliases = user['aliases']
        output.append(f"\nAliases ({len(aliases)}):")
        for alias in aliases:
            output.append(f"  • {alias}")
    
    output.append("=" * 60)
    click.echo('\n'.join(output))

def _format_users_list(users: list[dict]) -> None:
    """Format users list for display.
    
    Args:
        users: List of user dicts from API
    """
    output = []
    output.append(f"\n✅ Found {len(users)} user(s)")
    output.append("=" * 80)
    
    for user in users:
        email = user.get('primary_email', 'N/A')
        full_name = 'N/A'
        if user.get('name') and user['name'].get('full_name'):
            full_name = user['name']['full_name']
        suspended = "Suspended" if user.get('suspended') else "Active"
        is_admin = "Admin" if user.get('is_admin') else ""
        admin_label = f" [{is_admin}]" if is_admin else ""
        
        output.append(f"{email:<40} {full_name:<30} {suspended}{admin_label}")
    
    output.append("=" * 80)
    click.echo('\n'.join(output))

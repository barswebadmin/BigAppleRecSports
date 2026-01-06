"""CLI client imports - symlinks to backend clients for easy access.

This allows CLI commands to import backend clients without sys.path manipulation.
Example:
    from bars_cli.clients.leadership_bot import leadership_bot
    leadership_bot.lookup_user(...)
"""

# Import bots so they're available as bars_cli.clients.*
from . import leadership_bot
from . import dev_bot

__all__ = ['leadership_bot', 'dev_bot']


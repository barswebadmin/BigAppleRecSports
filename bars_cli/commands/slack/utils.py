"""
Shared utilities for Slack CLI commands.
"""
import click
from config import config


def get_bot_token(bot_name: str) -> str:
    """
    Get Slack bot token by bot name.
    
    Args:
        bot_name: Name of the bot (dev, exec, leadership, etc.)
        
    Returns:
        Bot token string
        
    Raises:
        click.BadParameter: If bot name is invalid
    """
    bot_name = bot_name.lower()
    
    bot_map = {
        'dev': config.Slack.Bots.Dev,
        'exec': config.Slack.Bots.Exec,
        'leadership': config.Slack.Bots.Leadership,
        'payment_assistance': config.Slack.Bots.PaymentAssistance,
        'refunds': config.Slack.Bots.Refunds,
        'registrations': config.Slack.Bots.Registrations,
        'web': config.Slack.Bots.Web,
    }
    
    bot = bot_map.get(bot_name)
    if not bot:
        available = ', '.join(bot_map.keys())
        raise click.BadParameter(
            f"Unknown bot: {bot_name}. Available: {available}",
            param_hint='--bot'
        )
    
    return bot.token


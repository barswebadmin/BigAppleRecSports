"""Slack Bolt app initialization for Leadership bot."""

from slack_bolt import App
from modules.integrations.slack.client.slack_config import SlackConfig

app = App(
    token=SlackConfig.Bots.Leadership.token,
    signing_secret=SlackConfig.Bots.Leadership.signing_secret
)

from modules.integrations.slack.leadership.handlers import *


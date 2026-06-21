import logging

from core.config import Settings

_settings = Settings()

logging.basicConfig(
    level=_settings.verbosity,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logging.getLogger().setLevel(_settings.verbosity)

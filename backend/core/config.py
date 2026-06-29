from typing import Literal

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)

# Parsing semantics shared by every settings class in this file.
SHARED_CONFIG = SettingsConfigDict(
    env_file="../.env",
    env_nested_delimiter="__",
    extra="ignore",
)


class Settings(BaseSettings):
    # App metadata. ``version`` is read from ``[project]`` in
    # backend/pyproject.toml via the customise_sources hook below.
    # ``pyproject_toml_depth=2`` lets the source walk up two parents from cwd.
    model_config = SettingsConfigDict(
        **SHARED_CONFIG,
        env_prefix="APP__",
        pyproject_toml_table_header=("project",),
        pyproject_toml_depth=2,
    )

    version:     str = Field(init=False)
    environment: str = Field(init=False)
    verbosity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(init=False)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
        )


class ShopifyConfig(BaseSettings):
    model_config = SettingsConfigDict(**SHARED_CONFIG, env_prefix="SHOPIFY__")

    api_version:     str = Field(init=False)
    store_id:        str = Field(init=False)
    location_id:     str = Field(init=False)
    shop_id:         str = Field(init=False)
    admin_token:     str = Field(init=False)
    locksmith_token: str = Field(init=False)
    webhook_secret:  str = Field(init=False)


settings = Settings()
shopify_config = ShopifyConfig()

import logging
import os
import typing as t
from pathlib import Path

from pydantic import AnyUrl, BaseSettings, PostgresDsn


class Config(BaseSettings):
    """Application configuration. During object instantiation pydantic reads env variables and secret files on disk."""

    class Config:
        env_file = os.getenv("CONFIG_ENV_FILE", None)
        secrets_dir = os.getenv("CONFIG_SECRETS_DIR", None)

    logging_level: t.Union[int, str] = logging.INFO
    logging_json_enabled: bool = False

    postgres_dsn: PostgresDsn

    solana_endpoint: AnyUrl
    solana_airdrop_amount: int = 1_000_000_000
    solana_mint_amount: int = 1_000

    token_repository_config_path: Path
    """A path to a config on a disk with :class:`spl_token_lending.repository.token.TokenRepositoryConfig` structure, 
    see :class:`spl_token_lending.repository.token.TokenRepositoryFactory`"""

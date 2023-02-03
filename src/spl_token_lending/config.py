import logging
import os
import typing as t
from pathlib import Path

from pydantic import AnyUrl, BaseSettings, PostgresDsn

from spl_token_lending.repository.token import TokenRepositoryConfig


class Config(BaseSettings):
    class Config:
        env_file = os.getenv("CONFIG_ENV_FILE", None)
        secrets_dir = os.getenv("CONFIG_SECRETS_DIR", None)

    logging_level: t.Union[int, str] = logging.INFO
    logging_json_enabled: bool = False

    solana_endpoint: AnyUrl
    postgres_dsn: PostgresDsn

    token_repository_config: t.Union[None, Path, TokenRepositoryConfig] = None

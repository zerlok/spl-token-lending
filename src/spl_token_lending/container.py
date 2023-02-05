import asyncio
import logging
import typing as t
from contextlib import asynccontextmanager, contextmanager

import sqlalchemy as sa
from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer
from gino import Gino
from solana.rpc.async_api import AsyncClient

from spl_token_lending.config import Config
from spl_token_lending.db.models import gino
from spl_token_lending.domain.cases import UserLendingCase, ViewLoansCase
from spl_token_lending.logging import setup_logging
from spl_token_lending.repository.loan import LoanRepository
from spl_token_lending.repository.token import TokenRepository, TokenRepositoryFactory
from spl_token_lending.repository.wallet import WalletRepository

_LOGGER = logging.getLogger(__name__)


def _create_config() -> Config:
    config = Config()

    setup_logging(config.logging_level, config.logging_json_enabled)

    return config


def _create_alembic_postgres_engine(config: Config) -> t.Iterator[sa.engine.Engine]:
    engine = sa.create_engine(config.postgres_dsn)

    try:
        yield engine

    finally:
        engine.dispose()


async def _create_gino_postgres_engine(config: Config, gino_meta: Gino) -> t.AsyncIterator[Gino]:
    async with gino_meta.with_bind(config.postgres_dsn) as engine:
        yield engine


async def _create_solana_client(config: Config) -> t.AsyncIterator[AsyncClient]:
    async with AsyncClient(config.solana_endpoint) as client:
        yield client


async def _create_token_repository(config: Config, factory: TokenRepositoryFactory) -> TokenRepository:
    return await factory.create_from_path(config.token_repository_config_path)


class Container(DeclarativeContainer):
    config = providers.Singleton(_create_config)

    db_metadata = providers.Object(t.cast(Gino, gino))  # type: ignore[var-annotated]
    alembic_engine = providers.Resource(_create_alembic_postgres_engine, config)
    gino_engine = providers.Resource(_create_gino_postgres_engine, config, db_metadata)

    solana_client = providers.Resource(_create_solana_client, config)

    wallet_repository = providers.Singleton(WalletRepository, solana_client, config.provided.solana_airdrop_amount)
    token_repository_factory = providers.Singleton(TokenRepositoryFactory, solana_client, wallet_repository,
                                                   config.provided.solana_mint_amount)
    token_repository = providers.Singleton(_create_token_repository, config, token_repository_factory)
    loan_repository = providers.Singleton(LoanRepository, gino_engine)

    user_lending_case = providers.Singleton(UserLendingCase, token_repository, loan_repository)
    view_loans_case = providers.Singleton(ViewLoansCase, loan_repository)


@asynccontextmanager
async def use_initialized_container(container: t.Optional[Container] = None) -> t.AsyncIterator[Container]:
    container = container or Container()

    await container.init_resources()  # type: ignore[misc]

    try:
        yield container

    finally:
        await container.shutdown_resources()  # type: ignore[misc]


@contextmanager
def use_initialized_container_sync(container: t.Optional[Container] = None) -> t.Iterator[Container]:
    container = container or Container()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        container.init_resources(),  # type: ignore[arg-type]
    )

    try:
        yield container

    finally:
        loop.run_until_complete(
            container.shutdown_resources(),  # type: ignore[arg-type]
        )

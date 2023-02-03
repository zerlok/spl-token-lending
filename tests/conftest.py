import asyncio
import logging
import typing as t
from pathlib import Path

import pytest
import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from dependency_injector import providers

from spl_token_lending.config import Config
from spl_token_lending.container import Container
from spl_token_lending.repository.token import TokenRepository, TokenRepositoryFactory


@pytest.fixture(scope="session")
def event_loop() -> t.Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.get_event_loop()

    yield loop

    loop.close()


@pytest.fixture(scope="session")
def monkeypatch() -> t.Iterator[MonkeyPatch]:
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
def config(monkeypatch: MonkeyPatch) -> Config:
    monkeypatch.setenv("TOKEN_REPOSITORY_CONFIG", str(Path(__file__).parent / "data" / "test-token.json"))
    monkeypatch.setenv("LOGGING_LEVEL", str(logging.DEBUG))
    monkeypatch.setenv("LOGGING_JSON_ENABLED", "no")
    monkeypatch.setenv("SOLANA_ENDPOINT", "https://api.devnet.solana.com")

    config = Config()

    return config


@pytest_asyncio.fixture(scope="session")
async def container(config: Config) -> t.AsyncIterator[Container]:
    c = Container()

    # TODO: think about refilling the initial amount of tokens during the test start - it will make tests more
    #  reproducible
    async def create_token_repository(config: Config, factory: TokenRepositoryFactory) -> TokenRepository:
        if not isinstance(config.token_repository_config, Path):
            raise TypeError("a path to token repository is required")

        return await factory.create_from_path(config.token_repository_config)

    c.config.override(providers.Object(config))
    c.token_repository.override(providers.Singleton(create_token_repository, c.config, c.token_repository_factory))

    await c.init_resources()  # type: ignore[misc]

    yield c

    await c.shutdown_resources()  # type: ignore[misc]


@pytest_asyncio.fixture(scope="session")
async def initialize_token_repository() -> None:
    factory = await container.token_repository_factory()
    await factory.create_from_path()


@pytest_asyncio.fixture()
async def clean_database(container: Container) -> None:
    gino = await container.gino_metadata()  # type: ignore[misc]
    # FIXME: run migrations at test session start, before running the first test. If it's not done, then uuid
    #  postgres extension won't be installed and uuid column `LoanModel.id` won't work.
    await gino.gino.drop_all()
    await gino.gino.create_all()

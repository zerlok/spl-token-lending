import asyncio
import logging
import os
import typing as t
from contextlib import suppress
from pathlib import Path
from subprocess import Popen

import pytest
import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from dependency_injector import providers
from pydantic import PostgresDsn

from spl_token_lending.config import Config
from spl_token_lending.container import Container, use_initialized_container
from spl_token_lending.db.models import gino
from spl_token_lending.repository.iterable import iter_with_exp_delay
from spl_token_lending.repository.token import TokenRepository, TokenRepositoryFactory

PROJECT_DIR = Path(__file__).parent.parent


@pytest.fixture(scope="session")
def event_loop() -> t.Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.get_event_loop()

    try:
        yield loop

    finally:
        loop.close()


@pytest.fixture(scope="session")
def monkeypatch() -> t.Iterator[MonkeyPatch]:
    patcher = MonkeyPatch()

    try:
        yield patcher

    finally:
        patcher.undo()


@pytest.fixture(scope="session")
def config(monkeypatch: MonkeyPatch) -> Config:
    monkeypatch.setenv("TOKEN_REPOSITORY_CONFIG", str(PROJECT_DIR / "tests" / "data" / "test-token.json"))
    monkeypatch.setenv("LOGGING_LEVEL", str(logging.DEBUG))
    monkeypatch.setenv("LOGGING_JSON_ENABLED", "no")
    monkeypatch.setenv("SOLANA_ENDPOINT", "https://api.devnet.solana.com")

    config = Config()

    return config


@pytest.fixture(scope="session")
def popen() -> t.Callable[[t.Sequence[str]], int]:
    def execute(args: t.Sequence[str]) -> int:
        with Popen(args=args, cwd=PROJECT_DIR, env=os.environ) as p:
            return p.wait()

    return execute


@pytest.fixture(scope="session")
def docker_compose(
        config: Config,
        popen: t.Callable[[t.Sequence[str]], int],
) -> t.Iterator[t.Callable[[t.Sequence[str]], int]]:
    base_args = ["docker-compose", "-p", f"pytest-{os.getpid()}", ]

    def execute(args: t.Sequence[str]) -> int:
        return popen([*base_args, *args])

    try:
        yield execute

    finally:
        execute(["down", "-v"])


@pytest_asyncio.fixture(scope="session")
async def docker_postgres_service(
        config: Config,
        docker_compose: t.Callable[[t.Sequence[str]], int],
) -> t.AsyncIterator[PostgresDsn]:
    code = docker_compose(["up", "-d", "postgres"])
    assert code == 0

    async for _ in iter_with_exp_delay():
        with suppress(ConnectionError):
            async with gino.with_bind(config.postgres_dsn) as engine:
                assert (await engine.scalar("SELECT 1")) == 1
                break

    else:
        raise RuntimeError("failed to connect to postgres in docker compose")

    try:
        yield config.postgres_dsn

    finally:
        docker_compose(["rm", "-fs", "postgres"])


@pytest_asyncio.fixture(scope="session")
async def container(config: Config, docker_postgres_service: PostgresDsn) -> t.AsyncIterator[Container]:
    c = Container()

    # TODO: think about refilling the initial amount of tokens during the test start - it will make tests more
    #  reproducible
    async def create_token_repository(config: Config, factory: TokenRepositoryFactory) -> TokenRepository:
        if not isinstance(config.token_repository_config, Path):
            raise TypeError("a path to token repository is required")

        return await factory.create_from_path(config.token_repository_config)

    c.config.override(providers.Object(config))
    c.token_repository.override(providers.Singleton(create_token_repository, c.config, c.token_repository_factory))

    async with use_initialized_container(c):
        yield c


@pytest.fixture(scope="session")
def migrated_database(docker_postgres_service: PostgresDsn, popen: t.Callable[[t.Sequence[str]], int]) -> None:
    assert popen(["alembic", "downgrade", "base"]) == 0
    assert popen(["alembic", "upgrade", "head"]) == 0


@pytest_asyncio.fixture()
async def clean_database(container: Container, migrated_database: object) -> None:
    db = container.db_metadata()
    await db.gino.drop_all()
    await db.gino.create_all()

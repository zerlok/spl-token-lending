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
from asyncpg import PostgresError
from dependency_injector import providers
from pydantic import PostgresDsn

from spl_token_lending.config import Config
from spl_token_lending.container import Container, use_initialized_container
from spl_token_lending.db.models import gino
from spl_token_lending.repository.iterable import iter_with_exp_delay

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
    if code != 0:
        raise RuntimeError("failed to start postgres in docker compose")

    async for _ in iter_with_exp_delay():
        with suppress(ConnectionError, PostgresError):
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

    c.config.override(providers.Object(config))

    async with use_initialized_container(c):
        yield c


@pytest.fixture(scope="session")
def migrated_database(docker_postgres_service: PostgresDsn, popen: t.Callable[[t.Sequence[str]], int]) -> None:
    code = popen(["alembic", "downgrade", "base"])
    if code != 0:
        raise RuntimeError("failed to run alembic downgrade")

    code = popen(["alembic", "upgrade", "head"])
    if code != 0:
        raise RuntimeError("failed to run alembic upgrade")


@pytest_asyncio.fixture()
async def clean_database(container: Container, migrated_database: object) -> None:
    db = container.db_metadata()
    await db.gino.drop_all()
    await db.gino.create_all()

import typing as t

from alembic import context
from alembic.operations import MigrateOperation
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from spl_token_lending.container import Container, use_initialized_container_sync
from spl_token_lending.db.models import gino

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = gino


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def process_revision_directives(
        ctx: MigrationContext,
        _: t.Tuple[str, str],
        directives: t.Sequence[MigrateOperation],
) -> None:
    # extract Migration
    migration_script = directives[0]
    # extract current head revision
    migration_config = ctx.config
    if migration_config is None:
        raise RuntimeError("migration config is None", ctx)

    head_revision = ScriptDirectory.from_config(migration_config).get_current_head()

    if head_revision is None:
        # edge case with first migration
        new_rev_id = 1
    else:
        # default branch with incrementation
        last_rev_id = int(head_revision.lstrip('0'))
        new_rev_id = last_rev_id + 1
    # fill zeros up to 4 digits: 1 -> 0001
    migration_script.rev_id = '{0:04}'.format(new_rev_id)  # type: ignore[attr-defined]


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """

    with use_initialized_container_sync() as container:  # type: Container
        context.configure(
            url=container.config().postgres_dsn,
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    with use_initialized_container_sync() as container:  # type: Container
        with container.alembic_engine().connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                process_revision_directives=process_revision_directives,
            )

            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

import os
from subprocess import Popen


def run_migration_upgrade() -> int:
    with Popen(args=["alembic", "upgrade", "head"], cwd=os.getcwd(), env=os.environ) as p:
        return p.wait()

import sqlalchemy as sa
from gino import Gino
from sqlalchemy.dialects import postgresql as pg

from spl_token_lending.repository.data import LoanItem

gino = Gino()


class LoanModel(gino.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "loan"

    id = sa.Column(pg.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()"))
    status = sa.Column(sa.Enum(LoanItem.Status), nullable=False)
    address = sa.Column(sa.String(), nullable=False)
    amount = sa.Column(sa.Integer(), nullable=False)

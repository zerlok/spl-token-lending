import typing as t
import uuid
from contextlib import asynccontextmanager

import sqlalchemy as sa
from gino import Gino
from gino.transaction import GinoTransaction
from solders.pubkey import Pubkey
from sqlalchemy.sql import Select

from spl_token_lending.db.models import LoanModel
from spl_token_lending.repository.data import Amount, LoanFilterOptions, LoanId, LoanItem, PaginationOptions


class LoanRepository:
    """Provides operations with loans, stores data in database via gino."""

    __SELECT_COUNT = sa.select([sa.func.count()]).select_from(LoanModel)  # type:ignore[arg-type]
    __SELECT_ITEMS = sa.select(LoanModel).select_from(LoanModel)  # type:ignore[arg-type]
    __SELECT_ITEMS_ORDERED = __SELECT_ITEMS.order_by(LoanModel.id)
    __INSERT_ITEMS = sa.insert(LoanModel).returning(*LoanModel)  # type:ignore[arg-type]
    __UPDATE_ITEMS = sa.update(LoanModel).returning(*LoanModel)  # type:ignore[arg-type]

    def __init__(self, gino: Gino) -> None:
        self.__gino = gino

    @asynccontextmanager
    async def use_transaction(self, loan_id: LoanId) -> t.AsyncIterator[GinoTransaction]:
        # TODO: lock loan row by id
        async with self.__gino.transaction() as tx:  # type: GinoTransaction
            yield tx

    async def get_by_id(self, loan_id: LoanId) -> t.Optional[LoanItem]:
        row = await self.__gino.one_or_none(self.__SELECT_ITEMS.where(LoanModel.id == loan_id))

        return self.__row2item(row) if row is not None else None

    async def count(self, filter_: t.Optional[LoanFilterOptions] = None) -> int:
        query = self.__append_filter(self.__SELECT_COUNT, filter_)

        return await self.__gino.scalar(query)  # type: ignore[no-any-return]

    async def find(
            self,
            filter_: t.Optional[LoanFilterOptions] = None,
            pagination: t.Optional[PaginationOptions] = None,
    ) -> t.Sequence[LoanItem]:
        query = self.__append_pagination(self.__append_filter(self.__SELECT_ITEMS_ORDERED, filter_), pagination)
        rows = await self.__gino.all(query)

        return [self.__row2item(r) for r in rows]

    async def create(self, status: LoanItem.Status, wallet: Pubkey, amount: Amount) -> LoanItem:
        value_to_insert = {
            LoanModel.status: status,
            LoanModel.wallet: str(wallet),
            LoanModel.amount: amount,
        }

        inserted_row = await self.__gino.one(self.__INSERT_ITEMS.values([value_to_insert]))

        return self.__row2item(inserted_row)

    async def update_existing_by_id(self, item: LoanItem) -> LoanItem:
        value_to_update = {
            LoanModel.status: item.status,
            LoanModel.wallet: str(item.wallet),
            LoanModel.amount: item.amount,
        }

        updated_row = await self.__gino.one(self.__UPDATE_ITEMS.values(value_to_update).where(LoanModel.id == item.id_))

        return self.__row2item(updated_row)

    def __append_filter(self, select_stmt: Select, filter_: t.Optional[LoanFilterOptions]) -> Select:
        if filter_ is None:
            return select_stmt

        if filter_.id_equals is not None:
            select_stmt = select_stmt.where(LoanModel.id == filter_.id_equals)
        if filter_.status_equals is not None:
            select_stmt = select_stmt.where(LoanModel.status == filter_.status_equals)
        if filter_.wallet_equals is not None:
            select_stmt = select_stmt.where(LoanModel.wallet == str(filter_.wallet_equals))

        return select_stmt

    def __append_pagination(self, select_stmt: Select, pagination: t.Optional[PaginationOptions]) -> Select:
        if pagination is None:
            return select_stmt

        return select_stmt.offset(pagination.offset).limit(pagination.limit)

    def __row2item(self, row: LoanModel) -> LoanItem:
        return LoanItem(
            id_=LoanId(t.cast(uuid.UUID, row.id)),
            status=LoanItem.Status(row.status),
            wallet=Pubkey.from_string(row.wallet),
            amount=Amount(row.amount),
        )

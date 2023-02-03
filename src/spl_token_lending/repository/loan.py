import typing as t
import uuid
from contextlib import asynccontextmanager

import sqlalchemy as sa
from gino import Gino
from gino.transaction import GinoTransaction
from solders.pubkey import Pubkey

from spl_token_lending.db.models import LoanModel
from spl_token_lending.repository.data import Amount, LoanId, LoanItem, PaginationOptions


class LoanRepository:
    __SELECT_COUNT = sa.select([sa.func.count()]).select_from(LoanModel)  # type:ignore[arg-type]
    __SELECT_ITEMS = sa.select(LoanModel).select_from(LoanModel)  # type:ignore[arg-type]
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

    async def count(self) -> int:
        return await self.__gino.scalar(self.__SELECT_COUNT)  # type: ignore[no-any-return]

    async def find(self, pagination: PaginationOptions) -> t.Sequence[LoanItem]:
        rows = await self.__gino.all(self.__SELECT_ITEMS.offset(pagination.offset).limit(pagination.limit))

        return [self.__row2item(r) for r in rows]

    async def count_by_address(self, address: Pubkey) -> int:
        raise NotImplementedError

    async def find_by_address(self, address: Pubkey, pagination: PaginationOptions) -> t.Sequence[LoanItem]:
        rows = await self.__gino.all(
            self.__SELECT_ITEMS
            .where(LoanModel.address == str(address))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )

        return [self.__row2item(r) for r in rows]

    async def create(self, status: LoanItem.Status, address: Pubkey, amount: Amount) -> LoanItem:
        value_to_insert = {
            LoanModel.status: status,
            LoanModel.address: str(address),
            LoanModel.amount: amount,
        }

        inserted_row = await self.__gino.one(self.__INSERT_ITEMS.values([value_to_insert]))

        return self.__row2item(inserted_row)

    async def update_existing_by_id(self, item: LoanItem) -> LoanItem:
        value_to_update = {
            LoanModel.status: item.status,
            LoanModel.address: str(item.address),
            LoanModel.amount: item.amount,
        }

        updated_row = await self.__gino.one(self.__UPDATE_ITEMS.values(value_to_update).where(LoanModel.id == item.id_))

        return self.__row2item(updated_row)

    def __row2item(self, row: LoanModel) -> LoanItem:
        return LoanItem(
            id_=LoanId(t.cast(uuid.UUID, row.id)),
            status=LoanItem.Status(row.status),
            address=Pubkey.from_string(row.address),
            amount=Amount(row.amount),
        )

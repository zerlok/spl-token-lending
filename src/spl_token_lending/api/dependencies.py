import functools as ft
import typing as t
import uuid

from fastapi import Depends
from solders.pubkey import Pubkey

from spl_token_lending.api.data import LoanStatus, decode_loan_item_status
from spl_token_lending.container import Container
from spl_token_lending.domain.cases import UserLendingCase, ViewLoansCase
from spl_token_lending.repository.data import LoanFilterOptions, LoanId, PaginationOptions


@ft.lru_cache(maxsize=1)
def get_container() -> Container:
    return Container()


async def get_user_lending_case(container: Container = Depends(get_container)) -> UserLendingCase:
    return await container.user_lending_case()  # type: ignore[misc,no-any-return]


async def get_view_user_loans_case(container: Container = Depends(get_container)) -> ViewLoansCase:
    return await container.view_loans_case()  # type: ignore[misc,no-any-return]


def get_pagination_options(offset: int = 0, limit: int = 1_000) -> PaginationOptions:
    return PaginationOptions(offset, limit)


def get_loan_filter_options(
        loan_id: t.Optional[uuid.UUID] = None,
        status: t.Optional[LoanStatus] = None,
        wallet: t.Optional[str] = None,
) -> LoanFilterOptions:
    return LoanFilterOptions(
        id_equals=LoanId(loan_id) if loan_id is not None else None,
        status_equals=decode_loan_item_status(status) if status is not None else None,
        wallet_equals=Pubkey.from_string(wallet) if wallet is not None else None,
    )

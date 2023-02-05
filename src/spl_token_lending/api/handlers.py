import typing as t

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status

from spl_token_lending.api.data import ItemsViewObject, LoanObject, LoanRequestObject, LoanSubmitObject
from spl_token_lending.api.dependencies import (
    get_loan_filter_options,
    get_pagination_options,
    get_user_lending_case, get_view_user_loans_case,
)
from spl_token_lending.domain.cases import UserLendingCase, ViewLoansCase
from spl_token_lending.domain.data import InitializedUserLoan, ItemsView, SubmittedUserLoan
from spl_token_lending.repository.data import LoanFilterOptions, LoanId, LoanItem, PaginationOptions

router = APIRouter(prefix="/loans")


@router.put("/", response_model=LoanObject)
async def request_loan(
        executor: UserLendingCase = Depends(get_user_lending_case),
        data: LoanRequestObject = Body(),
) -> LoanItem:
    """Initialize user token loan for provided wallet and for a specified amount.

    Initialized loan should be submitted by user with a signature for tokens to be transferred.
    """

    result = await executor.initialize(data.wallet, data.amount)
    if not isinstance(result, InitializedUserLoan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)

    return result.item


@router.patch("/{loan_id}", response_model=LoanObject)
async def submit_loan(
        executor: UserLendingCase = Depends(get_user_lending_case),
        loan_id: LoanId = Path(),
        data: LoanSubmitObject = Body(),
) -> LoanItem:
    """Submits the loan and transfers appropriate token amount to user associated token account.

    User must provide a signature by performing message sign: user must sign a loan id with hist own keypair and send
    the result to this handler.
    """

    result = await executor.submit(loan_id, data.signature)
    if not isinstance(result, SubmittedUserLoan):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.error)

    return result.item


@router.get("/", response_model=ItemsViewObject[LoanObject])
async def view_loans(
        executor: ViewLoansCase = Depends(get_view_user_loans_case),
        filter_: t.Optional[LoanFilterOptions] = Depends(get_loan_filter_options),
        pagination: PaginationOptions = Depends(get_pagination_options),
) -> ItemsView[LoanItem]:
    """Views all known loans with specified filter and pagination options."""

    return await executor.perform(filter_, pagination)

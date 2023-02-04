from dataclasses import replace

from gino.transaction import GinoTransaction
from solders.pubkey import Pubkey
from solders.signature import Signature

from spl_token_lending.domain.data import (
    FailedUserLoan, InitializedUserLoan, InitializedUserLoanResult,
    ItemsView,
    SubmittedUserLoan, SubmittedUserLoanResult,
)
from spl_token_lending.repository.data import Amount, LoanId, LoanItem, PaginationOptions
from spl_token_lending.repository.loan import LoanRepository
from spl_token_lending.repository.token import TokenRepository


# TODO: create pending transaction in solana and start a listener to wait for client signed the transaction. Waiter
#  may subscribe for specific transaction and change loan status in background.
# TODO: think about loan amount reduce when client returns the token back to owner's account, also close loan when
#  the whole amount was returned.
class UserLendingCase:
    """
    User can request a token amount to be lent over by the server and receive the requested amount on his solana wallet.
    """

    def __init__(self, token_repository: TokenRepository, loan_repository: LoanRepository) -> None:
        self.__token_repository = token_repository
        self.__loan_repository = loan_repository

    # TODO: support different token - create token repository for a provided token with appropriate owner from DB.
    async def initialize(
            self,
            address: Pubkey,
            amount: Amount,
    ) -> InitializedUserLoanResult:
        token_available_amount = await self.__token_repository.get_account_amount(self.__token_repository.owner_pubkey)
        if token_available_amount is None:
            return FailedUserLoan("failed to get token amount on source account")

        if amount > token_available_amount:
            return FailedUserLoan("insufficient token amount on source account")

        pending_loan = await self.__loan_repository.create(LoanItem.Status.PENDING, address, amount)

        return InitializedUserLoan(pending_loan)

    async def submit(self, loan_id: LoanId, signature: Signature) -> SubmittedUserLoanResult:
        pending_loan = await self.__loan_repository.get_by_id(loan_id)
        if pending_loan is None:
            return FailedUserLoan("loan was not found")

        if not self.__validate_signature(pending_loan, signature):
            return FailedUserLoan("provided signature is invalid")

        async with self.__loan_repository.use_transaction(pending_loan.id_) as tx:  # type: GinoTransaction
            active_loan = await self.__loan_repository.update_existing_by_id(
                item=replace(pending_loan, status=LoanItem.Status.ACTIVE),
            )

            ok = await self.__token_repository.transfer(active_loan.address, active_loan.amount)
            if not ok:
                tx.raise_rollback()

        return SubmittedUserLoan(active_loan) if ok else FailedUserLoan("transfer process failed unexpectedly")

    def __validate_signature(self, loan: LoanItem, signature: Signature) -> bool:
        return signature.verify(loan.address, loan.id_.bytes)


class ViewUserLoansCase:

    def __init__(self, loan_repository: LoanRepository) -> None:
        self.__loan_repository = loan_repository

    async def perform(self, key: Pubkey, pagination: PaginationOptions) -> ItemsView[LoanItem]:
        total = await self.__loan_repository.count_by_address(key)
        loans = await self.__loan_repository.find_by_address(key, pagination)

        return ItemsView(
            info=ItemsView.Info(
                offset=pagination.offset,
                limit=pagination.limit,
                total=total,
            ),
            items=loans,
        )


class ViewAllLoansCase:

    def __init__(self, loan_repository: LoanRepository) -> None:
        self.__loan_repository = loan_repository

    async def perform(self, pagination: PaginationOptions) -> ItemsView[LoanItem]:
        total = await self.__loan_repository.count()
        loans = await self.__loan_repository.find(pagination)

        return ItemsView(
            info=ItemsView.Info(
                offset=pagination.offset,
                limit=pagination.limit,
                total=total,
            ),
            items=loans,
        )

import pytest
import pytest_asyncio
from solders.keypair import Keypair

from spl_token_lending.container import Container
from spl_token_lending.domain.cases import UserLendingCase
from spl_token_lending.domain.data import (
    InitializedUserLoan,
    SubmittedUserLoan,
)
from spl_token_lending.repository.data import Amount, LoanItem
from spl_token_lending.repository.token import TokenRepository


@pytest.mark.slow
@pytest.mark.asyncio
class TestUserLendingCase:
    @pytest_asyncio.fixture(scope="class")
    async def executor(self, container: Container) -> UserLendingCase:
        return await container.user_lending_case()  # type: ignore[no-any-return,misc]

    @pytest_asyncio.fixture(scope="class")
    async def token_repo(self, container: Container) -> TokenRepository:
        return await container.token_repository()  # type: ignore[no-any-return,misc]

    @pytest_asyncio.fixture(scope="class")
    async def destination_wallet_keypair(self, container: Container) -> Keypair:
        # TODO: think how to make tests reproducible and remove keypair from the code, it's not secure to keep it here.
        return Keypair.from_base58_string(
            "43rz7Ac3hvcJU2aCg96FUWu7a1fz3xqHuLnpG2djnsncGcYvKWH2Vnc4YXwL4UjWzxJBQCMSWjW5j4mwDAYMVjHR")

    @pytest.mark.parametrize("amount", [
        pytest.param(
            Amount(1),
        ),
    ])
    @pytest.mark.asyncio
    async def test_user_lending_proceeds_successfully_with_sufficient_amount(
            self,
            executor: UserLendingCase,
            token_repo: TokenRepository,
            destination_wallet_keypair: Keypair,
            amount: Amount,
    ) -> None:
        token_amount_before = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())

        init_result = await executor.initialize(destination_wallet_keypair.pubkey(), amount)

        assert isinstance(init_result, InitializedUserLoan)
        initialized_loan = init_result.item
        assert initialized_loan == LoanItem(
            id_=initialized_loan.id_,
            status=LoanItem.Status.PENDING,
            address=destination_wallet_keypair.pubkey(),
            amount=amount,
        )

        signature = destination_wallet_keypair.sign_message(initialized_loan.id_.bytes)
        submit_result = await executor.submit(initialized_loan.id_, signature)

        assert isinstance(submit_result, SubmittedUserLoan)
        assert submit_result.item == LoanItem(
            id_=initialized_loan.id_,
            status=LoanItem.Status.ACTIVE,
            address=initialized_loan.address,
            amount=initialized_loan.amount,
        )

        token_amount_after = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())
        assert token_amount_after is not None
        assert amount == token_amount_after - (token_amount_before or 0)

import pytest
import pytest_asyncio
from solders.keypair import Keypair

from spl_token_lending.container import Container
from spl_token_lending.domain.cases import UserLendingCase
from spl_token_lending.domain.data import (
    FailedUserLoan, InitializedUserLoan,
    SubmittedUserLoan,
)
from spl_token_lending.repository.data import Amount
from spl_token_lending.repository.token import TokenRepository


# TODO: think about refilling the initial amount of tokens during the test start - it will make tests more
#  reproducible
@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.usefixtures("clean_database")
class TestUserLendingCase:
    AMOUNTS = [Amount(1), Amount(2)]

    @pytest_asyncio.fixture(scope="class")
    async def executor(self, container: Container) -> UserLendingCase:
        return await container.user_lending_case()  # type: ignore[no-any-return,misc]

    @pytest_asyncio.fixture(scope="class")
    async def token_repo(self, container: Container) -> TokenRepository:
        return await container.token_repository()

    @pytest_asyncio.fixture()
    async def destination_wallet_keypair(self, container: Container) -> Keypair:
        # TODO: think how to make tests reproducible but keep keypair value outside from the code, it's not secure to
        #  keep it here.
        return Keypair()

    @pytest.mark.parametrize("amount", AMOUNTS)
    @pytest.mark.asyncio
    async def test_token_amount_transferred_on_after_user_loan_submitted(
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

        token_amount_after_init = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())
        assert token_amount_after_init == token_amount_before

        signature = destination_wallet_keypair.sign_message(initialized_loan.id_.bytes)
        submit_result = await executor.submit(initialized_loan.id_, signature)

        assert isinstance(submit_result, SubmittedUserLoan)

        token_amount_after_submit = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())
        assert token_amount_after_submit is not None
        assert amount == token_amount_after_submit - (token_amount_before or 0)

    @pytest.mark.parametrize("amount", AMOUNTS)
    @pytest.mark.asyncio
    async def test_user_lending_fails_with_invalid_signature(
            self,
            executor: UserLendingCase,
            token_repo: TokenRepository,
            destination_wallet_keypair: Keypair,
            amount: Amount,
    ) -> None:
        other_keypair = Keypair()

        token_amount_before = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())

        init_result = await executor.initialize(destination_wallet_keypair.pubkey(), amount)

        assert isinstance(init_result, InitializedUserLoan)
        initialized_loan = init_result.item

        signature = other_keypair.sign_message(initialized_loan.id_.bytes)
        submit_result = await executor.submit(initialized_loan.id_, signature)

        assert isinstance(submit_result, FailedUserLoan)
        assert submit_result.error == "provided signature is invalid"

        token_amount_after = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())
        assert token_amount_after == token_amount_before

    @pytest.mark.parametrize("amount", [a * 1_000 for a in AMOUNTS])
    @pytest.mark.asyncio
    async def test_user_lending_fails_when_insufficient_amount(
            self,
            executor: UserLendingCase,
            token_repo: TokenRepository,
            destination_wallet_keypair: Keypair,
            amount: Amount,
    ) -> None:
        token_amount_before = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())

        init_result = await executor.initialize(destination_wallet_keypair.pubkey(), amount)

        assert isinstance(init_result, FailedUserLoan)
        assert init_result.error == "insufficient token amount on source account"

        token_amount_after = await token_repo.get_account_amount(destination_wallet_keypair.pubkey())
        assert token_amount_after == token_amount_before

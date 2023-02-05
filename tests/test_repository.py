from dataclasses import replace

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest
from solders.pubkey import Pubkey

from spl_token_lending.container import Container
from spl_token_lending.repository.data import Amount, LoanFilterOptions, LoanItem, PaginationOptions
from spl_token_lending.repository.loan import LoanRepository


@pytest.mark.usefixtures("clean_database")
@pytest.mark.asyncio
class TestLoanRepository:
    ITEM_VALUES = [
        (LoanItem.Status.PENDING, Pubkey.from_string("Dk5tmjFgGxqF8XbGvBwjJ4Unr1aStCQSQeED6nS8b6ab"),
         Amount(17)),
        (LoanItem.Status.ACTIVE, Pubkey.from_string("BuV7UvMpM9wXMDMjsQ1hfpfK4Y2GysDE4BmombWgouJi"),
         Amount(31)),
        (LoanItem.Status.CLOSED, Pubkey.from_string("8DDStVDaJYeh2wgANuFUVp5yvNNXuecoFJ1iq35B6XuS"),
         Amount(42)),
    ]

    @pytest_asyncio.fixture()
    async def repo(self, container: Container) -> LoanRepository:
        return await container.loan_repository()  # type: ignore[no-any-return,misc]

    @pytest_asyncio.fixture(params=ITEM_VALUES)
    async def created_loan(self, repo: LoanRepository, request: SubRequest) -> LoanItem:
        return await repo.create(*request.param)

    @pytest.mark.parametrize("status,wallet,amount", ITEM_VALUES)
    async def test_created_has_appropriate_values(
            self,
            repo: LoanRepository,
            status: LoanItem.Status,
            wallet: Pubkey,
            amount: Amount,
    ) -> None:
        created_item = await repo.create(status, wallet, amount)

        assert created_item == LoanItem(
            id_=created_item.id_,
            status=status,
            wallet=wallet,
            amount=amount,
        )

    @pytest.mark.parametrize("status,wallet,amount", ITEM_VALUES)
    async def test_loan_count_increases_after_creation(
            self,
            repo: LoanRepository,
            created_loan: LoanItem,
            status: LoanItem.Status,
            wallet: Pubkey,
            amount: Amount,
    ) -> None:
        count_before = await repo.count()
        await repo.create(status, wallet, amount)
        count_after = await repo.count()

        assert count_after == count_before + 1

    async def test_created_can_be_get_by_id(
            self,
            repo: LoanRepository,
            created_loan: LoanItem,
    ) -> None:
        retrieved_item = await repo.get_by_id(created_loan.id_)

        assert retrieved_item == created_loan

    async def test_created_can_by_found_by_wallet(self, repo: LoanRepository, created_loan: LoanItem) -> None:
        found_items = await repo.find(LoanFilterOptions(wallet_equals=created_loan.wallet), PaginationOptions())

        assert found_items == [created_loan, ]

    async def test_update_changes_status_for_appropriate_item(
            self,
            repo: LoanRepository,
            created_loan: LoanItem,
    ) -> None:
        expected_updated = replace(created_loan, status=LoanItem.Status.ACTIVE)
        actual_updated = await repo.update_existing_by_id(expected_updated)

        assert actual_updated == expected_updated

# TODO: implement tests for token repo
# @pytest.mark.asyncio
# class TestTokenRepository:
#     @pytest_asyncio.fixture()
#     async def repo(self, container: Container) -> LoanRepository:
#         return await container.token_repository()
#
#     async def test_get_amount_of_existing_account(self, repo: TokenRepository) -> None:
#         amount = await repo.get_amount()
#         await

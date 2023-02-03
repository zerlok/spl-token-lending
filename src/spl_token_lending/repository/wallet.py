import logging
import typing as t

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.rpc.responses import RequestAirdropResp

from spl_token_lending.repository.iterable import iter_with_exp_delay, wait_for_signature_status

_LOGGER = logging.getLogger(__name__)


class WalletRepositoryError(Exception):
    pass


class WalletRepository:

    def __init__(self, client: AsyncClient) -> None:
        self.__client = client

    async def create(self, amount: int) -> Keypair:
        wallet = Keypair()

        await self.init_balance(wallet, amount)

        return wallet

    async def init_balance(self, wallet: Keypair, amount: int) -> None:
        _LOGGER.debug("requesting airdrop to wallet", extra={"amount": amount, "wallet": wallet})

        airdrop_resp = await self.__request_airdrop(wallet, amount)
        if airdrop_resp is None:
            raise WalletRepositoryError("airdrop request failed", airdrop_resp, wallet)

        airdrop_finalized = await wait_for_signature_status(self.__client, airdrop_resp.value)
        if not airdrop_finalized:
            raise WalletRepositoryError("airdrop request failed", airdrop_resp, wallet, airdrop_finalized)

        if __debug__:
            resp = await self.__client.get_balance(wallet.pubkey())
            assert resp.value == amount

        _LOGGER.debug("airdrop requested to wallet", extra={
            "amount": amount,
            "wallet": wallet,
            "signature": airdrop_resp.value,
        })

    async def __request_airdrop(
            self,
            wallet: Keypair,
            amount: int,
    ) -> t.Optional[RequestAirdropResp]:
        async for _ in iter_with_exp_delay():
            airdrop_resp = await self.__client.request_airdrop(wallet.pubkey(), amount)

            _LOGGER.debug("airdrop response", extra={"resp": airdrop_resp, "wallet": wallet})
            if isinstance(airdrop_resp, RequestAirdropResp):
                return airdrop_resp

        return None

import logging
import typing as t
from pathlib import Path

from pydantic import BaseModel, Protocol, parse_file_as, validator
from solana.rpc.async_api import AsyncClient
from solana.rpc.core import RPCException
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.rpc.errors import SendTransactionPreflightFailureMessage
from solders.rpc.responses import GetTokenAccountBalanceResp
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address

from spl_token_lending.repository.data import Amount
from spl_token_lending.repository.iterable import wait_for_signature_status
from spl_token_lending.repository.wallet import WalletRepository

_LOGGER = logging.getLogger(__name__)


class TokenRepositoryError(Exception):
    pass


class TokenRepository:

    def __init__(self, client: AsyncClient, token: Pubkey, owner: Keypair) -> None:
        self.__client = client
        self.__owner = owner
        self.__token = AsyncToken(self.__client, token, TOKEN_PROGRAM_ID, owner)

    @property
    def token(self) -> Pubkey:
        return self.__token.pubkey

    @property
    def owner_pubkey(self) -> Pubkey:
        return self.__owner.pubkey()

    def get_account(self, wallet: Pubkey) -> Pubkey:
        return get_associated_token_address(wallet, self.__token.pubkey)

    async def get_or_create_account(self, wallet: Pubkey) -> Pubkey:
        account = self.get_account(wallet)

        resp = await self.__client.get_account_info(account)

        if resp.value is None:
            account = await self.create_account(wallet)

        return account

    async def create_account(self, wallet: Pubkey) -> Pubkey:
        _LOGGER.debug("creating token account", extra={"wallet": wallet})

        account = await self.__token.create_associated_token_account(wallet)
        _LOGGER.info("token account created", extra={"wallet": wallet, "account": account})

        return account

    async def get_account_amount(self, wallet: Pubkey) -> t.Optional[Amount]:
        account = self.get_account(wallet)

        resp = await self.__token.get_balance(account)

        return Amount(int(resp.value.amount)) if isinstance(resp, GetTokenAccountBalanceResp) else None

    async def transfer(self, wallet: Pubkey, amount: Amount) -> bool:
        source_account = self.get_account(self.__owner.pubkey())
        dest_account = await self.get_or_create_account(wallet)

        try:
            _LOGGER.debug("transfer started", extra={
                "source_account": source_account,
                "dest_account": dest_account,
                "amount": amount,
            })
            resp = await self.__token.transfer(source_account, dest_account, self.__owner, amount)

        except RPCException as err:
            transaction_err = self.__get_transaction_error(err)
            _LOGGER.warning("transfer failed", extra={
                "source_account": source_account,
                "dest_account": dest_account,
                "amount": amount,
                "err": transaction_err,
            }, exc_info=err)

            return False

        transfer_sig = resp.value

        ok = await wait_for_signature_status(self.__client, transfer_sig)
        if not ok:
            _LOGGER.warning("transfer transaction finalized status was not received, assuming transaction was failed",
                            extra={
                                "source_account": source_account,
                                "dest_account": dest_account,
                                "amount": amount,
                                "signature": transfer_sig
                            })

            return False

        _LOGGER.info("transaction succeeded", extra={
            "source_account": source_account,
            "dest_account": dest_account,
            "amount": amount,
            "signature": transfer_sig
        })

        return True

    def __get_transaction_error(self, err: RPCException) -> t.Optional[SendTransactionPreflightFailureMessage]:
        if len(err.args) > 0:
            arg0 = err.args[0]
            if isinstance(arg0, SendTransactionPreflightFailureMessage):
                return arg0

        return None


class TokenRepositoryConfig(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            Pubkey: str,
            Keypair: str,
        }

    owner: Keypair
    token: Pubkey

    @validator("token", pre=True)
    def validate_pubkey(cls, value: t.Union[str, Pubkey]) -> Pubkey:
        return Pubkey.from_string(value) if isinstance(value, str) else value

    @validator("owner", pre=True)
    def validate_keypair(cls, value: t.Union[str, Keypair]) -> Keypair:
        return Keypair.from_base58_string(value) if isinstance(value, str) else value


class TokenRepositoryInitializationError(Exception):
    pass


class TokenRepositoryFactory:
    def __init__(self, client: AsyncClient, airdrop_amount: int, mint_amount: int) -> None:
        self.__client = client
        self.__airdrop_amount = airdrop_amount
        self.__mint_amount = mint_amount
        self.__wallet_repository = WalletRepository(client)

    def create_from_config(self, config: TokenRepositoryConfig) -> TokenRepository:
        _LOGGER.debug("creating token repository from config", extra={"config": config.dict()})

        return TokenRepository(self.__client, config.token, config.owner)

    async def create_from_wallet(self, wallet: Keypair) -> TokenRepository:
        config = await self.__create_config_from_wallet(wallet)

        return self.create_from_config(config)

    # TODO: think about moving this config into DB
    async def create_from_path(self, path: Path) -> TokenRepository:
        _LOGGER.debug("creating token repository from config path", extra={"path": path})

        if path.exists():
            config = parse_file_as(TokenRepositoryConfig, path, proto=Protocol.json)

        else:
            config = await self.__create_config_path(path)

        return self.create_from_config(config)

    async def __create_config_path(self, path: Path) -> TokenRepositoryConfig:
        _LOGGER.info("creating new config for token repository", extra={"path": path})
        self.__check_path_writable(path)

        wallet = await self.__wallet_repository.create(self.__airdrop_amount)
        _LOGGER.info("new wallet initialized", extra={"wallet": wallet, "amount": self.__airdrop_amount})

        config = await self.__create_config_from_wallet(wallet)
        _LOGGER.debug("saving config", extra={"config": config.dict(), "path": path})

        self.__save_config(config, path)
        _LOGGER.info("new config saved", extra={"config": config.dict(), "path": path})

        return config

    async def __create_config_from_wallet(self, wallet: Keypair) -> TokenRepositoryConfig:
        _LOGGER.debug("initializing a new token", extra={"wallet": wallet})
        token = await AsyncToken.create_mint(self.__client, wallet, wallet.pubkey(), 9, TOKEN_PROGRAM_ID)
        _LOGGER.info("new token initialized", extra={"wallet": wallet, "token": token.pubkey})

        _LOGGER.debug("creating token account for wallet", extra={"wallet": wallet})
        wallet_token_account = await token.create_associated_token_account(wallet.pubkey())
        _LOGGER.info("token account for wallet created",
                     extra={"wallet": wallet, "token_account": wallet_token_account})

        # During the tests check that wallet, token and account has appropriate values
        assert wallet_token_account == get_associated_token_address(wallet.pubkey(), token.pubkey)
        assert wallet_token_account != wallet.pubkey()
        assert token.pubkey != wallet.pubkey()
        assert token.pubkey != wallet_token_account
        assert token.payer == wallet

        _LOGGER.debug("minting new tokens", extra={
            "wallet": wallet,
            "token_account": wallet_token_account,
            "amount": self.__mint_amount
        })
        mint_resp = await token.mint_to(wallet_token_account, token.payer, self.__mint_amount)
        _LOGGER.info("new tokens minted", extra={
            "wallet": wallet,
            "token_account": wallet_token_account,
            "amount": self.__mint_amount,
            "signature": mint_resp.value
        })

        config = TokenRepositoryConfig(
            owner=wallet,
            token=token.pubkey,
        )

        _LOGGER.info("config with new solana token created", extra={"wallet": wallet, "config": config.dict()})

        return config

    def __save_config(self, config: TokenRepositoryConfig, path: Path) -> None:
        with path.open("w") as f:
            f.write(config.json(by_alias=True))

    def __check_path_writable(self, path: Path) -> None:
        path.touch(mode=0o600, exist_ok=False)
        path.unlink(missing_ok=False)

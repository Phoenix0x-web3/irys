from dataclasses import dataclass

from data.config import ABIS_DIR
from data.settings import Settings
from libs.eth_async.classes import Singleton
from libs.eth_async.data.models import DefaultABIs, RawContract
from libs.eth_async.utils.files import read_json
from libs.exchanger.okx.models import OKXCredentials


class Contracts(Singleton):
    ETH = RawContract(title="ETH", address="0x0000000000000000000000000000000000000000", abi=DefaultABIs.Token)

    IRYS = RawContract(title="Irys", address="0xBC41F2B6BdFCB3D87c3d5E8b37fD02C56B69ccaC", abi=read_json(path=(ABIS_DIR, "irys.json")))

    IRYS_OMNIHUB_NFT = RawContract(title="IRYS_OMNIHUB_NFT", address="0x2E7eaC00E4c7D971A974918E3d4b8484Ea6f257e", abi=DefaultABIs.ERC721)

    IRYS_WEEP_NFT = RawContract(title="IRYS_WEEP_NFT", address="0xB041bF74fe472CAB9e1cacb1DAF92d51B0B87aC7", abi=DefaultABIs.ERC721)


settings = Settings()


@dataclass
class FromTo:
    from_: int | float
    to_: int | float


class OkxModel:
    required_minimum_balance: float
    withdraw_amount: FromTo
    delay_between_withdrawals: FromTo
    credentials: OKXCredentials


okx = OkxModel()
okx_credentials = OKXCredentials(api_key=settings.okx_api_key, secret_key=settings.okx_api_secret, passphrase=settings.okx_passphrase)

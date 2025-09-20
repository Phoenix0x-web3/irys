from data.config import ABIS_DIR
from libs.eth_async.classes import Singleton
from libs.eth_async.data.models import RawContract, DefaultABIs
from libs.eth_async.utils.files import read_json


class Contracts(Singleton):

    ETH = RawContract(
        title='ETH',
        address='0x0000000000000000000000000000000000000000',
        abi=DefaultABIs.Token
    )

    IRYS = RawContract(
        title='Irys',
        address='0xBC41F2B6BdFCB3D87c3d5E8b37fD02C56B69ccaC',
        abi=read_json(path=(ABIS_DIR, 'irys.json'))
    )

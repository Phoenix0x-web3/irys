import os

from web3.types import TxParams

from libs.base import Base
from libs.eth_async.client import Client
from libs.eth_async.data.models import RawContract, TokenAmount, TxArgs
from libs.eth_async.utils.files import read_json
from utils.browser import Browser
from utils.db_api.models import Wallet


class GalxeOnchain(Base):
    BASE_LINK = "https://graphigo.prd.galaxy.eco/query"

    def __init__(self, wallet: Wallet, browser: Browser, client: Client):
        self.client = client
        self.wallet = wallet
        self.browser = browser
        current_dir = os.path.dirname(__file__)
        self.galxe_points_contract = RawContract(
            title="GalxePoints",
            address="0x0c11DF9bB57c15926D5195B5F814c1a3aC07969C",
            abi=read_json(path=os.path.join(current_dir, "galxepoints.json")),
        )

    async def handle_claim_onchain_points(
        self, loyalty_point_address: str, verify_ids: list, amounts: list, claim_fee: str, signature: str
    ):
        if len(verify_ids) <= 1:
            return await self.claim_onchain_points(
                loyalty_point_address=loyalty_point_address,
                verify_id=verify_ids[0],
                amount=amounts[0],
                claim_fee=claim_fee,
                signature=signature,
            )
        else:
            return await self.claim_batch_onchain_points(
                loyalty_point_address=loyalty_point_address,
                verify_ids=verify_ids,
                amounts=amounts,
                claim_fee=claim_fee,
                signature=signature,
            )

    async def claim_batch_onchain_points(self, loyalty_point_address: str, verify_ids: list, amounts: list, claim_fee: str, signature: str):
        contract = await self.client.contracts.get(self.galxe_points_contract)
        if claim_fee:
            swap_params = TxArgs(
                _loyaltyPoint=loyalty_point_address,
                _verifyIds=[verify_ids],
                _users=[self.client.account.address],
                _amounts=[amounts],
                _claimFeeAmount=int(claim_fee),
                _signature=signature,
            )
            data = contract.encode_abi("increasePoints", args=(swap_params.tuple()))
            tx_params = TxParams(to=contract.address, data=data, value=int(claim_fee))
        else:
            swap_params = TxArgs(
                _loyaltyPoint=loyalty_point_address,
                _verifyIds=[verify_ids],
                _users=[self.client.account.address],
                _amounts=[amounts],
                _signature=0,
            )
            data = contract.encode_abi("increasePoints", args=(swap_params.tuple()))
            tx_params = TxParams(to=contract.address, data=data)

        result = await self.execute_transaction(
            tx_params=tx_params, activity_type=f"Claim batch {sum(amounts) / 10**18} points in Galxe {verify_ids} campaign"
        )

        if result.success:
            return result.tx_hash
        else:
            raise Exception(f"Claim batch points failed: {result.error_message}")

    async def claim_onchain_points(self, loyalty_point_address: str, verify_id: int, amount: int, claim_fee: str, signature: str):
        contract = await self.client.contracts.get(self.galxe_points_contract)
        if claim_fee:
            swap_params = TxArgs(
                _loyaltyPoint=loyalty_point_address,
                _verifyId=verify_id,
                _user=self.client.account.address,
                _amount=amount,
                _claimFeeAmount=int(claim_fee),
                _signature=signature,
            )
            data = contract.encode_abi("increasePoint", args=(swap_params.tuple()))
            tx_params = TxParams(to=contract.address, data=data, value=int(claim_fee))
        else:
            swap_params = TxArgs(
                _loyaltyPoint=loyalty_point_address,
                _verifyId=verify_id,
                _user=self.client.account.address,
                _amount=amount,
                _signature=signature,
            )
            data = contract.encode_abi("increasePoint", args=(swap_params.tuple()))
            tx_params = TxParams(to=contract.address, data=data)

        result = await self.execute_transaction(
            tx_params=tx_params, activity_type=f"Claim {amount / 10**18} points in Galxe {verify_id} campaign"
        )

        if result.success:
            return result.tx_hash
        else:
            raise Exception(f"Claim Points failed: {result.error_message}")

    async def gas_zip_bridge(self, client: Base, amount: TokenAmount):
        params = {
            "from": self.client.account.address,
            "to": self.client.account.address,
        }
        url_quote = f"https://backend.gas.zip/v2/quotes/{client.client.network.chain_id}/{amount.Wei}/1625"
        response = await self.browser.get(url=url_quote, params=params)
        data = response.json()
        trans_data = data["contractDepositTxn"]["data"]
        to = data["contractDepositTxn"]["to"]
        value = data["contractDepositTxn"]["value"]
        tx_params = TxParams(to=to, data=trans_data, value=value)

        result = await client.execute_transaction(
            tx_params=tx_params, activity_type=f"Gas Zip bridge from {client.client.network.name} {amount.Ether} Ether to Gravity"
        )

        if result.success:
            return result.tx_hash
        else:
            raise Exception(f"Gas Zip Bridge failed: {result.error_message}")

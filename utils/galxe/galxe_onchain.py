import os

from loguru import logger
from web3.types import TxParams

from libs.base import Base
from libs.eth_async.client import Client
from libs.eth_async.data.models import Network, RawContract, TokenAmount, TxArgs
from libs.eth_async.utils.files import read_json
from utils.browser import Browser
from utils.db_api.models import Wallet


class GalxeOnchain(Base):
    BASE_LINK = "https://graphigo.prd.galaxy.eco/query"

    def __init__(self, wallet: Wallet, browser: Browser, client: Client):
        self.client = client
        self.wallet = wallet
        self.browser = browser
        self.current_dir = os.path.dirname(__file__)
        self.galxe_points_contract = RawContract(
            title="GalxePoints",
            address="0x0c11DF9bB57c15926D5195B5F814c1a3aC07969C",
            abi=read_json(path=os.path.join(self.current_dir, "galxepoints.json")),
        )

    async def handle_claim_onchain_points(self, loyalty_point_address: str, verify_ids: list, amounts: list, claim_fee: str, signature: str):
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

        result = await self.execute_transaction(tx_params=tx_params, activity_type=f"Claim {amount / 10**18} points in Galxe {verify_id} campaign")

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

    async def subscription(self, client: Base, data: dict):
        data = data["data"]["registerInstantPaymentTask"]
        if client.client.network.name.upper() == "BASE":
            json_name = "base_galxe_subscription.json"
        else:
            json_name = "galxesubscription.json"
        contract = RawContract(title="Galxe Sub", address=data["contractAddress"], abi=read_json(path=os.path.join(self.current_dir, json_name)))
        contract = await self.client.contracts.get(contract)
        function = "crossChainSwapDeposit"
        tokenTransfers = []
        for transfer in data["tokenTransfers"]:
            amount = int(transfer["amount"])
            treasurer = transfer["treasurer"]
            tokenTransfers.append([amount, treasurer])

        swap_params = TxArgs(
            _user=self.client.account.address,
            _depositToken="0x0000000000000000000000000000000000000000",
            _depositAmount=int(data["taskFee"]),
            _taskId=int(data["taskId"]),
            _taskFee=int(data["taskFee"]),
            _targetEndpointId=int(data["crossChainSwapDepositResponse"]["targetEndpointId"]),
            _targetToken=data["crossChainSwapDepositResponse"]["targetToken"],
            _sourceSwap=[
                int(data["crossChainSwapDepositResponse"]["sourceSwap"]["minOut"]),
                data["crossChainSwapDepositResponse"]["sourceSwapPath"]
                if client.client.network.name.upper() == "BASE"
                else int(data["crossChainSwapDepositResponse"]["sourceSwap"]["feeTier"]),
            ],
            _targetSwap=[
                int(data["crossChainSwapDepositResponse"]["targetSwap"]["minOut"]),
                data["crossChainSwapDepositResponse"]["targetSwapPath"]
                if client.client.network.name.upper() == "BASE"
                else int(data["crossChainSwapDepositResponse"]["targetSwap"]["feeTier"]),
            ],
            _permit=[
                0,
                0,
                "0x0000000000000000000000000000000000000000000000000000000000000000",
                "0x0000000000000000000000000000000000000000000000000000000000000000",
            ],
            _nativeDrop=data["crossChainSwapDepositResponse"]["nativeDrop"],
            _messageFee=int(data["crossChainSwapDepositResponse"]["messageFee"]),
            _tokenTransfers=tokenTransfers,
            _signature=data["signature"],
        )

        transcation_data = contract.encode_abi(function, args=(swap_params.tuple()))
        tx_params = TxParams(to=contract.address, data=transcation_data, value=int(data["taskFee"]))

        result = await client.execute_transaction(tx_params=tx_params, activity_type=f"Galxe Subscription from {client.client.network.name}")

        if result.success:
            return result.tx_hash
        else:
            raise Exception(f"Galxe Subscription failed: {result.error_message}")

    async def relay_bridge(self, client: Base, amount: TokenAmount, to_chain: Network, to_wallet: str | None = None):
        json_data = {
            "user": f"{client.client.account.address}",
            "originChainId": client.client.network.chain_id,
            "destinationChainId": to_chain.chain_id,
            "originCurrency": "0x0000000000000000000000000000000000000000",
            "destinationCurrency": "0x0000000000000000000000000000000000000000",
            "recipient": f"{to_wallet if to_wallet else client.client.account.address}",
            "tradeType": "EXACT_INPUT",
            "amount": f"{amount.Wei}",
            "referrer": "relay.link/swap",
            "useExternalLiquidity": False,
            "useDepositAddress": False,
            "topupGas": False,
        }
        response = await self.browser.post(url="https://api.relay.link/quote", json=json_data)
        data = response.json()
        if "INSUFFICIENT_LIQUIDITY" in str(data):
            logger.warning(f"{self.wallet} relay don't  have enough liquidity for bridge")
            return False
        logger.debug(data)
        step = data["steps"][0]["items"][0]["data"]
        to_address = step["to"]
        tx_data = step["data"]
        to_address = self.client.w3.to_checksum_address(to_address)
        tx_params = TxParams(to=to_address, data=tx_data, value=amount.Wei)

        result = await client.execute_transaction(
            tx_params=tx_params, activity_type=f"Relay bridge from {client.client.network.name} {amount.Ether} Ether to {to_chain.name}"
        )

        if result.success:
            return result.tx_hash
        else:
            raise Exception(f"Relay Bridge failed: {result.error_message}")

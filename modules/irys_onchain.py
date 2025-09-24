from datetime import datetime
import time
import asyncio
from loguru import logger
from web3.types import TxParams

from data.models import Contracts
from data.settings import Settings
from libs.eth_async.data.models import TokenAmount
from utils.db_api.wallet_api import last_faucet_claim
from utils.db_api.models import Wallet
from utils.captcha.captcha_handler import CaptchaHandler
from utils.retry import async_retry
from libs.base import Base
from libs.eth_async.client import Client

class IrysOnchain(Base):
    def __init__(self, client: Client, wallet: Wallet):
        super().__init__(client, wallet)
        self.proxy_errors = 0

    async def mint_irys(self):
        balance_in_irys = await self.client.wallet.balance()
        contract = await self.client.contracts.get(Contracts.IRYS_OMNIHUB_NFT)
        balance = await self.check_nft_balance(contract=contract)
        if balance and not Settings().multiple_mint:
            logger.debug(f"{self.wallet} already have {balance} NFT and Multiple Mint Off")
            return
        if balance_in_irys.Ether < TokenAmount(amount=0.001).Ether:
            logger.warning(f"{self.wallet} balance not enough for mint Irys x OmniHub NFT")
            return
        data = "0xa25ffea800000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000000"
        mint_value = TokenAmount(amount=1000000000000000, wei=True)
        tx_params = TxParams(to=contract.address, data=data, value=mint_value.Wei)

        result = await self.execute_transaction(tx_params=tx_params, activity_type="Mint Irys x OmniHub NFT")

        contract = await self.client.contracts.get(Contracts.IRYS_WEEP_NFT)
        clear_address = str(self.client.account.address)[2:].lower()
        data = f"0x57bc3d78000000000000000000000000{clear_address}00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001000000000000000000000000eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000e0000000000000000000000000000000000000000000000000000000000000018000000000000000000000000000000000000000000000000000000000000000800000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
        tx_params = TxParams(to=contract.address, data=data)

        try:
            estimate_gas = await self.client.transactions.auto_add_params(tx_params=tx_params)
            logger.debug(estimate_gas)
        except Exception:
            logger.debug(f"{self.wallet} have > 20 Irys Weep NFT.")
            return True
        result = await self.execute_transaction(tx_params=tx_params, activity_type="Mint Irys Weep NFT")

        if result.success:
            return result.tx_hash
        else:
            raise Exception(f"Error Mint Irys x Weep NFT: {result.error_message}")


    @async_retry()
    async def irys_faucet(self):
        balance_in_irys = await self.client.wallet.balance()
        captcha_handler = CaptchaHandler(wallet=self.wallet)
        token = await captcha_handler.cloudflare_token(websiteURL="https://irys.xyz/faucet", websiterKey="0x4AAAAAAA6vnrvBCtS4FAl-")
        token = token['token']
        json_data = {
            'captchaToken': f'{token}',
            'walletAddress': f'{self.wallet.address}',
        }
        response = await self.browser.post(url="https://irys.xyz/api/faucet", json=json_data)
        data = response.json()
        last_faucet_claim(address=self.wallet.address, last_faucet_claim=datetime.utcnow())
        if data['success']:
            logger.success(f"{self.wallet} success get Irys Token from Faucet")
            return await self.wait_deposit(start_balance = balance_in_irys)
        else:
            logger.warning(f"{self.wallet} can't get Irys Token from Faucet message: {data['message']}")
        return data['success']

    @async_retry()
    async def wait_deposit(self, start_balance: TokenAmount):
        timeout = 60 * 30   
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                logger.warning(f"{self.wallet} faucet did not arrive after {timeout} seconds")
                return False

            logger.info(f"{self.wallet} waiting for faucet (elapsed: {int(elapsed)}s)")
            balance = await self.client.wallet.balance()

            if start_balance.Wei < balance.Wei:
                logger.info(f"{self.wallet} faucet detected")
                return True

            await asyncio.sleep(5)
    
    @async_retry()
    async def handle_balance(self):
        balance_in_platform = await self.check_platform_balance()
        logger.debug(balance_in_platform)
        if balance_in_platform.Ether > 0.001:
            return True
        balance_in_irys = await self.client.wallet.balance()
        logger.debug(balance_in_irys)
        if balance_in_irys.Ether < 0.01:
            faucet = await self.irys_faucet()
            if faucet:
                return await self.handle_balance()
            else:
                return False
        amount = float(balance_in_irys.Ether) * 0.9
        amount = TokenAmount(amount=amount)
        return await self.bridge_to_platform(amount=amount)
        
    async def bridge_to_platform(self, amount: TokenAmount):
        contract = await self.client.contracts.get(Contracts.IRYS)
        data = contract.encode_abi("deposit")
        tx_params = TxParams(to=contract.address, data=data, value=amount.Wei)

        result = await self.execute_transaction(tx_params=tx_params, activity_type=f"Deposit to Irys Platform {amount.Ether}")

        if result.success:
            return result.tx_hash
        else:
            raise Exception(f"Error Deposit to Irys Platform: {result.error_message}")

    async def check_platform_balance(self):
        contract = await self.client.contracts.get(Contracts.IRYS)
        balance = await contract.functions.getUserBalance(self.client.account.address).call()
        return TokenAmount(balance, wei=True)

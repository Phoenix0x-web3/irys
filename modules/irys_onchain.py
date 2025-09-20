from datetime import datetime
from loguru import logger
from web3.types import TxParams

from data.models import Contracts
from libs.eth_async.data.models import TokenAmount
from utils.db_api.wallet_api import last_faucet_claim
from utils.db_api.models import Wallet
from utils.captcha.captcha_handler import CaptchaHandler
from libs.base import Base
from libs.eth_async.client import Client

class IrysOnchain(Base):
    def __init__(self, client: Client, wallet: Wallet):
        super().__init__(client, wallet)
        self.proxy_errors = 0

    async def irys_faucet(self):
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
        else:
            logger.warning(f"{self.wallet} can't get Irys Token from Faucet message: {data['message']}")
        return data['success']
    
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

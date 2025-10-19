import asyncio
from loguru import logger
from datetime import datetime,timedelta
import random
from libs.eth_async.client import Client
from libs.base import Base
from libs.eth_async.data.models import Networks
from modules.irys_client import Irys
from modules.quests_client import Quests
from modules.irys_onchain import IrysOnchain

from utils.db_api.models import Wallet
from utils.db_api.wallet_api import mark_galxe_account_banned
from utils.galxe.galxe_client import GalxeClient


class Controller:

    def __init__(self, client: Client, wallet: Wallet):
        #super().__init__(client)
        self.client = client
        self.wallet = wallet
        self.base = Base(client=client, wallet=wallet)
        self.irys_client = Irys(client=client,wallet=wallet)
        self.quest_client = Quests(client=client,wallet=wallet)
        self.irys_onchain = IrysOnchain(client=Client(private_key=self.client.account._private_key.hex(), network=Networks.Irys, proxy=self.wallet.proxy), wallet=wallet)

    async def complete_portal_games(self):
        if await self.irys_onchain.handle_balance():
            return await self.irys_client.handle_arcade_game()

    async def complete_spritetype_games(self):
        return await self.irys_client.handle_spritetype_game()

    async def complete_onchain(self):
        if not self.wallet.last_faucet_claim or self.wallet.last_faucet_claim + timedelta(hours=24) < datetime.utcnow():
            await self.irys_onchain.irys_faucet()
        functions = [
            self.irys_onchain.mint_irys,
        ]
        random.shuffle(functions)
        for func in functions:
            await func()
        return

    async def complete_galxe_quests(self):
        galxe_client = GalxeClient(wallet=self.wallet, client=self.client)
        
        if await galxe_client.is_account_banned():
            logger.error(f"{self.wallet} Galxe account is banned!")
            mark_galxe_account_banned(id=self.wallet.id)
            return
        
        if self.wallet.galxe_account_banned:
            mark_galxe_account_banned(id=self.wallet.id, banned=False)
        
        if await galxe_client.handle_subscribe():
            logger.success(f"{self.wallet} subscribed to Galxe Premium")

        functions = [
            self.quest_client.complete_twitter_galxe_quests,
            self.quest_client.complete_spritetype_galxe_quests,
            self.quest_client.complete_irysverse_quiz,
            self.quest_client.complete_daily_irysverse_galxe_quests,
            self.quest_client.complete_irys_other_games_quests,
        ]
        random.shuffle(functions)
        for func in functions:
            try:
                await func(galxe_client)
            except Exception:
                continue
        await self.quest_client.get_and_claim_mystery_box(galxe_client)
        await self.quest_client.claim_rewards(galxe_client)
        await self.quest_client.update_points(galxe_client)
        return
    
    
    async def complete_galxe_quests_with_banned_account(self):
        galxe_client = GalxeClient(wallet=self.wallet, client=self.client)
        
        if await galxe_client.is_account_banned():
            logger.warning(f"{self.wallet} banned: Galxe account is banned! Continuing quests without subscription")
            mark_galxe_account_banned(id=self.wallet.id)
        else:
            mark_galxe_account_banned(id=self.wallet.id, banned=False)
            
        functions = [
            self.quest_client.complete_twitter_galxe_quests,
            self.quest_client.complete_spritetype_galxe_quests,
            self.quest_client.complete_irysverse_quiz,
            self.quest_client.complete_daily_irysverse_galxe_quests,
            self.quest_client.complete_irys_other_games_quests,
        ]
        random.shuffle(functions)
        for func in functions:
            try:
                await func(galxe_client)
            except Exception:
                continue
 
        await self.quest_client.claim_rewards(galxe_client)
        await self.quest_client.update_points(galxe_client)
        return


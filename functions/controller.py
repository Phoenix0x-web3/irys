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
        if self.wallet.completed_games and self.wallet.completed_games >= 1000:
            logger.info(f"{self.wallet} already have {self.wallet.completed_games} sprite type games")
            return False
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
        logger.warning(f"Galxe is unavailable now fixing bugs")
        return
        galxe_client = GalxeClient(wallet=self.wallet, client=self.client)
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
        await self.quest_client.update_points(galxe_client)
        return


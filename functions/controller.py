from loguru import logger
import random
from libs.eth_async.client import Client
from libs.base import Base
from modules.irys_client import Irys
from modules.quests_client import Quests

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

    async def complete_games(self):
        if self.wallet.completed_games and self.wallet.completed_games >= 1000:
            logger.info(f"{self.wallet} already have {self.wallet.completed_games} completed games")
            return False
        return await self.irys_client.handle_game()

    async def complete_galxe_quests(self):
        galxe_client = GalxeClient(wallet=self.wallet, client=self.client)
        functions = [
            self.quest_client.complete_twitter_galxe_quests,
            self.quest_client.complete_spritetype_galxe_quests,
            self.quest_client.complete_irysverse_quiz,
            self.quest_client.complete_daily_irysverse_galxe_quests,
        ]
        random.shuffle(functions)
        for func in functions:
            await func(galxe_client)
        await self.quest_client.update_points(galxe_client)
        return


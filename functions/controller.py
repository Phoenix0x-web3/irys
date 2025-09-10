from loguru import logger
import random
from libs.eth_async.client import Client
from libs.base import Base
from modules.irys_client import Irys

from utils.db_api.models import Wallet
from utils.db_api.wallet_api import db
from utils.logs_decorator import controller_log


class Controller:

    def __init__(self, client: Client, wallet: Wallet):
        #super().__init__(client)
        self.client = client
        self.wallet = wallet
        self.base = Base(client=client, wallet=wallet)
        self.irys_client = Irys(client=client,wallet=wallet)

    async def complete_games(self):
        if self.wallet.completed_games and self.wallet.completed_games >= 1000:
            logger.info(f"{self.wallet} already have {self.wallet.completed_games} completed games")
            return False
        return await self.irys_client.handle_game()

    async def complete_galxe_quests(self):
        functions = [
            self.irys_client.complete_twitter_galxe_quests,
            self.irys_client.complete_galxe_quests,
        ]
        random.shuffle(functions)
        for func in functions:
            await func()
        return


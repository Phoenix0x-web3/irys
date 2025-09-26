import asyncio
import random

from loguru import logger

from data.settings import Settings
from libs.eth_async.client import Client
from libs.eth_async.data.models import Network, Networks
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import update_points, update_rank
from utils.galxe.galxe_client import GalxeClient
from utils.twitter.twitter_client import TwitterClient

from .irys_client import Irys


class Quests(Irys):
    def __init__(self, client: Client, wallet: Wallet):
        super().__init__(client, wallet)
        self.proxy_errors = 0

    async def update_points(self, galxe_client):
        points, rank = await galxe_client.update_points_and_rank(campaign_id=58934)
        update_points(address=self.wallet.address, points=points)
        update_rank(address=self.wallet.address, rank=rank)
        logger.info(f"{self.wallet} have {self.wallet.points} points and rank {self.wallet.rank} in Galxe")

    async def complete_irys_other_games_quests(self, galxe_client: GalxeClient):
        campaign_ids = ["GCtydt8Ewv", "GCLV4t8ikW", "GC9r4t8ajy", "GCsd4t89L9", "GCFE4t8HrF"]
        random.shuffle(campaign_ids)
        for campaign_id in campaign_ids:
            info = await galxe_client.get_quest_cred_list(campaign_id=campaign_id)
            reward_configs = info["data"]["campaign"]["taskConfig"]["rewardConfigs"]
            reward_tiers = []
            for config in reward_configs:
                condition = config["conditions"][0]
                cred = condition["cred"]
                cred_id = int(cred["id"])
                exp_reward = int(config["rewards"][0]["arithmeticFormula"])
                eligible = config["eligible"]

                reward_tiers.append(
                    {
                        "cred_id": cred_id,
                        "exp_reward": exp_reward,
                        "eligible": eligible,
                        "name": cred["name"],
                    }
                )

            logger.debug(reward_tiers)

            for tier in reward_tiers:
                if not tier["eligible"]:
                    sync = await galxe_client.sync_quest(cred_id=tier["cred_id"])
                    if sync:
                        logger.success(f"{self.wallet} success sync quest for {tier['name']} on Galxe")
                        await asyncio.sleep(15)
                    else:
                        continue

            if await self.check_available_claim():
                await galxe_client.claim_points(campaign_id=campaign_id)

    async def complete_irysverse_quiz(self, galxe_client: GalxeClient):
        campaign_ids = ["GCVs3t6iHA"]
        for campaign_id in campaign_ids:
            info = await galxe_client.get_quest_cred_list(campaign_id=campaign_id)
            reward_configs = info["data"]["campaign"]["taskConfig"]["rewardConfigs"]
            reward_tiers = []
            for config in reward_configs:
                condition = config["conditions"][0]
                cred = condition["cred"]
                cred_id = int(cred["id"])
                exp_reward = int(config["rewards"][0]["arithmeticFormula"])
                eligible = config["eligible"]

                reward_tiers.append(
                    {
                        "cred_id": cred_id,
                        "exp_reward": exp_reward,
                        "eligible": eligible,
                        "name": cred["name"],
                    }
                )

            logger.debug(reward_tiers)

            for tier in reward_tiers:
                if not tier["eligible"]:
                    for _ in range(2):
                        sync = await galxe_client.sync_quiz(cred_id=tier["cred_id"], answers=["3", "0", "2", "0", "2", "2"])
                        if sync:
                            logger.success(f"{self.wallet} success sync quest for {tier['name']} on Galxe")
                            await asyncio.sleep(15)
                            break
                        else:
                            logger.warning(f"{self.wallet} can't sync quest for {tier['name']} on Galxe. Wait update")
                            continue

            if await self.check_available_claim():
                await galxe_client.claim_points(campaign_id=campaign_id)

    async def complete_daily_irysverse_galxe_quests(self, galxe_client: GalxeClient):
        campaign_ids = ["GCo13t6RXN"]
        for campaign_id in campaign_ids:
            info = await galxe_client.get_quest_cred_list(campaign_id=campaign_id)
            reward_configs = info["data"]["campaign"]["taskConfig"]["rewardConfigs"]
            reward_tiers = []
            for config in reward_configs:
                condition = config["conditions"][0]
                cred = condition["cred"]
                cred_id = int(cred["id"])
                exp_reward = int(config["rewards"][0]["arithmeticFormula"])
                eligible = config["eligible"]

                reward_tiers.append(
                    {
                        "cred_id": cred_id,
                        "exp_reward": exp_reward,
                        "eligible": eligible,
                        "name": cred["name"],
                    }
                )

            logger.debug(reward_tiers)
            for tier in reward_tiers:
                if not tier["eligible"]:
                    for _ in range(3):
                        await galxe_client.add_type(cred_id=tier["cred_id"], campaign_id=campaign_id)
                        sync = await galxe_client.sync_quest(cred_id=tier["cred_id"])
                        if sync:
                            logger.success(f"{self.wallet} success sync quest for {tier['name']} on Galxe")
                            await asyncio.sleep(15)
                            break
                        else:
                            logger.warning(f"{self.wallet} can't sync quest for {tier['name']} on Galxe. Wait update")
                            continue

            if await self.check_available_claim():
                await galxe_client.claim_points(campaign_id=campaign_id)

    async def complete_twitter_galxe_quests(self, galxe_client: GalxeClient):
        twitter_client = TwitterClient(user=self.wallet)
        campaign_ids = ["GC17CtmBrm"]
        random.shuffle(campaign_ids)
        for campaign_id in campaign_ids:
            info = await galxe_client.get_quest_cred_list(campaign_id=campaign_id)
            reward_configs = info["data"]["campaign"]["taskConfig"]["rewardConfigs"]
            reward_tiers = []
            for config in reward_configs:
                condition = config["conditions"][0]
                cred = condition["cred"]
                cred_id = int(cred["id"])
                follow_name = cred["name"].split("-")[0].strip()
                exp_reward = int(config["rewards"][0]["arithmeticFormula"])
                eligible = config["eligible"]

                reward_tiers.append(
                    {"cred_id": cred_id, "exp_reward": exp_reward, "eligible": eligible, "name": cred["name"], "follow_name": follow_name}
                )

            logger.debug(reward_tiers)
            for tier in reward_tiers:
                if not tier["eligible"]:
                    follow = await self.complete_twitter_task(
                        twitter_client=twitter_client, galxe_client=galxe_client, follow=tier["follow_name"]
                    )
                    if not follow:
                        logger.warning(f"{self.wallet} can't complete twitter quest")
                        return False

                    for _ in range(2):
                        sync = await galxe_client.sync_twitter_quest(cred_id=tier["cred_id"], campaign_id=campaign_id)
                        if sync:
                            logger.success(f"{self.wallet} success sync quest for {tier['name']} on Galxe")
                            # Keep that for next quest
                            # await asyncio.sleep(15)
                            # try:
                            #     await galxe_client.claim_points(campaign_id=campaign_id)
                            # except Exception:
                            #     await asyncio.sleep(60)
                            #     continue
                            break
                        else:
                            logger.warning(f"{self.wallet} can't sync quest for {tier['name']} on Galxe. Wait update")
                            await asyncio.sleep(60)
                            continue
                # else:
                #     try:
                #         await galxe_client.claim_points(campaign_id=campaign_id)
                #     except Exception as e:
                #         logger.info(f"{self.wallet} already claimed points for {tier['name']} quest")
                #         logger.debug(f"Wrong with claim {e}")

    async def complete_spritetype_galxe_quests(self, galxe_client: GalxeClient):
        completed_games = self.wallet.completed_games
        campaign_ids = ["GCFtLtfrJH", "GCLjLtf7zj"]
        random.shuffle(campaign_ids)
        for campaign_id in campaign_ids:
            info = await galxe_client.get_quest_cred_list(campaign_id=campaign_id)
            reward_configs = info["data"]["campaign"]["taskConfig"]["rewardConfigs"]
            reward_tiers = []
            for config in reward_configs:
                condition = config["conditions"][0]
                cred = condition["cred"]
                if campaign_id == "GCLjLtf7zj":
                    plays_required = int(cred["name"].split()[2])
                elif campaign_id == "GCFtLtfrJH":
                    plays_required = int(cred["name"].split()[0])
                else:
                    plays_required = 50
                cred_id = int(cred["id"])
                exp_reward = int(config["rewards"][0]["arithmeticFormula"])
                eligible = config["eligible"]

                reward_tiers.append(
                    {
                        "cred_id": cred_id,
                        "plays_required": plays_required,
                        "exp_reward": exp_reward,
                        "eligible": eligible,
                        "name": cred["name"],
                    }
                )

            logger.debug(reward_tiers)
            for tier in reward_tiers:
                if completed_games >= tier["plays_required"]:
                    if not tier["eligible"]:
                        for _ in range(2):
                            sync = await galxe_client.sync_quest(cred_id=tier["cred_id"])
                            if sync:
                                logger.success(f"{self.wallet} success sync quest for {tier['plays_required']} on Galxe")
                                await asyncio.sleep(15)
                                try:
                                    if await self.check_available_claim():
                                        await galxe_client.claim_points(campaign_id=campaign_id)
                                except Exception:
                                    await asyncio.sleep(60)
                                    continue
                                break
                            else:
                                logger.warning(f"{self.wallet} can't sync quest for {tier['plays_required']} on Galxe. Wait update")
                                continue
                    else:
                        try:
                            if await self.check_available_claim():
                                await galxe_client.claim_points(campaign_id=campaign_id)
                        except Exception as e:
                            logger.info(f"{self.wallet} already claimed points for {tier['name']} quest")
                            logger.debug(f"Wrong with claim {e}")

    async def get_tweet_url(self, id: str, twitter_client):
        text = f"Verifying my Twitter account for my #GalxeID gid:{id} @Galxe "
        tweet = await twitter_client.post_tweet(text=text)
        if tweet:
            return f"https://x.com/{twitter_client.twitter_account.username}/status/{tweet.id}"

    async def complete_twitter_task(self, twitter_client, galxe_client, follow: str):
        if self.wallet.twitter_status != "OK":
            logger.warning(f"{self.wallet} twitter status is {self.wallet.twitter_status}. Skip Twitter quests")
            return False
        if not self.wallet.twitter_token:
            logger.warning(f"{self.wallet} doesn't have twitter tokens for twitters action")
            return False
        if not await twitter_client.initialize():
            return False
        session = await galxe_client.session()
        twitter_connect_id = session["data"]["addressInfo"]["twitterUserID"]
        twitter_id = twitter_client.twitter_account.id
        if twitter_connect_id and int(twitter_connect_id) != int(twitter_id):
            twitter_connect_id = None
            await galxe_client.delete_social_account(social="twitter")
            await asyncio.sleep(5)
        if not twitter_connect_id:
            id = session["data"]["addressInfo"]["id"]
            tweet_url = await self.get_tweet_url(id=id, twitter_client=twitter_client)
            if not tweet_url:
                logger.error(f"{self.wallet} can't post tweets")
                return False
            connect = await galxe_client.connect_twitter(tweet_url=tweet_url)
            if connect["data"]["verifyTwitterAccount"]["twitterUserID"]:
                logger.success(f"{self.wallet} success twitter connect")
        return await twitter_client.follow_account(account_name=follow)

    async def check_available_claim(self):
        gravity_balance = await self.client.wallet.balance()
        if gravity_balance.Ether > 2.5:
            return True
        network_values = [value for key, value in Networks.__dict__.items() if isinstance(value, Network)]
        random.shuffle(network_values)
        for network in network_values:
            if network.name in Settings().network_for_bridge:
                try:
                    client = Client(private_key=self.client.account._private_key.hex(), network=network, proxy=self.client.proxy)
                    balance = await client.wallet.balance()
                    if balance.Ether > Settings().random_eth_for_bridge_max:
                        return True
                except Exception as e:
                    logger.warning(f"{self.wallet} can't check network {network.name} error: {e}")
                    continue
        logger.warning(f"{self.wallet} account without funds for claim Galxe Points")
        return False

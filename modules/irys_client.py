import hashlib
import asyncio
import time
import random
from loguru import logger

from utils.db_api.wallet_api import add_count_game, get_wallet_by_address
from utils.db_api.models import Wallet
from utils.galxe.galxe_client import GalxeClient
from utils.browser import Browser
from utils.retry import async_retry
from data.settings import Settings
from libs.base import Base
from libs.eth_async.client import Client

class Irys(Base):
    def __init__(self, client: Client, wallet: Wallet):
        super().__init__(client, wallet)
        self.proxy_errors = 0

    async def handle_game(self):
        random_playing_games = random.randint(7,10)
        logger.info(f"{self.wallet} will be {random_playing_games} times in this hour")
        playing_game = 0
        errors_game = 0
        while True:
            if errors_game > 3:
                return False
            if playing_game >= random_playing_games:
                return True
            game = await self.complete_game()
            if game:
                errors_game = 0
                playing_game += 1
                random_sleep = random.randint(Settings().random_pause_between_actions_min, Settings().random_pause_between_actions_max)
                logger.info(f"{self.wallet} sleep {random_sleep} seconds before next game")
                await asyncio.sleep(random_sleep)
            else:
                errors_game += 1
                continue

    async def complete_galxe_quests(self,):
        completed_games = self.wallet.completed_games
        campaign_ids = ["GCFtLtfrJH", "GCLjLtf7zj", "GCY3gt6MQE"]
        galxe_client = GalxeClient(wallet=self.wallet, client=self.client)
        random.shuffle(campaign_ids)
        for campaign_id in campaign_ids:
            info = await galxe_client.get_quest_cred_list(campaign_id=campaign_id)
            reward_configs = info['data']['campaign']['taskConfig']['rewardConfigs']
            reward_tiers = []
            for config in reward_configs:
                condition = config['conditions'][0]
                cred = condition['cred']
                if campaign_id == "GCLjLtf7zj":
                    plays_required = int(cred['name'].split()[2])
                elif campaign_id == "GCFtLtfrJH":
                    plays_required = int(cred['name'].split()[0])
                else:
                    plays_required = 50
                cred_id = int(cred['id'])
                exp_reward = int(config['rewards'][0]['arithmeticFormula'])
                eligible = config['eligible']
                
                reward_tiers.append({
                    'cred_id': cred_id,
                    'plays_required': plays_required,
                    'exp_reward': exp_reward,
                    'eligible': eligible,
                    'name': cred['name']
                })

            logger.debug(reward_tiers)
            for tier in reward_tiers:
                if completed_games >= tier['plays_required']:
                    if not tier['eligible']:
                        sync = await galxe_client.sync_quest(cred_id=tier['cred_id'])
                        for _ in range(2):
                            if sync:
                                logger.success(f"{self.wallet} success sync quest for {tier['plays_required']} on Galxe")
                                await asyncio.sleep(15)
                                try:
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
                            await galxe_client.claim_points(campaign_id=campaign_id)
                        except Exception as e:
                            logger.info(f"{self.wallet} already claimed points for {tier['name']} quest")
                            logger.debug(f"Wrong with claim {e}")

        await galxe_client.update_points_and_rank(campaign_id=58934)
        logger.info(f"{self.wallet} all claim or don't eligible to any points in Galxe")


    @async_retry()
    async def complete_game(self):
        headers = {
            'origin': 'https://spritetype.irys.xyz',
            'priority': 'u=1, i',
            'referer': 'https://spritetype.irys.xyz/',
            'sec-ch-ua-mobile': '?0',
        }
        stats = await self.generate_realistic_stats()
        logger.debug(stats)
        address = self.client.account.address
        wpm = stats["wpm"]
        accuracy = stats["accuracy"]
        time_stats = stats["time"]
        correct_chars = stats["correct_chars"]
        incorrect_chars = stats["incorrect_chars"]
        hash_result = await self.generate_anticheat_hash(wallet_address=address, wpm=wpm, accuracy=accuracy, time=time_stats, correct_chars=correct_chars, incorrect_chars=incorrect_chars)
        logger.info(f"{self.wallet} play {time_stats} seconds in game")
        await asyncio.sleep(time_stats)
        json_data = {
            'walletAddress': address,
            'gameStats': {
                'wpm': wpm,
                'accuracy': accuracy,
                'time': time_stats,
                'correctChars': correct_chars,
                'incorrectChars': incorrect_chars,
                'progressData': [],
            },
            'antiCheatHash': hash_result,
            'timestamp': int(time.time() * 1000),
        }
        request = None
        try:
            request = await self.browser.post(url="https://spritetype.irys.xyz/api/submit-result", headers=headers, json=json_data)
        except Exception as e:
            logger.warning(
                f"{self.wallet} connection error during request"
            )

            # Increment proxy error counter
            if (
                "proxy" in str(e).lower()
                or "connection" in str(e).lower()
                or "connect" in str(e).lower()
            ):
                self.proxy_errors += 1

                # If proxy error limit exceeded, mark proxy as bad
                max_proxy_errors = 3
                if self.proxy_errors >= max_proxy_errors:
                    logger.warning(
                        f"{self.wallet} proxy error limit exceeded ({self.proxy_errors}/{max_proxy_errors}), marking as BAD"
                    )
                    from utils.resource_manager import ResourceManager

                    resource_manager = ResourceManager()
                    await resource_manager.mark_proxy_as_bad(self.wallet.address)

                    # If auto-replace is enabled, try to replace proxy
                    if Settings().auto_replace_proxy:
                        success, message = await resource_manager.replace_proxy(
                            self.wallet.id
                        )
                        if success:
                            logger.info(
                                f"{self.wallet} proxy automatically replaced: {message}"
                            )
                            updated_user = get_wallet_by_address(address=self.wallet.address)
                            if updated_user:
                                self.wallet.proxy = updated_user.proxy
                                self.proxy_errors = 0
                                self.browser = Browser(self.wallet)
                        else:
                            logger.error(
                                f"{self.wallet} failed to replace proxy: {message}"
                            )

        if not request:
            return False
        data = request.json()
        if request.status_code == 200 and data['success']:
            logger.success(f"{self.wallet} success play game with {wpm} wpm")
            return add_count_game(address=self.wallet.address)
        return False


    async def generate_realistic_stats(self):
        """
        Generate realistic typing game statistics based on user typing level.
        
        Returns:
            dict: Dictionary containing wpm, accuracy, time, correct_chars, incorrect_chars
        """
        time = random.choice([15, 30, 60, 120])

        level = self.wallet.typing_level

        if level == 1:
            wpm = int(random.gauss(40, 5))
            accuracy = random.randint(85, 95)
        elif level == 2:
            wpm = int(random.gauss(65, 10))
            accuracy = random.randint(90, 98)
        elif level == 3:
            wpm = int(random.gauss(90, 10))
            accuracy = random.randint(93, 100)
        else:
            # fallback на случай некорректного уровня
            wpm = int(random.gauss(60, 15))
            accuracy = random.randint(90, 98)

        # Ограничиваем wpm, чтобы не вылезал за реальные рамки
        wpm = max(30, min(wpm, 130))

        correct_chars = int(wpm * 5 * (time / 60))

        if accuracy == 100:
            incorrect_chars = 0
        else:
            incorrect_chars = int(correct_chars * (100 - accuracy) / accuracy)

        return {
            "wpm": wpm,
            "accuracy": accuracy,
            "time": time,
            "correct_chars": correct_chars,
            "incorrect_chars": incorrect_chars
        }

    async def generate_anticheat_hash(self, wallet_address, wpm, accuracy, time, correct_chars, incorrect_chars):
        """
        Generate antiCheatHash based on wallet address and game statistics.
        
        Args:
            wallet_address (str): Wallet address (e.g., '0xabc')
            wpm (int): Words per minute
            accuracy (int): Accuracy percentage
            time (int): Game duration in seconds
            correct_chars (int): Number of correctly typed characters
            incorrect_chars (int): Number of incorrectly typed characters
        
        Returns:
            str: First 32 characters of SHA-256 hash
        """
        # Step 1: Compute intermediate values (replicating JS logic)
        total_chars = correct_chars + incorrect_chars
        n = 0 + 23 * wpm + 89 * accuracy + 41 * time + 67 * correct_chars + 13 * incorrect_chars + 97 * total_chars
        
        # Step 2: Compute o (sum of charCode * (position + 1))
        o = 0
        for i in range(len(wallet_address)):
            o += ord(wallet_address[i]) * (i + 1)
        
        # Step 3: Update n with wallet address entropy
        n += 31 * o
        
        # Step 4: Compute c with magic constant and modulo
        result = float(0x178ba57548d) * float(n)
        max_safe_int = float(2**53 - 1)

        c = int(result % max_safe_int)
        
        # Step 5: Build raw string
        raw_string = f"{wallet_address.lower()}_{wpm}_{accuracy}_{time}_{correct_chars}_{incorrect_chars}_{c}"
        
        # Step 6: Compute SHA-256 hash
        encoded = raw_string.encode('utf-8')
        sha256_hash = hashlib.sha256(encoded).hexdigest()
        
        # Step 7: Return first 32 characters
        return sha256_hash[:32]

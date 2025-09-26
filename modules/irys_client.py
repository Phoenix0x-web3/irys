import asyncio
import hashlib
import random
import time

from loguru import logger

from data.settings import Settings
from libs.base import Base
from libs.eth_async.client import Client
from utils.browser import Browser
from utils.db_api.models import Wallet
from utils.db_api.wallet_api import add_count_game, get_wallet_by_address
from utils.resource_manager import ResourceManager
from utils.retry import async_retry


class Irys(Base):
    def __init__(self, client: Client, wallet: Wallet):
        super().__init__(client, wallet)
        self.proxy_errors = 0

    async def handle_arcade_game(self):
        arcade_games = ["snake", "asteroids", "hex-shooter", "missile-command"]
        random_sleep_games = {
            "snake": {"min": 60 * 4, "max": 60 * 8},
            "asteroids": {"min": 60 * 8, "max": 60 * 15},
            "hex-shooter": {"min": 60 * 10, "max": 60 * 25},
            "missile-command": {"min": 60 * 10, "max": 60 * 25},
        }
        random_score_games = {
            "snake": {"min": 300, "max": 1_100},
            "asteroids": {"min": 55_000, "max": 600_000},
            "hex-shooter": {"min": 25_000, "max": 75_000},
            "missile-command": {"min": 150_000, "max": 1_800_000},
        }
        random.shuffle(arcade_games)
        for game_type in arcade_games:
            random_playing_games = random.randint(Settings().random_irys_games_min, Settings().random_irys_games_max)
            logger.info(f"{self.wallet} will be play {random_playing_games} times in {game_type} Game in this hour")
            playing_game = 0
            errors_game = 0
            while True:
                if playing_game >= random_playing_games or errors_game >= Settings().retry:
                    break
                start_game = await self.start_arcade_game(game_type=game_type)
                if start_game:
                    errors_game = 0
                    random_sleep = random.randint(
                        random_sleep_games.get(game_type).get("min"), random_sleep_games.get(game_type).get("max")
                    )
                    score = random.randint(random_score_games.get(game_type).get("min"), random_score_games.get(game_type).get("max"))
                    logger.info(f"{self.wallet} play ~{int(random_sleep / 60)} minutes in {game_type} game with score: {score}")
                    await asyncio.sleep(random_sleep)
                    try:
                        await self.finish_game(score=score, session_id=start_game["data"]["sessionId"], game_type=game_type)
                    except Exception:
                        errors_game += 1
                        continue
                    playing_game += 1
                    random_sleep = random.randint(Settings().random_pause_between_actions_min, Settings().random_pause_between_actions_max)
                    logger.info(f"{self.wallet} sleep {random_sleep} seconds before next game")
                    await asyncio.sleep(random_sleep)
                else:
                    errors_game += 1
                    continue
        return True

    @async_retry()
    async def start_arcade_game(self, game_type: str):
        time_stamp = int(time.time() * 1000)
        message = f"I authorize payment of 0.001 IRYS to play a game on Irys Arcade.\n    \nPlayer: {self.wallet.address}\nAmount: 0.001 IRYS\nTimestamp: {time_stamp}\n\nThis signature confirms I own this wallet and authorize the payment."
        signature = await self.sign_message(text=message)
        headers = {
            "origin": "https://play.irys.xyz",
            "priority": "u=1, i",
            "referer": "https://play.irys.xyz/",
            "sec-ch-ua-mobile": "?0",
        }
        json_data = {
            "playerAddress": f"{self.wallet.address}",
            "gameCost": 0.001,
            "signature": f"{signature}",
            "message": f"{message}",
            "timestamp": time_stamp,
            "sessionId": f"game_{time_stamp}_{self.generate_random_string()}",
            "gameType": f"{game_type}",
        }
        logger.debug(json_data)
        start_game = await self.browser.post(url="https://play.irys.xyz/api/game/start", headers=headers, json=json_data, timeout=120)
        if not start_game:
            return False
        data = start_game.json()
        if start_game.status_code == 200 and data["success"]:
            logger.success(f"{self.wallet} success start play {game_type} game")
            return data
        else:
            logger.warning(f"{self.wallet} wrong with start play {game_type} game. Try again")
            logger.debug(f"{self.wallet} play status code {start_game.status_code} data: {data}")
        return False

    @async_retry()
    async def finish_game(self, score: int, session_id: str, game_type: str):
        time_stamp = int(time.time() * 1000)
        message = f"I completed a {game_type} game on Irys Arcade.\n    \nPlayer: {self.wallet.address}\nGame: {game_type}\nScore: {score}\nSession: {session_id}\nTimestamp: {time_stamp}\n\nThis signature confirms I own this wallet and completed this game."
        signature = await self.sign_message(text=message)
        headers = {
            "origin": "https://play.irys.xyz",
            "priority": "u=1, i",
            "referer": "https://play.irys.xyz/",
            "sec-ch-ua-mobile": "?0",
        }
        json_data = {
            "playerAddress": f"{self.wallet.address}",
            "gameType": f"{game_type}",
            "score": score,
            "signature": f"{signature}",
            "message": f"{message}",
            "timestamp": time_stamp,
            "sessionId": f"{session_id}",
        }
        logger.debug(json_data)
        start_game = await self.browser.post(url="https://play.irys.xyz/api/game/complete", headers=headers, json=json_data, timeout=120)
        if not start_game:
            return False
        data = start_game.json()
        if start_game.status_code == 200 and data["success"]:
            logger.success(f"{self.wallet} {game_type} {data['message']}")
            return data
        else:
            logger.debug(f"{self.wallet} play status code {start_game.status_code} data: {data}")
            raise Exception(f"Wrong with finish game {game_type} game. Status code: {start_game.status_code}")

    async def handle_spritetype_game(self):
        random_playing_games = random.randint(7, 10)
        logger.info(f"{self.wallet} will be play {random_playing_games} times in SpriteType in this hour")
        playing_game = 0
        errors_game = 0
        while True:
            if playing_game >= random_playing_games or errors_game >= 3:
                return True
            game = await self.complete_spritetype_game()
            if game:
                errors_game = 0
                playing_game += 1
                random_sleep = random.randint(Settings().random_pause_between_actions_min, Settings().random_pause_between_actions_max)
                logger.info(f"{self.wallet} sleep {random_sleep} seconds before next game")
                await asyncio.sleep(random_sleep)
            elif game == "Hour":
                return True
            else:
                errors_game += 1
                continue

    @async_retry()
    async def complete_spritetype_game(self):
        headers = {
            "origin": "https://spritetype.irys.xyz",
            "priority": "u=1, i",
            "referer": "https://spritetype.irys.xyz/",
            "sec-ch-ua-mobile": "?0",
        }
        stats = await self.generate_realistic_stats()
        logger.debug(stats)
        address = self.client.account.address
        wpm = stats["wpm"]
        accuracy = stats["accuracy"]
        time_stats = stats["time"]
        correct_chars = stats["correct_chars"]
        incorrect_chars = stats["incorrect_chars"]
        hash_result = await self.generate_anticheat_hash(
            wallet_address=address,
            wpm=wpm,
            accuracy=accuracy,
            time=time_stats,
            correct_chars=correct_chars,
            incorrect_chars=incorrect_chars,
        )
        logger.info(f"{self.wallet} play {time_stats} seconds in game")
        await asyncio.sleep(time_stats)
        json_data = {
            "walletAddress": address,
            "gameStats": {
                "wpm": wpm,
                "accuracy": accuracy,
                "time": time_stats,
                "correctChars": correct_chars,
                "incorrectChars": incorrect_chars,
                "progressData": [],
            },
            "antiCheatHash": hash_result,
            "timestamp": int(time.time() * 1000),
        }
        request = None
        try:
            request = await self.browser.post(url="https://spritetype.irys.xyz/api/submit-result", headers=headers, json=json_data)
        except Exception as e:
            logger.warning(f"{self.wallet} connection error during request")

            # Increment proxy error counter
            if "proxy" in str(e).lower() or "connection" in str(e).lower() or "connect" in str(e).lower():
                self.proxy_errors += 1

                # If proxy error limit exceeded, mark proxy as bad
                max_proxy_errors = 3
                if self.proxy_errors >= max_proxy_errors:
                    logger.warning(f"{self.wallet} proxy error limit exceeded ({self.proxy_errors}/{max_proxy_errors}), marking as BAD")

                    resource_manager = ResourceManager()
                    await resource_manager.mark_proxy_as_bad(self.wallet.address)

                    # If auto-replace is enabled, try to replace proxy
                    if Settings().auto_replace_proxy:
                        success, message = await resource_manager.replace_proxy(self.wallet.id)
                        if success:
                            logger.info(f"{self.wallet} proxy automatically replaced: {message}")
                            updated_user = get_wallet_by_address(address=self.wallet.address)
                            if updated_user:
                                self.wallet.proxy = updated_user.proxy
                                self.proxy_errors = 0
                                self.browser = Browser(self.wallet)
                        else:
                            logger.error(f"{self.wallet} failed to replace proxy: {message}")

        if not request:
            return False
        data = request.json()
        if request.status_code == 200 and data["success"]:
            logger.success(f"{self.wallet} success play game with {wpm} wpm")
            return add_count_game(address=self.wallet.address)
        elif "error" in data and "Hourly" in data["error"]:
            logger.warning(f"{self.wallet} already play in this hour more > 10 type games")
            return "Hour"
        else:
            logger.warning(f"{self.wallet} wrong with play game. Try again")
            logger.debug(f"{self.wallet} play status code {request.status_code} data: {data}")
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

        return {"wpm": wpm, "accuracy": accuracy, "time": time, "correct_chars": correct_chars, "incorrect_chars": incorrect_chars}

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
        result = float(0x178BA57548D) * float(n)
        max_safe_int = float(2**53 - 1)

        c = int(result % max_safe_int)

        # Step 5: Build raw string
        raw_string = f"{wallet_address.lower()}_{wpm}_{accuracy}_{time}_{correct_chars}_{incorrect_chars}_{c}"

        # Step 6: Compute SHA-256 hash
        encoded = raw_string.encode("utf-8")
        sha256_hash = hashlib.sha256(encoded).hexdigest()

        # Step 7: Return first 32 characters
        return sha256_hash[:32]

    def generate_random_string(self):
        """
        Generates a random string similar to Math.random().toString(36).substr(2, 9) in JavaScript.
        This creates a 9-character string using base-36 characters (0-9, a-z) from the fractional part of a random float.
        """
        r = random.random()
        base36 = "0123456789abcdefghijklmnopqrstuvwxyz"
        s = ""
        for _ in range(9):
            r *= 36
            digit = int(r)
            s += base36[digit]
            r -= digit
        return s

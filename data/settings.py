import sys

import yaml
from loguru import logger

from data.config import LOG_FILE, SETTINGS_FILE
from libs.eth_async.classes import Singleton


class Settings(Singleton):
    def __init__(self):
        with open(SETTINGS_FILE, "r") as file:
            json_data = yaml.safe_load(file) or {}

        self.check_git_updates = json_data.get("check_git_updates", True)
        self.private_key_encryption = json_data.get("private_key_encryption", False)
        self.threads = json_data.get("threads", 4)
        self.range_wallets_to_run = json_data.get("range_wallets_to_run", [])
        self.exact_wallets_to_run = json_data.get("exact_wallets_to_run", [])
        self.shuffle_wallets = json_data.get("shuffle_wallets", True)
        self.show_wallet_address_logs = json_data.get("show_wallet_address_logs", True)
        self.log_level = json_data.get("log_level", "INFO")
        self.random_pause_start_wallet_min = json_data.get("random_pause_start_wallet", {}).get("min")
        self.random_pause_start_wallet_max = json_data.get("random_pause_start_wallet", {}).get("max")
        self.random_pause_between_actions_min = json_data.get("random_pause_between_actions", {}).get("min")
        self.random_pause_between_actions_max = json_data.get("random_pause_between_actions", {}).get("max")
        self.random_pause_wallet_after_completion_sprite_types_game_min = json_data.get(
            "random_pause_wallet_after_completion_sprite_types_game", {}
        ).get("min")
        self.random_pause_wallet_after_completion_sprite_types_game_max = json_data.get(
            "random_pause_wallet_after_completion_sprite_types_game", {}
        ).get("max")
        self.random_pause_wallet_after_all_completion_min = json_data.get("random_pause_wallet_after_all_completion", {}).get("min")
        self.random_pause_wallet_after_all_completion_max = json_data.get("random_pause_wallet_after_all_completion", {}).get("max")
        self.capmonster_api_key = json_data.get("capmonster_api_key", "")
        self.network_for_bridge = json_data.get("network_for_bridge", [])
        self.auto_replace_proxy = json_data.get("auto_replace_proxy ", True)
        self.random_eth_for_bridge_min = json_data.get("random_eth_for_bridge", {}).get("min")
        self.random_eth_for_bridge_max = json_data.get("random_eth_for_bridge", {}).get("max")
        self.random_irys_games_min = json_data.get("random_irys_games", {}).get("min")
        self.random_irys_games_max = json_data.get("random_irys_games", {}).get("max")

        self.retry = json_data.get("retry", 3)
        self.multiple_mint = json_data.get("multiple_mint", False)


# Configure the logger based on the settings
settings = Settings()

if settings.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
    raise ValueError(f"Invalid log level: {settings.log_level}. Must be one of: DEBUG, INFO, WARNING, ERROR")
logger.remove()  # Remove the default logger
logger.add(sys.stderr, level=settings.log_level)

logger.add(LOG_FILE, level="DEBUG")
